"""Small reusable CLI helpers for practical examples, not a graph framework."""
import argparse
import os
from pathlib import Path
import sys
from uuid import uuid4

from langgraph.types import Command
from sgraph_chat_host.host_cn import create_model
from sgraph_chat_host.host_setup_cn import load_profile, run_setup
from sgraph_chat_host.terminal_cn import terminal_reader


class DemoModel:
    """Deterministic plumbing demo; it is not an LLM or an evaluation of quality."""
    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    def invoke(self, messages, config=None):
        self.calls.append(list(messages))
        return self.reply(messages)

    async def ainvoke(self, messages, config=None):
        return self.invoke(messages, config)

    def bind_tools(self, tools, **kwargs):
        return self


def arguments(argv, description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--demo", action="store_true", help="offline deterministic sample, no API")
    parser.add_argument("--model", help="LangChain provider:model; otherwise use environment/saved Host configuration")
    parser.add_argument("--input", help="initial request; otherwise read stdin")
    parser.add_argument("--data", type=Path, help="source file or directory (see example README)")
    parser.add_argument("--approval", help="explicit interrupt response, e.g. yes or no")
    parser.add_argument("--output", type=Path, help="output directory for email drafts")
    return parser.parse_args(argv)


def model_for(graph_path, args, reply):
    if args.demo:
        print("[Offline demo: scripted model, not an LLM]", file=sys.stderr)
        return DemoModel(reply)
    name = args.model or os.environ.get("SGRAPH_MODEL")
    factory = None if args.model else os.environ.get("SGRAPH_MODEL_FACTORY")
    if name or factory:
        return create_model(name, factory, base_dir=graph_path.parent)
    profile = load_profile() or run_setup()
    return create_model(profile["model"], base_dir=graph_path.parent, connection_options=profile["options"])


def request_text(args, default):
    if args.input is not None:
        return args.input
    if args.demo:
        return default
    if sys.stdin.isatty():
        with terminal_reader(sys.stdin, sys.stderr) as read:
            try:
                return read("> ")
            except EOFError:
                return ""
    return sys.stdin.read()


def execute(graph, initial, *, approval=None):
    """Drive one native invocation with optional explicit interrupt replies."""
    config = {"configurable": {"thread_id": str(uuid4())}, "recursion_limit": 40}
    result = graph.invoke(initial, config)
    while result.get("__interrupt__"):
        pending = result["__interrupt__"]
        if approval is not None:
            replies = {item.id: approval for item in pending}
        else:
            if not sys.stdin.isatty():
                raise ValueError("This run needs human input; use a terminal or explicit --approval")
            previews = [m.text for m in result.get("messages", []) if m.type == "ai" and m.text]
            if previews:
                print("[Review before input]\n" + previews[-1], file=sys.stderr)
            with terminal_reader(sys.stdin, sys.stderr) as read:
                replies = {}
                for item in pending:
                    print(f"[Interrupt] {item.value}", file=sys.stderr)
                    try:
                        replies[item.id] = read("Resume> ")
                    except EOFError:
                        raise ValueError("Cancelled at EOF; no reply submitted") from None
        result = graph.invoke(Command(resume=replies), config)
    return result


def display(result):
    replies = [message for message in result.get("messages", []) if message.type == "ai" and message.text]
    if replies:
        print(replies[-1].text)
