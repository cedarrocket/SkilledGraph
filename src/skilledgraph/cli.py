"""Thin launcher: select a Host; the Host builds and runs its own graph."""

import argparse
import inspect
import sys

from .api import parse_graph
from .binding import load_file_object
from .diagnostics import BindingError, Diagnostic


def launch(argv=None):
    parser = argparse.ArgumentParser(prog="sgraph", description="Run a SkilledGraph Markdown file. Host arguments follow the graph path; an optional -- separates them.")
    parser.add_argument("--check", action="store_true", help="parse/validate only; never import referenced code")
    parser.add_argument("graph")
    parser.add_argument("host_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    spec = parse_graph(args.graph)
    if args.check:
        if args.host_args:
            parser.error("--check does not accept Host arguments")
        print(f"OK: {spec.path} ({len(spec.nodes)} nodes)")
        return 0
    host_args = args.host_args
    if host_args[:1] == ["--"]:
        host_args = host_args[1:]
    reference = spec.config.setting("host") if spec.config else None
    if reference is None:
        from sgraph_chat_host.host import main as host
    else:
        setting = next(s for s in spec.config.settings if s.key == "host")
        try:
            prefix, separator, payload = reference.partition(":")
            if prefix != "python" or not separator:
                raise ValueError("@host requires python:FILE:ENTRY")
            host = load_file_object(payload, base_dir=spec.path.parent)
            if not callable(host):
                raise TypeError("Host entry must be callable")
        except Exception as exc:
            raise BindingError(Diagnostic("binding.host", f"Cannot bind {reference!r}: {exc}", setting.value_span, "bind")) from exc
    result = host(spec.path, host_args)
    if inspect.isawaitable(result):
        if inspect.iscoroutine(result):
            result.close()
        raise TypeError("Host entry must be synchronous; manage async execution inside the Host")
    if result is not None and (not isinstance(result, int) or isinstance(result, bool)):
        raise TypeError("Host must return an integer exit code or None")
    return 0 if result is None else result


def main(argv=None):
    try:
        return launch(argv)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"sgraph: {exc}", file=sys.stderr)
        return 1
