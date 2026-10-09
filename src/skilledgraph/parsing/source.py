"""Source indexing which preserves original newlines and code-point offsets."""

from bisect import bisect_right
from pathlib import Path
import re

from ..diagnostics import Diagnostic, ParseError
from ..spec import SourcePosition, SourceSpan


class Source:
    def __init__(self, path: Path, text: str):
        self.path = path
        self.text = text
        self.starts = [0]
        self.lines: list[str] = []
        previous = 0
        for match in re.finditer(r"\r\n|\r|\n", text):
            self.lines.append(text[previous:match.start()])
            previous = match.end()
            self.starts.append(previous)
        if previous < len(text):
            self.lines.append(text[previous:])
        self.normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        self.normalized_starts = [0]
        for match in re.finditer("\n", self.normalized):
            self.normalized_starts.append(match.end())

    def position(self, offset: int) -> SourcePosition:
        index = bisect_right(self.starts, offset) - 1
        return SourcePosition(index + 1, offset - self.starts[index] + 1, offset)

    def span_offsets(self, start: int, end: int) -> SourceSpan:
        return SourceSpan(self.path, self.position(start), self.position(end))

    def boundary(self, line: int) -> int:
        return self.starts[line] if line < len(self.starts) else len(self.text)

    def region(self, start_line: int, end_line: int) -> SourceSpan:
        return self.span_offsets(self.boundary(start_line), self.boundary(end_line))

    def line_span(self, line: int, start: int = 0, end: int | None = None) -> SourceSpan:
        width = len(self.lines[line]) if line < len(self.lines) else 0
        offset = self.boundary(line)
        return self.span_offsets(offset + start, offset + (width if end is None else end))

    def raw(self, span: SourceSpan) -> str:
        return self.text[span.start.offset:span.end.offset]

    def fail(self, code: str, message: str, line: int) -> None:
        raise ParseError(Diagnostic(code, message, self.line_span(line)))
