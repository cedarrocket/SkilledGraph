# [Config]
- **@host**: python:./host_en.py:main

# [Node] Assistant
For addition, you must call mcp_add. Answer after receiving the result; do not calculate it yourself.

## [Transitions]
- @ToolCalls -> ExecuteTools
- @Otherwise -> @End

# [ToolNode] ExecuteTools
- **@tools**: [mcp_add]

## [Transitions]
- @Default -> Assistant
