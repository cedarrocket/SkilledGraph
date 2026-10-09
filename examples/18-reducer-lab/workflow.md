# [Config]
- **@host**: python:./host.py:main
- **@state**: python:./actions.py:State

# [Node] Start
- **@uses**: python:./actions.py:start
>>> Host 通过原生 Builder 添加并行边和等待汇合。

# [Node] SourceA
- **@uses**: python:./actions.py:source_a

# [Node] SourceB
- **@uses**: python:./actions.py:source_b

# [Node] Report
- **@uses**: python:./actions.py:report

## [Transitions]
- @Default -> @End
