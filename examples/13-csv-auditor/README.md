# CSV 账目检查与报告修正

代码精确计算 CSV 指标，模型提出清洗建议，代码核验报告中的指标和值类型，失败后要求修正，最多三次。没有修改 CSV。

```bash
.venv/bin/sgraph examples/13-csv-auditor/workflow.md -- --demo
.venv/bin/sgraph examples/13-csv-auditor/workflow.md -- --data /path/to/records.csv --input '检查数据问题并给出清洗建议'
```

CSV 必须包含 id、amount、customer 三列；编号为原文件行号（表头第 1 行）。默认样例应得到：5 行、可解析金额合计 30.50、重复 ID A2、金额错误第 5 行、客户缺失第 6 行。金额使用 Decimal；合计包含重复记录，不能当作去重后的业务净额。

流程：Load → Draft(pyfunction) → Validate(router) → Render／Draft／Failure。metrics 是 Python 原生 State 字段；pyfunction 将指标转成材料并调用模型。正文要求 JSON，Python 执行校验；没有使用不存在的输出 Schema DSL。

实际价值：批量导入前的快速质量检查。限制：报告格式及数值可核验，建议的业务合理性仍需人工判断；金额处理仅为数据检查，不提供财务决策或自动修账。模型只收到指标及用户请求，不收到 CSV 原始客户记录。
