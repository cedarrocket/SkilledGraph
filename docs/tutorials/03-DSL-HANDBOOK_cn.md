# 第三篇：DSL 与 Python 协同开发手册 (DSL Handbook & Cheat Sheet)

[中文](03-DSL-HANDBOOK_cn.md) | [English](03-DSL-HANDBOOK_en.md) | [← 上一篇：循序渐进实战教程](02-STEP-BY-STEP_cn.md) | [返回教程首页](README_cn.md)

本手册是你在编写 SkilledGraph 工作流时的**案头速查工具书**。我们将 `docs/standard/v0.1/` 中上万字的严谨规范，提炼成了直观的语法卡片、对比表格、模板代码与常见排错指南。

---

## 1. 一图看懂 DSL 文件全景结构

一个标准的 `.md` 工作流文件由 **可选前言 + 可选 `# [Config]` + 一个或多个 `# [Node]` / `# [ToolNode]`** 组成：

```markdown
这里可以写普通文字作为文件前言（在第一个标题之前）。
前言不属于任何节点，也不会发给大模型。

# [Config]
- **@host**: python:./host.py:main
- **@state**: python:./actions.py:State

# [Node] Step1
- **@uses**: pyfunction:./actions.py:load_data
- **@router**: python:./actions.py:decide_next

>>> 这是作者注释（以顶格 >>> 开头），不会发给大模型，仅供审计或备注。

这里是 Step1 的节点正文（Prompt）。
可以包含普通段落、列表，或者闭合的代码块：
```markdown
代码块里的 # [Node] FakeNode 只是普通文字，不会被当成真正的节点！
```

## [Transitions]
| 路由键 | 目标节点 | 说明 |
| --- | --- | --- |
| ok | Step2 | 数据正常，进入下一步 |
| need_tool | RunTools | 需要调用工具 |

# [ToolNode] RunTools
- **@tools**: [search, calculate]

## [Transitions]
- @Default -> Step1

# [Node] Step2
根据之前的信息输出最终结论。

## [Transitions]
- @Default -> @End
```

### 结构铁律：
1. **顶格书写**：所有 `# [Config]`、`# [Node]`、`# [ToolNode]`、`## [Transitions]`、`- **@KEY**: VALUE` 以及 `>>>` 注释，都**必须从物理第 1 列（顶格）开始写**，前面不能缩进。
2. **大小写严格敏感**：`# [Node] A` 是节点，但 `# [node] A` 只是普通 Markdown 一级标题！`@Default`、`@End`、`@ToolCalls`、`@Otherwise` 同样严格区分大小写。
3. **入口与顺序**：文件中的**第 1 个节点**就是图的入口（`START -> 第1个节点`）。节点在文件中的排列顺序**不会**自动产生连线，所有跳转必须靠 `## [Transitions]` 声明。
4. **`Transitions` 必须在节点最后**：每个节点最多只能有一个 `## [Transitions]`，且必须是该节点的最后一个区块。在 `## [Transitions]` 下面不能再写普通 Prompt 正文或 `- **@uses**`，直到遇到下一个 `# [Node]`。

---

## 2. 四大配置项 (`@KEY`) 速查表

在 SkilledGraph 中，配置项的语法固定为：`- **@键名**: 值`（注意 `**@` 连在一起，冒号在粗体外面）。

**没有任何隐式配置或未公开的键名**。不同区块允许使用的键严格固定：

| 配置项 | 允许出现的位置 | 格式示例 | 作用说明 |
| --- | --- | --- | --- |
| **`@host`** | `# [Config]` | `- **@host**: python:./host.py:main` | 指定用 `sgraph` 启动该文件时调用的 Python 入口函数。不写则默认使用内置聊天宿主。 |
| **`@state`** | `# [Config]` | `- **@state**: python:./state.py:State` | 指定图的 LangGraph `State` Schema（如 `TypedDict` 或 `MessagesState` 子类）。不写则默认使用 `MessagesState`。 |
| **`@uses`** | `# [Node]` | `- **@uses**: pyfunction:./a.py:fn`<br>`- **@uses**: python:./a.py:fn`<br>`- **@uses**: request_input:提示词`<br>`- **@uses**: monty:./calc.py` | 指定当前节点的执行方式。不写则默认为“调用一次大模型”的普通 Prompt 节点。 |
| **`@router`** | `# [Node]` 或 `# [ToolNode]` | `- **@router**: python:./a.py:route`<br>`- **@router**: monty:./route.py` | 节点执行完且 State 合并后，调用该函数计算并返回路由键字符串。 |
| **`@tools`** | **`# [ToolNode]` 专用（必填）** | `- **@tools**: all`<br>`- **@tools**: [add, search_notes]` | 指定该工具节点可执行哪些工具（工具名不加引号，不能有尾随逗号）。**普通 `# [Node]` 不可使用 `@tools`。** |

> **小细节**：如果你在节点正文里写了 `- **重点**: 注意事项` 或 `- @uses: xxx`（没加粗），解析器会把它当成普通的 Prompt 列表文字；但只要你写了 `- **@`，解析器就会开启严格语法检查——拼错键名（比如 `- **@model**: gpt-4`）会直接报错，绝不会静默当成正文混过去！

---

## 3. 五种节点执行模式全对比

一个 `# [Node]` 到底干什么活，完全取决于它的 `- **@uses**` 怎么写。下表帮你一秒选对模式：

| 模式 | `@uses` 怎么写 | 会自动调大模型吗？ | 节点正文 (Prompt) 怎么处理？ | Python 函数接收什么？返回什么？ | 典型适用场景 |
| --- | --- | --- | --- | --- | --- |
| **1. 默认 Prompt 节点** | *(不写 `@uses`)* | **会（调 1 次）** | 作为本次调用的 `SystemMessage`（不存入历史） | 无需 Python 函数；自动把 `[SystemMessage(正文), ...历史消息]` 发给模型，把回复追加进 `messages` | 纯对话、总结、翻译、直接让模型输出路由键做分类 |
| **2. 材料函数节点 (`pyfunction`)** | `pyfunction:./file.py:fn` | **会（调 1 次）** | 作为本次调用的 `SystemMessage`（不存入历史） | **入参**：`state`<br>**返回**：任意材料（`str`/`dict`/`list`/`BaseMessage`），**不要返回 State 更新字典**。材料会转为 `HumanMessage` 连同历史一起发给模型，材料+回复共同存入 `messages` | 调模型前，先用 Python 读本地文件、查数据库或拼装统计数据喂给模型 |
| **3. 原生代码节点 (`python`)** | `python:./file.py:fn` | **不会** | 框架忽略正文（自定义绑定可通过 `node.prompt` 读取） | **入参**：`state`（及可选 `config`/`runtime`）<br>**返回**：原生 LangGraph State 更新字典（如 `{"count": 1}`）或 `Command` | 格式校验、正则提取、修改状态字段、不涉及大模型的纯逻辑计算 |
| **4. 交互提问节点 (`request_input`)** | `request_input:提示语` | **不会** | 忽略正文 | 无需 Python 函数；触发原生 `interrupt(提示语)`，人类恢复的字符串自动存为一条 `HumanMessage` | 运行中途请求用户补充信息、人工审批确认 |
| **5. 沙箱表达式 (`monty`)** | `monty:./script.py` *(注意无 `:函数名`)* | **不会** | 忽略正文 | 脚本内直接读取 JSON 化的 `state` 变量；**文件最后一个表达式的值**作为返回的 State 更新字典（或作为 `@router` 的路由键字符串） | 需要限制内存（32MB）/时间（1s）、禁止文件与网络访问的轻量级安全数据变换 |

### 关于文件路径引用 (`python:FILE:ENTRY` / `pyfunction:FILE:ENTRY`) 的黄金法则：
1. **`FILE` 必须以 `./`、`../` 开头，或者是操作系统的绝对路径**。不能写裸文件名（如 `python:tools.py:run` 是错的，必须写 `python:./tools.py:run`），也不能写包模块路径（如 `python:my_pkg.tools:run` 不支持）。
2. **相对路径永远相对于当前 `.md` 文件所在的文件夹**，无论你在哪个目录下执行 `sgraph` 命令！
3. **`ENTRY` 只能是简单的变量/函数/类名**，不能写带括号的调用（如 `:create()` 是错的，写 `:create`）。

---

## 4. 路由与跳转 (`## [Transitions]`) 完全指南

### 4.1 两种书写格式（二选一，不可混用）

**列表格式**（适合简单跳转）：
```markdown
## [Transitions]
- pass -> Publish
- fail -> Rewrite
```

**表格格式**（适合分支较多、需要写备注的场景）：
```markdown
## [Transitions]
| 路由键 | 下一步节点 | 触发条件说明（第3列起不参与执行） |
| --- | --- | --- |
| pass | Publish | 校验通过，直接发布 |
| fail | Rewrite | 发现错误，打回重写 |
```

### 4.2 四种特殊 `@` 标记的精确含义

| 标记 | 出现位置 | 含义与限制 |
| --- | --- | --- |
| **`@Default`** | 路由键（箭头左边 / 第1列） | **唯一无条件边**。表示不管发生什么，无条件跳往目标。**绝对不能和任何其他路由键混在一个表里**（它不是 `else` 兜底！）。 |
| **`@End`** | 目标节点（箭头右边 / 第2列） | 表示当前路径到此结束（对应 LangGraph 的 `END`）。注意不能简写成 `- @End`，必须写 `- @Default -> @End` 或 `- done -> @End`。 |
| **`@ToolCalls`** | 路由键（箭头左边 / 第1列） | 检查合并后 `State.messages` 的最后一条消息：如果是 `AIMessage` 且包含非空的 `tool_calls`，则命中此分支（优先级最高，会跳过显式 `@router`）。 |
| **`@Otherwise`** | 路由键（箭头左边 / 第1列） | **真正的条件兜底（Fallback）**！当 `@ToolCalls` 和其他普通路由键都没匹配上时，走 `@Otherwise` 分支。 |

### 4.3 条件节点的路由键从哪来？（决策流程图）

当你在 `## [Transitions]` 里写了条件分支（不是 `@Default`）时，SkilledGraph 按以下顺序决定走哪条路：

```text
节点执行完毕，输出已通过 Reducer 合并进 State
                     |
                     v
  [表里声明了 @ToolCalls，且最后一条 AIMessage 有 tool_calls 吗？]
         | 是                                    | 否
         v                                       v
  直接跳往 @ToolCalls 的目标          [节点声明了 - **@router** 吗？]
                                         | 是                    | 否
                                         v                       v
                               调用 router(state)      [是默认 Prompt 或 pyfunction 节点吗？]
                               拿返回的字符串作为键       | 是                    | 否 (如 python 节点)
                                         \               v                       v
                                          \     取模型本次回复去首尾空白   构建阶段直接报错！
                                           \         作为路由键            (必须配 @router)
                                            \           /
                                             v         v
                                     [路由键在表里能精确匹配到吗？]
                                         | 能            | 不能
                                         v               v
                                  跳往对应目标    [表里声明了 @Otherwise 吗？]
                                                     | 是            | 否
                                                     v               v
                                              跳往 @Otherwise   抛出 RoutingError！
```

> **实战建议**：
> - 如果一个模型节点**既要输出长篇业务回答，又要决定下一步路由**，请不要依赖“默认模型文本选路”（因为长篇回答去空白后不等于路由键）。正确做法是：要么给它配一个 Python `@router` 去解析回答，要么拆成两个节点（前一个节点生成回答，后一个节点只输出路由键或用 Python 校验）。

---

## 5. 状态 (`State`)、消息历史与 Reducer 机制

### 5.1 默认状态：`MessagesState`
如果你不在 `# [Config]` 里写 `@state`，图默认使用 LangGraph 的 `MessagesState`，它只有一个字段：
```python
messages: Annotated[list[ AnyMessage ], add_messages]
```
- **追加而非覆盖**：因为自带 `add_messages` Reducer，你的 Python 节点在返回消息更新时，**只需要返回新增的那一两条消息**：
  ```python
  # 正确：只返回本次新增的消息，LangGraph 会自动把它追加到历史末尾
  return {"messages": [AIMessage(content="校验通过")]}
  
  # 错误（除非你故意想重写历史）：不要把整个 state["messages"] 重新塞回去
  ```
- **额外字段不会自动发给模型**：如果你自定义了 `class State(MessagesState): score: int`，默认 Prompt 节点在调用大模型时，**依然只读取 `state["messages"]`**，`score` 字段不会自动拼进 Prompt。如果你想让模型看到 `score`，可以用 `pyfunction` 把 `score` 转成材料消息，或者在 `python` 节点里把它写进一条 `HumanMessage`。

### 5.2 自定义 State 与 Reducer
你可以在 Python 文件里定义任何原生 LangGraph 支持的 `TypedDict` State：

```python
from typing import Annotated
from typing_extensions import TypedDict
from operator import add
from langgraph.graph import MessagesState

# 方式 1：在保留聊天历史的基础上扩充字段（最常用，支持普通 Prompt 节点）
class AgentState(MessagesState):
    attempts: int                           # 无 Reducer：后一次返回的值直接覆盖前一次
    logs: Annotated[list[str], add]         # 有 Reducer (operator.add)：每次返回的列表会自动拼接

# 方式 2：纯数据计算图（不含 messages，所有节点都用 @uses: python:... 或 monty:...）
class CalcState(TypedDict):
    value: int
    events: Annotated[list[str], add]
```

---

## 6. Python API 集成与原生 LangGraph 混编

除了在命令行用 `sgraph workflow.md` 运行，你完全可以把 SkilledGraph 当成一个 Python 库，嵌入到你自己的 FastAPI 后端、桌面应用或复杂 Agent 系统中。

SkilledGraph 只暴露 **3 个极简核心函数**：

```python
from skilledgraph import parse_graph, build_graph, load_graph
```

### 用法 1：直接编译并运行 (`load_graph`)
```python
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from skilledgraph import load_graph

# 加载并编译成 100% 原生的 LangGraph CompiledStateGraph
graph = load_graph(
    "my_workflow.md",
    model=my_langchain_model,                      # 可选：传入聊天模型
    tools=[my_tool_1, my_tool_2],                  # 可选：传入工具列表
    state_schema=MyCustomState,                    # 可选：显式覆盖文件中的 @state
    compile_kwargs={"checkpointer": InMemorySaver()} # 可选：原样透传给 builder.compile()
)

# 接下来就是标准的 LangGraph 调用方式（invoke / ainvoke / stream / astream）
result = graph.invoke(
    {"messages": [HumanMessage(content="你好")]},
    config={"configurable": {"thread_id": "user-123"}}
)
```

### 用法 2：获取原生 Builder 进行手术刀级改造 (`build_graph`)
如果某个高级特性（例如**多分支并行 Fan-out / Fan-in 汇聚**，参考 `examples/15-parallel-code-review/`）在 Markdown DSL 里没有提供语法，你可以先用 `build_graph()` 拿到未编译的原生 `StateGraph` Builder，加上原生边之后再编译：

```python
from skilledgraph import build_graph

# 1. 让 SkilledGraph 帮你完成所有节点的挂载和基础连线
builder = build_graph("workflow.md", model=my_model)

# 2. 直接调用原生 LangGraph API 添加并行分发与汇聚边！
for reviewer in ("Correctness", "Security", "Style"):
    builder.add_edge("Prepare", reviewer)
builder.add_edge(["Correctness", "Security", "Style"], "Synthesize")

# 3. 手动编译运行
graph = builder.compile()
```

### 用法 3：注册你自己的 `@uses` 执行器 (`bindings`)
觉得内置的 `python:`、`pyfunction:`、`request_input:`、`monty:` 不够用？你可以用 10 行代码写一个自己的 `@uses` 前缀（比如 `- **@uses**: my_rag:product_docs`）：

```python
from langchain_core.messages import HumanMessage
from skilledgraph import load_graph

# 定义绑定函数：签名固定为 (payload, *, base_dir, node, model=None)
def bind_my_rag(payload: str, *, base_dir, node, model=None):
    # payload 就是冒号后面的 "product_docs"
    # node.prompt 就是你在 Markdown 节点里写的正文！
    def run_node(state):
        docs = search_database(collection=payload, query=state["messages"][-1].text)
        return {"messages": [HumanMessage(content=f"参考文档：{docs}\n要求：{node.prompt}")]}
    return run_node

# 在构建图时通过 bindings 参数传入即可！
graph = load_graph("workflow.md", model=my_model, bindings={"my_rag": bind_my_rag})
```

---

## 7. 新手最常踩的 10 个坑（排错速查表）

遇到报错时，先对照这张表检查，95% 的问题都能在 30 秒内解决：

| 现象 / 报错信息 | 原因剖析 | 正确改法 |
| --- | --- | --- |
| **1. 写了 `# [node] Test` 或 `  - **@uses**: ...`，结果没生效，被当成了普通 Prompt 发送** | DSL 关键字严格区分大小写，且**必须顶格（第 1 列）书写**。 | 改为顶格的 `# [Node] Test` 和顶格的 `- **@uses**: ...`。 |
| **2. 报错 `Unknown setting` 或在 `# [Config]` 里写 `- **@model**: ...` 报错** | `# [Config]` 只允许 `@host` 和 `@state`；模型配置属于 Host 环境，绝不写进 DSL。 | 删掉 `@model`，改用 `sgraph workflow.md -- --setup` 或环境变量 `SGRAPH_MODEL` 配置模型。 |
| **3. 报错 `Cannot bind 'python:tools.py:run'`（找不到文件）** | 内置文件引用不支持裸文件名，必须显式写出 `./` 或 `../` 相对路径前缀。 | 改为 `- **@uses**: python:./tools.py:run`。 |
| **4. 报错 `Node 'X' needs @router: this execution binding has no implicit route-key protocol`** | 你给一个 `@uses: python:...` 或 `request_input:...` 的节点写了条件跳转表（非 `@Default`），但没配 `@router`。只有普通模型节点和 `pyfunction` 才能用模型回复自动选路。 | 给该节点加上 `- **@router**: python:./tools.py:my_router`。 |
| **5. 报错 `Node 'X' returned route 'Report'; legal keys: ('ready', 'missing')`** | 你的 `@router` 函数或模型直接返回了右边的**目标节点名**（`Report`），或者模型输出了多余的句号/解释文字。 | `@router` 和模型必须返回箭头**左边的路由键**（如 `'ready'`），且模型不能输出多余解释。 |
| **6. 在条件跳转表里写了 `- @Default -> Fallback` 想当兜底，结果解析报错** | `@Default` 是“唯一无条件边”，**不能和任何其他条件键混用**，它不是 `else`！ | 把兜底行的 `@Default` 改成 **`@Otherwise`**（即 `- @Otherwise -> Fallback`）。 |
| **7. 写了 `- @End` 想结束节点，结果解析报错** | `@End` 只能放在箭头右边当目标，不能省略左边的路由键。 | 改为 `- @Default -> @End`。 |
| **8. 在普通 `# [Node]` 里写了 `- **@tools**: [add]` 报错** | `@tools` 只能用在专用的 `# [ToolNode]` 节点里；普通 `# [Node]` 不能同时既是模型节点又是工具执行节点。 | 把工具执行拆成一个独立的 `# [ToolNode] ExecuteTools`，并在模型节点用 `- @ToolCalls -> ExecuteTools` 跳过去。 |
| **9. `pyfunction` 函数返回了 `{"status": "ok"}`，结果 `state["status"]` 根本没更新** | `pyfunction` 是**材料函数**，它返回的字典会被转成 JSON 字符串包装进 `HumanMessage` 喂给模型，**不会**用来更新 `State` 字段！ | 如果你想直接修改 `State` 字段，请用 `- **@uses**: python:./file.py:fn`。 |
| **10. 在 `## [Transitions]` 下面写了 `>>> 注释` 或一段 Prompt，结果解析报错** | `## [Transitions]` 必须是节点的最后一部分，进入该区域后只允许写跳转列表或一张表格，直到下一个 `# [Node]`。 | 把所有 Prompt 正文、`>>>` 注释和 `- **@uses**` 移到 `## [Transitions]` **上方**。 |

---

## 8. 编写新工作流的标准自检清单 (Checklist)

每次当你（或者你让 AI 编码助手）写完一个新的 SkilledGraph 工作流时，请按以下 3 步做一次快速验证：

1. **第一步：跑只读语法检查**
   ```bash
   sgraph --check path/to/workflow.md
   ```
   确保没有拼写错误、未闭合代码块或孤立的目标节点名。
2. **第二步：用离线模型替身跑通所有分支**
   在消耗真实大模型 Token 之前，先用 `--model-factory` 指向一个几行代码的 `DemoModel`（或者在自定义 Host 里加一个 `--demo` 参数），把每一条条件路由（比如成功分支、重试分支、失败耗尽分支）都跑通一遍，确认 `State` 字段和 `messages` 更新符合预期。
3. **第三步：切换真实模型验收**
   去掉 `--demo` 或 `--model-factory`，连接真实 LLM 检验 Prompt 的实际遵循效果。

---

[← 上一篇：循序渐进实战教程](02-STEP-BY-STEP_cn.md) | [返回教程首页](README_cn.md)
