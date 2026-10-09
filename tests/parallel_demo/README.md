# 原生并行示例

项目根目录执行，无模型或密钥：

```bash
.venv/bin/sgraph tests/parallel_demo/workflow.md
```

DSL 提供节点和原生 State 引用；配套 Host 使用 build_graph() 得到原生 Builder，补充以下边后 compile。没有增加 DSL 并行语法。

```text
             ┌─ Left ──────────────┐
Start ───────┤                     ├─ Join ─ End
             └─ Right ─ RightLast ─┘
```

Left/Right 各等待约 0.3 秒，同一 super-step 并行运行；RightLast 再等待约 0.1 秒。add_edge(["Left", "RightLast"], "Join") 显式等待两个分支结束。Join 只执行一次，能看到双方通过 operator.add Reducer 合并的 events。

输出包括每个分支的起止时间、重叠判定和汇总。时间仅供观察，自动测试用屏障证明并行，不依赖机器速度。分支更新顺序不等于完成先后顺序。

本例是高级原生 API 验收，刻意将若干节点的 Transitions 留空，因为它们的后继由 Host 添加；新手普通 DSL 仍应显式写结束与转移。tests/test_parallel.py 另覆盖异步并行、原生 Command/Send 动态分发、无 Reducer 并发写同一字段时的原生错误。
