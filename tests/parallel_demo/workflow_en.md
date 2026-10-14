# [Config]
- **@host**: python:./host_en.py:main
- **@state**: python:./actions_en.py:State

# [Node] Start
- **@uses**: python:./actions_en.py:start
>>> Native parallel acceptance: the companion Host adds edges through build_graph, without introducing DSL syntax.

# [Node] Left
- **@uses**: python:./actions_en.py:left

# [Node] Right
- **@uses**: python:./actions_en.py:right

# [Node] RightLast
- **@uses**: python:./actions_en.py:right_last

# [Node] Join
- **@uses**: python:./actions_en.py:join

## [Transitions]
- @Default -> @End
