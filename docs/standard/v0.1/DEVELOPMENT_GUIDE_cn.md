# SkilledGraph v0.1 开发与验收指南

更新日期：2026-10-09。本文面向贡献者，不新增语言特性。行为依据是[语言规范](LANGUAGE_SPEC_cn.md)和[功能实现白皮书](IMPLEMENTATION_WHITEPAPER_cn.md)；已完成验收及限制见[当前状态](../../development/STATUS_cn.md)。

## 代码分工

| 目录 | 职责 |
| --- | --- |
| `src/skilledgraph/parsing/` | Markdown 上下文、只读解析与静态验证 |
| `src/skilledgraph/` | GraphSpec、诊断、文件绑定、执行器、原生构图与薄启动器 |
| `examples/chat-host/` | 独立标准 Host、模型配置、终端及首次向导 |
| `examples/01-*` 至 `examples/18-*` | 可运行工作流及原生扩展案例 |
| `sgraph_agent/` | 持续 ReAct 应用、权限检查、工具及上下文管理 |
| `tests/` | 语言样本、离线测试和显式 opt-in 的真实服务测试 |

核心 API 返回原生 LangGraph 对象，不引入第二套图运行时。Host 与执行器的应用策略不得反向成为隐式 DSL 语法。State／Reducer 保持原生定义，不自动补回用户删除的默认字段或合并规则。

## 开发环境与测试

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[chat,agent,mcp]'
.venv/bin/python -m unittest discover -s tests -v
```

Windows PowerShell 使用同样的依赖和测试入口：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[chat,agent,mcp]"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tests/mcp_demo/check_cn.py --output .local-docs/mcp-results.json
```

[跨平台 CI](../../../.github/workflows/tests.yml) 在 Ubuntu、macOS、Windows 上运行同一套离线测试和本地 stdio MCP 验收，覆盖 Python 3.11 与 3.14。CI 关闭 Python UTF-8 模式以发现默认编码依赖；测试读写文本显式使用 UTF-8，含中文输出的示例子进程使用 UTF-8 模式和对应的输出解码。真实模型服务不进入 CI。

`tests/fixtures/language/` 的 Markdown 资料通过 `.gitattributes` 固定为 LF，专门的 `crlf_cn.md` 保留原始 CRLF 字节。换行测试还在运行时生成 LF／CRLF 两种输入，验证解析结果一致且输入字节不变。

Windows 跳过需要 POSIX 工作区文件 API 的 agent 用例和两项 PTY 交互用例；agent 模型配置、请求构造及 CLI 帮助仍执行。这些 skip 表示对应功能未获 Windows 验收，不表示 agent 已支持 Windows。核心 DSL 解析、构图、执行和普通 Host 用例不按操作系统跳过。

只使用解析器可以安装 `-e .`；纯图运行可使用 runtime extra。完整可选功能测试需要相应依赖；缺少依赖的 skip 不应被描述为该功能通过。常规 unittest 使用离线模型和临时资料，不需要真实 API key。真实服务测试必须显式运行，命令和实际用量见[测试说明](../../../tests/live/README_cn.md)。

## 应保持的契约

- 只读解析不导入引用脚本、不构建图、不读取模型配置；保留源文本、精确正文及位置。
- 无隐式 Config、隐式顺序边或自动结束边。前向目标在全文件节点读取后校验。
- 引用路径以图文件目录为基准，不改变 cwd。绑定失败不猜模块或静默降级。
- 显式 API 定义、文件声明和默认值的优先级符合白皮书；未选中的引用不提前加载。
- @uses 接管节点执行，框架不再额外调用模型；正文如何使用由执行器决定。
- 普通 Prompt 与 pyfunction 的模型调用、消息转换和历史提交符合默认策略，只提交需要合并的更新。
- router 在 reducer 合并之后读取 State，返回路由键；工具特殊条件按规范优先级处理。
- 原生 Command 与静态边叠加，表外原生跳转不默认封禁；@End 不取消其他并行分支。
- parse／build／load 不启动 Host。标准 Host 只由默认 CLI 分支延迟选择，自定义 Host 不依赖它。
- 自定义 State、reducer、原生 config／runtime、同步与异步调用以及 interrupt 通道保持可用。

## 验证重点

修改解析器时，验证上下文边界、错误位置、正文保留、前向引用、表格和列表。使用[语言样本](../../../tests/fixtures/language/README_cn.md)及 manifest；不得格式化 crlf_cn.md 的换行或 prompt-extraction_cn.md 的尾部空格。

修改绑定或执行策略时，验证输入和返回契约、调用次数、增量 State 更新、导入缓存和失败行为。涉及异步、并行、Send、reducer 或中断时，验证实际原生执行；不能用成功解析替代运行验收。

修改 Host 时，验证文件路径与 argv 传递、管道和终端输入、配置优先级、中断 ID 对应恢复、取消及退出码。中断节点可能重跑，副作用和恢复安全由相应实现负责。

涉及工具时，区分模型声明和 ToolNode 的可执行工具集合，验证调用 ID 配对、同步／异步执行及资源寿命。MCP 连接由 Host 管理，不加入 DSL 凭据或传输配置。

修改打包时，验证 wheel 内容、项目目录外导入、CLI 和示例数据。核心与标准 Host 的隔离由 tests/test_host_boundary_cn.py 验证。

## 变更与报告

按变更影响执行必要测试，记录实际命令、结果和未覆盖范围。确定性模型验证流程契约，不证明模型智能；真实 API 的有限样本不保证其他模型、材料或平台同样有效。

改变现行语义时同步修订规范、示例和测试。未实现的模块引用、DSL 输出 Schema、文件级执行器等功能，不应被悄悄接受。扩展原生功能时优先使用现有 Python 接入，避免为每项应用需求增加关键字。


## 追踪验收

验证 Config 值与作用域、接收器缺失、原生 load/build 返回值、State/Reducer 不变、静态与条件路由、Command/Send、真实节点进入、循环与并发、同步与异步、Schema/Runtime 注入、中断恢复、错误、显式摘要和默认内容排除。覆盖关闭追踪的嵌套图、其他 callbacks 及原生子图发现。执行完整回归，关闭追踪时保持原有行为。


## 子图验收

覆盖 @source 作用域、正文、名称与 Markdown 字面量；独立 Schema 默认值；相对路径、缺失／非法子文件、符号链接引用环、重复／菱形引用及重新构建快照；原生 reducer 合并；子图 @End 与父 router 顺序；工具／模型／context 传递；并发 Send；同步／异步中断恢复；逐文件追踪开关与父执行关联。离线执行中英文 19-subgraphs 示例。parse／--check 仍只检查当前文件。
