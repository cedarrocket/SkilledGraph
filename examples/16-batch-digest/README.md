# 动态批量文档摘要

按独立一行 `---` 分隔文档，为每份文档创建一个 Send 任务，分别总结，再按文档序号汇总待办描述和未知信息。最终待办列表不重新分配负责人或完成日期；需要这些信息时附原文依据供人核对。可用于会议纪要、日报和多文件说明摘要。

```bash
.venv/bin/sgraph examples/16-batch-digest/workflow.md -- --demo
.venv/bin/sgraph examples/16-batch-digest/workflow.md -- --data /path/to/batch.md
cat batch.md | .venv/bin/sgraph examples/16-batch-digest/workflow.md
```

输入是多份文档的文本，不是文件目录。每个 worker 只收到自己那一份文档；原始批次消息通过原生 RemoveMessage 移除，避免最终汇总再次读取全部原文。每个结果保留至多 600 字 evidence 片段供最终报告核对来源；这不等于完整的事实校验。results 使用原生 operator.add Reducer，合并后明确按 index 排序，不能依赖并行返回顺序。

Dispatch 为 @uses python，返回 Command(goto=[Send(...)])；Summarize 为此例 Host 提供的 worker:summary 执行器，使用节点正文和各自输入调用模型，支持同步和异步；Report 为普通 pyfunction 材料调用。worker 是局部 bindings 注册，不是新增 DSL 关键字。Python 执行器拥有原生动态分发能力，转移表依旧只表达单目标边。

实际价值：文档数运行前未知时的 map-reduce 摘要。限制：每份文档仍需适合模型上下文，当前按分隔符拆分而非 tokenizer；没有自动并发限制或中间结果持久化。大批次应由自定义 Host 设置原生 max_concurrency 或限制批次大小；摘要仍可能遗漏或误解关系，不能替代原文。实测曾把发布负责人推断为测试负责人，因此最终输出收窄为待办描述与来源，原文人名与日期以直接引用展示，而非自动分派任务。
