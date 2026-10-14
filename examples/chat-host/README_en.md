# Standard chat Host example

This Host is separate from the DSL core. Its source lives in `src/sgraph_chat_host/` and loads graphs through SkilledGraph's public APIs, outside `src/skilledgraph/`.

```bash
pip install -e '.[chat]'
sgraph examples/chat-host/workflow_en.md
```

Without model configuration, an interactive terminal starts the Chinese/English API setup wizard. Once configured, the Host reads one request, executes the graph, displays node responses and exits. Dynamic interrupts collect keyboard replies and resume execution. Model factories, environment variables, pipes and `--setup` are documented in the [usage guide](../../docs/development/USAGE_en.md).

| File | Responsibility |
| --- | --- |
| host_en.py | Model creation, single graph execution, dynamic resumption and arguments |
| host_config_en.py | Environment connection parameters, headers and OpenCode session ID |
| host_setup_en.py | First-run configuration and saved profiles |
| host_locales_en.py | Chinese/English strings and locale selection |
| terminal_en.py | Line editing and hidden input |

The separate `sgraph_chat_host` package is installed with the project for default operation and example reuse. Without `@host`, the launcher lazily selects this example's `main(graph_path, argv)`; the parser does not execute chat logic.

`workflow_en.md` explicitly declares `@host: python:./host_en.py:main`. The directory-level host_en.py wraps the independent package. Custom Hosts can replace this entry. Calling parse_graph(), build_graph() or load_graph() does not load the standard Host.

Examples and sgraph_agent can explicitly reuse model/configuration/terminal modules. This is application reuse, not a DSL requirement. Old skilledgraph.host* and skilledgraph.terminal imports were removed.

Use `runtime` for graph execution. Terminal editing dependencies are supplied by `chat`, `deepseek`, `mcp` and `agent` extras. The locale dictionary deliberately retains both languages in each language copy.
