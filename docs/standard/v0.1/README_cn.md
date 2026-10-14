# SkilledGraph v0.1 标准文档

版本：v0.1。更新日期：2026-10-09。当前实现和验证边界见[项目状态](../../development/STATUS_cn.md)，安装与运行见[使用指南](../../development/USAGE_cn.md)。

## 文档与权威范围

| 文档 | 定义范围 | 建议读者 |
| --- | --- | --- |
| [语言规范](LANGUAGE_SPEC_cn.md) | 文件结构、语法、正文提取、控制流及诊断边界 | 用户、解析器开发者、审计者 |
| [功能实现白皮书](IMPLEMENTATION_WHITEPAPER_cn.md) | 组件职责、公共 API、原生接入及默认执行器行为 | 框架与 Host 开发者 |
| [开发与验收指南](DEVELOPMENT_GUIDE_cn.md) | 代码分工、贡献验证和兼容性检查 | 贡献者、维护者 |

语言规则以语言规范为准；组件、接口和默认执行策略以白皮书为准。开发指南不新增语言规则。使用指南和测试报告通过引用使用标准，不建立另一套规则。出现矛盾时应修正文档，不根据旧提案或实现偶然行为自动裁决。

“必须／不得”表示当前契约；“推荐”表示建议；“暂缓／未定”不构成已支持功能。规范中的工具、request_input 和 monty 扩展章节同样属于现行约定。

## 项目定位

SkilledGraph 是个人脚本工具：用 Markdown 表达模型指令和显式流程，把代码留给外部函数，把 State、Reducer、调度和高级能力留给原生 LangGraph。独立的[标准 chat Host 示例](../../../examples/chat-host/README_cn.md)提供开箱即用体验，高级用户可以取得原生 Builder 或编译图继续开发。

不建立通用 Agent Framework，不镜像全部 LangGraph API，不增加独立 State 类型系统、表达式语言或自研调度器。Skill 风格的可读性不构成 Agent Skills／SKILL.md 标准兼容承诺。

## 最小示例

```markdown
# [Node] Assistant

回答用户的问题。

## [Transitions]
- @Default -> @End
```

第一个节点是入口；节点顺序不产生隐式边。未声明 @uses 的节点采用默认 Prompt 策略。模型、初始输入和运行资源由 Host 提供。配置模型后，可以保存为 hello.md 并运行 `sgraph hello.md`。

更多内容见[示例目录](../../../examples/README_cn.md)、[语言验收输入](../../../tests/fixtures/language/README_cn.md)及[使用指南](../../development/USAGE_cn.md)。

## 变更管理

改变输入接受规则、公共接口或可观察语义时，应修订相应规范、示例和测试，并明确记录兼容性影响。默认执行器内部策略可以调整，但影响用户行为时仍须记录，不以实现细节为由隐性改变契约。
