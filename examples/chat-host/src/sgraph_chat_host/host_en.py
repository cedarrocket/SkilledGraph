"""A small synchronous chat Host. Configuration belongs here, not in the DSL."""

import argparse
import json
import os
from pathlib import Path
import sys
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, convert_to_messages

from skilledgraph import load_graph, parse_graph
from skilledgraph.binding import load_file_object
from .host_config_en import model_options, opencode_go_options
from .terminal_en import terminal_reader


def create_model(model_name=None, factory=None, *, base_dir: Path, connection_options=None):
    if factory:
        prefix, separator, payload = factory.partition(":")
        if prefix != "python" or not separator:
            raise ValueError("Model factory must use python:FILE:ENTRY")
        # This is an explicitly selected Host factory, not Schema auto-detection.
        return load_file_object(payload, base_dir=base_dir)()
    if not model_name:
        raise ValueError("Set SGRAPH_MODEL=provider:model, pass --model, or select --model-factory python:FILE:ENTRY")
    try:
        from langchain.chat_models import init_chat_model
    except ImportError as exc:
        raise ImportError("Model initialization requires skilledgraph[chat] and your provider's integration package") from exc
    options = dict(connection_options or {})
    options.update(model_options(base_dir=base_dir))
    options = opencode_go_options(options, base_url=os.environ.get("OPENAI_BASE_URL")
                                  if model_name.startswith("openai:") else None)
    return init_chat_model(model_name, **options)


def run_chat(graph, *, input_stream=None, output_stream=None, error_stream=None):
    """Run one graph execution, collecting string replies to dynamic interrupts.

    Callers supplying a compiled graph must enable its checkpointer to resume.
    Each call gets a fresh thread; checkpoints are not conversation memory.
    """
    from langgraph.types import Command

    input_stream = sys.stdin if input_stream is None else input_stream
    output_stream = sys.stdout if output_stream is None else output_stream
    error_stream = sys.stderr if error_stream is None else error_stream
    interactive = input_stream.isatty()
    config = {"configurable": {"thread_id": str(uuid4())}}

    def run(text, read=None):
        graph_input = {"messages": [HumanMessage(content=text)]}
        shown_messages = []
        while True:
            pending = {}
            interrupted = False
            for namespace, update in graph.stream(graph_input, config=config, stream_mode="updates", subgraphs=True):
                if "__interrupt__" in update:
                    interrupted = True
                    pending.update((item.id, item) for item in update["__interrupt__"])
                for node, state_update in update.items():
                    if node == "__interrupt__" or not isinstance(state_update, dict):
                        continue
                    messages = state_update.get("messages", [])
                    if messages is None:
                        continue
                    if not isinstance(messages, list):
                        messages = [messages]
                    for message in convert_to_messages(messages):
                        if isinstance(message, AIMessage):
                            # Subgraph boundary updates repeat already streamed messages.
                            # 子图返回会再次携带已显示的消息，按消息 ID 去重。
                            # Native reducers may assign IDs after an update is emitted.
                            # 原生 reducer 可能在更新输出后才赋予消息 ID。
                            if any((old is message or (message.id is not None and old.id == message.id))
                                   and text == message.text for old, text in shown_messages):
                                continue
                            shown_messages.append((message, message.text))
                            label = " / ".join([part.split(":", 1)[0] for part in namespace] + [node])
                            print(f"[{label}] {message.text}", file=output_stream, flush=True)
            if not interrupted:
                return 0
            for item in pending.values():
                value = item.value if isinstance(item.value, str) else json.dumps(item.value, ensure_ascii=False)
                print(f"[Interrupt] {value}", file=error_stream, flush=True)
            if read is None:
                raise RuntimeError("Graph interrupted; piped input cannot supply replies. Use an interactive terminal or custom Host.")
            if not pending:
                raise RuntimeError("Static breakpoint requires a custom Host/native API; basic Host supports dynamic interrupt() only")
            if not graph.checkpointer:
                raise RuntimeError("Interrupt resume requires a graph compiled with a checkpointer")
            replies = {}
            try:
                for item in pending.values():
                    if len(pending) > 1:
                        print(f"[Reply] {item.value}", file=error_stream, flush=True)
                    replies[item.id] = read("Resume> ")
            except EOFError:
                print("Interrupted run cancelled at EOF; no resume value submitted.", file=error_stream)
                return 1
            graph_input = Command(resume=replies)

    if not interactive:
        text = input_stream.read()
        return run(text) if text else 0
    with terminal_reader(input_stream, error_stream) as read:
        try:
            text = read("> ")
        except EOFError:
            return 0
        return run(text, read) if text.strip() else 0


def main(graph_path: Path, argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog=f"sgraph {graph_path.name} --", description="Basic chat Host; reads one input, runs the graph once, then exits.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--model", help="LangChain provider:model (or SGRAPH_MODEL)")
    group.add_argument("--model-factory", help="python:FILE:ENTRY factory (or SGRAPH_MODEL_FACTORY); paths relative to the graph")
    group.add_argument("--setup", action="store_true", help="configure an OpenAI-compatible API interactively, then exit")
    args = parser.parse_args(argv)
    if args.model or args.model_factory:
        model_name, factory = args.model, args.model_factory
    else:
        model_name = os.environ.get("SGRAPH_MODEL")
        factory = os.environ.get("SGRAPH_MODEL_FACTORY")
    from .host_setup_en import load_profile, run_setup
    if args.setup:
        run_setup()
        return 0
    if model_name or factory:
        model = create_model(model_name, factory, base_dir=graph_path.parent)
    else:
        profile = load_profile()
        if profile is None:
            profile = run_setup()
        model = create_model(profile["model"], base_dir=graph_path.parent,
                             connection_options=profile["options"])
    from langgraph.checkpoint.memory import InMemorySaver
    spec = parse_graph(graph_path)
    from skilledgraph import TraceRecorder
    recorder = TraceRecorder()
    graph = load_graph(spec, model=model, trace=recorder,
                       compile_kwargs={"checkpointer": InMemorySaver()})
    try:
        return run_chat(graph)
    finally:
        if recorder.events:
            print("[Trace]\n" + (recorder.render() or "No nodes executed."), file=sys.stderr)
