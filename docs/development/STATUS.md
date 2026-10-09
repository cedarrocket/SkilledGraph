# 当前实现与验收范围

更新日期：2026-10-09。当前版本为 0.1.0.dev0。语言和运行契约见[标准文档](../standard/v0.1/README.md)，安装与使用见[使用指南](USAGE.md)。

## 已实现

- 只读 Markdown 解析、精确正文与源码位置诊断。
- parse_graph、build_graph、load_graph，返回原生 Builder 或编译图。
- 默认 Prompt、python／pyfunction、router、State／Reducer 原生接入。
- ToolNode、工具选择、工具信号路由与完整工具循环。
- sgraph 启动器和独立[标准 chat Host](../../examples/chat-host/README.md)：单次执行、连接向导、终端编辑、动态中断恢复。
- 可选 monty 执行器，以及持续会话的 [sgraph_agent](../../sgraph_agent/README.md)。

18 组工作流与标准 Host 示例覆盖串行、条件、工具、人工确认、原生并行、Send 和自定义 reducer。并行及动态分发通过 Python／原生 API 接入，没有 DSL fan-out 语法。

## 测试证据

最近完整离线回归为 **273 项 unittest 通过**。测试包括实际原生构图与执行、消息及 reducer 处理、并行／异步、中断恢复、工具检查和 Host 隔离。离线模型替身只证明相应流程及数据契约。

| 范围 | 公开记录 |
| --- | --- |
| 解析、绑定和基础执行 | [M1](M1_PARSER.md)、[M2](M2_BUILDING.md)、[M3～M5](M3_M5_COMPLETION.md) |
| 工具与本地 MCP | [工具](TOOLS_COMPLETION.md)、[MCP](MCP_ACCEPTANCE.md) |
| Host 与连接 | [中断](HOST_INTERRUPT_ACCEPTANCE.md)、[配置向导](HOST_SETUP_ACCEPTANCE.md)、[独立分离](CHAT_HOST_SEPARATION.md) |
| 真实模型连接 | [DeepSeek](DEEPSEEK_ACCEPTANCE.md)、[OpenCode Go](OPENCODE_GO_ACCEPTANCE.md) |
| 实用工作流 | [五个实用 agent](PRACTICAL_AGENTS_ACCEPTANCE.md)、[高级 reducer](ADVANCED_REDUCERS_ACCEPTANCE.md)、[原生并行](PARALLEL_ACCEPTANCE.md) |
| 终端 agent | [sgraph_agent](SGRAPH_AGENT_ACCEPTANCE.md) |

报告及配套 JSON 保留各次测试结果，包括中间失败和修正。早期报告中的依赖、目录、功能范围和累计测试数是当时的快照，当前入口以本页和使用指南为准。

## 已知边界

- 个人脚本工具，不承诺所有 LangGraph 功能、模型或部署方式均已验收。
- 基础 Host 不延续下一次执行的消息；持续会话由 sgraph_agent 或自定义 Host 提供。
- 模块引用、文件级执行器选择、DSL 输出 Schema、多模型声明及 DSL 并行语法未提供。
- 本地 stdio MCP 已测试，远程 MCP 与跨平台运行未验收；sgraph_agent 当前使用 POSIX 文件／进程能力。
- 历史压缩有损；进程内 checkpoint 不提供跨进程持久化保证。
- 工具审批不是 Bash OS 沙箱；重试和中断不自动保证副作用只执行一次。
- 部分原生适配使用固定版本的私有 API，依赖升级需复验。
