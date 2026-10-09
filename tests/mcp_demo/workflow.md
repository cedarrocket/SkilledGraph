# [Config]
- **@host**: python:./host.py:main

# [Node] Assistant
计算加法时必须调用 mcp_add 工具，拿到结果后回答。不要自行计算。

## [Transitions]
- @ToolCalls -> ExecuteTools
- @Otherwise -> @End

# [ToolNode] ExecuteTools
- **@tools**: [mcp_add]

## [Transitions]
- @Default -> Assistant
