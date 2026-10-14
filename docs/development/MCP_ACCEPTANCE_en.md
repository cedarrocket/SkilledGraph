# One-shot Host and Local MCP Acceptance

Date: 2026-10-09. Basic Host reads one terminal line/all piped stdin, runs once, and exits; blank/EOF does not invoke. Graph edges still drive tool loops; no cross-input conversation memory. 171 offline checks passed, including unread second line and no empty-input call.

## MCP results

Local stdio **5/5**:

1. Discover mcp_add.
2. Child-process tool returns42 for17+25.
3. Two graph rounds return42/5 with increasing counts, same server_pid and paired ToolMessage IDs: session was retained.
4. Real DeepSeek requests mcp_add and answers42.
5. Adapter exit terminates child.

[Original record](MCP_LOCAL_RESULTS.json): two DeepSeek requests,745 input/75 output,820 total tokens. Requested deepseek-chat; response model_name deepseek-flash.

## Integration and findings

LangChain1.4.4 MCPAdapter, FastMCP4.1.0, MCP SDK2.3.0; optional extra, no core import. Host lists tools, bind_tools and load_graph(tools=...). Existing DSL ToolNode/conditions are unchanged. Use ainvoke for async adapted tools.

Initial discovery/tools/multi-round graph passed, immediate cleanup failed because StdioTransport keep_alive=True retained child. Explicit keep_alive=False fixed the example; core was unchanged. Session context covers full graph. Native API is beta; upgrades need tests. [Official tools](https://docs.langchain.com/oss/python/langchain/mcp/tools).

## Run

Host starts service; no global MCP config. After provider setup:

```bash
printf 'Use the tool to calculate 17+25.\n' | python -m skilledgraph tests/mcp_demo/workflow_en.md
python tests/mcp_demo/check_en.py
```

[Complete demo](../../tests/mcp_demo/README_en.md). Only stdio/arithmetic/text/session cleanup accepted; not remote HTTP/auth/reconnect/user input/sampling/multimodal. Earlier reports saying MCP untested were historical; this is the later local result.
