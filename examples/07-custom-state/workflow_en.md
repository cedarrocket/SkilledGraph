# [Config]
- **@state**: python:./state_en.py:State

# [Node] Analyze

Read the material and produce a self-contained analysis summary.

## [Transitions]
- @Default -> Report

# [Node] Report

Write a concise report from the currently visible summary.

## [Transitions]
- @Default -> @End
