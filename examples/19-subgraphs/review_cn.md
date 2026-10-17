# [Config]
- **@trace**: on

# [Node] Examine
[examine] 检查回答中缺失的证据、矛盾与未满足的用户要求。

## [Transitions]
- @Default -> Suggest

# [Node] Suggest
[suggest] 根据检查给出具体修改建议。不要声称已经运行检查程序或工具。

## [Transitions]
- @Default -> @End
