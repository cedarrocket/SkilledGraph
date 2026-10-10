import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

try:
    import langgraph
    from langchain_core.messages import AIMessage
except ImportError:
    raise unittest.SkipTest("requires runtime extra")

from skilledgraph import load_graph
from skilledgraph.cli import launch, main
from sgraph_chat_host.host import create_model, run_chat
from tests.test_execution import Model

ROOT = Path(__file__).resolve().parents[1]


class Terminal(io.StringIO):
    def isatty(self):
        return True


class HostTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.path = self.directory / "graph.md"
        self.path.write_text("# [Node] A\nHello\n## [Transitions]\n- @Default -> @End\n", encoding="utf-8")

    def test_terminal_runs_once_and_leaves_next_line_unread(self):
        model = Model()
        graph = load_graph(self.path, model=model)
        output = io.StringIO()
        input_stream = Terminal("first\nsecond\n")
        run_chat(graph, input_stream=input_stream, output_stream=output, error_stream=io.StringIO())
        self.assertEqual(input_stream.read(), "second\n")
        self.assertEqual([[m.content for m in call[1:]] for call in model.calls], [["first"]])
        self.assertEqual(output.getvalue(), "[A] answer\n")

    def test_pipe_is_one_input_and_all_replies_displayed(self):
        model = Model()
        graph = load_graph(ROOT / "examples/02-chain/workflow.md", model=model)
        output = io.StringIO()
        run_chat(graph, input_stream=io.StringIO("first\nsecond\n"), output_stream=output)
        self.assertEqual(model.calls[0][1].content, "first\nsecond\n")
        self.assertIn("[Analyze] answer", output.getvalue())
        self.assertIn("[Report] answer", output.getvalue())

    def test_route_key_displayed(self):
        graph = load_graph(self.path, model=Model("key"))
        output = io.StringIO()
        run_chat(graph, input_stream=io.StringIO("input"), output_stream=output)
        self.assertIn("key", output.getvalue())

    def test_custom_host_receives_absolute_path_and_argv_without_build(self):
        self.path.write_text("# [Config]\n- **@host**: python:./host.py:main\n- **@state**: python:./missing.py:State\n# [Node] A\n- **@uses**: nonexistent:any\n", encoding="utf-8")
        (self.directory / "host.py").write_text('def main(graph_path, argv):\n    assert graph_path.is_absolute()\n    assert graph_path.name == "graph.md"\n    assert argv == ["--custom", "value"]\n    return 7\n', encoding="utf-8")
        self.assertEqual(launch([str(self.path), "--", "--custom", "value"]), 7)

    def test_check_never_imports_host(self):
        self.path.write_text("# [Config]\n- **@host**: python:./missing.py:main\n# [Node] A\n", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(launch(["--check", str(self.path)]), 0)

    def test_end_to_end_module_cli_factory_and_pipe(self):
        (self.directory / "model.py").write_text('from langchain_core.messages import AIMessage\nclass Model:\n    def invoke(self, messages, config=None):\n        return AIMessage(content="echo:" + messages[-1].content)\ndef create():\n    return Model()\n', encoding="utf-8")
        result = subprocess.run([sys.executable, "-m", "skilledgraph", str(self.path), "--", "--model-factory", "python:./model.py:create"], input="hello", capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "[A] echo:hello\n")

    def test_missing_model_is_clear(self):
        with self.assertRaisesRegex(ValueError, "SGRAPH_MODEL"):
            create_model(base_dir=self.directory)

    def test_provider_initialization_delegated_to_langchain(self):
        try:
            import langchain.chat_models
        except ImportError:
            self.skipTest("requires chat extra")
        with patch("langchain.chat_models.init_chat_model") as init:
            create_model("provider:model", base_dir=self.directory)
            init.assert_called_once_with("provider:model")

    def test_environment_factory_and_explicit_option_precedence(self):
        from sgraph_chat_host.host import main as host_main
        with patch.dict(os.environ, {"SGRAPH_MODEL_FACTORY": "python:./env.py:create", "SGRAPH_MODEL": "env:model"}), patch("sgraph_chat_host.host.create_model", return_value=Model()) as create, patch("sgraph_chat_host.host.run_chat", return_value=0):
            self.assertEqual(host_main(self.path, []), 0)
            create.assert_called_with("env:model", "python:./env.py:create", base_dir=self.directory)
            self.assertEqual(host_main(self.path, ["--model", "explicit:model"]), 0)
            create.assert_called_with("explicit:model", None, base_dir=self.directory)

    def test_host_failure_exit_codes(self):
        with contextlib.redirect_stderr(io.StringIO()) as output:
            self.assertEqual(main([str(self.directory / "missing.md")]), 1)
        self.assertIn("missing.md", output.getvalue())
        with patch("skilledgraph.cli.launch", side_effect=KeyboardInterrupt):
            self.assertEqual(main([]), 130)

    def test_invalid_host_return(self):
        self.path.write_text("# [Config]\n- **@host**: python:./host.py:main\n# [Node] A\n", encoding="utf-8")
        (self.directory / "host.py").write_text('def main(path, argv):\n    return "invalid"\n', encoding="utf-8")
        with self.assertRaisesRegex(TypeError, "exit code"):
            launch([str(self.path)])


    def test_custom_state_example_cli_without_model(self):
        result = subprocess.run([sys.executable, "-m", "skilledgraph", str(ROOT / "examples/09-state-only/workflow.md")], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("'value': 2", result.stdout)
        self.assertIn("'doubled'", result.stdout)

    def test_help_does_not_require_model(self):
        result = subprocess.run([sys.executable, "-m", "skilledgraph", str(self.path), "--", "--help"], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0)
        self.assertIn("--model-factory", result.stdout)


    def test_native_message_representations_are_displayed(self):
        self.path.write_text("# [Node] A\n- **@uses**: custom:any\n", encoding="utf-8")
        def bind(payload, **kwargs):
            return lambda state: {"messages": [("assistant", "tuple reply"), {"role": "assistant", "content": "dict reply"}]}
        graph = load_graph(self.path, bindings={"custom": bind})
        output = io.StringIO()
        run_chat(graph, input_stream=io.StringIO("input"), output_stream=output)
        self.assertEqual(output.getvalue(), "[A] tuple reply\n[A] dict reply\n")

    def test_connection_options_are_forwarded(self):
        try:
            import langchain.chat_models
        except ImportError:
            self.skipTest("requires chat extra")
        (self.directory / "key.txt").write_text("dummy\n", encoding="utf-8")
        with patch.dict(os.environ, {"SGRAPH_API_KEY_FILE": "key.txt", "SGRAPH_BASE_URL": "https://example.test", "SGRAPH_TEMPERATURE": "0"}, clear=True), patch("langchain.chat_models.init_chat_model") as init:
            create_model("deepseek:deepseek-chat", base_dir=self.directory)
            init.assert_called_once_with("deepseek:deepseek-chat", api_key="dummy", base_url="https://example.test", temperature=0.0)

    def test_factory_owns_configuration(self):
        (self.directory / "model.py").write_text('def create():\n    return "factory model"\n', encoding="utf-8")
        with patch.dict(os.environ, {"SGRAPH_API_KEY_FILE": "missing.txt"}):
            self.assertEqual(create_model(factory="python:./model.py:create", base_dir=self.directory), "factory model")


    def test_empty_terminal_input_exits_without_invoking(self):
        for text in ("", "\n"):
            model = Model()
            graph = load_graph(self.path, model=model)
            self.assertEqual(run_chat(graph, input_stream=Terminal(text), output_stream=io.StringIO(),
                                      error_stream=io.StringIO()), 0)
            self.assertEqual(model.calls, [])

    def interrupt_graph(self):
        from langgraph.checkpoint.memory import InMemorySaver
        self.path.write_text("# [Node] Ask\n- **@uses**: python:./ask.py:ask\n## [Transitions]\n- @Default -> Report\n# [Node] Report\nReply\n## [Transitions]\n- @Default -> @End\n", encoding="utf-8")
        (self.directory / "ask.py").write_text('from langgraph.types import interrupt\ndef ask(state):\n    first = interrupt("first?")\n    second = interrupt({"question": "second?"})\n    return {"messages": [("human", first + ":" + second)]}\n', encoding="utf-8")
        model = Model()
        graph = load_graph(self.path, model=model, compile_kwargs={"checkpointer": InMemorySaver()})
        return graph, model

    def test_two_interrupts_resume_and_run_finishes_once(self):
        graph, model = self.interrupt_graph()
        output, errors = io.StringIO(), io.StringIO()
        stream = Terminal("initial\nyes\nno\nunused\n")
        self.assertEqual(run_chat(graph, input_stream=stream, output_stream=output, error_stream=errors), 0)
        self.assertEqual(stream.read(), "unused\n")
        self.assertEqual(len(model.calls), 1)
        self.assertEqual([m.content for m in model.calls[0][1:]], ["initial", "yes:no"])
        self.assertEqual(output.getvalue(), "[Report] answer\n")
        self.assertIn('second?', errors.getvalue())

    def test_interrupt_eof_cancels_without_model_invocation(self):
        graph, model = self.interrupt_graph()
        self.assertEqual(run_chat(graph, input_stream=Terminal("initial\n"),
                                  output_stream=io.StringIO(), error_stream=io.StringIO()), 1)
        self.assertEqual(model.calls, [])

    def test_pipe_interrupt_is_clear_and_does_not_resume(self):
        graph, model = self.interrupt_graph()
        with self.assertRaisesRegex(RuntimeError, "piped input"):
            run_chat(graph, input_stream=io.StringIO("initial"), error_stream=io.StringIO())
        self.assertEqual(model.calls, [])

    def test_interrupt_empty_reply_is_a_value(self):
        graph, model = self.interrupt_graph()
        self.assertEqual(run_chat(graph, input_stream=Terminal("initial\n\nno\n"),
                                  output_stream=io.StringIO(), error_stream=io.StringIO()), 0)
        self.assertEqual(model.calls[0][-1].content, ":no")

    def test_host_runs_have_separate_threads(self):
        graph, model = self.interrupt_graph()
        for text in ("one", "two"):
            run_chat(graph, input_stream=Terminal(text + "\na\nb\n"),
                     output_stream=io.StringIO(), error_stream=io.StringIO())
        self.assertEqual([[m.content for m in call[1:]] for call in model.calls],
                         [["one", "a:b"], ["two", "a:b"]])

    @unittest.skipUnless(os.name == "posix", "requires PTY")
    def test_cli_terminal_editing_and_interrupt_resume(self):
        import pty
        import select
        import time
        master, slave = pty.openpty()
        self.addCleanup(os.close, master)
        env = dict(os.environ, TERM="xterm", PROMPT_TOOLKIT_NO_CPR="1")
        proc = subprocess.Popen([sys.executable, "-m", "skilledgraph",
            str(ROOT / "examples/11-interrupt/workflow.md"), "--", "--model-factory",
            "python:../support/demo_model.py:create"], stdin=slave, stdout=slave, stderr=slave, env=env)
        os.close(slave)
        self.addCleanup(lambda: proc.poll() is None and proc.kill())
        transcript = bytearray()
        def until(needle):
            deadline = time.monotonic() + 15
            while needle not in transcript:
                if time.monotonic() > deadline:
                    self.fail(repr(bytes(transcript)))
                if select.select([master], [], [], 0.1)[0]:
                    try:
                        transcript.extend(os.read(master, 65536))
                    except OSError:
                        self.fail(repr(bytes(transcript)))
        until(b">")
        os.write(master, b"hello\r")
        until(b"Resume>")
        # Move left twice, delete the wrong character, insert the correction.
        os.write(master, b"abXd\x1b[D\x1b[D\x1b[3~c\r")
        until(b"Offline demo: abcd")
        self.assertEqual(proc.wait(timeout=10), 0, bytes(transcript))

    def test_parallel_interrupts_receive_their_own_replies(self):
        from langgraph.graph import StateGraph, MessagesState, START, END
        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.types import interrupt
        def left(state):
            return {"messages": [("assistant", "left:" + interrupt("left?"))]}
        def right(state):
            return {"messages": [("assistant", "right:" + interrupt("right?"))]}
        builder = StateGraph(MessagesState)
        builder.add_node("left", left).add_node("right", right)
        builder.add_edge(START, "left").add_edge(START, "right")
        builder.add_edge("left", END).add_edge("right", END)
        graph = builder.compile(checkpointer=InMemorySaver())
        output, errors = io.StringIO(), io.StringIO()
        @contextlib.contextmanager
        def reader(*args):
            def read(prompt):
                if prompt == "> ":
                    return "initial"
                # Interrupt delivery order is native and not guaranteed. Reply
                # to the question actually displayed, not its completion order.
                return "L" if errors.getvalue().splitlines()[-1] == "[Reply] left?" else "R"
            yield read
        with patch("sgraph_chat_host.host.terminal_reader", reader):
            run_chat(graph, input_stream=Terminal(""), output_stream=output, error_stream=errors)
        self.assertIn("[left] left:L", output.getvalue())
        self.assertIn("[right] right:R", output.getvalue())

    def test_tool_interrupt_resumes_native_tool_node(self):
        from langchain_core.tools import tool
        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.types import interrupt
        @tool
        def confirm() -> str:
            """Ask for confirmation."""
            return interrupt("tool approval?")
        self.path.write_text("# [Node] Request\n- **@uses**: custom:request\n## [Transitions]\n- @Default -> Exec\n# [ToolNode] Exec\n- **@tools**: all\n## [Transitions]\n- @Default -> Report\n# [Node] Report\nReport tool result\n## [Transitions]\n- @Default -> @End\n", encoding="utf-8")
        def bind(payload, **kwargs):
            return lambda state: {"messages": [AIMessage(content="", tool_calls=[
                {"name": "confirm", "args": {}, "id": "call-confirm", "type": "tool_call"}])]}
        model = Model()
        graph = load_graph(self.path, model=model, tools=[confirm], bindings={"custom": bind},
                           compile_kwargs={"checkpointer": InMemorySaver()})
        output = io.StringIO()
        run_chat(graph, input_stream=Terminal("initial\napproved\n"), output_stream=output, error_stream=io.StringIO())
        self.assertIn("[Report] answer", output.getvalue())
        self.assertEqual(model.calls[0][-1].content, "approved")
        self.assertEqual(model.calls[0][-1].tool_call_id, "call-confirm")

    def test_static_breakpoint_requires_custom_host(self):
        from langgraph.checkpoint.memory import InMemorySaver
        graph = load_graph(self.path, model=Model(), compile_kwargs={
            "checkpointer": InMemorySaver(), "interrupt_before": ["A"]})
        with self.assertRaisesRegex(RuntimeError, "Static breakpoint"):
            run_chat(graph, input_stream=Terminal("initial\n"), error_stream=io.StringIO())
