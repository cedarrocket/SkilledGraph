# 原生 fan-out 与并行验收

日期：2026-10-09。未修改编译器或 DSL 语法，仅增加实际原生兼容验收。

## 当前能力边界

build_graph 返回原生 StateGraph Builder，支持添加多个出边、等待汇合边和原生 conditional edges。@uses python 保留原生 Callable 返回，支持 Command(goto=[多个目标]) 或 Command(goto=[Send(...)]) 动态分发。普通 DSL 转移表及受校验 router 仍选择单个键，不接受目标列表，也没有显式 fan-out/fan-in 语法。不能把多行转移表当成全部执行。

并行分支按原生 super-step 执行，读取本步输入快照；同一步提交的更新由 State Reducer 合并。不支持自动修复无 Reducer 的并发同字段写入。汇合需要按拓扑定义：两条独立入边不等于一般性的等待所有分支；本例使用 add_edge(["Left", "RightLast"], "Join")，验证不等长分支全部结束后只执行一次 Join。

## 验证

全量 unittest 191/191 通过。新增 tests/test_parallel_cn.py 四项测试：

- 同步分支通过 threading.Barrier(2) 证明实际并发，不等长分支汇合只运行一次，并看到全部合并结果。
- 异步分支通过 asyncio.Barrier(2) 证明实际并发。
- 原生 Command + 三个 Send 对同一 Worker 分发不同输入，结果全部合并。
- 无 Reducer 的两个并行更新保留原生 InvalidUpdateError。

CLI 示例 tests/parallel_demo/workflow_cn.md 正常退出。一次实测 Left/Right 均在约 0.001s 开始并在 0.301s 结束，RightLast 于 0.401s 完成，Join 约 0.402s 执行；重叠判定 True。该时间记录只是示例观察，不是性能保证。

示例和测试无需模型 API，未修改普通 Prompt 或 Host 的执行规则。

原生背景参考：[LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)。
