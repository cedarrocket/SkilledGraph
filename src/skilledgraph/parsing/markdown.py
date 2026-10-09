"""CommonMark context with narrowly scoped SkilledGraph block overrides.

Only the block parser is used; source is never rendered or inline-decoded.
The pinned markdown-it-py version keeps the block-rule API reproducible.
"""

from dataclasses import dataclass
import re

from markdown_it import MarkdownIt
from markdown_it.rules_block import fence
from markdown_it.rules_block.state_block import StateBlock
from markdown_it.token import Token

from .source import Source


@dataclass(frozen=True, slots=True)
class Directive:
    kind: str
    line: int


_MARKERS = (
    ("node", re.compile(r"^#[ \t]+\[(?:Node|ToolNode)\]")),
    ("config", re.compile(r"^#[ \t]+\[Config\]")),
    ("transitions", re.compile(r"^##[ \t]+\[Transitions\]")),
    ("setting", re.compile(r"^-[ \t]+\*\*@")),
    ("description", re.compile(r"^>>>")),
)


def directives(source: Source) -> tuple[Directive, ...]:
    def directive_rule(state: StateBlock, start: int, end: int, silent: bool) -> bool:
        # bMarks/tShift are changed inside blockquotes and list items. Match the
        # physical column, not their logical content position. During lookahead,
        # a root-level setting must also terminate a preceding ordinary list.
        if state.blkIndent != 0 or state.bMarks[start] + state.tShift[start] != source.normalized_starts[start]:
            return False
        if not silent and state.level != 0:
            return False
        line = source.lines[start]
        kind = next((kind for kind, pattern in _MARKERS if pattern.match(line)), None)
        if kind is None:
            return False
        if silent:
            return True
        token = state.push("sgraph", "", 0)
        token.map = [start, start + 1]
        token.meta["kind"] = kind
        state.line = start + 1
        return True

    def strict_fence(state: StateBlock, start: int, end: int, silent: bool) -> bool:
        matched = fence(state, start, end, silent)
        if not matched or silent:
            return matched
        token = state.tokens[-1]
        last = state.line - 1
        pos = state.bMarks[last] + state.tShift[last]
        closing = state.src[pos:state.eMarks[last]]
        pattern = re.escape(token.markup[0]) + "{" + str(len(token.markup)) + r",}[ \t]*"
        if last <= start or state.is_code_block(last) or re.fullmatch(pattern, closing) is None:
            source.fail("fence.unclosed", "Code fence must be closed in its Markdown container", start)
        return True

    md = MarkdownIt("commonmark").enable("table")
    # DSL markers take precedence over GFM table-header recognition too: a
    # reference payload is allowed to contain pipes and must stay opaque.
    md.block.ruler.before("table", "sgraph", directive_rule,
                          {"alt": ["paragraph", "reference", "blockquote", "list"]})
    md.block.ruler.at("fence", strict_fence, {"alt": ["paragraph", "reference", "blockquote", "list"]})
    tokens: list[Token] = []
    # Source already normalizes CR/CRLF. Bypass core normalization (which would
    # replace NULs) and rendering, keeping every other source character intact.
    md.block.parse(source.normalized, md, {}, tokens)
    return tuple(Directive(token.meta["kind"], token.map[0])
                 for token in tokens if token.type == "sgraph" and token.map is not None)
