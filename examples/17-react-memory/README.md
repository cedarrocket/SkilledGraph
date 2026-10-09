# 多轮 ReAct、历史继承与压缩

一个可交互循环的 Host，配合显式工具循环的 agent。它示范持续会话和内容压缩的组合，不复刻 pi 的完整 harness。

```bash
# 离线脚本模型：自动跑三轮，并触发压缩
.venv/bin/sgraph examples/17-react-memory/workflow.md -- --demo --budget-chars 120

# 真实模型：终端循环，/exit 或 Ctrl+D 结束
.venv/bin/sgraph examples/17-react-memory/workflow.md -- --budget-chars 6000

# 独立三轮，适合外部终端脚本；需要已配置模型 API
.venv/bin/sgraph examples/17-react-memory/workflow.md -- \
  --turn '我叫林，请用中文回答。' \
  --turn '请调用工具计算17加25。' \
  --turn '我的名字是什么？'
```

## 图与 Host 分工

```text
CheckBefore → [CompactBefore] → Agent ⇄ Tools
                                 ↓ 无工具调用
                             CheckAfter → [CompactAfter] → End
Host 读取下一条输入，再从首节点开始，同一 thread 延续 State。
```

DSL 定义检查、压缩、工具循环和结束；Host 创建 InMemorySaver 和固定 thread_id，并且每轮只提交新的 HumanMessage。没有把全部历史反复作为更新提交，也没有改变基础 chat Host 的单轮默认行为。独立 Session 默认有独立 thread，可通过 Python 显式传入同一 thread_id 和共享 checkpointer。

Agent 使用绑定工具的模型；压缩节点使用未绑定工具的模型，也可通过 create_graph(..., summarizer=...) 替换为专用摘要模型。局部 memory:compact 是 Hardcode_Execution_Backend 绑定，只负责该节点的摘要调用与更新。State 和 Reducer 仍通过原生 Python 定义，不经执行器包装。

## 压缩策略与 Reducer

普通更新委托原生 add_messages，保留按 ID 修改和 RemoveMessage 能力。压缩节点先按真正的用户消息分割轮次，保留最近 --keep-turns 轮（默认 1），摘要旧轮次和已有摘要，再提交一个 Python 私有的 compact 更新：包含旧消息完整快照与新消息列表。

memory_reducer 在快照完全吻合时用新列表替换旧列表；检测到新增消息或同 ID 内容改动则拒绝旧摘要覆盖。Reducer 不调用模型、不做 I/O。摘要是带 memory_summary 元数据的 HumanMessage 资料，不升级为永久 SystemMessage 指令。最近轮次的 Human/AI/tool_calls/ToolMessage 完整保留，压缩前后检查工具配对；多工具结果可按不同顺序返回。

预算使用粗略字符数（含工具调用表示），不是精确 tokenizer。压缩前和回答结束后都会检查；即使超过预算，也不切掉唯一轮次或保留轮次，因此单个巨大输入／工具结果仍可能超过上下文。摘要为空、有工具调用或未缩小历史时直接失败，旧历史不替换。没有自动重试、强行截断或事实恢复保证。

这是串行压缩策略，替换操作不具备可交换的并行合并语义；同一 thread 的输入应由 Host 串行处理，不能把它当作多个客户端并发写入的事务机制。反复压缩有损，可能遗忘或误述事实。需要可靠记忆的业务应另存原始事实并校验。

InMemorySaver 只在本进程内保存，但仍保留旧 checkpoints：压缩缩小的是之后送给模型的有效历史，不代表删除旧记录、节省整个 checkpointer 存储或跨进程持久化。使用数据库 checkpoint、历史清理或中断 UI 应由自己的 Host 实现。

离线及真实结果见[高级 Reducer 验收](../../docs/development/ADVANCED_REDUCERS_ACCEPTANCE.md)。
