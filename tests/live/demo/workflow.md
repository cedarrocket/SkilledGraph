# [Config]
- **@host**: python:./host.py:main

# [Node] Assistant
需要加法运算时，必须调用 add 工具。拿到工具结果后回答用户。

## [Transitions]
- @ToolCalls -> ExecuteTools
- @Otherwise -> @End

# [ToolNode] ExecuteTools
- **@tools**: [add]

## [Transitions]
- @Default -> Assistant
