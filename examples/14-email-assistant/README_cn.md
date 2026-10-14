# 邮件分类、政策辅助和人工确认草稿

将邮件分为账单、技术或一般问题，加载对应政策、起草回复，展示草稿后通过 request_input 询问是否保存。只保存本地 Markdown，不发送邮件。

```bash
.venv/bin/sgraph examples/14-email-assistant/workflow_cn.md -- --demo
.venv/bin/sgraph examples/14-email-assistant/workflow_cn.md -- --demo --approval no
.venv/bin/sgraph examples/14-email-assistant/workflow_cn.md -- --input '邮件内容' --output ./drafts
```

真实模式默认在终端展示草稿并等待 yes/no；管道输入遇到确认时需要显式 `--approval yes` 或 `--approval no`。这个选项是用户预先给出的回复，不是默认跳过确认。只有 yes、是、同意进入保存路径，其他输入取消。demo 模式对合成草稿默认 yes；不指定 --output 时创建独立临时目录，路径会显示，可自行清理。

所有业务边在 DSL 定义，分类使用表格转移，政策加载用 python，草稿材料用 pyfunction，人工输入用 request_input，原生 InMemorySaver 支持恢复。模型输出不用于决定文件名，文件名为随机 UUID。

实际价值：客服或个人邮件的草拟与复核。限制：政策为示范数据，使用前须替换；不会自动获取邮箱、处理附件或发信，也不会验证退款等业务事实。保存只是完成草稿准备。
