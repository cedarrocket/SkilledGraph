# [Config]
- **@host**: python:./host.py:main
- **@state**: python:./actions.py:State

# [Node] Start
- **@uses**: python:./actions.py:start
>>> 原生 API 并行验收：本文件的边由配套 Host 使用 build_graph 添加，不是新增 DSL 语法。

# [Node] Left
- **@uses**: python:./actions.py:left

# [Node] Right
- **@uses**: python:./actions.py:right

# [Node] RightLast
- **@uses**: python:./actions.py:right_last

# [Node] Join
- **@uses**: python:./actions.py:join

## [Transitions]
- @Default -> @End
