# 五个实用 agent：实现与验收

日期：2026-10-09。使用现有 v0.1 DSL 和公开 API，新增 examples/12～16，没有新增语言关键字或编译核心功能。每例包含 workflow_cn.md、Python 配套、合成资料、README 及离线 demo。

## 用途和能力覆盖

| 示例 | 实际用途 | DSL 表达 | Python／Host 补足 |
| --- | --- | --- | --- |
| [12 本地知识库问答](../../examples/12-evidence-assistant/README_cn.md) | 检索项目笔记并提供来源 | ToolNode、工具循环、router、修正分支 | 注册检索工具、引用名称校验、自定义 State |
| [13 CSV 检查](../../examples/13-csv-auditor/README_cn.md) | 计算指标、生成清洗建议、校验并修正报告 | python、pyfunction、条件转移、失败出口 | Decimal 计算、JSON 校验、三次尝试上限 |
| [14 邮件草稿](../../examples/14-email-assistant/README_cn.md) | 按政策草拟回复，人工确认后保存 | 分类表、政策分支、request_input、批准／取消 | checkpointer、文件保存；不发送邮件 |
| [15 并行代码审查](../../examples/15-parallel-code-review/README_cn.md) | 正确性、安全性、可维护性三视角审查 | Prompt 节点、材料调用、报告结束 | build_graph 添加并行边和等待汇合、AST 检查 |
| [16 批量摘要](../../examples/16-batch-digest/README_cn.md) | 动态分发文档、隔离摘要、有序汇总 | python 分发、局部 worker 绑定、pyfunction 汇总 | 原生 Command/Send、results Reducer、输入隔离与排序 |

模式参考 LangGraph 官方[工作流与 agent](https://docs.langchain.com/oss/python/langgraph/workflows-agents)、[邮件处理设计](https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph)和[数据工具示例](https://docs.langchain.com/oss/python/langgraph/sql-agent)。这里选择本地笔记和 CSV，避免测试依赖搜索服务、邮箱或数据库账号。

## 确定性测试

全量 unittest **225 项通过**。新增 [test_practical_agents_cn.py](../../tests/test_practical_agents_cn.py) 共 15 项，包含五个 CLI 离线运行，以及：

- 工具检索、虚构引用的有限重试、无资料回答。
- CSV 精确计算、错误报告修正、尝试上限、缺字段与非法金额。
- 邮件三类政策、批准后落盘、拒绝不写文件、中断恢复。
- 用线程 Barrier 验证三个审查分支实际并发；报告只在全部完成后运行，各分支不读取同一步其他分支的回复。
- 动态 worker 输入隔离、原始批次移除、结果排序、同步与异步调用、空批次拒绝。

最后修改 demo 文本和报告 Prompt 后，实用示例及解析器的 **94 项针对性测试再次通过**。离线脚本模型只验证控制流和数据契约，不证明模型推理能力。

旧的“所有示例均用通用模型直接 load_graph”测试调整为前 11 个入门示例：新示例必须经自己的 Host 注册工具、Schema、并行边或绑定，通用加载不能代表其完整运行。另修正了旧并行中断测试对回复顺序的错误假设；回复现在按中断提示匹配，未修改运行时。

## 真实模型测试

使用 DeepSeek `deepseek:deepseek-chat`、temperature=0、timeout=60、max_tokens=1024、max_retries=0。全部输入为随例合成资料，邮件批准仅用于临时目录内的合成草稿。没有读取真实笔记、客户 CSV、邮件或用户代码。

最新各例流程契约 **5/5 通过**：知识库工具检索并引用已返回来源；CSV 报告通过数值校验；邮件完成分类、确认恢复及草稿保存；并行审查产生三份意见并汇合；三个动态 worker 分别完成后汇总。

[最终汇总记录](PRACTICAL_AGENTS_LIVE_RESULTS.json)按每例最新结果汇集，包含 **13 次调用、4046 tokens**，不是一次重新执行全部示例的结果。四轮实际总用量是 **30 次调用、11785 tokens**：

| 轮次 | 范围 | 调用 | tokens | 原始记录 |
| --- | --- | ---: | ---: | --- |
| 初轮 | 五例 | 13 | 7706 | [INITIAL](PRACTICAL_AGENTS_LIVE_INITIAL_RESULTS.json) |
| 收窄输出复测 | CSV、审查、摘要 | 9 | 2157 | [FOLLOWUP](PRACTICAL_AGENTS_LIVE_FOLLOWUP_RESULTS.json) |
| 摘要来源片段复测 | 摘要 | 4 | 936 | [EVIDENCE](PRACTICAL_AGENTS_LIVE_EVIDENCE_RESULTS.json) |
| 摘要输出格式复测 | 摘要 | 4 | 986 | [FINAL_DIGEST](PRACTICAL_AGENTS_LIVE_FINAL_DIGEST_RESULTS.json) |

没有为了全绿删除中间结果。初轮流程断言通过，但人工检查发现审查与摘要输出过长被截断；后续限制输出长度，并让测试遇到 finish_reason=length 直接失败。最终新增复测的所有调用均正常 stop；最初保留的问答与邮件记录尚未采集 finish_reason，不能声称该字段已经覆盖全部最终样本。

内容质量也暴露出两个问题：CSV 建议曾直接删除重复行并提及不存在的日期字段；摘要曾把发布负责人归为测试负责人，把评审日当作完成日。调整后，CSV 明确先核实重复记录；摘要保留最多 600 字来源片段，但仅加入来源仍未阻止误归属。最终收窄输出为“待办动作与来源”，人名和日期以原句单独引用，最后一轮所检查的误归属已消失。

这些是提示及输出约定的改进，不是通用事实校验器。PASS 表示脚本中的流程断言通过；来源名检查不证明陈述被来源支持，格式和数值校验也不证明建议合理。真实测试是有限样本，不保证其他材料或其他模型有相同效果。

## 对当前 DSL 的判断

普通串行流程、条件路由、工具循环、材料调用和人工确认，已能清楚地放进 Markdown；精确计算及校验放在 Python 后，语言不需要增加 JSON Schema 或业务专用语法。前三例的大部分流程由 DSL 直接表达。

原生接入通道也能承载并行等待、Send 和自定义 Reducer。代价是后两例需要懂 LangGraph 的 Host／执行器代码，不能称为“只写几行 Markdown 即可实现复杂并行”。没有引入未冻结的分号跳转语法，也没有把 Reducer 包装成 Hardcode_Execution_Backend。

当前最需要继续关注的是使用说明与数据边界：工具必须由 Host 注册；并行共享消息与隔离 worker 是不同选择；汇合和结果顺序必须明确；模型反馈循环需要业务上限；生成内容仍需与可核验指标或原文区分。这批示例暂未发现必须修改 DSL 语法才能实现的阻塞。

## 复现

离线体验无需 API key，任选一个：

```bash
.venv/bin/sgraph examples/12-evidence-assistant/workflow_cn.md -- --demo
.venv/bin/sgraph examples/14-email-assistant/workflow_cn.md -- --demo --approval no
.venv/bin/sgraph examples/16-batch-digest/workflow_cn.md -- --demo
.venv/bin/python -m unittest tests.test_practical_agents -v
```

真实调用使用显式连接配置，只有 --run 才执行；每例最多八次模型请求：

```bash
export SGRAPH_MODEL=deepseek:deepseek-chat
export SGRAPH_API_KEY_FILE="$HOME/sys_prog/deepseek_api.txt"
export SGRAPH_TEMPERATURE=0
export SGRAPH_TIMEOUT=60
export SGRAPH_MAX_TOKENS=1024
export SGRAPH_MAX_RETRIES=0
export LANGSMITH_TRACING=false
.venv/bin/python examples/support/run_practical_live_cn.py --run --output /tmp/practical-agents-results.json
```

可重复 --case 筛选示例。不要为混合用途验收使用只授权编码工作的套餐；脚本对已知 Go 套餐地址作提醒性拒绝，不替用户判断其他服务条款。其他模型与真实自选材料尚未验收。
