# [Config]
- **@host**: python:./host_en.py:main
- **@state**: python:./actions_en.py:State

# [Node] Start
- **@uses**: python:./actions_en.py:start
>>> Host adds native parallel edges and a waiting join.

# [Node] SourceA
- **@uses**: python:./actions_en.py:source_a

# [Node] SourceB
- **@uses**: python:./actions_en.py:source_b

# [Node] Report
- **@uses**: python:./actions_en.py:report

## [Transitions]
- @Default -> @End
