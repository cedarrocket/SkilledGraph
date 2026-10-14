# Host 动态中断与终端编辑验收

日期：2026-10-09。初轮范围：基础 Host，不新增 DSL 语法；随后按用户确认补充 request_input 执行器。修改 src/skilledgraph/host_cn.py，使用 prompt-toolkit 3.0.52；runtime/chat/deepseek/mcp 可选依赖均声明此终端依赖。基础解析安装不引入终端组件。

## 实现行为

基础 main 使用 InMemorySaver 编译图；run_chat 每次创建新 thread_id，读取一次初始输入，然后运行图至完成。动态 interrupt() 触发时展示 JSON 可序列化提示，终端收集字符串回复，以中断 ID 映射传入 Command(resume=...)。Host 不自动追加 HumanMessage；更新后的示例由 request_input 执行器完成这个动作。恢复后继续同一次执行，完成退出。

PromptSession 为实际终端提供方向键、Delete、Home/End、默认 Emacs 编辑键和进程内输入历史。Ctrl-C 交给 CLI 返回 130；空行处 Ctrl-D 表示 EOF。中断处 EOF 返回 1，不提交尚未完成的回复集；空回复提交为合法字符串。管道一次读完后遇到中断明确报错。静态断点需自定义 Host；持久化恢复、类型化表单和多行编辑未纳入本轮。

## 验证结果

全量 `.venv/bin/python -m unittest discover -s tests -q`：180/180 通过，含 26 项 Host 测试。新增第 11 组完整示例也通过解析和 CLI 执行。

- 同一节点两次 interrupt，恢复后仅调用后续模型一次，保留初始消息与补充材料。
- 并行节点同时中断，回复按各自 ID 匹配。
- DSL ToolNode 内工具调用 interrupt，恢复后 ToolMessage 保留 tool_call_id 与回复内容，并传入后续模型。
- 中断处 EOF 取消、主动空回复、管道输入不自动恢复。
- 相同 graph 多次 run_chat 使用不同 thread，不延续上一轮历史。
- 静态断点明确要求自定义 Host。
- POSIX 伪终端启动真实 sgraph CLI，提交初始输入后等待 Resume>；输入 abXd，左移两次、Delete、插入 c，最终后续节点收到 abcd，进程正常退出。

测试全为本地确定性测试，未调用模型 API。沙箱内全量运行遇到已有异步线程挂起；中止后在沙箱外运行通过。早期全量回归唯一失败是示例数量断言仍为 10，更新为 11 后通过。

## 手动运行

项目根目录执行：

```bash
.venv/bin/sgraph examples/11-interrupt/workflow_cn.md -- --model-factory python:../support/demo_model_cn.py:create
```

先输入请求并 Enter；看到中断问题后，在 Resume> 中输入补充内容，后续 Report 输出离线回声并退出。此例无需密钥或网络。运行真实模型时省略 --model-factory 并使用已有 SGRAPH_MODEL 等环境变量。

原生节点在恢复时从头执行，中断前的工作可能再次发生；这是 LangGraph 的原生语义，节点作者应使相关副作用可安全重跑。参考：[LangGraph Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)、[prompt-toolkit 输入与编辑](https://python-prompt-toolkit.readthedocs.io/en/stable/pages/asking_for_input.html)。

## request_input 追加验收

同日按用户确认实现内置 `request_input:提示文本`，替换示例 11 的外部 Python 文件引用。参数直接传入 interrupt；以双引号开始的参数由执行器按 JSON 字符串解码，支持提示中的换行与引号。设置仍只能占单个物理行。正文忽略，不调用模型；字符串回复作为 HumanMessage 更新交给 Reducer。新增 tests/test_request_input_cn.py 的 7 项测试，覆盖原始提示、解析器不解码、空／非法提示绑定错误、非字符串回复错误、异步恢复、router 读取合并后回复及 messages 通道要求。

最终全量 187/187 通过；已有 CLI 伪终端测试现在直接执行 request_input 示例，继续验证光标编辑、暂停恢复和后续节点输入。该执行器不增加全局中断封套或强制 Host 协议；自定义 Host 仍按原生 API 决定如何处理与恢复中断。
