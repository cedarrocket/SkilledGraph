# SkilledGraph 新手教程与 DSL 开发指南

[中文](README_cn.md) | [English](README_en.md)

欢迎来到 SkilledGraph 教程目录！

如果你打开过 `docs/standard/v0.1/`，你可能会觉得它像一份严苛的编译器法律条文——那里充满了 EBNF 语法、字节偏移、责任边界和“必须/不得”。作为**框架开发标准与语言契约**，它是非常合格的；但作为**人类开发者的入门教程**，它缺乏直观的心智模型和循序渐进的引导。

这个 `docs/tutorials/` 目录专为**使用者与工作流开发者**编写。我们抛开晦涩的编译器术语，用直观的图解、可运行的例子和清晰的“人话”，带你快速掌握 SkilledGraph。

---

## 一句话理解 SkilledGraph

> **用 Markdown 写 Prompt 和流程图，用普通 Python 函数写数据和逻辑，底层自动编译成原生 LangGraph。**

在传统 Agent 开发中，你往往需要把大段 Prompt 字符串硬编码在 Python 代码里，还要写一堆样板代码来连线节点。而在 SkilledGraph 中：
- **流程长什么样、Prompt 怎么写** → 全部放在干净的 `.md` 文件里，一目了然。
- **怎么查数据、怎么调接口、怎么校验结果** → 全部放在同目录的 `.py` 文件里，保持纯正的 Python 体验。
- **状态管理、断点恢复、并发调度** → 100% 原生 LangGraph，不发明二手轮子。

---

## 阅读路线图

无论你是第一次接触本项目，还是正在编写自己的复杂 Agent，都可以按以下顺序阅读：

### 1. [10 分钟快速上手 (01-QUICKSTART_cn.md)](01-QUICKSTART_cn.md)
**适合人群**：第一次接触 SkilledGraph，想立刻跑通第一个工作流的人。
- 环境安装与免 API Key 离线体验
- 3 个核心概念建立心智模型（Node、Transitions、State）
- 亲手写出第一个单节点助手与双节点流水线
- 如何配置真实大模型（OpenAI 兼容接口 / DeepSeek / 本地模型）

### 2. [循序渐进实战教程 (02-STEP-BY-STEP_cn.md)](02-STEP-BY-STEP_cn.md)
**适合人群**：已经跑通 Hello World，想学习如何在工作流里接 Python 代码、做条件分支、调工具和人工确认的人。
- **第 1 站：条件分支与模型选路** —— 让 LLM 自己决定下一步走哪条路
- **第 2 站：用 `pyfunction` 喂数据** —— 先跑 Python 拿材料，再连同 Prompt 一起发给模型
- **第 3 站：用 `python` 节点 + `@router` 写硬核逻辑** —— 自定义 `State`、精确校验与失败重试循环
- **第 4 站：工具调用 (`ToolNode`)** —— 搭建标准的 ReAct 工具执行循环
- **第 5 站：人工介入 (`request_input`)** —— 运行中途暂停询问用户，拿到回复后无缝恢复
- **第 6 站：脱离默认聊天框 (`@host`)** —— 编写自己的业务入口脚本，彻底掌控输入输出

### 3. [DSL 与 Python 协同开发手册 (03-DSL-HANDBOOK_cn.md)](03-DSL-HANDBOOK_cn.md)
**适合人群**：日常开发时放在手边随时查阅的语法与模式参考书。
- Markdown DSL 完整语法速查表（标题、4 个 `@` 配置项、2 种跳转表、3 个保留标记）
- 5 种节点执行模式全对比（默认 Prompt vs `pyfunction` vs `python` vs `request_input` vs `monty`）
- 数据流与消息历史（`MessagesState`）究竟是怎么传递的？
- Python API 集成指南（`parse_graph` / `build_graph` / `load_graph` 与原生 LangGraph 混编）
- 新手最容易踩的 10 个坑与排查清单（Troubleshooting）

---

## 与现有文档的关系

| 目录 | 定位 | 什么时候看它？ |
| --- | --- | --- |
| **`docs/tutorials/`（本目录）** | **新手教程与实战开发手册** | 学习怎么写 `.md` 工作流、怎么配 `.py` 文件、日常查语法与排错 |
| [`examples/`](../../examples/README_cn.md) | **18 个官方可运行示例** | 想直接复制现成模板（如 CSV 审计、知识库问答、并行审查）时 |
| [`docs/development/USAGE_cn.md`](../development/USAGE_cn.md) | **CLI 与环境变量参考** | 查 `sgraph` 命令行参数、环境变量名、配置向导细节时 |
| [`docs/standard/v0.1/`](../standard/v0.1/README_cn.md) | **语言规范与实现白皮书** | 修改 SkilledGraph 源码、开发自定义执行器，或确认极端边缘语法契约时 |

准备好开始了吗？请直接打开 **[第一篇：10 分钟快速上手 (01-QUICKSTART_cn.md)](01-QUICKSTART_cn.md)**！
