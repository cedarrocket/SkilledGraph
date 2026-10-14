# v0.1 language acceptance fixtures

Parser inputs and expected results. M1 executed all 45 original samples through [parser tests](../../test_parser_en.py), with additional context, source-position and import-isolation checks; see [M1](../../../docs/development/M1_PARSER_en.md). Parser acceptance is not runtime acceptance.

- valid/: syntactically/static-structurally valid input.
- invalid/: input rejected during parsing or static validation.
- [manifest_en.json](manifest_en.json): accept/reject expectations, selected fields and reasons.

Both language copies intentionally preserve fixture bytes, including Chinese Unicode, rather than translate them. This keeps source positions, exact prompts and diagnostic expectations equivalent. Missing Python references need not exist: read-only parsing must not import them. Empty prompts are legal; execution determines support and does not automatically disable invocation. no-table-* tests nonrecommended boundaries; cycles need not terminate.

Manifest expected fields compare entry, node order, exact prompt/settings/descriptions/transition keys and targets. This is not the final public IR. Unlisted text/positions must still be preserved. transitions:null means no block, distinct from an invalid empty block.

Invalid reasons describe diagnostic conditions, not frozen messages/error codes or ordering. Source positions should be reported. crlf_en.md deliberately uses CRLF; prompt-extraction_en.md preserves trailing spaces. Do not normalize them as formatting. Additional CR/no-final-newline/container-fence/position/binding/runtime tests supplement these samples.

See [language specification](../../../docs/standard/v0.1/LANGUAGE_SPEC_en.md) and [development guide](../../../docs/standard/v0.1/DEVELOPMENT_GUIDE_en.md).
