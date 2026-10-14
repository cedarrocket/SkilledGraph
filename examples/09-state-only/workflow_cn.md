# [Config]
- **@host**: python:./host_cn.py:main
- **@state**: python:./state_cn.py:State

# [Node] Increment
- **@uses**: python:./tools_cn.py:increment

## [Transitions]
- @Default -> Double

# [Node] Double
- **@uses**: python:./tools_cn.py:double

## [Transitions]
- @Default -> @End
