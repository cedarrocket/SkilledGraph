"""Build the immutable source description from Markdown-aware directives."""

from dataclasses import dataclass, field
import re

from ..spec import ConfigSpec, Description, GraphSpec, NodeSpec, Setting
from .markdown import directives
from .source import Source
from .transitions import parse_transitions
from .validation import is_name, validate_graph


_NODE = re.compile(r"^#[ \t]+\[(Node|ToolNode)\][ \t]+([^ \t]+)[ \t]*$")
_SETTING = re.compile(r"^-[ \t]+\*\*@([^* \t]+)\*\*[ \t]*:[ \t]*(.*)$")
_HEADERS = {
    "config": re.compile(r"^#[ \t]+\[Config\][ \t]*$"),
    "transitions": re.compile(r"^##[ \t]+\[Transitions\][ \t]*$"),
}


@dataclass
class _Node:
    name: str
    start: int
    kind: str = "Node"
    settings: list[Setting] = field(default_factory=list)
    descriptions: list[Description] = field(default_factory=list)
    removed: set[int] = field(default_factory=set)
    transition_line: int | None = None

    def finish(self, source: Source, end: int) -> NodeSpec:
        body_end = self.transition_line if self.transition_line is not None else end
        lines = ["" if index in self.removed else source.lines[index]
                 for index in range(self.start + 1, body_end)]
        first, last = 0, len(lines)
        while first < last and not lines[first].strip(" \t"):
            first += 1
        while last > first and not lines[last - 1].strip(" \t"):
            last -= 1
        block = None if self.transition_line is None else parse_transitions(source, self.transition_line, end)
        return NodeSpec(
            self.name, tuple(self.settings), "\n".join(lines[first:last]),
            tuple(self.descriptions), block, source.region(self.start, end),
            source.line_span(self.start), source.region(self.start + 1, body_end), self.kind,
        )


def _setting(source: Source, line: int, allowed: set[str], existing: list[Setting]) -> Setting:
    raw = source.lines[line]
    match = _SETTING.fullmatch(raw)
    if match is None:
        source.fail("setting.syntax", "Expected - **@KEY**: VALUE", line)
    key = match[1]
    if key not in {"host", "state", "uses", "router", "tools"}:
        source.fail("setting.unknown", f"Unknown setting: @{key}", line)
    if key not in allowed:
        source.fail("setting.scope", f"Setting @{key} is not allowed in this scope; file settings require Config", line)
    value = match[2].strip(" \t")
    if not value:
        source.fail("setting.empty", f"Setting @{key} requires a value", line)
    if any(item.key == key for item in existing):
        source.fail("setting.duplicate", f"Duplicate setting: @{key}", line)
    start = match.start(2) + len(match[2]) - len(match[2].lstrip(" \t"))
    return Setting(key, value, raw, source.line_span(line), source.line_span(line, start, start + len(value)))


def parse_source(source: Source) -> GraphSpec:
    nodes: list[NodeSpec] = []
    node: _Node | None = None
    config_start: int | None = None
    config_end: int | None = None
    config_settings: list[Setting] = []
    config_descriptions: list[Description] = []
    preamble_descriptions: list[Description] = []
    preamble_end = len(source.lines)

    for directive in directives(source):
        kind, line = directive.kind, directive.line
        raw = source.lines[line]
        if kind == "node":
            match = _NODE.fullmatch(raw)
            if match is None or not is_name(match[2]):
                source.fail("node.name", "Node requires one valid name without whitespace or formatting", line)
            if node is not None:
                nodes.append(node.finish(source, line))
            else:
                if config_start is None:
                    preamble_end = line
                config_end = line
            node = _Node(match[2], line, match[1])
        elif kind == "config":
            if _HEADERS[kind].fullmatch(raw) is None:
                source.fail("config.syntax", "Invalid Config header", line)
            if node is not None:
                source.fail("config.scope", "Config must precede the first node", line)
            if config_start is not None:
                source.fail("config.duplicate", "Only one Config block is allowed", line)
            config_start = line
            preamble_end = line
        elif kind == "transitions":
            if _HEADERS[kind].fullmatch(raw) is None:
                source.fail("transitions.syntax", "Invalid Transitions header", line)
            if node is None:
                source.fail("transitions.scope", "Transitions must belong to a node", line)
            if node.transition_line is not None:
                source.fail("transitions.duplicate", "Only one Transitions block is allowed per node", line)
            node.transition_line = line
        elif kind in {"setting", "description"}:
            if node is not None and node.transition_line is not None:
                source.fail("transitions.content", "Settings and independent descriptions are not allowed in Transitions", line)
            if kind == "setting":
                allowed = ({"tools", "router"} if node.kind == "ToolNode" else {"uses", "router"}) if node else {"host", "state"} if config_start is not None else set()
                settings = node.settings if node else config_settings
                settings.append(_setting(source, line, allowed, settings))
            else:
                text = raw[3:]
                if text.startswith(" "):
                    text = text[1:]
                description = Description(text, raw, source.line_span(line))
                descriptions = (node.descriptions if node else config_descriptions
                                if config_start is not None else preamble_descriptions)
                descriptions.append(description)
            if node:
                node.removed.add(line)

    if node is None:
        source.fail("graph.empty", "A graph requires at least one node", 0)
    nodes.append(node.finish(source, len(source.lines)))
    config = None
    if config_start is not None:
        assert config_end is not None
        span = source.region(config_start, config_end)
        config = ConfigSpec(tuple(config_settings), tuple(config_descriptions), source.raw(span), span,
                            source.line_span(config_start))
    preamble_span = source.region(0, preamble_end)
    graph = GraphSpec(source.path, source.text, source.raw(preamble_span), preamble_span,
                      tuple(preamble_descriptions), config, tuple(nodes))
    validate_graph(graph)
    return graph
