# SkilledGraph

SkilledGraph 是面向个人脚本的 Markdown DSL：用几行文本描述 LLM 节点和转移，用外部 Python 处理需要代码的逻辑，复杂任务交给用户自己的 Host 与原生 LangGraph。

当前开发依据是 **[v0.1 标准文档集](docs/standard/v0.1/README.md)**。v0.1 当前范围的开发与确定性测试已完成：提供解析、原生图构建、普通 Prompt、python／pyfunction、router、State／Reducer 接入及 sgraph 启动器。273项测试通过；DeepSeek 与本地 MCP 已受控验收，跨平台运行尚未验收。

- [语言规范](docs/standard/v0.1/LANGUAGE_SPEC.md)：精确语法、文本提取、控制流及诊断。
- [功能实现白皮书](docs/standard/v0.1/IMPLEMENTATION_WHITEPAPER.md)：架构、API、绑定、默认执行器及原生扩展。
- [开发与验收指南](docs/standard/v0.1/DEVELOPMENT_GUIDE.md)：阶段计划、最小解析里程碑及完成标准。
- [示例](examples/README.md)与[验收输入](tests/fixtures/language/README.md)：后续实现验证材料。

用户可先阅读[使用指南](docs/development/USAGE.md)和示例，贡献者从标准文档及[当前状态](docs/development/STATUS.md)进入。规范定义契约，验收报告说明实际测试范围；文档分类见[文档入口](docs/README.md)。

## 工具调用示例

运行 `.venv/bin/sgraph examples/10-tool-calling/workflow.md`，即可离线体验模型请求工具、原生 ToolNode 执行与最终回答。规则见[标准语言规范](docs/standard/v0.1/LANGUAGE_SPEC.md)，验证见[工具功能记录](docs/development/TOOLS_COMPLETION.md)。

## 首次 API 配置

基础 chat Host 已独立为[标准示例](examples/chat-host/README.md)，源码位于 `examples/chat-host/src/sgraph_chat_host/`。DSL 核心位于 `src/skilledgraph/`；`sgraph` 在未声明 `@host` 时延迟选择标准示例，保留开箱即用的运行方式。

安装 `skilledgraph[chat]` 后，在终端直接执行 `sgraph examples/01-assistant/workflow.md`。没有显式模型设置及已保存配置时，会启动中文／英文配置向导，收集 API 地址、模型 ID、密钥、接口模式及可选请求头。重新配置可用 `sgraph examples/01-assistant/workflow.md -- --setup`。配置和凭据保存在用户目录，不写入 DSL；详见[使用指南](docs/development/USAGE.md)。

## 实用 agent 示例

新增五个可运行示例：本地知识库问答、CSV 检查、人工确认邮件草稿、并行代码审查、动态批量摘要。入口见[示例目录](examples/README.md)，实现边界和真实测试结果见[验收记录](docs/development/PRACTICAL_AGENTS_ACCEPTANCE.md)。每例支持 `--demo` 离线体验；前三例主要由 DSL 编排，后两例通过原生 API 接入并行能力。

高级 State／Reducer 示例见[循环 ReAct 与压缩](examples/17-react-memory/README.md)、[并发 Reducer 实验室](examples/18-reducer-lab/README.md)及[验收记录](docs/development/ADVANCED_REDUCERS_ACCEPTANCE.md)。

## 真实终端 agent

[sgraph_agent](sgraph_agent/README.md)提供持续 ReAct 会话、Responses API、基础文件／Bash／Monty 工具、工具执行前逐次许可和压缩节点。安装 `skilledgraph[agent]` 后运行 `sgraph-agent`，具体连接命令与边界见 README；[真实及离线验收](docs/development/SGRAPH_AGENT_ACCEPTANCE.md)已完成。
