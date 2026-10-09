# 文档入口

公开文档分为三类，避免把设计承诺与某一次测试结果混为一谈。

| 类别 | 入口 | 用途 |
| --- | --- | --- |
| 现行标准 | [v0.1 标准文档](standard/v0.1/README.md) | 语言规则、执行契约和公共接口 |
| 使用与贡献 | [使用指南](development/USAGE.md)、[开发与验收指南](standard/v0.1/DEVELOPMENT_GUIDE.md) | 安装、运行、扩展及贡献验证 |
| 状态与实测证据 | [当前状态](development/STATUS.md) | 已实现能力、验收报告和已知边界 |

`standard/v0.1/LANGUAGE_SPEC.md` 定义语言；`IMPLEMENTATION_WHITEPAPER.md` 定义组件、API 和默认执行策略。示例位于 `examples/`，语言验收输入位于 `tests/fixtures/`。

`development/` 的实现及验收报告是非规范性证据；其中阶段报告描述报告日期的状态，不能覆盖现行标准或作为当前支持范围的唯一依据。JSON 记录保留实际测试结果及中间失败，不代表普遍质量保证。

内部讨论、撤回方案、旧规范、接口快照和文档交付记录不属于公开文档，也不包含在发布分支中。
