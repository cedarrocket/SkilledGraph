"""Public entry points implemented in the current milestone."""

from pathlib import Path
from os import PathLike

from .diagnostics import Diagnostic, ParseError
from .parsing.parser import parse_source
from .parsing.source import Source
from .spec import GraphSpec


def parse_graph(path: str | PathLike[str]) -> GraphSpec:
    """Parse a UTF-8 DSL file, without loading any referenced resources.

    Filesystem errors propagate as OSError; malformed UTF-8 and invalid DSL
    produce ParseError. Source paths are absolute. No graph is constructed.
    """
    source_path = Path(path).absolute()
    raw = source_path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        prefix = raw[:error.start].decode("utf-8")
        source = Source(source_path, prefix)
        raise ParseError(Diagnostic(
            "source.encoding", "Source must be valid UTF-8",
            source.span_offsets(len(prefix), len(prefix)), "read",
        )) from error
    return parse_source(Source(source_path, text))


def build_graph(path_or_spec, *, state_schema=None, input_schema=None,
                output_schema=None, context_schema=None, model=None, tools=None, bindings=None):
    """Bind a file/spec and return a native, editable StateGraph builder.

    Requires the runtime extra. Imports selected files, but never invokes nodes,
    models, or the file Host. Schema definitions are passed through unchanged.
    """
    from .building import build

    spec = path_or_spec if isinstance(path_or_spec, GraphSpec) else parse_graph(path_or_spec)
    return build(spec, state_schema=state_schema, input_schema=input_schema,
                 output_schema=output_schema, context_schema=context_schema,
                 model=model, tools=tools, bindings=bindings)


def load_graph(path_or_spec, *, state_schema=None, input_schema=None,
               output_schema=None, context_schema=None, model=None, tools=None, bindings=None,
               compile_kwargs=None, trace=None):
    """Build and compile a graph, forwarding compile_kwargs to native compile."""
    from .diagnostics import BuildError

    spec = path_or_spec if isinstance(path_or_spec, GraphSpec) else parse_graph(path_or_spec)
    from .subgraphs import resolve_tree
    from .building import build
    tree = resolve_tree(spec)
    tracing = tree.requires_trace
    if tracing:
        from .tracing import TraceRecorder
        if not isinstance(trace, TraceRecorder):
            raise ValueError("@trace: on requires load_graph(..., trace=TraceRecorder())")
    builder = build(spec, state_schema=state_schema, input_schema=input_schema,
                    output_schema=output_schema, context_schema=context_schema,
                    model=model, tools=tools, bindings=bindings, _tree=tree)
    try:
        graph = builder.compile(**({} if compile_kwargs is None else compile_kwargs))
        return graph.with_config(callbacks=[trace]) if tracing else graph
    except Exception as exc:
        raise BuildError(Diagnostic("build.compile", str(exc), spec.nodes[0].header_span, "compile")) from exc
