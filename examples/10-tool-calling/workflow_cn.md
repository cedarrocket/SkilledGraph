# [Config]

- **@host**: python:./host_cn.py:main

# [Node] Assistant

使用加法工具计算用户请求，再回答结果。

## [Transitions]

| 条件 | 目标 |
| --- | --- |
| @ToolCalls | ExecuteTools |
| @Otherwise | @End |

# [ToolNode] ExecuteTools

- **@tools**: [add]

## [Transitions]

- @Default -> Assistant
