"""Immutable, data-only parse results; offsets refer to original Unicode text."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True, slots=True)
class SourcePosition:
    """One-based line/column and zero-based Unicode-character offset."""

    line: int
    column: int
    offset: int


@dataclass(frozen=True, slots=True)
class SourceSpan:
    """Half-open range in the original decoded file (including original CRLF)."""

    path: Path
    start: SourcePosition
    end: SourcePosition


@dataclass(frozen=True, slots=True)
class Setting:
    key: str
    value: str
    raw: str
    span: SourceSpan
    value_span: SourceSpan


@dataclass(frozen=True, slots=True)
class Description:
    text: str
    raw: str
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class Transition:
    key: str
    target: str
    raw: str
    span: SourceSpan
    key_span: SourceSpan
    target_span: SourceSpan
    extra_cells: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TransitionBlock:
    format: Literal["list", "table"]
    records: tuple[Transition, ...]
    raw: str
    span: SourceSpan
    header_span: SourceSpan
    table_header: tuple[str, ...] = ()
    table_separator: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class NodeSpec:
    name: str
    settings: tuple[Setting, ...]
    prompt: str
    descriptions: tuple[Description, ...]
    transitions: TransitionBlock | None
    span: SourceSpan
    header_span: SourceSpan
    body_span: SourceSpan
    kind: Literal["Node", "ToolNode"] = "Node"

    def setting(self, key: str) -> str | None:
        return next((item.value for item in self.settings if item.key == key), None)


@dataclass(frozen=True, slots=True)
class ConfigSpec:
    settings: tuple[Setting, ...]
    descriptions: tuple[Description, ...]
    raw: str
    span: SourceSpan
    header_span: SourceSpan

    def setting(self, key: str) -> str | None:
        return next((item.value for item in self.settings if item.key == key), None)


@dataclass(frozen=True, slots=True)
class GraphSpec:
    path: Path
    source_text: str
    preamble: str
    preamble_span: SourceSpan
    preamble_descriptions: tuple[Description, ...]
    config: ConfigSpec | None
    nodes: tuple[NodeSpec, ...]

    @property
    def entry(self) -> str:
        return self.nodes[0].name

    def source_slice(self, span: SourceSpan) -> str:
        if span.path != self.path:
            raise ValueError("Span belongs to a different source file")
        return self.source_text[span.start.offset:span.end.offset]
