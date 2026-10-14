# sgraph_agent：可用的终端 ReAct agent

这是独立的个人终端助手，使用当前 SkilledGraph DSL 编排，调用真实模型和真实工具。没有演示模型或预设回复。目标是提供类似 pi 的“持续对话 → 工具执行 → 许可 → 上下文压缩”基础工作方式，不复刻完整 pi 产品。

## 安装与启动

在项目根目录安装：

```bash
python -m pip install -e '.[agent]'
```

本仓库已有虚拟环境可直接运行。DeepSeek Responses：

```bash
.venv/bin/sgraph-agent-cn \
  --model deepseek-flash \
  --base-url https://api.deepseek.com \
  --key-file "$HOME/sys_prog/deepseek_api.txt" \
  --reasoning-effort none \
  --workspace /path/to/your/project
```

将 workspace 换成你要工作的目录。可尝试“读取项目说明，找出关键模块”“搜索所有 TODO”“用 Python 检查这些数据”“修复这个文件并运行验证”。读取与计算自动执行，写入／编辑／所有 Bash 每次询问是否允许。

也可使用 `python -m sgraph_agent.host_cn` 或 `sgraph sgraph_agent/workflow_cn.md -- ...`。没有显式模型时继承基础 Host 保存的模型与连接配置；显式 --model 或 SGRAPH_MODEL 则使用命令参数／环境提供的连接，不混用旧配置的凭据。--base-url、--key-file 优先。没有模型配置时复用已有初始化向导。--api 默认 responses，支持显式 --api chat；向导保存的接口模式不覆盖此 agent 的 --api 选择。使用 OpenAI 或其他兼容服务时指定自己的模型 ID、地址和 key 文件即可；凭据不会写进 DSL。

DeepSeek 当前 Responses 官方模型名是 deepseek-flash／deepseek-v4-pro，不能把已有 deepseek-chat 配置自动等同为 Responses 支持；不要默默替换模型或回退到 Chat。该服务与模型的真实结果见[验收](../docs/development/SGRAPH_AGENT_ACCEPTANCE_cn.md)。

单次请求与管道：

```bash
.venv/bin/sgraph-agent-cn --model deepseek-flash --base-url https://api.deepseek.com \
  --key-file "$HOME/sys_prog/deepseek_api.txt" --reasoning-effort none \
  --workspace . --prompt '读取 README_cn.md，然后用 python 计算 sum(range(100))'
```

非终端模式仍允许受限读取和 Python，但所有需要许可的调用自动拒绝，不通过管道猜测批准。没有 --yes 或默认无限授权。

## 会话和图

交互命令：/exit 退出；/clear 开始新会话；/status 查看 thread 与消息／压缩数量。终端使用现有 prompt-toolkit 编辑器。会话保存在进程内 InMemorySaver；每轮仅提交新 HumanMessage，从首节点重跑并继承同一 thread 的历史。没有磁盘会话保存或跨进程恢复。

[workflow_cn.md](workflow_cn.md)定义：

```text
CheckContext → [CompactContext] → Agent
                                   │ tool calls
                              PermissionGate → ExecuteTools → CheckContext
                                   │ no tool calls
                              CheckAfter → [CompactAfter] → End
Host 读取下一条消息，保持同一 thread。
```

ExecuteTools 是局部执行器，内部使用原生 ToolNode。它只执行已批准且指纹仍吻合的调用，按请求顺序串行执行；被拒绝的调用返回对应 ToolMessage，原始 AI tool_calls 不删除。不会因一个拒绝让同批其他工具丢失结果配对。许可在独立的前置节点进行，没有“中断重跑时先执行一次工具”的行为。

## 工具与权限

| 工具 | 功能 | 默认处理 |
| --- | --- | --- |
| read_file | UTF-8、行号、分段读取 | 工作区内自动，最多读 1 MiB 文件并返回 12000 字符 |
| list_files | 列出文件／目录 | 自动；每目录扫描至多 2000 项，返回至多 500 项 |
| search_files | 字面子串搜索 | 自动；至多遍历 500 项，深度小于 8，至多 50 个匹配；自动遍历跳过 .venv／node_modules／缓存与构建目录 |
| python | Monty Python 子集计算，可传 data 字典 | 自动；没有挂载、网络或外部函数 |
| write_file | 创建或替换 UTF-8 文件 | 每次 interrupt 请求许可；父目录必须已存在 |
| edit_file | 精确替换唯一的 old_text | 每次请求许可；不是模糊补丁 |
| bash | 正常用户权限 Bash | 所有命令都请求许可，不让模型判断是否危险 |

许可载荷包含工作区、工具、完整参数、调用 ID 和原因；Host 展示后只接受显式肯定。空输入及拒绝都不执行。审批属于本次确切调用，不是整轮／整会话授权；参数更改或路径条件变化不能沿用批准。

专用文件工具使用 POSIX dir-fd、O_NOFOLLOW、普通文件检查，拒绝越界路径、符号链接、硬链接和特殊设备；屏蔽 .git、.aws、.ssh、.codex、.agents、.env*、auth.json、credentials、deepseek_api.txt、*.key、*.pem 等常见私密路径。列表和搜索同样过滤。此名单不能识别任意正常文件中的秘密，选定工作区及提供给模型的内容仍由用户负责。编辑存在并发外部修改竞争，不作为多人文件事务工具。

**Bash 不是 OS 沙箱。** 批准后可访问工作区以外的文件、网络并创建进程，权限等于运行 Host 的用户。工作区只是 cwd；不能把文件工具的路径限制误认为 Bash 的权限限制。Bash 不继承 API key 等环境变量、不开启 profile、stdin 关闭；默认超时 10 秒、上限 30 秒，输出最多 16000 bytes，超时／输出超限会终止进程组。这不是对全部内存、磁盘及外部副作用的资源隔离，也不能保证脱离进程组的后代一定被终止。

## Monty

python 使用固定 pydantic-monty 1.1.0，每次新建局部 Monty 执行。只传 JSON data，无宿主对象、文件挂载、外部函数或 CPython 回退；代码上限 20000 UTF-8 bytes，输入上限 1 MiB，宿主 JSON 序列化同样有界（避免共享对象指数展开），堆限制 32 MiB，执行时间 1 秒，递归深度 100。print 输出受限捕获，不直接写终端。支持的 Python 语法／模块以 Monty 子集为准，不能 pip install 或任意导入 CPython 库。

此外提供可选内置 Hardcode_Execution_Backend：`@uses monty:./program.py`。程序可通过 JSON 化的 state 读取输入，最后表达式返回 State 更新字典；用于 @router 时返回路由字符串。它不调用模型、不处理 Reducer 或原生 Command。详细契约见[白皮书](../docs/standard/v0.1/IMPLEMENTATION_WHITEPAPER_cn.md)末尾。

## 上下文管理与运行边界

--context-budget 默认 12000，是历史 JSON 字符数／2 的启发式估算，计入工具参数及推理块，但不包含系统指令和工具 Schema 的额外占用；需要为所选模型留出输出和 Schema 空间。超过 70% 时判断能否压缩旧完整轮次，保留最近 --keep-turns 轮（默认 1）。摘要通过特定 compact 节点调用模型，只输入可见对话及工具记录，不把加密推理块当成摘要资料；再由原生 Python Reducer 的快照替换接口应用。Reducer 不做模型调用、不管理执行器。

旧历史本身超过摘要预算、摘要为空、带工具调用、响应不完整或没有缩小历史就停止，旧历史不替换。超预算但只剩保留轮次时不会强行切掉工具消息，而是在调用模型前停止并说明；可缩短输入、增加预算或 /clear。摘要有损，不能保证事实一直保留；压缩只缩小有效历史，旧 checkpoints 仍保存原文。

Responses 不使用 previous_response_id，store=False；有效历史完全由客户端 State 决定。OpenAI 使用加密推理项回传选项；DeepSeek 明文 reasoning 的无状态适配独立放在 responses_cn.py，依赖当前固定的 langchain-openai 1.7.0 私有序列化接口，升级依赖时需复验。其他兼容端点与其他 OpenAI 模型未真实验收。

每轮默认最多 16 次 Agent 模型调用，最多每批 8 个工具调用。摘要调用另计，不含在 Agent 调用上限内；图递归上限也有限。业务异常后不假定整轮回滚：已批准执行的操作可能已经生效；进程崩溃恢复不提供 exactly-once 副作用保证。未完成的 checkpoint 不允许直接提交新轮次覆盖，用 /clear 开始新会话，先检查已产生的文件和副作用。

它提供基础文件／代码助手，尚无流式 token UI、MCP 自动加载、skills 加载、远程搜索、后台任务和多进程持久化；这些不属于本次实现。

## 模块与验证

- workflow_cn.md：流程与提示；graph_cn.py：模型／压缩执行器绑定。
- memory_cn.py：Schema、判断、快照替换 Reducer；policy_cn.py：中断许可和工具过滤。
- tools_cn.py／filesystem_cn.py／shell_cn.py：工具与本地执行边界。
- connection_cn.py／responses_cn.py：连接与 Responses 兼容；host_cn.py：终端会话。

测试命令、真实结果及边界详见[验收记录](../docs/development/SGRAPH_AGENT_ACCEPTANCE_cn.md)。
