# 三视角并行代码审查

同时审查正确性、安全性和可维护性，全部完成后结合 AST 检查生成优先级报告。代码只作为文本和 AST 分析，绝不执行。

```bash
.venv/bin/sgraph examples/15-parallel-code-review/workflow.md -- --demo
.venv/bin/sgraph examples/15-parallel-code-review/workflow.md -- --data /path/to/code.py
cat code.py | .venv/bin/sgraph examples/15-parallel-code-review/workflow.md
```

默认样例包含空列表除零和不可信命令调用两类问题。真实模式向模型发送所选代码；请按自己的数据分享边界选择文件。

```text
         ┌─ Correctness ─────┐
Start ───┼─ Security ────────┼─ Report ─ End
         └─ Maintainability ─┘
```

DSL 定义节点指令及 Report 结束；Host 通过 build_graph() 添加多个出边和 `add_edge(branches, "Report")` 等待边。未使用尚未实现的分号语法。没有转移表的分支节点是刻意留给原生 Builder 接入的高级用法。默认消息 Reducer 合并三份报告；三个审查节点读取相同原始输入，彼此不会看到同一步其他分支的输出。

实际价值：代码提交前的补充审查。限制：模型可能误报或遗漏，AST 调用名也不证明漏洞；不替代测试和专业审计。脚本模型 demo 只展示流程，真实效果取决于所选模型。
