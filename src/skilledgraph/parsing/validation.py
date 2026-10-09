"""Graph-wide checks which never inspect or import executable references."""

import unicodedata

from ..diagnostics import Diagnostic, ParseError
from ..spec import GraphSpec
from ..tool_selection import parse_tool_selection


def is_name(value: str) -> bool:
    return bool(value) and all(
        char in "_-" or unicodedata.category(char)[0] in "LN" for char in value
    )


def validate_graph(graph: GraphSpec) -> None:
    names: set[str] = set()
    for node in graph.nodes:
        if node.name in names:
            raise ParseError(Diagnostic(
                "node.duplicate", f"Duplicate node: {node.name}", node.header_span, "validate",
            ))
        names.add(node.name)
        if node.kind == "ToolNode":
            setting = next((s for s in node.settings if s.key == "tools"), None)
            if setting is None:
                raise ParseError(Diagnostic("tools.required", "ToolNode requires @tools", node.header_span, "validate"))
            try:
                parse_tool_selection(setting.value)
            except ValueError as exc:
                raise ParseError(Diagnostic("tools.syntax", str(exc), setting.value_span, "validate")) from exc


    for node in graph.nodes:
        if node.transitions is None:
            continue
        keys: set[str] = set()
        records = node.transitions.records
        for record in records:
            if record.key in keys:
                raise ParseError(Diagnostic(
                    "route.duplicate", f"Duplicate route key in {node.name}: {record.key}",
                    record.key_span, "validate",
                ))
            keys.add(record.key)
            if record.target != "@End" and record.target not in names:
                raise ParseError(Diagnostic(
                    "route.unknown_target", f"Unknown target in {node.name}: {record.target}",
                    record.target_span, "validate",
                ))
        if "@Default" in keys and len(keys) != 1:
            default = next(record for record in records if record.key == "@Default")
            raise ParseError(Diagnostic(
                "route.default_mixed", "@Default cannot be mixed with named conditional routes",
                default.key_span, "validate",
            ))
