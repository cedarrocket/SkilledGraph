# Minimal local MCP test

No external MCP setup is needed. The Host starts server_en.py over stdio, discovers mcp_add, keeps the session open throughout graph execution and closes the child process. The graph uses existing ToolNode and tool-call transitions without new syntax.

```bash
python -m pip install -e '.[mcp,deepseek]'
# Real MCP child, deterministic offline model
.venv/bin/python tests/mcp_demo/check_en.py
# Optional live DeepSeek + MCP
export SGRAPH_MODEL=deepseek:deepseek-chat
export SGRAPH_API_KEY_FILE="$HOME/sys_prog/deepseek_api.txt"
export SGRAPH_TEMPERATURE=0
export SGRAPH_TIMEOUT=45
export SGRAPH_MAX_TOKENS=256
export LANGSMITH_TRACING=false
.venv/bin/python tests/mcp_demo/check_en.py --live
# Manual use
printf 'Use the tool to add 17 and 25.\n' | .venv/bin/sgraph tests/mcp_demo/workflow_en.md
```

Direct terminal execution reads one input and exits. This Host uses asyncio.run and graph.ainvoke; asynchronous-only MCP tools cannot be executed through synchronous invoke.

check_en.py verifies discovery, actual subprocess calls, two rounds on one session, call IDs/results and cleanup. `--live` additionally checks model requests and answers. Overall timeout is 120 seconds; the default report is docs/development/MCP_LOCAL_RESULTS.json.

Remote HTTP, authentication, reconnects, sampling, human input and multimodal content are outside coverage. langchain.mcp is beta in this pinned version; see [acceptance](../../docs/development/MCP_ACCEPTANCE_en.md).
