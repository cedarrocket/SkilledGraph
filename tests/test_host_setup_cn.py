"""First-run setup stays local; all credentials here are synthetic."""
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from sgraph_chat_host.host_config_cn import model_options, parse_headers
from sgraph_chat_host.host_locales_cn import language
from sgraph_chat_host.host_setup_cn import config_path, load_profile, run_setup, save_profile


class Terminal(io.StringIO):
    def isatty(self):
        return True


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "config" / "host.json"

    def setup(self, lines, env=None):
        self.output = io.StringIO()
        return run_setup(input_stream=Terminal(lines), error_stream=self.output,
                         environ={} if env is None else env, path=self.path)

    def test_wizard_roundtrip_and_permissions(self):
        profile = self.setup('https://gateway.test/v1\nmodel-one\n2\ndummy-secret\n{"X-Session-ID":"session-one"}\n', {"LANG": "zh_CN.UTF-8"})
        self.assertEqual(profile, load_profile(self.path))
        self.assertEqual(profile["model"], "openai:model-one")
        self.assertTrue(profile["options"]["use_responses_api"])
        self.assertEqual(profile["options"]["default_headers"], {"X-Session-ID": "session-one"})
        self.assertIn("初始化", self.output.getvalue())
        self.assertNotIn("dummy-secret", self.output.getvalue())
        self.assertNotIn("session-one", self.output.getvalue())
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)

    def test_environment_key_reuse_is_not_copied_to_disk(self):
        profile = self.setup('\nlocal-model\n\n\n\n', {"OPENAI_API_KEY": "environment-secret"})
        self.assertEqual(profile["options"], {"base_url": "https://api.openai.com/v1", "use_responses_api": False})
        self.assertNotIn("environment-secret", self.path.read_text(encoding="utf-8"))

    def test_invalid_values_reprompt_without_echo(self):
        profile = self.setup('bad-url\nhttp://localhost:1234/v1\n\nlocal\n9\n1\n\nnot-needed\n{"X":"bad-secret\\n"}\n{}\n')
        self.assertEqual(profile["model"], "openai:local")
        self.assertIn("Invalid", self.output.getvalue())
        self.assertNotIn("bad-secret", self.output.getvalue())

    def test_eof_leaves_existing_config_untouched(self):
        profile = self.setup('\nmodel\n\ndummy\n\n')
        with self.assertRaisesRegex(ValueError, "cancelled"):
            self.setup('\n')
        self.assertEqual(load_profile(self.path), profile)

    def test_keyboard_interrupt_leaves_no_config(self):
        from contextlib import contextmanager
        @contextmanager
        def reader(*args):
            def read(*args, **kwargs):
                raise KeyboardInterrupt
            yield read
        with patch("sgraph_chat_host.terminal_cn.terminal_reader", reader), self.assertRaises(KeyboardInterrupt):
            self.setup("")
        self.assertFalse(self.path.exists())

    def test_pipe_does_not_prompt_or_consume_input(self):
        source = io.StringIO("graph input")
        with self.assertRaisesRegex(ValueError, "SGRAPH_MODEL"):
            run_setup(input_stream=source, environ={}, path=self.path)
        self.assertEqual(source.read(), "graph input")
        self.assertFalse(self.path.exists())

    def test_locale_precedence_and_fallback(self):
        for env, expected in (({"LANG": "zh-TW"}, "zh"), ({"LANG": "zh_CN", "LC_ALL": "C"}, "en"),
                              ({"LANG": "en_US", "LC_MESSAGES": "zh_CN"}, "zh"),
                              ({"SGRAPH_LANGUAGE": "en", "LC_ALL": "zh_CN"}, "en"), ({"LANG": "de_DE"}, "en")):
            self.assertEqual(language(env), expected)

    def test_config_path_override_and_xdg(self):
        self.assertEqual(config_path({"SGRAPH_HOST_CONFIG": str(self.path)}), self.path)
        self.assertEqual(config_path({"XDG_CONFIG_HOME": str(self.path.parent)}), self.path.parent / "skilledgraph/host.json")

    def test_corrupt_config_does_not_echo_contents(self):
        self.path.parent.mkdir()
        self.path.write_text('{"secret":"hidden-value",broken', encoding="utf-8")
        with self.assertRaises(ValueError) as caught:
            load_profile(self.path)
        self.assertNotIn("hidden-value", str(caught.exception))
        self.assertIn("--setup", str(caught.exception))
        self.path.write_bytes(b"\xffhidden-value")
        with self.assertRaises(ValueError) as caught:
            load_profile(self.path)
        self.assertNotIn("hidden-value", str(caught.exception))

    def test_headers_validation_and_environment_override(self):
        for headers in ('{"Bad Name":"secret"}', '{"X":"secret\\r\\n"}', '["secret"]', '{"X":1}', '{"X":"one","x":"two"}'):
            with self.assertRaises(ValueError):
                parse_headers(headers)
        self.assertEqual(model_options(base_dir=self.path.parent, environ={"SGRAPH_HEADERS_JSON": '{"X":"ok"}'}),
                         {"default_headers": {"X": "ok"}})

    def test_main_uses_saved_profile_and_environment_selection_bypasses_it(self):
        try:
            from sgraph_chat_host.host_cn import main
        except ImportError:
            self.skipTest("requires runtime extra")
        profile = self.setup('\nmodel\n\ndummy\n\n')
        graph_path = self.path.parent / "graph.md"
        graph_path.write_text("# [Node] A\nHello\n", encoding="utf-8")
        with patch.dict(os.environ, {"SGRAPH_HOST_CONFIG": str(self.path)}, clear=True), \
             patch("sgraph_chat_host.host_cn.create_model") as create, \
             patch("sgraph_chat_host.host_cn.load_graph"), patch("sgraph_chat_host.host_cn.run_chat", return_value=0):
            self.assertEqual(main(graph_path, []), 0)
            create.assert_called_with(profile["model"], base_dir=graph_path.parent, connection_options=profile["options"])
            self.path.write_text("broken", encoding="utf-8")
            with patch.dict(os.environ, {"SGRAPH_MODEL": "deepseek:test"}):
                self.assertEqual(main(graph_path, []), 0)
                create.assert_called_with("deepseek:test", None, base_dir=graph_path.parent)

    def test_main_auto_setup_and_explicit_setup_exit(self):
        try:
            from sgraph_chat_host.host_cn import main
        except ImportError:
            self.skipTest("requires runtime extra")
        graph_path = Path(self.temp.name) / "graph.md"
        graph_path.write_text("# [Node] A\nHello\n", encoding="utf-8")
        profile = {"version": 1, "model": "openai:demo", "options": {
            "base_url": "http://localhost/v1", "use_responses_api": False}}
        with patch.dict(os.environ, {}, clear=True), patch("sgraph_chat_host.host_setup_cn.load_profile", return_value=None), \
             patch("sgraph_chat_host.host_setup_cn.run_setup", return_value=profile) as setup, \
             patch("sgraph_chat_host.host_cn.create_model") as create, patch("sgraph_chat_host.host_cn.load_graph"), \
             patch("sgraph_chat_host.host_cn.run_chat", return_value=0):
            self.assertEqual(main(graph_path, []), 0)
            setup.assert_called_once()
            create.assert_called_once()
            create.reset_mock()
            self.assertEqual(main(graph_path, ["--setup"]), 0)
            create.assert_not_called()

    def test_environment_connection_options_override_saved_values(self):
        try:
            from sgraph_chat_host.host_cn import create_model
            import langchain.chat_models
        except ImportError:
            self.skipTest("requires chat extra")
        saved = {"base_url": "https://saved.test/v1", "api_key": "saved", "use_responses_api": False,
                 "default_headers": {"X": "saved"}}
        with patch.dict(os.environ, {"SGRAPH_API_KEY": "env", "SGRAPH_HEADERS_JSON": '{"X":"env"}'}, clear=True), \
             patch("langchain.chat_models.init_chat_model") as init:
            create_model("openai:demo", base_dir=self.path.parent, connection_options=saved)
            init.assert_called_once_with("openai:demo", base_url="https://saved.test/v1", api_key="env",
                                         default_headers={"X": "env"}, use_responses_api=False)
        self.assertEqual(saved["api_key"], "saved")

    def test_chat_and_responses_real_client_build_correct_requests(self):
        try:
            import httpx
            import langchain_openai
            from sgraph_chat_host.host_cn import create_model
        except ImportError:
            self.skipTest("requires chat extra")
        for responses in (False, True):
            with self.subTest(responses=responses):
                captured = []
                def handler(request):
                    captured.append(request)
                    if responses:
                        data = {"id": "resp-local", "object": "response", "created_at": 0, "status": "completed",
                                "model": "demo", "output": [{"id": "msg-local", "type": "message", "role": "assistant",
                                    "status": "completed", "content": [{"type": "output_text", "text": "connected", "annotations": []}]}],
                                "parallel_tool_calls": True, "tool_choice": "auto", "tools": [], "error": None}
                    else:
                        data = {"id": "chatcmpl-local", "object": "chat.completion", "created": 0, "model": "demo",
                                "choices": [{"index": 0, "message": {"role": "assistant", "content": "connected"}, "finish_reason": "stop"}]}
                    return httpx.Response(200, json=data)
                with httpx.Client(transport=httpx.MockTransport(handler)) as client, patch.dict(os.environ, {}, clear=True):
                    model = create_model("openai:demo", base_dir=self.path.parent, connection_options={
                        "base_url": "https://gateway.test/v1", "api_key": "dummy", "use_responses_api": responses,
                        "default_headers": {"X-Session-ID": "session-local"}, "http_client": client})
                    self.assertEqual(model.invoke("hello").text, "connected")
                self.assertEqual(len(captured), 1)
                self.assertEqual(captured[0].url.path, "/v1/responses" if responses else "/v1/chat/completions")
                self.assertEqual(captured[0].headers["X-Session-ID"], "session-local")
                self.assertEqual(captured[0].headers["Authorization"], "Bearer dummy")

    @unittest.skipUnless(os.name == "posix", "requires PTY")
    def test_cli_setup_real_terminal_masks_credentials_and_exits(self):
        try:
            import langchain_core
        except ImportError:
            self.skipTest("requires runtime extra")
        import pty
        import select
        import subprocess
        import sys
        import time
        root = Path(__file__).resolve().parents[1]
        master, slave = pty.openpty()
        self.addCleanup(os.close, master)
        env = {k: v for k, v in os.environ.items() if not k.startswith("SGRAPH_")}
        env.update(SGRAPH_HOST_CONFIG=str(self.path), SGRAPH_LANGUAGE="en", TERM="xterm", PROMPT_TOOLKIT_NO_CPR="1")
        proc = subprocess.Popen([sys.executable, "-m", "skilledgraph", str(root / "examples/01-assistant/workflow_cn.md"),
                                 "--", "--setup"], stdin=slave, stdout=slave, stderr=slave, env=env)
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
        for prompt, answer in ((b"API base URL", b"\r"), (b"Model ID", b"demo\r"),
                               (b"Chat Completions", b"1\r"), (b"API key", b"dummy-secret\r"),
                               (b"Extra HTTP headers", b'{"X-Session-ID":"header-secret"}\r')):
            until(prompt)
            # Wait until the prompt has rendered its final separator before
            # sending keys so they cannot be echoed by the terminal driver.
            time.sleep(0.05)
            os.write(master, answer)
        until(b"Saved.")
        self.assertEqual(proc.wait(timeout=10), 0)
        self.assertNotIn(b"dummy-secret", transcript)
        self.assertNotIn(b"header-secret", transcript)
        self.assertEqual(load_profile(self.path)["model"], "openai:demo")

    def test_go_real_client_reuses_session_and_new_model_gets_new_session(self):
        try:
            import httpx
            from sgraph_chat_host.host_cn import create_model
            import langchain_openai
        except ImportError:
            self.skipTest("requires chat extra")
        captured = []
        def handle(request):
            captured.append(dict(request.headers))
            return httpx.Response(200, json={"id": "chatcmpl-demo", "object": "chat.completion", "created": 0,
                "model": "demo", "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}]})
        with httpx.Client(transport=httpx.MockTransport(handle)) as client, patch.dict(os.environ, {}, clear=True):
            options = {"api_key": "dummy", "base_url": "https://opencode.ai/zen/go/v1", "http_client": client,
                       "use_responses_api": False}
            model = create_model("openai:demo", base_dir=self.path.parent, connection_options=options)
            model.invoke("one")
            model.invoke("two")
            other = create_model("openai:demo", base_dir=self.path.parent, connection_options=options)
            other.invoke("three")
        self.assertEqual(captured[0]["x-opencode-session"], captured[1]["x-opencode-session"])
        self.assertNotEqual(captured[0]["x-opencode-session"], captured[2]["x-opencode-session"])
        self.assertEqual(captured[0]["user-agent"], "sgraph-harness-agent/0.1.0.dev0")
        self.assertNotIn("default_headers", options)
