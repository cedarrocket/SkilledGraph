# [Config]
- **@host**: python:./host_en.py:main

# [Node] Assistant
For addition, you must call the add tool. Answer after receiving its result.

## [Transitions]
- @ToolCalls -> ExecuteTools
- @Otherwise -> @End

# [ToolNode] ExecuteTools
- **@tools**: [add]

## [Transitions]
- @Default -> Assistant
