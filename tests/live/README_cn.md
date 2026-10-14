# DeepSeek 真实模型验收

本目录不参与默认 unittest 网络测试。显式 --run 才会发起真实 API 调用。工具只操作合成测试数据，不读取用户文件，不测试 MCP。

## 配置

安装可选集成：

```bash
python -m pip install -e '.[deepseek]'
```

标准 DeepSeek 凭据环境变量为 DEEPSEEK_API_KEY。也可通过 Host 的 SGRAPH_API_KEY_FILE 读取单行 key 文件，不必将 key 填进命令历史：

```bash
export SGRAPH_MODEL=deepseek:deepseek-chat
export SGRAPH_API_KEY_FILE="$HOME/sys_prog/deepseek_api.txt"
export SGRAPH_TEMPERATURE=0
export SGRAPH_TIMEOUT=45
export SGRAPH_MAX_TOKENS=256
export SGRAPH_MAX_RETRIES=0
export LANGSMITH_TRACING=false

.venv/bin/python tests/live/run_deepseek_cn.py --run
```

API key 只发送给所配置服务用于鉴权。不要开启 HTTP 请求头调试。报告只记录合成输入、回复、调用参数、用量、耗时和错误；不会保存 key。

可重复 --case 参数筛选用例，--output 指定报告路径。默认结果写入 docs/development/DEEPSEEK_LIVE_RESULTS.json。生成的报告包含服务返回的实际 model_name；它可能与请求使用的模型别名不同。CLI 子进程调用不计入进程内 token 合计。

## 手动体验

普通对话：

```bash
.venv/bin/sgraph examples/01-assistant/workflow_cn.md
```

真实工具调用：

```bash
printf '请用工具计算17加25。\n' | .venv/bin/sgraph tests/live/demo/workflow_cn.md
```

demo Host 使用基础模型 bind_tools，并将实际工具对象传入 load_graph；DSL 只决定工具执行节点及边。run_chat 显示 AI 回复，工具请求没有文本时可能显示一行空回复。这个简单 Host 不打印 ToolMessage，验收脚本会直接检查 ToolMessage 及调用 ID。

## 用例

普通回答、两节点历史传递、列表和表格路由各两分支、pyfunction 材料、单工具、多工具、依赖前一工具结果的多轮调用、异步调用、参数错误恢复、业务异常传播、管道 Host 与独立 CLI，共 15 项。精确输出断言用于受控用例，不保证真实模型永远遵循。

## OpenCode Go 套餐

已有本机 opencode-go API 凭据时，可显式运行：

```bash
.venv/bin/python tests/live/run_opencode_go_cn.py --run
```

默认只读 ~/.local/share/opencode/auth.json，也可用 --auth-file 指定。以自身 User-Agent 和每次会话稳定的 x-opencode-session 发送合成编码任务，最多两个案例，结果写入 docs/development/OPENCODE_GO_LIVE_RESULTS.json。需额度；不写回用户配置。见[真实验收记录](../../docs/development/OPENCODE_GO_ACCEPTANCE_cn.md)。

## 五个实用 agent

examples/12～16 的真实测试入口是 `examples/support/run_practical_live_cn.py --run`，使用合成资料、每例八次调用上限。配置与输出选项见[验收记录](../../docs/development/PRACTICAL_AGENTS_ACCEPTANCE_cn.md)。离线覆盖在 `tests/test_practical_agents_cn.py`，默认 unittest 不调用 API。

## 多轮记忆与压缩

`tests/live/run_memory_cn.py --run` 使用合成姓名、偏好及计算问题，验证多轮历史继承、压缩和真实工具循环。最多八次模型调用，配置与离线测试见[高级 Reducer 验收](../../docs/development/ADVANCED_REDUCERS_ACCEPTANCE_cn.md)。

## 真实终端 agent 与 Responses

`tests/live/run_sgraph_agent_cn.py --run` 使用隔离临时工作区验证真实 DeepSeek Responses：读取／Monty、Bash 拒绝、精确批准的合成写入和命令、压缩后记忆。支持 --case 与 --reasoning-effort，具体配置和轮次结果见[验收](../../docs/development/SGRAPH_AGENT_ACCEPTANCE_cn.md)。
