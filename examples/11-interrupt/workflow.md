# [Node] AskUser
- **@uses**: request_input:请补充你希望采用的输出格式，例如：简短列表。

## [Transitions]
- @Default -> Report

# [Node] Report
请根据用户补充的信息回复。

## [Transitions]
- @Default -> @End
