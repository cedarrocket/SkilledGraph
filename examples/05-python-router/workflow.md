# [Config]
- **@state**: python:./state.py:State

# [Node] Inspect
- **@uses**: python:./tools.py:inspect
- **@router**: python:./tools.py:route

>>> 代码更新 status，router 读取合并后的 State；此节点没有自动模型调用。

## [Transitions]
- ready -> Report
- missing -> RequestMaterial

# [Node] Report

根据历史中的输入与检查结果生成简明报告。

## [Transitions]
- @Default -> @End

# [Node] RequestMaterial

请用户提供待分析材料。

## [Transitions]
- @Default -> @End
