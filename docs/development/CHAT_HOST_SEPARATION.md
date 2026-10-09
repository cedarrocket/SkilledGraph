# 标准 chat Host 与 DSL 核心分离

日期：2026-10-09。仅调整代码组织、导入和打包，不修改语言语义或默认 Host 行为。

## 最终布局

- `src/skilledgraph/`：只读解析、GraphSpec、诊断、文件绑定、执行器、原生构图和薄启动器。
- `examples/chat-host/src/sgraph_chat_host/`：标准 chat Host、模型连接配置、首次配置向导、locales、终端行编辑。
- `examples/chat-host/host.py`、`workflow.md`：显式 `@host` 文件引用和可运行示例。
- `sgraph_agent/`：独立的持续会话 agent，显式复用标准 Host 的配置和终端模块。

移除核心包中的 host.py、host_config.py、host_setup.py、host_locales.py、terminal.py。新包随当前项目发行，以保留默认运行体验；它的源码与命名空间独立，不引入 Host 基类或新 DSL 设置。

## 启动与导入约定

没有 `@host` 时，CLI 延迟导入 `sgraph_chat_host.host.main`。有文件 `@host` 时，加载选定入口并传入图文件绝对路径与剩余参数；`--check` 只解析。parse／build／load 不导入标准 Host。

原 `skilledgraph.host*` 和 `skilledgraph.terminal` 导入不再提供；项目内示例、测试和 live 脚本已改用 `sgraph_chat_host`。图文件和命令行参数无需迁移。模型配置文件路径、环境变量、OpenCode session ID、单次执行及动态中断恢复策略保持原有约定。

`runtime` extra 移除 prompt-toolkit；需要终端的 chat／deepseek／mcp／agent extras 继续声明该依赖。纯图运行无需终端编辑器。

## 验证

- Host／配置／首次向导／架构边界共 52 项测试通过。
- 完整 unittest **273 项通过**，包含原有 18 组工作流、sgraph_agent 和新增边界测试；解析器同时检查第 19 份标准 Host 示例。
- 边界测试在新进程中禁止导入 sgraph_chat_host，验证 parse、build、load、--check 和自定义 Host 仍能工作。
- `sgraph examples/chat-host/workflow.md -- --help` 通过；显式文件 Host 用离线回声模型完成管道请求。
- 重新安装 editable 包成功。构建 wheel 并验证新 Host 包齐全，旧 skilledgraph Host 模块不存在，sgraph_agent/workflow.md 仍包含在包中。
- 从 /tmp 加载解包的 wheel，验证默认启动器选择独立 Host；模型创建和执行使用 mock，不调用 API。

完整测试命令：

```bash
.venv/bin/python -m unittest discover -s tests -q
```

异步测试在当前受限沙箱内挂起，停止该次运行后在沙箱外完成上述全量离线回归。首次全量回归只发现示例数量断言仍为 18；加入标准 Host 示例后更新为 19，复跑全部通过。本次没有执行真实模型或 MCP 网络测试。
