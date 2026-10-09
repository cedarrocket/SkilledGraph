# v0.1 语言验收样本

这是解析器的输入与预期结果。M1 已通过 [tests/test_parser.py](../../test_parser.py)执行全部45份样本，并增加上下文、源位置和导入隔离验证；实际测试范围见[M1 记录](../../../docs/development/M1_PARSER.md)。这些通过结果只覆盖解析，不代表图运行已经实现。

- `valid/`：语法及 DSL 静态结构合法的输入。
- `invalid/`：应在解析或静态验证阶段拒绝的输入。
- [manifest.json](manifest.json)：每个输入的接受结果、必要字段投影或错误原因。

valid 不等于绑定或运行成功。引用不存在的 fixture 文件不需要补齐：只读解析不能导入代码。`empty-prompt` 语法合法，是否支持空指令由所选执行方式决定，不能自动关闭模型调用；`no-table-*` 用于非推荐的无转移边界；`cycle` 不要求最终结束。

manifest 的 `expected` 用于比对解析输出中的入口、节点顺序、精确 Prompt、设置、说明与转移键／目标；它不是最终公开 IR。未列出的原文与位置仍须按规范保留。`transitions: null` 表示没有区块，与空区块错误区别。

错误案例的 reason 是诊断条件，不要求异常文本逐字相同，也未冻结错误码。实现应报告源位置；一个文件存在多个错误时，不要求固定诊断顺序。

`crlf.md` 有意使用 CRLF，`prompt-extraction.md` 有意保留末行空格，编辑器或格式化工具不得把它们当排版垃圾清理。实现阶段应增加 CR、无末尾换行、跨容器围栏、来源位置、绑定与运行测试，不把这些语法样本当作全部运行验收。

依据：[现行语言规范](../../../docs/standard/v0.1/LANGUAGE_SPEC.md)中的精确语法、正文提取及诊断要求。解析里程碑和验收方式见[开发指南](../../../docs/standard/v0.1/DEVELOPMENT_GUIDE.md)。
