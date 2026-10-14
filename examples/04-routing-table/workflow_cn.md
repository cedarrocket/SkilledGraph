# [Node] Evaluate

检查已有材料是否足以形成报告。
足够时只返回 enough；不足时只返回 insufficient。不要输出解释或其他内容。

## [Transitions]
| 路由 | 目标 | 说明 |
| --- | --- | --- |
| enough | Report | 材料足够 |
| insufficient | RequestMaterial | 请求用户补充 |

# [Node] Report

根据已有材料生成简明报告。

## [Transitions]
| 路由 | 目标 |
| --- | --- |
| @Default | @End |

# [Node] RequestMaterial

说明还需要用户补充哪些材料，然后等待本次运行结束。

## [Transitions]
| 路由 | 目标 |
| --- | --- |
| @Default | @End |
