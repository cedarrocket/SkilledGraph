# 高级 Reducer 与循环记忆验收

日期：2026-10-09。新增两个可运行示例和 20 项离线测试；全量 **245 项 unittest 通过**。不修改 DSL 语法、编译核心或基础 Host 的默认运行方式。

## 循环 ReAct 和压缩

[17-react-memory](../../examples/17-react-memory/README_cn.md)包含多轮终端 Host、工具循环、调用前／回答后的压缩检查，以及 memory:compact 节点执行器。

- 使用 InMemorySaver 与固定 thread_id，Host 每轮仅提交新消息。下一轮从首节点开始，自动继承同一 thread 的 State；不会重交并重复追加历史。
- 普通消息使用原生 add_messages；自定义 memory_reducer 另接受 Python 层的完整快照替换更新。快照同时比较 ID 和内容，旧快照不能覆盖新增消息或同 ID 编辑。
- 摘要模型调用发生在节点，Reducer 只处理数据。旧完整轮次与已有摘要一起压缩；最近 N 轮完整保留，工具请求／结果配对不能拆散。
- 可同步或异步运行；换独立 thread 没有旧记忆；同一内存 checkpointer 可供重新构建的图继续读取同一 thread。

这是示范持续会话的 Host，不是 pi 的完整实现。默认终端支持编辑，输入 /exit、Ctrl+D 或 Ctrl+C 结束；脚本可使用可重复 --turn。它不自动实现中断 UI、磁盘持久化或恢复命令。

压缩预算是字符启发式，不是上下文长度保证。唯一的巨大轮次／保留轮次不会被删去。空摘要、带工具调用的摘要、未缩小内容的摘要会失败，旧历史保留；失败前提交的新用户输入仍存在 checkpoint 中，不能把失败理解为整个回合回滚。摘要可能遗失或误述事实；旧 checkpoints 仍保存原文，压缩不等于删除存储。

压缩替换与追加不满足可交换的并发语义；示例将压缩安排在串行位置。快照检查不是同一 thread 并发 invoke 的事务锁。Host 应串行提交同一会话输入。

## 其他典型 Reducer

[18-reducer-lab](../../examples/18-reducer-lab/README_cn.md)使用并行来源与等待汇合，无模型依赖：

| 案例 | 验证内容 | 约束 |
| --- | --- | --- |
| 版本化业务记录 | 取较高版本，兼容更新的各排列结果一致；结合性与幂等性 | 同键同版本应有唯一内容；同版本冲突报错，不保留完整旧版本审计 |
| 稳定事件 ID 去重 | 多分支重复事件及重复提交不双计数，合计 8 | 业务负责稳定 ID；同 ID 不同值报错，不保证所有副作用 exactly-once |
| 完成任务集合 | 排序并集，无重复、无顺序依赖 | 不把列表追加误认为集合 |
| 原生 Overwrite | 汇合后的唯一节点清空事件缓冲 | 两个分支同一步重置同一字段被原生 InvalidUpdateError 拒绝 |
| 消息 ID 编辑与删除 | 同 ID 更新不新增；RemoveMessage 删除；REMOVE_ALL_MESSAGES 重置；删除不存在 ID 报错 | 原生消息操作不自动维护业务上的工具配对 |

Reducer 自定义仍是 Python Annotated Schema，未增加 DSL 包装层。Hardcode_Execution_Backend 处理节点执行，不能当作 reducer 注册器。

## 测试范围

[test_advanced_reducers_cn.py](../../tests/test_advanced_reducers_cn.py)的 20 项包含上述数据操作，以及：

- 多轮继承不重复消息；不同 thread 隔离。
- ReAct 工具循环和完整工具轮次保留；多个工具结果乱序仍有效。
- 输入前和回答后都能触发压缩；重复摘要包含已有摘要。
- 同步／异步运行、共享 checkpoint 重建后继续会话。
- 快照新增与同 ID 编辑冲突；孤立 ToolMessage 与未完成工具调用拒绝。
- 摘要为空或过长时不替换旧历史；最近两轮保留及巨大单轮不无限压缩。
- 两个新增 CLI 完整离线运行。

离线脚本模型提供预设摘要来测试数据通道，不能评价摘要智能质量。

## 真实模型验收

[原始结果](ADVANCED_REDUCERS_LIVE_RESULTS.json)：DeepSeek deepseek-chat，temperature=0、timeout=60、max_tokens=1024、max_retries=0。仅发送合成材料。

三轮是：告知姓名及中文偏好并附重复背景 → 请求工具计算 17+25 → 询问姓名及语言偏好。**通过**：压缩 1 次；calculate 工具被实际调用并得出 42；最终回答“林”“中文”。共 **5 次模型调用、3806 tokens**，没有 length 截断。这是一组有限真实样本，不代表所有事实都能在反复摘要后保留。

## 运行

```bash
.venv/bin/sgraph examples/17-react-memory/workflow_cn.md -- --demo --budget-chars 120
.venv/bin/sgraph examples/18-reducer-lab/workflow_cn.md
.venv/bin/python -m unittest tests.test_advanced_reducers -v
```

真实 API 测试显式 opt-in，最多八次请求：

```bash
export SGRAPH_MODEL=deepseek:deepseek-chat
export SGRAPH_API_KEY_FILE="$HOME/sys_prog/deepseek_api.txt"
export SGRAPH_TEMPERATURE=0
export SGRAPH_TIMEOUT=60
export SGRAPH_MAX_TOKENS=1024
export SGRAPH_MAX_RETRIES=0
export LANGSMITH_TRACING=false
.venv/bin/python tests/live/run_memory_cn.py --run --output /tmp/react-memory-results.json
```

设计依据参见 LangGraph 官方[记忆、删除与摘要](https://docs.langchain.com/oss/python/langgraph/add-memory)和[State／Reducer](https://docs.langchain.com/oss/python/langgraph/graph-api)。现有接入通道能够实现这些功能；关键风险在压缩策略、并发合并的数学性质与业务约束，当前无需为 reducer 增加 DSL 语法。
