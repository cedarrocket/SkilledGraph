# SkilledGraph v0.1 Language Specification

> 2026-10-09: tool calling is implemented. The extension sections at the end update the earlier setting allowlist, interfaces, and scope.

Status: current language specification. Date: 2026-10-09. Terms and authority are defined in the [standard entry](README_en.md). This document defines Markdown input and graph semantics; builtin execution and model adaptation are defined in the [implementation whitepaper](IMPLEMENTATION_WHITEPAPER_en.md).

Reading order: §§1–4 define characters, context, and file structure; §§5–7 define settings, body extraction, and transition tables; §§8–10 define control flow, extension boundaries, and diagnostics; §11 lists deferred features.

## 1. Language model and scope

One UTF-8 file defines one graph containing at least one node. Declaration order is retained; the first node is the entry. Node order does not create implicit edges. The preamble belongs to no node and is not included in default model input.

The DSL expresses Config, nodes, body text, non-executable descriptions, execution references, and transition tables. It does not declare credentials, temperature, I/O mappings, State field types, or reducer expressions. These belong to the Host, external code, and native definitions.

## 2. Characters, names, and Markdown context

Input is decoded as UTF-8; CRLF/CR are normalized to LF, while source positions must remain traceable to the original file. Structural horizontal whitespace HWS consists only of ASCII space or tab, not other Unicode whitespace.

A name contains one or more code points in Unicode General Categories L* or N*, or `_` or `-`. Combining marks M* and whitespace are excluded. Names compare by their original code points: case-sensitive, without normalization, and not necessarily Python identifiers. Node names are unique within a file; ordinary route keys are unique within a node. The `@` prefix is reserved for language markers.

Markdown block and inline context follows [CommonMark 0.31.2](https://spec.commonmark.org/0.31.2/); pipe-table boundaries follow the [GFM table extension](https://github.github.com/gfm/#tables-extension-), except where this specification explicitly overrides them. Other Markdown is retained as source text; rendering is not required.

Structural markers, settings, and descriptions are recognized at physical column 1 at the top level. Global dedentation must not activate markers. Identical text inside fenced code, indented code, inline code, raw HTML blocks, ordinary blockquotes, or nested lists remains literal. A direct top-level list item is a valid setting location; ignoring all lists would be incorrect. Top-level `>>>` specifically overrides normal blockquote interpretation.

Fences must close according to Markdown rules; an unclosed fence raises an error at its opening. Raw HTML is retained; there is no HTML-comment stripping or dedicated closing check. No additional DSL escape conversion occurs. Use a closed code block to show literal DSL markers.

## 3. Line grammar

The following EBNF applies only in positions where recognition is allowed, excluding the line ending. The last line may omit a newline.

```ebnf
HWS          = " " | "\t" ;
HWS0         = { HWS } ;
HWS1         = HWS, { HWS } ;
NAME_CHAR    = Unicode_Letter | Unicode_Number | "_" | "-" ;
NAME         = NAME_CHAR, { NAME_CHAR } ;
NODE         = "#", HWS1, "[Node]", HWS1, NAME, HWS0 ;
CONFIG       = "#", HWS1, "[Config]", HWS0 ;
TRANSITIONS  = "##", HWS1, "[Transitions]", HWS0 ;
SETTING      = "-", HWS1, "**@", KEY, "**", HWS0, ":", HWS0, VALUE ;
KEY          = "host" | "state" | "uses" | "router" ;
DESCRIPTION  = ">>>", REST_OF_LINE ;
ROUTE_KEY    = NAME | "@Default" ;
TARGET       = NAME | "@End" ;
LIST_RECORD  = "-", HWS1, ROUTE_KEY, HWS0, "->", HWS0, TARGET, HWS0 ;
BLANK        = HWS0 ;
```

VALUE is a nonempty single-line string after trimming outer HWS; REST_OF_LINE may be empty. Structural tokens cannot contain inserted spaces, but tokens may be separated by multiple HWS characters. Reserved headers cannot have extra text, comments, or Markdown closing hashes.

`# [node] A` and `# [Graph]` are ordinary headings, not fuzzy matches. `# [Node]` is an incomplete reserved structure and must fail; `# [Node] A B` is an invalid name.

```markdown
#   [Node]   Analyze
-   **@uses** :   python:./tools_en.py:run
##   [Transitions]
- @Default->@End
```

These whitespace variations are valid.

## 4. File regions and recognition order

```text
File = preamble + optional Config + one or more Nodes
Config = Config header + settings / descriptions / ordinary preamble text
Node = node header + body / node settings / descriptions + optional Transitions
Transitions = transition header + list records OR one table
```

Config appears at most once, before the first node; its region ends at that node. There is no implicit Config. A node extends to the next node or EOF. Transitions appears at most once and is the node's final block, extending to the next node or EOF. It needs no closing marker and never resumes ordinary body text.

Recognition order:

1. Decode and normalize line endings, preserving source-position mapping.
2. Determine Markdown literal and container contexts.
3. Recognize Node, Config, and Transitions at allowed locations and establish regions.
4. Recognize setting prefixes in the preamble, Config, or node body and check scope.
5. Recognize top-level `>>>` descriptions in those regions.
6. Preserve the remaining source as preamble or body; extracted text must not reactivate DSL recognition.

Transitions accepts only its chosen record format and allowed blank lines. Duplicate headers, settings, standalone descriptions, prose, and other headings are errors. A valid next node header ends the region.

## 5. Settings

Settings use `- **@KEY**: VALUE`, case-sensitively. Only outer HWS is trimmed; values are not evaluated, environment-expanded, or automatically unquoted.

| Setting | Scope | Meaning |
| --- | --- | --- |
| @host | explicit Config | select the Host reference for the launcher |
| @state | explicit Config | select the native State schema before construction |
| @uses | node body | select Hardcode_Execution_Backend and its reference |
| @router | node body | select the callable obtaining a route key after node execution |

Settings may be interspersed with text, blank lines, and descriptions until Transitions. There is no property-region closing rule. A setting cannot occur twice in the same scope.

Checking starts at physical column 1 with `-`, HWS1, and immediate `**@`. Once recognized, an unknown key, unclosed bold marker, missing colon, empty value, duplicate, or wrong scope must fail rather than become body text. `- @uses: ...`, `- **uses**: ...`, and ordinary bold list items are plain text.

```markdown
# [Config]
- **@state**: python:./state_en.py:State

# [Node] Prepare
- **@uses**: pyfunction:./tools_en.py:prepare

Answer using the supplied material.

## [Transitions]
- @Default -> @End
```

Config does not accept model configuration, arbitrary host.* parameters, or I/O expressions. File-level execution-backend selection is deferred and has no setting key.

## 6. Body, descriptions, and exact extraction

The body is original Markdown, not rewritten rendering. Each top-level line beginning `>>>` is an independent non-executable description: remove that prefix and at most one following ASCII space, retaining the description for auditing. A subsequent line without this prefix resumes normal body content. Descriptions do not enter default model input and do not disable model calls.

Body extraction:

1. Take normalized source lines after the node header and before Transitions, or to node end if absent.
2. Replace each extracted setting or description line with an empty string, retaining its line position.
3. Trim leading and trailing lines containing only ASCII spaces/tabs.
4. Preserve internal lines verbatim and join with LF; append no extra final LF. All-blank content becomes an empty string.

```markdown
# [Node] A
First line
- **@uses**: python:./tools_en.py:run
>>> Description
Second line  

## [Transitions]
- @Default -> @End
```

The body's JSON representation is `"First line\n\n\nSecond line  "`; the final two spaces are retained. Code, ordinary quotes, nested-list markers, undecoded entities, and backslashes remain literal. Original text, settings, descriptions, and positions are separately preserved; body text is not the entire parse result.

An empty or description-only body is syntactically valid and does not skip a default Prompt call. The framework supplies body uniformly to every Hardcode_Execution_Backend and does not reject it solely because of execution type. Using, ignoring, or rejecting body is the backend's decision; builtin policies are in the whitepaper.

## 7. Transition-table syntax

Each Transitions block contains at least one record and uses either a list or one pipe table, never a mixture.

```markdown
## [Transitions]
- ready -> Report
- missing -> RequestMaterial
```

```markdown
## [Transitions]
| Route | Target | Explanation |
| --- | --- | --- |
| ready | Report | Sufficient material |
| missing | RequestMaterial | Request more material |
```

The forms are equivalent. List records may be separated by blank lines; nested records, inline comments, and extra trailing tokens are invalid.

Table rules:

- Header, separator, and data rows start at column 1. Outer pipes are optional; boundaries and escaped pipes follow GFM, not naive splitting on every pipe.
- Header has at least two columns; separator has the same count. Each separator column may have surrounding colons and must contain at least one `-`; outer HWS may be ignored.
- At least one data row is required, with at least two actual cells. Trim HWS from the first two cells and validate them as ROUTE_KEY/TARGET. Empty cells, bold, links, inline code, and name unescaping are invalid.
- Third and later columns have unrestricted content and count, including more cells than the header. Preserve all original cells; they do not execute or enter default model input.
- Data rows are contiguous; no internal blank line. Blank lines are allowed before/after the table. Records or another header after the table ends are errors, not continuation or a second table.
- Header labels and alignment do not execute. No prose may surround the table inside Transitions.
- There is no >>> comment feature in Transitions: a standalone line fails; the first two cells follow name validation; literal >>> in extra cells is not interpreted.

## 8. Graph control flow

| Form | Meaning |
| --- | --- |
| @Default → TARGET | sole unconditional edge; cannot mix with named keys; not failure fallback |
| NAME → TARGET | route-key mapping; even one record remains conditional |
| target @End | no successor on this DSL path; other native branches are not cancelled |
| no Transitions | no DSL successor; valid but not recommended for teaching |

Forward references, self-loops, cycles, unreachable nodes, and several keys sharing a target are allowed. A reachable end is not mandatory. Target nodes must exist. Other @ markers are invalid, subject to the tool extension below. Default/END are not aliases; if valid names, they are ordinary names. There is no `- @End` shorthand.

Published examples and authoring tools should explicitly use `- @Default -> @End`. Nodes without tables remain boundary fixtures; the interpreter need not warn.

With a valid @router: execute node → native reducer merges update → router reads merged State → returns key → exact validation and table lookup → schedule. Router is not another DSL node, does not provide business-State updates, and returns a key rather than a target name. uses/router share reference loading; construction determines placement.

A router without a conditional table has no valid routing semantics. The first version permits a later dedicated check but does not promise execution of an unused router. Without router, execution must explicitly provide a route value; arbitrary return values or native goto are not guessed. Default model text routing is defined in the whitepaper.

An invalid key raises a runtime error: no guessing, repair, implicit retry, or additional model call. @Default cannot catch it.

Native callables may jump directly; out-of-table targets are not prohibited by default. A native jump does not cancel DSL outgoing edges; both can schedule. The builder must not interpret goto as a replacement table edge/key or schedule the same DSL edge twice. More complex scheduling follows native capabilities and must be tested; automatic deduplication of repeated user targets is not promised.

## 9. State, references, and extension boundaries

State/reducers use native definitions, not DSL types. Users may extend or completely replace defaults; the framework must not restore fields/reducers, rewrite annotations, or reimplement merging. Pure callable graphs need no messages. Default model nodes require compatible State or explicit adaptation; no hidden second State is created. Other State fields do not automatically enter model input.

At language level, a reference is a complete string and source position. Parsing does not import, execute, verify object existence, or require its final segment to be a function name. Builtin file interpretation is in the whitepaper. Relative files use the DSL source directory without changing cwd. An in-memory source would need an explicit base, but no public in-memory parser entry is defined.

Explicit Host/API definitions take priority over file declarations, which take priority over defaults. Unselected references need not be imported; their declarations remain auditable. Invalid selected references fail without guessing modules or silently changing execution mode.

@uses gives execution ownership to its backend: no additional invoke before/after it. Native sync/async, runtime parameters, and special returns remain accessible; not every callable is reduced to a material function or custom result envelope. Interfaces and builtin capabilities are in the whitepaper.

## 10. Diagnostics

Diagnostics include phase, concise cause, and source position. Reference errors identify the original reference; routing errors identify node, returned key, and legal keys. Exception types/codes are not frozen by the language, nor is error ordering for multiply invalid files.

| Phase | Required errors |
| --- | --- |
| parse/static | no node; invalid/duplicate names; duplicate/misplaced Config; duplicate/misplaced Transitions; unclosed fence |
| parse/static | setting syntax, key, value, duplicate, or scope |
| parse/static | empty transitions; mixed forms; second/discontinuous table; missing executable cells; extra prose/descriptions |
| parse/static | invalid/duplicate keys; invalid/missing targets; unknown special marker; mixed @Default/named keys |
| bind/build | unresolved or incompatible selected references; missing execution policy; incompatible required model/State contract |
| bind/build | builtin python conditional table without router or explicit key protocol |
| run | invalid route values; execution/backend/native errors under their respective contracts |

Validate targets after reading all nodes, allowing forward references. Read-only diagnostics must not import code. A backend rejecting body text reports a capability error, not a universal DSL syntax error.

## 11. Deferred features

No initial-version syntax is defined for file-level Hardcode_Execution_Backend selection, module references, model-output Schema settings, material-history-off, dedicated escapes, HTML comments, @failed, retry/recovery, DSL parallel dispatch/subgraphs, or model/I/O configuration expressions.

They are not hidden features; unknown settings fail. Deferring DSL expression does not prevent Host/native Python capabilities or introduce universal permission/control-flow prohibitions.

## Tool-calling extension (2026-10-09)

Adds ToolNode, @tools, and two reserved route conditions, extending the earlier allowlist and key rules. Existing behavior is unchanged; multi-model declarations and MCP connection configuration are outside scope.

Tool node title: `# [ToolNode] NAME`. Naming, locations, declaration-order entry, targets, and regions match Node; both kinds share one namespace. NodeSpec.kind is Node or ToolNode. Identical headers inside fences/containers remain body.

ToolNode requires exactly one `- **@tools**: all` or `- **@tools**: [name, name]`. Lists allow whitespace around commas and may be empty. Names use ASCII letters/numbers/underscore/hyphen, case-sensitively; quotes, trailing commas, duplicates, and list: are unsupported. all selects explicitly supplied tools, not service discovery. Missing/duplicate external names fail binding. @tools is allowed only on ToolNode; ToolNode permits @router but not @uses. Body is retained but ignored by native tool execution; no model call occurs. Do not put instructions there expecting a model to follow them.

New conditions, in either transition format:

- `@ToolCalls`: merged State.messages ends in an AIMessage with nonempty tool_calls.
- `@Otherwise`: fallback after other conditions fail; not an exception handler.
- `@Default` remains a sole unconditional edge and cannot mix with either.

Priority is independent of source order:

1. A declared, matched @ToolCalls chooses its target and bypasses @router.
2. Otherwise call explicit @router; absent one, builtin model nodes use the latest merged AI text, trimmed, as an ordinary key.
3. A matching ordinary key selects its target; otherwise use @Otherwise; without fallback raise routing error.

Literal model/router text "@ToolCalls" cannot fake the signal. Non-builtin execution with ordinary keys still requires router; special-only tables do not. Tables without special conditions retain prior behavior. Tool requests create no automatic edges; missing @ToolCalls does not implicitly execute tools.

A ToolNode handles all calls in one AIMessage, without implicit name-based splitting or automatic return to the caller. Its successor comes from its transition table. Native Command capabilities remain available.

This uses standard messages. The framework does not repair custom reducers or guarantee tool protocol after users delete/change messages.

## Builtin interaction extension (2026-10-09)

`- **@uses**: request_input:prompt text` is a builtin execution reference, not new structural syntax. Values occupy one physical line; double quotes do not create multiline settings. Optional JSON-string decoding, including `\n`, belongs to the backend; the parser preserves source. Parameters, resumes, and updates are in the whitepaper's request_input section.

## Optional sandbox extension (2026-10-09)

`- **@uses**: monty:./program_en.py`, or the same reference in @router, is an optional builtin in existing reference syntax, not a new setting, node kind, or reducer declaration. File payload and return contracts are in the whitepaper's monty section.
