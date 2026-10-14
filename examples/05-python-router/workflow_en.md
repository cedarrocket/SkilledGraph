# [Config]
- **@state**: python:./state_en.py:State

# [Node] Inspect
- **@uses**: python:./tools_en.py:inspect
- **@router**: python:./tools_en.py:route

>>> Code updates status; router reads merged State. This node does not automatically invoke a model.

## [Transitions]
- ready -> Report
- missing -> RequestMaterial

# [Node] Report

Write a concise report using the input and inspection results in history.

## [Transitions]
- @Default -> @End

# [Node] RequestMaterial

Ask the user for material to analyze.

## [Transitions]
- @Default -> @End
