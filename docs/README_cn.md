# 文档入口

[中文](README_cn.md) | [English](README_en.md) | [语言版本 / Languages](LOCALIZATION_cn.md)

这里汇总了 SkilledGraph 的全部公开文档。如果你是**第一次使用本项目或想学习如何编写 `.md` 工作流**，请直接从第一行 **[新手教程与 DSL 开发手册](tutorials/README_cn.md)** 开始阅读！

| 类别 | 推荐入口 | 适合谁看？ |
| --- | --- | --- |
| **新手教程与开发手册（推荐首选）** | **[10分钟快速上手](tutorials/01-QUICKSTART_cn.md)**、**[循序渐进实战](tutorials/02-STEP-BY-STEP_cn.md)**、**[DSL 协同开发速查手册](tutorials/03-DSL-HANDBOOK_cn.md)**（[总目录](tutorials/README_cn.md)） | 所有使用者、工作流作者：用直观图解和可运行例子学习如何写 DSL 与 Python 扩展、排查常见错误 |
| **CLI 与日常使用指南** | [使用指南](development/USAGE_cn.md)、[开发与验收指南](standard/v0.1/DEVELOPMENT_GUIDE_cn.md) | 查询 `sgraph` 命令行参数、环境变量、配置向导细节与贡献验证方法 |
| **现行语言与实现标准** | [v0.1 标准文档集](standard/v0.1/README_cn.md)（[语言规范](standard/v0.1/LANGUAGE_SPEC_cn.md)、[实现白皮书](standard/v0.1/IMPLEMENTATION_WHITEPAPER_cn.md)） | 框架维护者、解析器开发者：查阅精确语法边界、组件职责契约和公共 API 规范 |
| **状态与实测验收证据** | [当前状态](development/STATUS_cn.md) | 了解已实现能力边界、离线/真实模型验收报告与已知限制 |

### 文档效力说明

- `tutorials/` 与 `development/USAGE_cn.md` 是面向人类开发者的教学与操作指南；`examples/` 提供 18 组可运行示例，`tests/fixtures/` 提供语言解析器的验收样本。
- `standard/v0.1/LANGUAGE_SPEC_cn.md` 与 `IMPLEMENTATION_WHITEPAPER_cn.md` 定义底层的权威语法契约与组件职责。
- `development/` 下的各阶段报告与 JSON 实测记录属于非规范性证据，仅反映测试当日的结果，不替代现行语言标准。
