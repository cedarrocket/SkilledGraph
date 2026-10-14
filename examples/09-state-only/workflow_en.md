# [Config]
- **@host**: python:./host_en.py:main
- **@state**: python:./state_en.py:State

# [Node] Increment
- **@uses**: python:./tools_en.py:increment

## [Transitions]
- @Default -> Double

# [Node] Double
- **@uses**: python:./tools_en.py:double

## [Transitions]
- @Default -> @End
