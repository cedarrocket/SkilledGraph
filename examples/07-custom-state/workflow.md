# [Config]
- **@state**: python:./state.py:State

# [Node] Analyze

阅读用户材料，给出能够独立阅读的分析摘要。

## [Transitions]
- @Default -> Report

# [Node] Report

根据当前可见的分析摘要生成简明报告。

## [Transitions]
- @Default -> @End
