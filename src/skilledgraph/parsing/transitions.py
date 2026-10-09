"""Strict DSL transition records; additional table cells remain raw text."""

import re

from ..spec import Transition, TransitionBlock
from .source import Source
from .validation import is_name


_LIST = re.compile(r"^-[ \t]+([^ \t]+?)[ \t]*->[ \t]*([^ \t]+)[ \t]*$")
_DELIMITER = re.compile(r":?-+:?\Z")


def _cells(line: str) -> list[tuple[str, int, int]]:
    """GFM pipe boundaries, preserving original escape characters and columns.

    GFM treats a pipe immediately preceded by backslash as escaped, including
    pipes inside inline code. Unlike Markdown rendering, do not decode cells.
    """
    bounds = [index for index, char in enumerate(line)
              if char == "|" and (index == 0 or line[index - 1] != "\\")]
    starts = [0, *(index + 1 for index in bounds)]
    ends = [*bounds, len(line)]
    result = [(line[start:end], start, end) for start, end in zip(starts, ends)]
    if bounds and not result[0][0].strip(" \t"):
        result.pop(0)
    if bounds and result and not result[-1][0].strip(" \t"):
        result.pop()
    return result


def _record(source: Source, line: int, key_cell: tuple[str, int, int],
            target_cell: tuple[str, int, int], extras: tuple[str, ...] = ()) -> Transition:
    def trimmed(cell: tuple[str, int, int]) -> tuple[str, int, int]:
        text, start, end = cell
        value = text.strip(" \t")
        left = len(text) - len(text.lstrip(" \t"))
        return value, start + left, start + left + len(value)

    key, key_start, key_end = trimmed(key_cell)
    target, target_start, target_end = trimmed(target_cell)
    if key not in {"@Default", "@ToolCalls", "@Otherwise"} and not is_name(key):
        source.fail("route.key", f"Invalid route key: {key!r}", line)
    if target != "@End" and not is_name(target):
        source.fail("route.target", f"Invalid route target: {target!r}", line)
    return Transition(
        key, target, source.lines[line], source.line_span(line),
        source.line_span(line, key_start, key_end),
        source.line_span(line, target_start, target_end), extras,
    )


def parse_transitions(source: Source, heading: int, end: int) -> TransitionBlock:
    nonblank = [index for index in range(heading + 1, end) if source.lines[index].strip(" \t")]
    if not nonblank:
        source.fail("transitions.empty", "Transitions requires at least one record", heading)
    first = nonblank[0]
    first_text = source.lines[first]
    header_cells = _cells(first_text)
    span = source.region(heading, end)

    # A valid table header/delimiter pair takes precedence over its arbitrary
    # header labels (which could themselves resemble a list record).
    delimiter_cells = _cells(source.lines[first + 1]) if first + 1 < end else []
    table_pair = len(header_cells) >= 2 and bool(delimiter_cells) and all(
        _DELIMITER.fullmatch(cell[0].strip(" \t")) for cell in delimiter_cells
    )
    if not table_pair and _LIST.fullmatch(first_text):
        records = []
        for index in nonblank:
            match = _LIST.fullmatch(source.lines[index])
            if match is None:
                source.fail("transitions.list_record", "Expected a complete list route; formats cannot be mixed", index)
            records.append(_record(
                source, index,
                (match[1], *match.span(1)), (match[2], *match.span(2)),
            ))
        return TransitionBlock("list", tuple(records), source.raw(span), span, source.line_span(heading))

    if len(header_cells) < 2 or first_text[0] in " \t":
        source.fail("transitions.format", "Expected list routes or one top-level table", first)
    if not table_pair or len(delimiter_cells) != len(header_cells):
        source.fail("table.delimiter", "Table requires a matching delimiter row directly below its header", min(first + 1, end - 1))
    if source.lines[first + 1][0] in " \t":
        source.fail("table.indent", "Table rows must start in column 1", first + 1)
    records = []
    table_ended = False
    for index in range(first + 2, end):
        text = source.lines[index]
        if not text.strip(" \t"):
            table_ended = True
            continue
        if table_ended:
            source.fail("table.discontinuous", "A table cannot resume or contain more text after a blank line", index)
        if text[0] in " \t":
            source.fail("table.indent", "Table rows must start in column 1", index)
        cells = _cells(text)
        if len(cells) < 2:
            source.fail("table.columns", "Each table record must supply both execution columns", index)
        records.append(_record(source, index, cells[0], cells[1], tuple(cell[0] for cell in cells[2:])))
    if not records:
        source.fail("table.empty", "Table requires at least one data record", first)
    return TransitionBlock(
        "table", tuple(records), source.raw(span), span, source.line_span(heading),
        tuple(cell[0] for cell in header_cells), tuple(cell[0] for cell in delimiter_cells),
    )
