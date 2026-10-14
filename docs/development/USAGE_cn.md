# 使用 SkilledGraph v0.1

SkilledGraph 把 Markdown 转为原生 LangGraph 图。普通节点调用一次模型；需要代码时，通过 uses 选择 Hardcode_Execution_Backend。复杂输入输出、模型参数和资源生命周期交给 Host。

基础 chat Host 是独立的[标准示例](../../examples/chat-host/README_cn.md)，使用 `sgraph_chat_host` 命名空间，源码位于 `examples/chat-host/src/`。未声明 `@host` 时，启动器选择该示例；解析、构图 API 不加载它。需要复用模型创建或终端输入时，从 `sgraph_chat_host.host`、`sgraph_chat_host.terminal` 等模块导入，旧的 `skilledgraph.host*`／`skilledgraph.terminal` 路径已移除。

## 安装与离线试跑

在项目目录创建环境并安装：

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[chat]'
```

只使用解析器可安装 `-e .`；自己提供模型或只运行代码图可安装 `-e '.[runtime]'`。chat 包含 runtime 和 LangChain 的模型初始化入口，具体提供方需要另装其集成包。

下面两条命令无需模型服务或密钥：

```sh
sgraph examples/09-state-only/workflow_cn.md
printf '你好\n' | sgraph examples/01-assistant/workflow_cn.md -- --model-factory python:../support/demo_model_cn.py:create
```

第一条通过文件声明的自定义 Host 运行计算图，输出 value=2 及两条事件。第二条使用随项目提供的离线回声模型，只验证完整调用链，不具备 LLM 能力。

## 写几行 Markdown

保存为 hello.md：

```markdown
# [Node] Assistant

你是一位简洁的助手。回答用户的问题。

## [Transitions]
- @Default -> @End
```

只检查语法，不导入 Python 引用：

```sh
sgraph --check hello.md
```

真实模型由环境指定，例如先安装所用提供方的 LangChain 集成包，然后把下例的 `provider:model` 替换成实际名称，并按提供方配置密钥或本地服务：

```sh
export SGRAPH_MODEL='provider:model'
sgraph hello.md
```

Host 使用 LangChain 的 [init_chat_model](https://reference.langchain.com/python/langchain/chat_models/base/init_chat_model) 初始化该名称，提供方集成包由用户选择安装。也可单次指定 `sgraph hello.md -- --model provider:model`。

交互终端中，读取一行输入，执行一次图后退出；EOF 或空白行直接退出。每次从首节点开始。使用管道时，整个标准输入作为一次消息，包括换行；例如 `cat input.txt | sgraph hello.md`。输出为 `[节点名] 回复`，显示每个节点的 AI 回复，包括模型路由键。终端输入使用 prompt-toolkit，支持方向键、Home/End、Delete、常用 Emacs 编辑键和本次进程内的输入历史；Enter 提交，Ctrl-D 在空行时退出，Ctrl-C 取消。当前不提供专门的多行编辑或跨进程输入历史。

基础 Host 用 InMemorySaver 保存当前进程内的执行检查点，每次运行创建新的 thread_id，遇到原生动态 interrupt() 时显示提示并读取字符串回复，通过 Command(resume=...) 恢复同一次执行；完成后退出，不开启新一轮聊天。恢复值由节点自行处理，不自动写入 messages。多个中断按 ID 对应回复，连续中断可重复恢复。中断提示可以是 JSON 数据，但复杂表单、类型化回复、静态断点和跨进程恢复交给自定义 Host。管道输入遇到中断会明确报错；中断处 EOF 取消执行并返回退出码 1，不提交空回复；主动 Enter 提交的空字符串是有效回复。

离线体验（无需 API key）：

```bash
.venv/bin/sgraph examples/11-interrupt/workflow_cn.md -- --model-factory python:../support/demo_model_cn.py:create
```

输入初始请求后，会出现中断问题和 Resume>，输入补充内容后执行 Report 并退出。自定义 Host 复用 run_chat 时，需自行给传入的图配置 checkpointer。原生恢复会从中断节点开头重跑，中断前的副作用必须由节点作者妥善处理，参见 [LangGraph 中断说明](https://docs.langchain.com/oss/python/langgraph/interrupts)。

## 代码材料与路由

同目录 tools_cn.py：

```python
def prepare(state):
    return "记录 A：12；记录 B：8。"
```

DSL 节点：

```markdown
# [Node] Report
- **@uses**: pyfunction:./tools_cn.py:prepare

总结本次材料。

## [Transitions]
- @Default -> @End
```

pyfunction 函数接收 State。返回材料和正文、历史一起交给模型，材料及模型回复进入 messages；正文不保存。None／空列表不提供材料，但仍调用模型。需要明确的消息角色时可返回 LangChain 原生消息对象。

python 执行器直接运行原生节点，不自动调用模型，允许原生 State 更新和 Command 等返回。代码路由使用 @router，读取节点更新合并后的 State，返回表内键；文件相对路径均以 DSL 所在目录为基准。完整例子见[示例目录](../../examples/README_cn.md)。

## 用 Python 加载和扩展

```python
from skilledgraph import parse_graph, build_graph, load_graph

spec = parse_graph("examples/09-state-only/workflow_cn.md")
graph = load_graph(spec)
result = graph.invoke({"value": 0, "events": []})
```

parse_graph 不导入引用；build_graph 返回原生 Builder；load_graph 返回原生编译图。build／load 不执行文件中的 @host。可以提供 model、state_schema、input_schema、output_schema、context_schema、bindings；load 另接受 compile_kwargs，直接传给原生 compile。

自定义 reducer 在原生 Python Schema 中声明，通过 state_schema 或文件 @state 传入，不经过执行器包装。纯 Python 图可以完全没有 messages。普通 Prompt 和 pyfunction 需要 messages 字段；任意自定义 reducer 的结果由用户负责。

模型对象提供 `invoke(messages, config=...) -> AIMessage`；异步运行还需 `ainvoke(messages, config=...)`。LangChain 聊天模型符合这一接入方式。返回值不自动猜成消息。

bindings 的值采用 `bind(payload, *, base_dir, node, model=None)` 绑定函数，返回原生 Callable／Runnable。node 为只读 NodeSpec。替换 python 绑定不影响 @state／@host 文件加载。接口例子及文件缓存约定见[M2 记录](M2_BUILDING_cn.md)。

## 定制模型或 Host

需要 temperature、供应商特殊参数或自行创建客户端时，可以指定一个零参数模型工厂，无需修改 DSL。例如 my_model.py：

```python
import os
from langchain.chat_models import init_chat_model


def create():
    return init_chat_model(os.environ["SGRAPH_MODEL"], temperature=0)
```

```sh
sgraph hello.md -- --model-factory python:./my_model.py:create
```

也可设置 SGRAPH_MODEL_FACTORY。显式命令行选择优先于两个环境变量；只用环境时 factory 优先于 SGRAPH_MODEL。工厂引用路径相对于图文件。模型对象的生命周期覆盖 Host 的运行过程，核心构建器不会自动关闭它。

更复杂 I/O 或非消息初始状态，写一个同步 Host 入口：

```python
from pathlib import Path
from skilledgraph import load_graph


def main(graph_path: Path, argv: list[str]) -> int | None:
    graph = load_graph(graph_path)
    print(graph.invoke({"value": 0, "events": []}))
    return 0
```

文件开头显式选择它：

```markdown
# [Config]
- **@host**: python:./host_cn.py:main
- **@state**: python:./state_cn.py:State
```

启动器把图文件绝对路径和剩余参数交给 Host，由 Host 自己构建图。`sgraph graph.md -- --custom value` 会传入 `["--custom", "value"]`。Host 返回整数退出码或 None；异步应用在同步入口内部管理事件循环即可。不要在 Host 内递归调用 CLI 来加载同一个 Host。

## 测试与支持范围

```sh
python -m unittest discover -s tests -v
```

当前所有确定性验收使用离线模型替身，不访问收费模型服务。运行范围、实测版本与限制见[M3～M5 完成记录](M3_M5_COMPLETION_cn.md)。当前未提供文件级执行器、模块引用、DSL 输出 Schema、失败路由或重试等暂缓语法。

## 工具调用

无需模型服务即可体验完整工具循环：

```bash
.venv/bin/sgraph examples/10-tool-calling/workflow_cn.md
```

预期输出包含工具结果 `tool: 5` 和最终回答 `ai: 结果是 5`。示例 Host 使用确定性模型生成工具请求，ToolNode 实际执行 add 函数。

真实模型由自定义 Host 绑定工具，再将模型与工具对象分别交给图：

```python
bound_model = base_model.bind_tools([add])
graph = load_graph(graph_path, model=bound_model, tools=[add])
result = graph.invoke({"messages": [HumanMessage(content="2 + 3 等于多少？")]})
```

以上代码片段假定 base_model、add、graph_path 和导入已由 Host 准备；完整可运行文件见[示例 Host](../../examples/10-tool-calling/host_cn.py)。

DSL 用 `# [ToolNode] ExecuteTools` 声明执行节点，以 `@tools: all` 或 `@tools: [add]` 选择执行集合。普通 Node 不声明 @tools。模型节点通过 `@ToolCalls -> ExecuteTools` 分支进入执行节点，用 `@Otherwise -> @End` 接收最终自由文本回答；执行节点显式跳回模型节点。没有隐式循环或自动返回调用者。

MCP 适配器产生的兼容工具对象可通过同一 tools 参数提供。连接、凭据、异步会话生命周期仍由 Host 管理；本轮没有执行 MCP 集成测试。异步工具使用 graph.ainvoke/astream。

完整规则见[语言规范](../standard/v0.1/LANGUAGE_SPEC_cn.md)末尾“工具调用扩展”，验证范围见[工具功能记录](TOOLS_COMPLETION_cn.md)。

## 环境变量配置模型连接

基础 Host 保留 SGRAPH_MODEL 与 SGRAPH_MODEL_FACTORY，并新增以下连接参数。它们属于 Host，不是 DSL 属性。

| 环境变量 | 用途 |
| --- | --- |
| SGRAPH_API_KEY | 显式 API key |
| SGRAPH_API_KEY_FILE | 单行 key 文件，与 SGRAPH_API_KEY 互斥；支持 ~，相对路径基于图目录 |
| SGRAPH_BASE_URL | 服务 API 地址，传给模型集成的 base_url |
| SGRAPH_TEMPERATURE | 非负有限浮点数 |
| SGRAPH_TIMEOUT | 正有限秒数 |
| SGRAPH_MAX_TOKENS | 正整数 |
| SGRAPH_MAX_RETRIES | 非负整数 |

未设置的参数不覆盖模型集成默认值。未显式指定 key 时，集成读取自己的标准环境变量，例如 DEEPSEEK_API_KEY。不自动搜索 key 文件，不自动读取 OpenCode 凭据或配置。Python model factory 自行管理连接，这些新参数不会自动传给 factory。不同提供方仍可通过 factory 定制其特有参数。

DeepSeek 使用可选依赖 `pip install -e '.[deepseek]'`。在终端设置：

```bash
export SGRAPH_MODEL=deepseek:deepseek-chat
export SGRAPH_API_KEY_FILE="$HOME/sys_prog/deepseek_api.txt"
export SGRAPH_TEMPERATURE=0
export SGRAPH_TIMEOUT=45
.venv/bin/sgraph examples/01-assistant/workflow_cn.md
```

完整真实工具 Host、测试命令和用例见[真实模型验收入口](../../tests/live/README_cn.md)，结果分析见[DeepSeek 验收报告](DEEPSEEK_ACCEPTANCE_cn.md)。

## 本地 MCP 示例

已提供无需全局服务配置的[stdio MCP 示例](../../tests/mcp_demo/README_cn.md)，Host 自动启动本地工具服务，运行完成后清理。设置 DeepSeek 环境变量后可执行 `printf '请调用工具计算17加25。\n' | .venv/bin/sgraph tests/mcp_demo/workflow_cn.md`。本地验收范围见[MCP 报告](MCP_ACCEPTANCE_cn.md)。

## 无需 Python 的文本输入节点

```markdown
# [Node] AskUser
- **@uses**: request_input:请补充输出格式。

## [Transitions]
- @Default -> @End
```

request_input 不调用模型，将参数作为原生中断提示，恢复后将字符串回复写成 HumanMessage 更新。节点正文不参与执行。普通长文本直接写在同一行；需要提示换行时用双引号 JSON 字符串，例如 `request_input:"第一行\n第二行"`。引号不支持物理跨行；解码由执行器负责，不改变解析器。回复不会自动作为路由键，条件选路仍需 router。仅含 request_input 的图通过 API 加载不需要模型；默认 chat Host 仍按已有流程配置模型。

## 首次 API 配置向导

安装 chat 可选依赖（包含 langchain-openai）后，交互终端没有 `--model`、`--model-factory`、SGRAPH_MODEL、SGRAPH_MODEL_FACTORY 或已保存配置时，自动进入向导。也可主动重新配置：

```bash
.venv/bin/sgraph examples/01-assistant/workflow_cn.md -- --setup
```

主动配置完成即退出；自动首次配置后继续运行当前图。向导收集：

1. API 基础 URL，例如 `https://api.openai.com/v1` 或服务商提供的兼容地址；不要填写完整 `/chat/completions` 或 `/responses` 路径。
2. 模型 ID，按服务商说明填写，不自动枚举模型。
3. Chat Completions 或 Responses 接口模式。
4. 隐藏输入的 API key；回车可复用已有 SGRAPH_API_KEY、SGRAPH_API_KEY_FILE 或 OPENAI_API_KEY。环境密钥不会被复制进配置文件。无鉴权本地接口可填写 `not-needed`。
5. 可选静态 HTTP 请求头 JSON，例如 `{"X-Session-ID":"your-session"}`，隐藏输入，回车跳过。也可使用 SGRAPH_HEADERS_JSON；此变量整体替换保存的请求头。

所有向导文本先按 SGRAPH_LANGUAGE，再按 LC_ALL、LC_MESSAGES、LANG 选择语言；中文 locale 使用中文，其他语言回退英文。没有环境语言标识时读取 Python 的系统语言标识，不调用 setlocale、不要求安装特定 OS locale。可用 `SGRAPH_LANGUAGE=zh` 或 `en` 显式覆盖。语言自动选择按实现设计跨平台；实际测试平台为 Linux。

保存位置优先 SGRAPH_HOST_CONFIG；否则使用 XDG_CONFIG_HOME/skilledgraph/host.json，Windows 在无 XDG_CONFIG_HOME 时使用 APPDATA/skilledgraph/host.json，其余回退 ~/.config/skilledgraph/host.json。本次输入的密钥和请求头以明文保存；POSIX 文件权限为 0600，Windows 依赖用户目录权限。密码输入不进入编辑历史。EOF 或 Ctrl-C 取消时不保存、不覆盖现有配置。尚未验证的配置也会保存，保存完成提示明确说明尚未测试连接。

显式 CLI 模型／factory 优先于环境模型／factory；只要提供这些选择，就不读取保存的配置，不混用其中的网关地址和密钥。只有采用保存的模型时，SGRAPH 连接环境变量覆盖对应保存参数；provider 标准环境变量仍由原生客户端读取。factory 继续完全管理自己的连接。`--setup` 主动替换配置，不会运行图，也不采用当前模型选择。管道输入不会进入向导或消耗图输入：没有可用配置时明确报错。

兼容范围是 OpenAI 风格 Chat Completions 与 Responses，加上静态自定义请求头。OpenCode Zen 不同模型可能使用不同协议，需按[官方端点表](https://opencode.ai/docs/zen/)填写模式和基础 URL；仅支持其中这两种 OpenAI 风格协议。没有实现 OpenCode 套餐 OAuth、订阅鉴权、动态 session 标识生成、自动登录或配置文件导入，也不保证某套餐授权允许从外部应用调用。复杂接入继续使用模型 factory 或自定义 Host。

### OpenCode Go 实测补充

Go 客户端除接口和密钥外，应按[官方说明](https://opencode.ai/docs/go/)发送自己的 User-Agent，以及同一会话内稳定的 x-opencode-session。例如静态头部字段可填：

```json
{"User-Agent":"skilledgraph/0.1.0.dev0","x-opencode-session":"your-conversation-id"}
```

基础 Host 连接 `https://opencode.ai/zen/go/v1` 时，现在会自动补充自己的 User-Agent 和 `sgraph-harness-agent-<UUID>` 形式的 x-opencode-session；无需手填上述两个头部。每次启动创建一个模型及新的会话 ID，同一图执行中的所有节点、工具循环和中断恢复复用该模型，因此保持同一 ID。

显式头部按名称大小写无关匹配并优先保留。若旧配置中保存了静态 session ID，应删除该项以启用自动生成。自定义 Host 若复用同一个模型处理多个会话，需自行管理显式 session 头或为新会话创建新的模型；模型 factory 继续自行负责。自动值不写回配置文件，不发送给其他接口。对 glm-5.3-flash，基础地址为 https://opencode.ai/zen/go/v1，选择 Chat Completions，模型 ID 填 glm-5.3-flash。本项目已真实验证普通编码请求及工具循环；其他模型按端点表选择协议，不能把此次结果推广为所有套餐模型。详见[验收记录](OPENCODE_GO_ACCEPTANCE_cn.md)。
