"""Markdown parsing and native LangGraph construction."""

from .api import parse_graph, build_graph, load_graph
from .diagnostics import Diagnostic, ParseError, BindingError, BuildError, RoutingError, SkilledGraphError
from .spec import (
    ConfigSpec,
    Description,
    GraphSpec,
    NodeSpec,
    Setting,
    SourcePosition,
    SourceSpan,
    Transition,
    TransitionBlock,
)

__all__ = [
    "parse_graph", "build_graph", "load_graph", "SkilledGraphError",
    "BindingError", "BuildError", "RoutingError", "Diagnostic", "ParseError", "GraphSpec", "NodeSpec",
    "ConfigSpec", "Setting", "Description", "SourcePosition", "SourceSpan",
    "Transition", "TransitionBlock",
]


def __getattr__(name):
    # Keep parse-only imports independent of the optional runtime.
    # 纯解析导入不依赖可选运行时。
    if name == "TraceRecorder":
        from .tracing import TraceRecorder
        return TraceRecorder
    if name in {"trace_summary", "atrace_summary"}:
        from . import trace_integration
        return getattr(trace_integration, name)
    raise AttributeError(name)


__all__ += ["TraceRecorder", "trace_summary", "atrace_summary"]
