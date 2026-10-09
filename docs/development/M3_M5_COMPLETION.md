# M3～M5：默认执行、Host 与兼容验收

> 非规范性阶段报告：本文保留当时的实现和测试状态；当前支持范围与运行方式见[项目状态](STATUS.md)和[使用指南](USAGE.md)。

日期：2026-10-09。v0.1 当前范围的开发已完成；未实现项仅包括规范明示暂缓功能和本文列明的未覆盖环境。此前 M1／M2 记录是阶段历史，本文件说明本轮新增实现。

## 模块分工

- execution.py：普通 Prompt 和 pyfunction 的模型输入、材料转换、消息更新和默认文本选路。
- binding.py：文件对象加载、python／pyfunction 绑定；不接管 reducer。
- building.py：Schema 选择、执行器绑定、原生节点与边装配；返回可继续修改的 Builder。
- host.py：最小 chat Host、环境模型选择、模型工厂、输入和逐节点回复显示。
- cli.py／__main__.py：只读选择文件 Host、绝对路径和参数透传、检查模式及命令入口。

默认模型依赖放在 Host；parse／build／load 不读取模型环境或启动 Host。不增加框架 Runtime、通用插件基类或 DSL 配置表达式。

## 默认路由值的实现决策

普通 Prompt／内置 pyfunction 无 router 且有条件表时，执行器从本次 AIMessage 文本取得裁剪后的键，严格查表，返回原生 Command(update={"messages": ...}, goto=目标)。更新中保留原始回复，路由值不存入 State，不从 reducer 之后的历史反推。

因此同一条 DSL 条件边只由这次 Command 调度，构建器不重复挂另一条条件边；同时向原生 Builder 声明可能目标用于校验和图示。外部 router 仍挂原生条件边，执行顺序保持节点更新合并后调用。普通代码 Command.goto 仍与 DSL 已声明边叠加。

这不新增用户返回协议：选择键、查表和构造 Command 均为内置实现的硬编码。自定义绑定不会因名为 pyfunction 就被框架额外调用模型或套用此行为。核心不把任意用户返回值当作键。

原型已验证：reducer 有意把所有消息改成 redacted 时仍按原始模型回复选路；同步与异步并发运行不串键；条件跳转后的检查点暂停恢复沿已确定路径继续。没有共享可变路由槽或私有 State 字段。

## 默认执行细节

静态正文非空时为 SystemMessage，后接历史和本次材料；只提交新增材料和 AI 回复。普通 Prompt 没有材料函数，空正文仍调用模型。pyfunction 的 None／空列表不产生材料；原生消息保留对象及元数据；字符串为 HumanMessage；字典／数据列表转 JSON，序列化失败则转 str；其他对象转 str。正文、已有历史和其他 State 字段不自动写入更新。

构建期检查所需模型和 messages 通道；运行期检查当前历史为列表／元组，模型结果为 AIMessage。模型配置通过 RunnableConfig 透传。同步运行不偷偷启动事件循环；异步材料函数要求 ainvoke，异步模型运行要求模型提供 ainvoke。同步材料函数在异步调用中直接执行；阻塞 I/O 用户应写异步函数或自行 offload。

原生 State／Reducer 不被改写。运行错误原样传播；非法键报 RoutingError。若节点在返回更新前失败，没有承诺先保存其模型回复或材料；也不提供外部副作用事务保证。

## Host 与命令约定

提供 `sgraph` 和 `python -m skilledgraph`。`--check` 是启动器参数，放在文件名前；文件名后的参数全部交给 Host，允许用一个 `--` 分隔。自定义 Host 优先于内置 chat Host，启动器不预先构建图。

内置 Host 只增加 --model／--model-factory，以及对应 SGRAPH_MODEL／SGRAPH_MODEL_FACTORY。模型名称经 LangChain init_chat_model 创建，提供方包按需安装；其他配置放在模型工厂或自定义 Host。工厂是明确的 Host 入口，不改变 @state 只取对象、不调用工厂的约定。

交互输入按行运行，每次新 State、首节点开始、不保留上一轮历史。管道读完整 stdin 作为一次输入。显示 updates 中各节点提交的 AIMessage，包含模型路由键；不提供逐 token 终端 UI，原生 graph.stream／astream 的消息流通道仍可使用。纯代码更新没有 AI 消息时不输出文本；复杂输出由自定义 Host 处理。

Host 中断时明确说明需原生 API／自定义 Host 恢复；不隐式配置 Checkpointer 或会话 ID。业务异常退出1，Ctrl-C退出130，自定义 Host 的整数返回值交给命令退出码。Python launch 接口保留异常供调试。

## 验收与限制

完整 unittest 共137项通过：79项解析、24项绑定构建、20项模型执行、14项 Host／CLI。9组现有完整 DSL 均通过可控模型或纯代码端到端运行。额外验证包括模型消息流、异步消息流、回调 tags、config／runtime、原生中断恢复、并发隔离和独立 CLI 子进程。

安装检查包括 editable install、sgraph 命令、离线管道示例、自定义 State Host、wheel 构建及安装后在仓库外运行 API／CLI。另在未安装 runtime 的环境运行测试：79项解析测试通过，26项运行相关测试／模块跳过，确认基础解析可独立使用。实际版本 Python 3.14.4、markdown-it-py 3.0.0、LangGraph 1.2.14、langchain-core 1.6.9、可选 LangChain 1.4.4。pyproject 固定直接依赖版本，不声称锁定全部传递依赖。

以下不是已验收承诺：Python 3.11～3.13／Windows／macOS 环境矩阵，真实提供方网络／凭据行为，任意 LangGraph 插件与全部持久化后端组合。真实模型服务未调用，模型服务计费、可用性和回答质量未作验证。

原生内部 RunnableCallable、coerce_to_runnable 及分支 Schema 推断用于保留签名和路由输入类型；这是依赖升级的维护接点，需复跑兼容测试。模型默认选路用公开 Command API；没有修改或复制 LangGraph 调度引擎。

文档和所有确认范围内的代码已落盘；使用入口见[USAGE.md](USAGE.md)。若继续开发，优先根据实际使用问题修正兼容性，不能把规范暂缓项自动当作下一批已授权功能。
