# 并发业务 Reducer 实验室

不调用模型，运行两个原生并行分支，验证三类自定义合并以及 Overwrite：

```bash
.venv/bin/sgraph examples/18-reducer-lab/workflow.md
.venv/bin/python -m unittest tests.test_advanced_reducers -v
```

- records：按业务键合并版本化记录，保留较高 version；同一版本、不同内容拒绝静默覆盖。示例最终 ticket 为 version=2、resolved。
- events：按稳定事件 ID 去重。同一 e1 被两个分支返回，只累计一次；e1=3、e2=5 合计为 8。ID 重用但数值不同报错。相比 operator.add 累计增量，重复提交不会翻倍；这不自动为业务生成稳定 ID，也不等于整个执行具有 exactly-once 保证。
- completed：排序集合并集。无重复，结果与分支返回先后无关。
- Report：等两个分支全部结束后取结果，再用原生 Overwrite({}) 清空 events 缓冲。没有用 reducer 把总额重置为零；报告保留合并后的快照。

并行边和等待汇合由 Host 的 build_graph 原生 API 配置。State 从 Python Schema 直接加载，没有 Reducer DSL 或 Hardcode_Execution_Backend 包装层。

版本合并的交换性、结合性和幂等性以有效输入为前提：同一业务键及版本应只有一种内容。来源违反约定时，错误检查只覆盖参与当前最大版本比较的值；已淘汰的低版本冲突不会完整保留供审计。需要全量冲突审计应保留版本日志，再做独立验证。

Overwrite 绕过 reducer，不具备并发解决冲突的能力；同一步两个分支同时 Overwrite 同一字段会被 LangGraph 拒绝，因此清理由汇合后的唯一节点执行。全部自定义 reducer 不修改传入字典／列表，不读取外部时钟或服务。

更多测试还覆盖消息按 ID 编辑、RemoveMessage、删除全部消息、无效删除、压缩快照冲突和摘要失败，见[验收](../../docs/development/ADVANCED_REDUCERS_ACCEPTANCE.md)。
