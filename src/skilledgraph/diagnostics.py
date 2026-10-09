"""Source-aware diagnostics without importing any execution dependencies."""

from dataclasses import dataclass
from typing import Literal

from .spec import SourceSpan


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: str
    message: str
    span: SourceSpan
    phase: Literal["read", "parse", "validate", "bind", "build", "compile", "run"] = "parse"


class SkilledGraphError(ValueError):
    def __init__(self, diagnostic: Diagnostic):
        self.diagnostic = diagnostic
        pos = diagnostic.span.start
        super().__init__(
            f"{diagnostic.span.path}:{pos.line}:{pos.column}: "
            f"{diagnostic.phase} [{diagnostic.code}] {diagnostic.message}"
        )


class ParseError(SkilledGraphError):
    pass


class BindingError(SkilledGraphError):
    pass


class BuildError(SkilledGraphError):
    pass


class RoutingError(SkilledGraphError):
    pass
