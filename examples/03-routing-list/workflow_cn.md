# [Node] Evaluate

检查已有材料是否足以形成报告。
足够时只返回 enough；不足时只返回 insufficient。不要输出解释或其他内容。

## [Transitions]
- enough -> Report
- insufficient -> RequestMaterial

# [Node] Report

根据已有材料生成简明报告。

## [Transitions]
- @Default -> @End

# [Node] RequestMaterial

说明还需要用户补充哪些材料，然后等待本次运行结束。

## [Transitions]
- @Default -> @End
