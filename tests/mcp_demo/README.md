# 最小本地 MCP 测试

不需要配置外部 MCP 服务。Host 自动启动同目录 server.py，通过 stdio 发现 mcp_add 工具；会话包围整个图执行，退出时关闭子进程。图使用现有 ToolNode 和工具调用条件，不增加 DSL 语法。

安装可选依赖：

```bash
python -m pip install -e '.[mcp,deepseek]'
```

无网络模型测试（真实 MCP 子进程，模型用确定性替身）：

```bash
.venv/bin/python tests/mcp_demo/check.py
```

真实 DeepSeek + MCP 验收：

```bash
export SGRAPH_MODEL=deepseek:deepseek-chat
export SGRAPH_API_KEY_FILE="$HOME/sys_prog/deepseek_api.txt"
export SGRAPH_TEMPERATURE=0
export SGRAPH_TIMEOUT=45
export SGRAPH_MAX_TOKENS=256
export LANGSMITH_TRACING=false
.venv/bin/python tests/mcp_demo/check.py --live
```

手动体验：

```bash
printf '请调用工具计算17加25。\n' | .venv/bin/sgraph tests/mcp_demo/workflow.md
```

终端直接执行 sgraph 时也只读取一行，运行完退出。这个 MCP Host 使用 asyncio.run，实际工具图用 ainvoke 执行；不要用同步 invoke 调用只提供异步实现的 MCP 工具。

check.py 验证工具发现、外部子进程调用、同会话两轮工具调用、调用 ID 与结果、进程清理；--live 额外验证模型请求及最终答案。脚本有 120 秒整体超时。默认报告 docs/development/MCP_LOCAL_RESULTS.json。

测试未覆盖远程 HTTP、鉴权、重连、采样、人工输入或多模态内容。langchain.mcp 在当前版本属于 beta；验证范围与版本见[验收记录](../../docs/development/MCP_ACCEPTANCE.md)。
