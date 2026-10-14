# 单次 Host 与本地 MCP 验收

日期：2026-10-09。

基础 Host 现在读取一次输入、执行图后退出：终端读取一行，空白或 EOF 不执行；管道读取完整 stdin。内部工具循环仍由图的边驱动。没有加入跨输入会话记忆。171 项离线 unittest 通过，其中 Host 测试确认第二行不被读取以及空输入不调用模型。

## MCP 结果

本地 stdio MCP **5/5 检查通过**：
1. 发现 mcp_add 工具。
2. 调用独立子进程中的工具，17 + 25 得到 42。
3. 图内连续两轮工具调用得到 42、5，调用计数递增且 server_pid 相同，确认会话没有被重建；ToolMessage ID 正确。
4. DeepSeek 实际发出 mcp_add 请求，取得 42，最终回答“17 加 25 的结果是 42”。
5. 退出 adapter 上下文后，服务子进程已结束。

[原始报告](MCP_LOCAL_RESULTS.json)；本次 DeepSeek 两次模型请求，745 input tokens、75 output tokens，总计 820 tokens。请求别名 deepseek-chat，服务响应 model_name 为 deepseek-flash。

## 接入方式与发现

使用 langchain 1.4.4 的 langchain.mcp.MCPAdapter，FastMCP 4.1.0，MCP SDK 2.3.0。可选 mcp 依赖组已经添加，核心不导入 MCP。工具由 Host 在 adapter.list_tools 后提供给模型 bind_tools 与 load_graph(tools=...)；DSL 原样使用 ToolNode、@ToolCalls、@Otherwise。图使用 ainvoke，因为适配后的工具为异步工具。

首次离线测试的发现、工具执行、图内多轮调用都通过，立即清理检查失败。原因是 StdioTransport 默认 keep_alive=True，会保留子进程直到进一步清理；本示例显式 keep_alive=False，复测通过。没有修改 SkilledGraph 核心或重写工具执行。会话上下文覆盖整个图运行。

官方接口依据：[LangChain MCP tools](https://docs.langchain.com/oss/python/langchain/mcp/tools)。该接口当前为 beta，依赖升级应复验。

## 使用

服务由 Host 自动启动，无需全局 MCP 配置。设置前一轮的 DeepSeek 环境变量后：

```bash
printf '请调用工具计算17加25。\n' | .venv/bin/sgraph tests/mcp_demo/workflow_cn.md
```

离线 MCP 检查：
```bash
.venv/bin/python tests/mcp_demo/check_cn.py
```

完整说明、Host、服务与 DSL 在[tests/mcp_demo](../../tests/mcp_demo/README_cn.md)。

仅验收本地 stdio、算术工具、结构化文本结果及会话清理；未覆盖远程 HTTP、鉴权、重连、人工输入、采样或多模态。此前 DeepSeek/工具验收文件中“本轮未测试 MCP”是当时范围，当前本地 MCP 结果以本文件为准。
