# 有来源的本地知识库问答

对本地 Markdown 笔记提出问题，模型调用检索工具、生成引用，再由 Python 校验引用名称。无结果时应明确没有证据；校验失败最多修正三轮。

```bash
.venv/bin/sgraph examples/12-evidence-assistant/workflow.md -- --demo
printf '发布前要做什么，什么时候回滚？' | .venv/bin/sgraph examples/12-evidence-assistant/workflow.md
.venv/bin/sgraph examples/12-evidence-assistant/workflow.md -- --data /path/to/notes --input '你的问题'
```

真实模式使用环境变量或已保存的基础 Host 模型配置，需模型支持 tool calling。仅检索指定目录顶层的 .md 文件，跳过符号链接；按关键词匹配返回至多四个片段，每篇至多 4000 字。默认资料是随例提供的合成发布政策。自选笔记的命中内容会发给模型。

流程：Research →（ToolCalls）SearchNotes → Research → Verify → 结束／修正／未核实提示。全部边由 DSL 声明。State 增加 attempts 和 validation；Reducer 保持原生消息合并。

实际价值：轻量政策、项目说明和个人知识库问答。限制：关键词检索没有语义召回；检查仅证明“引用名确实出现在检索结果”，不证明答案每条陈述被来源支持。示例中的检索内容被当作资料，但这不是完整的提示注入防御系统。
