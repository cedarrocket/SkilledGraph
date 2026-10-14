# [Config]

- **@host**: python:./host_en.py:main

# [Node] Assistant

Use the addition tool for the requested calculation, then answer.

## [Transitions]

| Condition | Target |
| --- | --- |
| @ToolCalls | ExecuteTools |
| @Otherwise | @End |

# [ToolNode] ExecuteTools

- **@tools**: [add]

## [Transitions]

- @Default -> Assistant
