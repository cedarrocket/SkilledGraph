# v0.1 示例

[标准 chat Host](chat-host/README.md)独立提供模型连接、终端输入、首次配置和中断恢复，源码不属于 DSL 核心。下列 18 组工作流继续使用默认 Host 或各自声明的 Host。

这些是按[现行语言规范](../docs/standard/v0.1/LANGUAGE_SPEC.md)编写的完整 DSL 文件。引用的 Python 文件已随例子提供，不依赖未定义模块引用。18组例子已通过解析及端到端运行验收，模型例子使用确定性的离线模型替身；已提供 sgraph CLI。可通过 parse_graph 检查结构，见[M1 使用说明](../docs/development/M1_PARSER.md)。执行器行为以[功能实现白皮书](../docs/standard/v0.1/IMPLEMENTATION_WHITEPAPER.md)为准，本页说明各例语义，安装和 CLI 用法见[使用指南](../docs/development/USAGE.md)。

| 示例 | 说明 | 运行所需能力 |
| --- | --- | --- |
| [01-assistant](01-assistant/workflow.md) | 一个 Prompt，明确结束 | 默认 chat State、模型 |
| [02-chain](02-chain/workflow.md) | 两节点继承历史 | 默认消息合并、模型 |
| [03-routing-list](03-routing-list/workflow.md) | 列表条件边，模型文本选路 | 只输出键，去掉首尾空白后查表 |
| [04-routing-table](04-routing-table/workflow.md) | 与列表例等价的表格 | 管道表格解析 |
| [05-python-router](05-python-router/workflow.md) | 代码更新额外字段，router 查表 | 原生 Schema、python、router、模型 |
| [06-pyfunction](06-pyfunction/workflow.md) | 函数材料与 Prompt 共同调用模型 | 本例的字符串材料适配、模型 |
| [07-custom-state](07-custom-state/workflow.md) | 替换 messages 的合并规则 | 原生 Schema、模型 |
| [08-native-jump](08-native-jump/workflow.md) | 原生 goto 与 Default 同时生效 | 原生 Command、消息 Reducer |
| [10-tool-calling](10-tool-calling/workflow.md) | 显式 ToolNode 与完整工具调用循环 | 自定义 Host、确定性模型、真实加法工具 |
| [11-interrupt](11-interrupt/workflow.md) | 原生动态中断、终端回复与恢复 | 基础 Host、进程内 checkpointer、模型 |
| [09-state-only](09-state-only/workflow.md) | 没有 messages 的计算图，自定义 Reducer | 原生 Schema、python，无模型 |
| [12-evidence-assistant](12-evidence-assistant/README.md) | 本地笔记检索、工具循环与来源校验 | tool calling、Python 校验 |
| [13-csv-auditor](13-csv-auditor/README.md) | CSV 指标检查、报告修正与数值校验 | pyfunction、原生 State、router |
| [14-email-assistant](14-email-assistant/README.md) | 邮件分类、政策、人工确认和保存草稿 | 条件表、request_input、checkpointer |
| [15-parallel-code-review](15-parallel-code-review/README.md) | 三视角并行审查与等待汇合 | 原生 Builder、并行模型调用 |
| [16-batch-digest](16-batch-digest/README.md) | 动态文档分发、隔离摘要与有序汇总 | Command/Send、原生 Reducer、局部 worker 执行器 |
| [17-react-memory](17-react-memory/README.md) | 多轮 ReAct、历史继承、完整轮次摘要替换 | 自定义消息 Reducer、checkpointer、循环 Host |
| [18-reducer-lab](18-reducer-lab/README.md) | 并行版本合并、去重计数、集合与缓冲重置 | 原生 Annotated、Builder、Overwrite，无模型 |

默认例子的初始输入可采用一条 HumanMessage，由 Host 提供。只依赖普通回答的例子不假设模型已有文件、搜索或工具能力。条件例建议先用模型替身控制返回键以验证路径，再测试真实模型。

## 预期行为与依赖

01：一次模型调用，新 AI 消息进入 State，然后结束。

02：Analyze 与 Report 各调用模型一次；Report 看到原输入和 Analyze 输出。节点静态正文不作为历史消息保存。

03／04：输入“已提供实验样本与结果表，请总结”可用于 enough 分支；“我没有材料，请帮我总结”可用于 insufficient 分支。模型判断不具有确定性，验收用替身分别返回两种键；每次只选一个后继，模型只输出路由键，去掉首尾空白后精确查表。原始模型消息照常提交到历史，由所选 Reducer 合并。

05：`Inspect` 执行脚本，不调用模型。初始 messages 非空时写入 `status="ready"`，追加一条说明消息；空列表时写入 `status="missing"`。router 读取**合并后的** status，分别进入 Report／RequestMaterial，各调用一次模型。Schema 在图构建前加载；脚本返回新消息更新而不是重交全部历史。

06：prepare(state) 返回字符串，内置 pyfunction 将其包装为 HumanMessage，与正文、历史联合调用一次，然后提交材料及模型回复到 messages；合并遵循所选 Reducer，正文不保存。消息转换及执行顺序已在白皮书确定，不是解析器的模型调用逻辑。

07：Schema 的 messages 没有合并 Reducer，采用原生覆盖行为。Analyze 提交一条新消息后，Report 只看到这条消息；这是例子有意选择的状态语义，不应补回默认历史。

08：Process 的原生 Command 指向 Extra，DSL Default 指向 Report；两个目标都应执行，都使用 Python 写入各自一条消息，没有模型调用。先后顺序不作保证。messages 使用合并 Reducer，因此两个分支的更新可合并；各分支 @End 不取消另一个分支。Extra 故意不在 Process 转移表中，默认不封禁。这里遵循原生 [Command 与静态边叠加](https://docs.langchain.com/oss/python/langgraph/graph-api#command)行为。

09：由自定义 Host／原生调用提供 `{"value": 0, "events": []}`。Increment 更新 value 为 1，并提交事件 `"incremented"`；Double 更新为 2，并提交 `"doubled"`，最终 events 为两条。`operator.add` 是原生 Reducer，不是 DSL 内置 reducer 语法；本例没有消息字段，也不需要 chat Host 或模型。

Python 例子使用 LangGraph、langchain-core 与 typing-extensions 的原生类型；直接运行依赖版本已固定，全部例子的模型替身／纯代码验收见[M3～M5 记录](../docs/development/M3_M5_COMPLETION.md)。09 自带 Host，可直接运行 `sgraph examples/09-state-only/workflow.md`；01～07需配置模型，08通过原生 API运行。原生 Schema／Reducer 行为参见 [LangGraph State](https://docs.langchain.com/oss/python/langgraph/graph-api#state)。

pyfunction 的简单材料可以像 06 一样直接返回字符串；需要明确控制消息角色、内容或元数据时，推荐返回原生消息对象或对象列表。例如：

```python
from langchain_core.messages import HumanMessage


def prepare(state):
    return HumanMessage(content="记录 A：金额 12。记录 B：金额 8。")
```

消息对象会保留角色、内容和元数据，消息列表保留顺序。字符串直接包装为 HumanMessage；普通字典／数据列表可序列化时转成 JSON 文本，否则转字符串；其他对象转字符串，自动文本消息均采用 HumanMessage。普通字典不根据 role／content 字段自动识别为消息。这些转换不代表 State 字段更新，也不要求用户必须学习消息对象。

None／空列表表示没有额外材料，仍使用已有历史和正文调用模型；空字符串则产生一条空文本消息。

无 Transitions 等非推荐边界输入放在 [tests/fixtures](../tests/fixtures/language/README.md)，不混入新手示例。

11：AskUser 的 request_input 执行器将冒号后的文本传入原生 interrupt()，Host 收集字符串回复并恢复同一次执行。执行器将字符串回复保存为 HumanMessage，Report 因此可以读取它。运行命令见[使用指南](../docs/development/USAGE.md)。

## 五个实用 agent（12～16）

各例 README 提供用途、输入、流程和边界。每个都有 --demo 离线模式，使用脚本模型验证整条图、真实工具和状态更新；这不代表真实 LLM 智能效果。去掉 --demo 后使用环境变量或保存的基础 Host 连接。--model 可显式指定，--input 可替代 stdin；其他选项见各例 README。共享的 examples/support/practical.py 只是简短 CLI 帮助，不增加 DSL 或框架协议。

设计参考官方[常见工作流](https://docs.langchain.com/oss/python/langgraph/workflows-agents)、[邮件处理思路](https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph)及[SQL agent 数据工具模式](https://docs.langchain.com/oss/python/langgraph/sql-agent)。示例采用本地可复现材料，不依赖在线搜索、邮箱账号或数据库服务。

测试覆盖、真实 API 用量和内容质量分析见[实用 agent 验收](../docs/development/PRACTICAL_AGENTS_ACCEPTANCE.md)。

## 高级 Reducer（17～18）

17 提供独立循环 Host，保留基础 Host 的单轮默认行为；18 是纯代码的并发合并实验。运行方式和边界见各例 README，20 项测试及真实模型三轮记忆测试见[验收记录](../docs/development/ADVANCED_REDUCERS_ACCEPTANCE.md)。


## 子图复用（19）

[19-subgraphs](19-subgraphs/README.md) 两次引用同一审查图，展示独立图定义、分层追踪与离线运行。
