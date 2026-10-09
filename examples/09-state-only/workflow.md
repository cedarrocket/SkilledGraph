# [Config]
- **@host**: python:./host.py:main
- **@state**: python:./state.py:State

# [Node] Increment
- **@uses**: python:./tools.py:increment

## [Transitions]
- @Default -> Double

# [Node] Double
- **@uses**: python:./tools.py:double

## [Transitions]
- @Default -> @End
