# SkilledGraph

[中文](README_cn.md) | [English](README_en.md) | [语言版本说明 / Localization](docs/LOCALIZATION_en.md)

> **用 Markdown 写 Prompt 和流程图，用普通 Python 函数写数据和逻辑，底层编译为 100% 原生 LangGraph。**

在开发 LLM 工作流和 Agent 时，把几百行 Prompt 塞进 Python 字符串里不仅难以维护，还会让图的节点连线淹没在样板代码中。

**SkilledGraph** 是一个轻量级的个人工作流 DSL：
- **流程与提示词留在 Markdown (`.md`)**：有哪些节点、每个节点跟模型说什么话、下一步跳去哪里，打开文档一目了然。
- **数据与逻辑留在 Python (`.py`)**：读文件、查数据库、调工具、校验格式，全部用最普通的 Python 函数编写。
- **零自研调度器，100% 原生 LangGraph**：编译产物就是标准的 LangGraph `StateGraph` / `CompiledStateGraph`，原生支持 `MessagesState`、自定义 Reducer、ToolNode、断点恢复（Interrupt）与并发分支。

---

## 30 秒看懂 SkilledGraph

只需一个 `hello.md`，就能定义一个带工具调用循环的完整工作流：

```markdown
# [Node] Assistant

使用加法工具计算用户请求，再回答结果。

## [Transitions]
| 条件 | 目标节点 | 说明 |
| --- | --- | --- |
| @ToolCalls | ExecuteTools | 模型请求调用工具时，跳去执行工具 |
| @Otherwise | @End | 没有工具调用时，直接输出最终回答并结束 |

# [ToolNode] ExecuteTools
- **@tools**: [add]

## [Transitions]
- @Default -> Assistant
```

需要在调模型前先用 Python 读取本地数据？加一行 `- **@uses**: pyfunction:./tools.py:prepare`；
需要运行中途停下来等人工确认？加一行 `- **@uses**: request_input:请确认是否发送？`。

---

## 快速安装与体验

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[chat]'
```

### 1. 免 API Key 离线体验

仓库内置了确定性的离线演示模型与示例，克隆后无需配置任何密钥即可直接运行：

```bash
# 检查工作流语法（纯静态检查，毫秒级完成）
sgraph --check examples/01-assistant/workflow.md

# 体验完整的模型请求工具 -> ToolNode 执行 -> 最终回答循环
sgraph examples/10-tool-calling/workflow.md

# 体验动态中断（Interrupt）与终端人工回复恢复
sgraph examples/11-interrupt/workflow.md -- --model-factory python:../support/demo_model.py:create
```

### 2. 连接真实大模型（交互式向导）

直接运行任意未指定自定义 Host 的工作流：

```bash
sgraph examples/01-assistant/workflow.md
```

首次运行时会自动启动中/英文配置向导（后续可随时用 `sgraph examples/01-assistant/workflow.md -- --setup` 重新配置），引导你填入：
- **API 基础地址**（如 `https://api.openai.com/v1`、DeepSeek、OpenRouter 或本地 Ollama/LM Studio 地址）
- **模型 ID** 与 **API Key**（凭据安全保存在用户目录 `~/.config/skilledgraph/host.json`，绝不写进 Markdown 工作流）

---

## 从这里开始学习（新手教程与开发手册）

我们提供了一套专为人类开发者编写的循序渐进教程，建议按顺序阅读：

1. **[教程总入口 (`docs/tutorials/README.md`)](docs/tutorials/README.md)**：核心理念与文档导航。
2. **[第一篇：10 分钟快速上手 (`01-QUICKSTART.md`)](docs/tutorials/01-QUICKSTART.md)**：安装、单节点助手、多步流水线与对话历史传递机制。
3. **[第二篇：循序渐进实战教程 (`02-STEP-BY-STEP.md`)](docs/tutorials/02-STEP-BY-STEP.md)**：6 站掌握模型选路、`pyfunction` 材料函数、`python` 校验节点、`ToolNode` 工具循环、`request_input` 人工介入与自定义 `@host`。
4. **[第三篇：DSL 与 Python 协同开发手册 (`03-DSL-HANDBOOK.md`)](docs/tutorials/03-DSL-HANDBOOK.md)**：完整语法速查表、5 种节点模式对比、Python API（`parse_graph` / `build_graph` / `load_graph`）混编指南，以及**新手最常踩的 10 个坑排错表**。

---

## 18 个开箱即用的示例与实战应用

所有示例均位于 [`examples/`](examples/README.md)，涵盖从 6 行代码的最小节点到复杂的多步工程 Agent（均支持 `--demo` 离线运行）：

- **基础构建块（`01` ~ `11`）**：单节点对话、多步链、列表/表格条件路由、Python 路由、`pyfunction` 材料注入、自定义 State Reducer、原生 `Command.goto`、纯计算图、[工具调用 (`10-tool-calling`)](examples/10-tool-calling/workflow.md)、[人工中断恢复 (`11-interrupt`)](examples/11-interrupt/workflow.md)。
- **5 个实用工程 Agent（`12` ~ `16`）**：本地知识库检索与引用核验、CSV 报表审计与数值验算、带人工审批的邮件草稿助手、三视角并行代码审查、动态 `Send` 批量文档摘要（详见[实用 Agent 验收记录](docs/development/PRACTICAL_AGENTS_ACCEPTANCE.md)）。
- **高级状态与并发实验（`17` ~ `18`）**：[多轮 ReAct 与上下文压缩](examples/17-react-memory/README.md)、[并发 Reducer 实验室](examples/18-reducer-lab/README.md)（详见[高级 Reducer 验收记录](docs/development/ADVANCED_REDUCERS_ACCEPTANCE.md)）。
- **独立终端 Coding Agent（[`sgraph_agent`](sgraph_agent/README.md)）**：基于 SkilledGraph 构建的持续多轮 ReAct 终端助手，支持文件读写、Bash、Monty 沙箱、逐次工具审批与自动上下文压缩（安装 `pip install -e '.[agent]'` 后运行 `sgraph-agent`，详见[验收报告](docs/development/SGRAPH_AGENT_ACCEPTANCE.md)）。

---

## 在 Python 代码中作为库使用

除了使用 `sgraph` 命令行启动器，你也可以通过 3 个核心 API 将 `.md` 工作流直接嵌入任何 Python 项目：

```python
from langchain_core.messages import HumanMessage
from skilledgraph import parse_graph, build_graph, load_graph

# 1. 只读静态解析（不导入任何 Python 脚本）
spec = parse_graph("examples/01-assistant/workflow.md")

# 2. 获取原生 LangGraph StateGraph Builder（可继续调用 builder.add_edge 等原生方法）
builder = build_graph(spec, model=my_model)

# 3. 直接编译为原生 CompiledStateGraph 并调用 invoke / ainvoke / stream
graph = load_graph(spec, model=my_model, tools=my_tools)
result = graph.invoke({"messages": [HumanMessage(content="你好！")]})
```

---

## 文档全景导航

| 我想看... | 推荐入口 |
| --- | --- |
| **新手入门、图文教程、常见报错排查** | **[新手教程与 DSL 开发手册 (`docs/tutorials/`)](docs/tutorials/README.md)** |
| **命令行参数、环境变量、配置向导细节** | [CLI 与使用指南 (`docs/development/USAGE.md`)](docs/development/USAGE.md)、[独立聊天 Host 说明](examples/chat-host/README.md) |
| **可复制的完整代码模板** | [18 组官方示例目录 (`examples/`)](examples/README.md) |
| **严谨的编译器语言规范与 API 契约** | [v0.1 标准文档集](docs/standard/v0.1/README.md)：[语言规范](docs/standard/v0.1/LANGUAGE_SPEC.md)、[实现白皮书](docs/standard/v0.1/IMPLEMENTATION_WHITEPAPER.md)、[开发指南](docs/standard/v0.1/DEVELOPMENT_GUIDE.md) |
| **测试覆盖、真实模型与跨平台验收证据** | [文档分类入口](docs/README.md)、[项目当前状态](docs/development/STATUS.md)、[工具记录](docs/development/TOOLS_COMPLETION.md)、[语法验收样本](tests/fixtures/language/README.md) |

## License

Copyright 2026 cedarrocket and contributors.

本项目采用 [Apache License 2.0](LICENSE) 开源许可证。
