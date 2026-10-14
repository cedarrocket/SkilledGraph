# [Config]
- **@host**: python:./host_cn.py:main
- **@state**: python:./actions_cn.py:State

# [Node] Start
- **@uses**: python:./actions_cn.py:start
>>> Host 通过原生 Builder 添加并行边和等待汇合。

# [Node] SourceA
- **@uses**: python:./actions_cn.py:source_a

# [Node] SourceB
- **@uses**: python:./actions_cn.py:source_b

# [Node] Report
- **@uses**: python:./actions_cn.py:report

## [Transitions]
- @Default -> @End
