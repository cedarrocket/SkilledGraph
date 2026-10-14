# [Config]
- **@host**: python:./host_cn.py:main
- **@state**: python:./actions_cn.py:State

# [Node] Start
- **@uses**: python:./actions_cn.py:start
>>> 原生 API 并行验收：本文件的边由配套 Host 使用 build_graph 添加，不是新增 DSL 语法。

# [Node] Left
- **@uses**: python:./actions_cn.py:left

# [Node] Right
- **@uses**: python:./actions_cn.py:right

# [Node] RightLast
- **@uses**: python:./actions_cn.py:right_last

# [Node] Join
- **@uses**: python:./actions_cn.py:join

## [Transitions]
- @Default -> @End
