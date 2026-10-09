# OpenCode Go 真实套餐验收

日期：2026-10-09。用户授权使用本机已有 opencode-go API 凭据进行少量真实请求。凭据从 ~/.local/share/opencode/auth.json 只读取得，不复制到仓库或 Host 配置，不输出密钥，也不修改 OpenCode 配置。

## 请求约定

按 [Go 官方客户端要求](https://opencode.ai/docs/go/)发送合成编码任务，使用自身 User-Agent `skilledgraph/0.1.0.dev0`，为每个独立会话创建稳定的 `x-opencode-session`。没有冒充 OpenCode，也没有使用其他 provider 的凭据或接口。两次工具循环模型请求共用会话 ID；另一个独立测试使用新的会话 ID。

模型 glm-5.3-flash，基础地址 https://opencode.ai/zen/go/v1，Chat Completions。传入的配置经现有 host.create_model 创建 LangChain 模型，再由 SkilledGraph 加载和执行图。请求头沿用现有 default_headers 参数，无需新增 DSL 或套餐鉴权包装。模型和端点以本次实测为准，不保证所有 Go 模型都使用此协议。

## 结果

2/2 测试通过，共 3 次实际 POST 请求：

1. 普通 Prompt 节点生成 add(a,b) 的正确 Python 实现，并通过 Python AST 语法检查；179 tokens。
2. 模型请求 read_snippet，原生 ToolNode 实际执行一次；模型收到带匹配 tool_call_id 的 ToolMessage 后返回修正后的加法函数；两次请求分别 226 与 281 tokens。

合计 686 tokens（输入 457、输出 229），服务端报告值。所有输入和工具结果为合成代码，无仓库源码或个人文件内容发送。单次 max_tokens=1024、timeout=60、max_retries=0。

完整非敏感结果见 [JSON](OPENCODE_GO_LIVE_RESULTS.json)。真实脚本不会进入默认 unittest 发现，需显式运行：

```bash
.venv/bin/python tests/live/run_opencode_go.py --run
```

该脚本显式读取 opencode-go API 凭据；它不是运行时自动导入 OpenCode 配置的功能。基础向导仍支持手动填写 API 地址、模型名和这两个请求头。初轮使用显式 session 值；后续已补充自动生成，详见下节。

本次验证 Chat Completions 路径及此模型的工具调用。没有新增 Responses 套餐实测，也没有验证其他 Go 模型、所有套餐或一般非编码流量。

## 自动会话头补充验收

按用户要求，create_model 在有效基础地址为 https://opencode.ai/zen/go/v1 时，补充缺失的 User-Agent `sgraph-harness-agent/0.1.0.dev0` 和 `x-opencode-session: sgraph-harness-agent-<UUID>`。每次模型创建生成一次；基础 Host 每次运行创建新模型，图内调用／工具循环／中断恢复保持同一个模型与会话 ID。不会逐次请求换 ID，也不把随机值保存到配置文件。

显式请求头大小写无关地保留，模型 factory 不被介入。非 Go 基础地址不自动添加这些头部。自定义 Host 复用模型跨多个会话时，需自行管理会话 ID；原生运行 API 不被包装。

新增 4 项本地测试，覆盖新旧模型会话 ID、不修改输入配置、大小写覆盖、其他地址不注入，以及真实客户端多次 mock 请求保持同一头部。全量 unittest 210/210 通过。

真实测试脚本已去除手写 session 和 User-Agent，让 Host 代码自动补充。2/2 通过，共 3 次请求、643 tokens。请求记录确认普通请求与工具循环使用不同 UUID，工具循环的两次请求共享同一个 UUID。非敏感报告见 [自动会话结果](OPENCODE_GO_AUTO_SESSION_RESULTS.json)。初轮 686 tokens 记录保留，不混作同一轮用量。
