# Language versions and maintenance

Chinese `_cn` and English `_en` precede the extension: README_cn.md, workflow_en.md, host_en.py and test_parser_cn.py. Unsuffixed originals remain compatibility entries, preserving commands, references and imports.

## Read and run

- [Chinese home](../README_cn.md) / [English home](../README_en.md).
- [Chinese standards](standard/v0.1/README_cn.md) / [English standards](standard/v0.1/README_en.md).
- [Chinese examples](../examples/README_cn.md) / [English examples](../examples/README_en.md).
- [Chinese terminal agent](../sgraph_agent/README_cn.md) / [English agent](../sgraph_agent/README_en.md).

```bash
python -m pip install -e '.[chat,agent,mcp]'
python -m skilledgraph examples/10-tool-calling/workflow_cn.md
python -m skilledgraph examples/10-tool-calling/workflow_en.md
sgraph-agent-cn --help
sgraph-agent-en --help
```

Graphs reference matching-language Python. Imports, mock targets, default materials and tool descriptions also match. DSL keywords, node names, route keys, State fields and API names remain unchanged. Default notes select the matching language; user-selected directories retain ordinary all-Markdown scanning.

The setup wizard remains multilingual. Use SGRAPH_LANGUAGE=zh for Chinese or SGRAPH_LANGUAGE=en for English, subject to the Host usage guide. File language does not override environment preferences. Shared __init__.py/__main__.py preserve compatibility; use sgraph-agent-en, python -m sgraph_agent.host_en or the English graph for the English application.

## Shared and preserved material

All 18 src/skilledgraph core files remain byte-for-byte unchanged; their existing comments/docstrings are already English. There is no interpreter duplication or new DSL syntax. LICENSE, dependencies, CI, package entries and language-independent checks are shared.

Parser fixtures deliberately preserve original bytes in both variants: Chinese Unicode, exact bodies, trailing spaces and CRLF are test data. Manifests change input filenames, with explanatory text translated where appropriate. Unicode test strings, the bilingual locale dictionary and Chinese affirmative aliases remain intentional.

Historical API JSON/model responses are shared and unmodified. English reports describe the same historical observations with original counts/limitations. Translated live scripts require explicit --run; historical records are not evidence of English live reruns. This localization used offline models and local MCP only, without new paid API requests.

Personal docs/agent-guide, .local-docs and .local-history stay local and Git-ignored. They are not included in publication.

## Verification and maintenance

```bash
python tools/check_localizations.py
python -m unittest discover -s tests -p 'test_*_cn.py' -q
python -m unittest discover -s tests -p 'test_*_en.py' -q
python -m unittest discover -s tests -q
python tests/mcp_demo/check_cn.py --output /tmp/mcp-cn.json
python tests/mcp_demo/check_en.py --output /tmp/mcp-en.json
```

On Windows choose a suitable temporary output directory/Python path. Full discovery runs original, Chinese and English suites: 822 checks are three versions of 274 checks, not 822 independent features.

The [manifest](../tools/localization_manifest.json) lists compatibility sources, variants, shared files and local exclusions. The [checker](../tools/check_localizations.py) validates coverage, Python syntax, relative links, fixture bytes and manifest contracts. It is not a translator. Changes require matching language updates, references, assertions and text budgets; new files must enter the manifest. Never translate protocol names or normalize byte-sensitive fixtures.

See [Chinese acceptance](development/LOCALIZATION_ACCEPTANCE_cn.md) / [English acceptance](development/LOCALIZATION_ACCEPTANCE_en.md).
