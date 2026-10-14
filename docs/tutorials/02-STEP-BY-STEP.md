# 第二篇：循序渐进实战教程 (Step-by-Step)

[中文](02-STEP-BY-STEP_cn.md) | [English](02-STEP-BY-STEP_en.md) | [← 上一篇：10 分钟快速上手](01-QUICKSTART.md) | [返回教程首页](README.md) | [下一篇：DSL 与 Python 协同开发手册 →](03-DSL-HANDBOOK.md)

在上一篇中，我们学会了用 `# [Node]` 和 `- @Default -> ...` 串联起简单的 Prompt 流水线。

但在真实世界里，一个有用的 Agent 工作流往往需要：**分支判断、读取本地数据、用代码校验结果、调用工具（Tool Calling），或者在关键操作前请求人类确认**。

本篇教程分为 **6 个进阶站点**，每一站只引入一个新特性，并对应仓库 `examples/` 中的真实可运行案例。

---

## 第 1 站：让模型自己做选择题（模型文本选路）

**场景**：用户输入一段话，我们先让 `Evaluate` 节点判断材料够不够。如果够了，跳去 `Report` 写报告；如果不够，跳去 `RequestMore` 追问用户。

当一个普通模型节点的 `## [Transitions]` 里写的不是 `@Default`，而是**具名路由键**时，SkilledGraph 会自动开启**默认文本选路**：

### 写法 A：列表形式（参考 `examples/03-routing-list/workflow.md`）

```markdown
# [Node] Evaluate

判断用户提供的信息是否足以撰写完整分析报告。
只在以下两个路由键中选择一个输出，不要输出任何标点或解释：
- enough
- insufficient

## [Transitions]
- enough -> Report
- insufficient -> RequestMore

# [Node] Report

根据已有信息生成完整分析报告。

## [Transitions]
- @Default -> @End

# [Node] RequestMore

礼貌地指出缺失的信息，并请用户补充材料。

## [Transitions]
- @Default -> @End
```

### 写法 B：表格形式（参考 `examples/04-routing-table/workflow.md`）

如果你觉得列表不够直观，想给每个分支加点人类可读的备注，可以把 `## [Transitions]` 写成 Markdown 表格：

```markdown
## [Transitions]
| 路由键 | 目标节点 | 备注说明（给人类看，不参与执行） |
| --- | --- | --- |
| enough | Report | 信息充足，直接生成报告 |
| insufficient | RequestMore | 信息不足，向用户追问 |
```

> **核心规则（避坑必看）**：
> 1. **列表和表格二选一**：同一个 `## [Transitions]` 里不能既写列表又写表格。表格的前两列固定是“路由键”和“目标节点”，第 3 列及以后你可以随便写说明文字。
> 2. **精确匹配**：当没有配置 Python `@router` 时，框架会把模型回复的首尾空格去掉（`reply.text.strip()`），然后**直接去表里查**。它**不会**帮你从一段长篇大论里用正则抠单词，也**不会**帮你去掉引号或代码块。所以你的 Prompt 必须明确要求模型：“**只输出路由键本身，不要输出其他内容**”。
> 3. **`@Default` 不是兜底（Fallback）！**：一旦用了具名路由键（如 `enough`），就不能在同一个表里写 `@Default`。如果模型返回了表里没有的词，运行会直接报错，防止工作流静默走错分支。

---

## 第 2 站：先跑 Python 拿材料，再喂给模型（`pyfunction`）

**场景**：你想让模型总结今天的账单，但账单数据存在本地文件或需要几行 Python 算出来。你不希望为此放弃便利的 Prompt 节点写法。

这时候就轮到 `- **@uses**: pyfunction:文件路径:函数名` 登场了！（参考 `examples/06-pyfunction/`）

### 1. 编写 `tools.py`（提供原材料）

```python
def prepare(state) -> str:
    # 接收当前图的 state，返回你要喂给模型的材料（字符串、字典、列表或原生 Message 均可）
    return "记录 A：金额 12。记录 B：金额 8。"
```

### 2. 编写 `workflow.md`（组装材料与 Prompt）

```markdown
# [Node] Analyze
- **@uses**: pyfunction:./tools.py:prepare

>>> 以三个右尖括号开头的行是作者注释，不会发给大模型！

根据函数提供的记录计算总金额，并说明计算过程。

## [Transitions]
- @Default -> @End
```

### `pyfunction` 节点在底层为你做了哪 5 件事？

当你运行上面这个节点时，SkilledGraph 会按顺序自动执行：
1. 调用你的 `prepare(state)` 函数，拿到返回值 `"记录 A：金额 12。记录 B：金额 8。"`。
2. 把这个返回值自动包装成一条 `HumanMessage`（如果是字典/列表会自动转成 JSON 字符串；如果你直接返回 LangChain 的 `BaseMessage` 则原样保留）。
3. 组装发给大模型的输入列表：
   `[SystemMessage(节点正文), ...已有的历史消息..., HumanMessage(本次材料)]`
4. **调用一次大模型**，拿到 `AIMessage` 回复。
5. 把 **`[本次材料消息, 模型回复]`** 一起追加到 `State.messages` 历史中！

你可以直接离线运行示例 06 看看效果：
```bash
printf '请开始分析\n' | sgraph examples/06-pyfunction/workflow.md -- --model-factory python:../support/demo_model.py:create
```
你会发现模型收到的是 **3 条输入消息**（1 条系统提示词 + 1 条你的输入 + 1 条 `prepare` 函数生成的账单材料）！

---

## 第 3 站：纯 Python 节点、自定义 State 与代码路由（`python` + `@router` + `@state`）

**场景**：有些步骤根本不需要调用大模型（比如检查输入格式、用正则表达式验算模型的计算结果、更新重试计数器），并且要根据代码计算出的状态决定下一步跳去哪。

这时候我们要组合使用三个神器（参考 `examples/05-python-router/`）：
- **`# [Config]` 里的 `- **@state**`**：声明自定义的 LangGraph `State` 类。
- **节点里的 `- **@uses**: python:...`**：完全由你的 Python 函数接管节点执行，**框架不会自动调用大模型**。
- **节点里的 `- **@router**: python:...`**：节点执行完、状态合并后，用 Python 函数读取最新 `State` 并返回路由键字符串。

让我们看一个完整的 3 文件配合案例：

### 1. 定义状态结构 `state.py`
继承 `MessagesState`，既保留了默认的 `messages` 聊天历史通道，又增加了一个自定义的 `status` 字段：
```python
from langgraph.graph import MessagesState

class State(MessagesState):
    status: str
```

### 2. 编写节点动作与路由函数 `tools.py`
```python
from langchain_core.messages import AIMessage

# 1. 这是 @uses 调用的节点函数：接收 State，返回要更新的 State 字典
def inspect(state):
    status = "ready" if state["messages"] else "missing"
    text = "已收到待处理输入。" if status == "ready" else "尚未收到输入。"
    return {"status": status, "messages": [AIMessage(content=text)]}

# 2. 这是 @router 调用的路由函数：读取合并后的最新 State，返回路由键字符串
def route(state) -> str:
    return state["status"]
```

### 3. 编写工作流 `workflow.md`
```markdown
# [Config]
- **@state**: python:./state.py:State

# [Node] Inspect
- **@uses**: python:./tools.py:inspect
- **@router**: python:./tools.py:route

>>> 代码更新 status，router 读取合并后的 State；此节点没有自动模型调用。

## [Transitions]
- ready -> Report
- missing -> RequestMaterial

# [Node] Report

根据历史中的输入与检查结果生成简明报告。

## [Transitions]
- @Default -> @End

# [Node] RequestMaterial

请用户提供待分析材料。

## [Transitions]
- @Default -> @End
```

### 黄金执行顺序（必背！）：
在 `Inspect` 节点上，执行顺序严格遵循：
> **`inspect(state)` 运行并返回更新字典** ➔ **LangGraph Reducer 将更新合并进 `State`** ➔ **`route(state)` 读取合并后的 `State`** ➔ **返回 `"ready"` 或 `"missing"`** ➔ **查 `## [Transitions]` 表跳转到目标节点**。

> **重要提醒**：
> - `route(state)` 返回的必须是**左边的路由键**（如 `"ready"`），而不是右边的目标节点名（`"Report"`）。
> - 使用 `python:...` 的节点如果要走条件分支（非 `@Default`），**必须**显式配一个 `@router`。

---

## 第 4 站：给模型装上双手——工具调用循环（`ToolNode`）

**场景**：模型需要调用计算器、搜索本地知识库或执行函数，拿到结果后再回答用户（标准的 ReAct 循环）。

在 SkilledGraph 中，工具调用不是黑盒魔法，而是**一条清晰可见的图循环**（参考 `examples/10-tool-calling/`）：

```text
                  有工具调用请求 (@ToolCalls)
   +-------------+ ------------------------> +--------------+
   |  Assistant  |                           | ExecuteTools |
   |  (# [Node]) | <------------------------ | (#[ToolNode])|
   +-------------+      无条件跳回 (@Default)  +--------------+
         |
         | 没有调工具，直接给出了回答 (@Otherwise)
         v
       @End
```

### 看看 `examples/10-tool-calling/workflow.md` 是怎么写的：

```markdown
# [Config]
- **@host**: python:./host.py:main

# [Node] Assistant

使用加法工具计算用户请求，再回答结果。

## [Transitions]
| 条件 | 目标 |
| --- | --- |
| @ToolCalls | ExecuteTools |
| @Otherwise | @End |

# [ToolNode] ExecuteTools
- **@tools**: [add]

## [Transitions]
- @Default -> Assistant
```

### 理解工具调用的 4 个关键点：

1. **专用节点标题 `# [ToolNode] 节点名`**：
   它不是 `# [Node]`，而是 `# [ToolNode]`！它内部必须声明 `- **@tools**: [工具名1, 工具名2]` 或者 `- **@tools**: all`（表示允许执行 Host 传入的所有工具）。
2. **两个保留路由条件 `@ToolCalls` 与 `@Otherwise`**：
   - `@ToolCalls`：当 `Assistant` 输出的最后一条 `AIMessage` 里包含非空的 `tool_calls` 时，自动命中此分支，跳去 `ExecuteTools`。
   - `@Otherwise`：当模型没有请求调工具（说明它已经算完并给出了最终文本回答）时，命中此兜底分支，跳去 `@End`。
3. **工具执行完不会自动跳回！**：
   你必须在 `ExecuteTools` 下面显式写上 `- @Default -> Assistant`，让工具执行产生的 `ToolMessage` 回到 `Assistant` 节点，供模型生成最终回答。
4. **工具对象在哪里提供？在 Host 里！**
   Markdown 只负责写名字 `[add]`。真正的 Python 工具函数（用 `@tool` 装饰）和 `model.bind_tools([add])` 是在 Python 端传入 `load_graph(graph_path, model=bound_model, tools=[add])` 的（下一站我们马上讲 Host）。

直接运行下面命令，离线体验一次完整的工具调用：
```bash
sgraph examples/10-tool-calling/workflow.md
```
输出：
```text
human: 2 + 3 等于多少？
ai: 
tool: 5
ai: 结果是 5
```

---

## 第 5 站：运行中途暂停，等待人类确认（`request_input`）

**场景**：Agent 起草了一封邮件，或者发现用户需求缺少关键参数，需要在工作流运行到一半时**暂停（Interrupt）**，向终端里的用户提问，等用户输入回复后再继续往下走。

你不需要写一行 Python 代码就能实现中断节点！直接使用内置的 `request_input` 执行器（参考 `examples/11-interrupt/workflow.md`）：

```markdown
# [Node] AskUser
- **@uses**: request_input:请补充你希望采用的输出格式，例如：简短列表。

## [Transitions]
- @Default -> Report

# [Node] Report
请根据用户补充的信息回复。

## [Transitions]
- @Default -> @End
```

### 它是如何工作的？
1. 当图执行到 `AskUser` 时，它**不会调用大模型**，而是直接触发 LangGraph 原生的 `interrupt("请补充你希望采用的输出格式...")`。
2. 默认的终端 Host 捕获到中断后，会在屏幕上打印这段提示，并显示 `Resume>` 提示符等待你输入。
3. 你在键盘上输入 `"Markdown 表格"` 并回车后，图从断点处恢复执行。
4. `AskUser` 把你的回复包装成一条新的 `HumanMessage("Markdown 表格")` 追加到 `State.messages` 中，然后跳到 `Report` 节点！
5. 如果你的提示词需要换行，可以用 JSON 双引号包起来写在一行里：
   `- **@uses**: request_input:"请补充以下信息：\n1. 目标读者\n2. 字数要求"`

立刻在终端里交互体验一下（无需 API Key）：
```bash
sgraph examples/11-interrupt/workflow.md -- --model-factory python:../support/demo_model.py:create
```
先随便输入一句初始请求，接着就会看到中断提示和 `Resume>`，再输入你的补充要求即可看到 `Report` 节点的汇总输出！

---

## 第 6 站：编写你自己的 `@host`，彻底掌控一切

在前几站中，有些例子没有写 `# [Config]` 的 `@host`，有些写了 `- **@host**: python:./host.py:main`。这两者有什么区别？

- **不写 `@host` 时**：`sgraph` 默认启动内置的聊天宿主（`sgraph_chat_host`）。它做的事情很单纯：从终端读一行你的输入作为 `HumanMessage` ➔ 从头跑一遍图 ➔ 打印每个节点的 AI 回复 ➔ 退出。
- **什么时候需要自己写 `@host`？**
  1. 你的图需要传入自定义的初始 `State` 字段（比如 `{"value": 0, "events": []}` 或 CSV 文件路径）。
  2. 你的图使用了 `ToolNode`，需要在启动时传入 `tools=[...]` 并调用 `model.bind_tools(...)`。
  3. 你想自定义命令行参数（比如 `--demo`、`--input`），或者想把结果保存成文件而不是只打印在终端。

### 写一个自定义 Host 只需要 10 行 Python！

任何自定义 Host 都只是一个普通的同步 Python 函数，签名固定为 `main(graph_path: Path, argv: list[str]) -> int | None`（参考 `examples/09-state-only/host.py`）：

```python
from pathlib import Path
from skilledgraph import load_graph

def main(graph_path: Path, argv: list[str]) -> int | None:
    # 1. 编译当前 Markdown 工作流（也可以在这里传 model=..., tools=...)
    graph = load_graph(graph_path)
    
    # 2. 传入你自定义的初始 State 字典，调用原生 LangGraph 的 invoke()
    result = graph.invoke({"value": 0, "events": []})
    
    # 3. 随心所欲地处理或打印返回值
    print(result)
    return 0
```

然后在 `workflow.md` 顶部关联它：
```markdown
# [Config]
- **@host**: python:./host.py:main
- **@state**: python:./state.py:State
```

这样一来，当你在终端运行 `sgraph workflow.md -- --my-arg 123` 时：
- `sgraph` 会把 `workflow.md` 的绝对路径传给 `graph_path`。
- 把 `--` 后面的 `["--my-arg", "123"]` 原封不动传给 `argv`。
- 剩下的构建、模型绑定、异步事件循环（`asyncio.run(graph.ainvoke(...))`）全由你的 `main` 函数说了算！

---

## 进阶实战推荐：去看那 5 个综合 Agent 示例！

学完了这 6 站，你已经掌握了 SkilledGraph 的全部核心积木！如果你想看这些积木组合起来能搭出多么实用的工程应用，强烈建议接下来直接浏览 `examples/12-*` 到 `18-*`（它们全都支持 `--demo` 免 Key 离线运行）：

1. **[12-evidence-assistant](../../examples/12-evidence-assistant/README.md)**：本地知识库问答（`ToolNode` 搜索笔记 + `python` 节点校验引用来源真伪 + 失败打回重写）。
2. **[13-csv-auditor](../../examples/13-csv-auditor/README.md)**：CSV 报表审计（`pyfunction` 注入精确统计指标 + `python` 校验模型报告中有无算错数字）。
3. **[14-email-assistant](../../examples/14-email-assistant/README.md)**：邮件助手（模型分类路由 + `request_input` 人工审核草稿 + 批准后落盘保存）。
4. **[15-parallel-code-review](../../examples/15-parallel-code-review/README.md)** & **[16-batch-digest](../../examples/16-batch-digest/README.md)**：利用 `build_graph()` 获取原生 LangGraph Builder，实现多分支并行代码审查与 `Send` 动态 Map-Reduce 批量文档摘要。

在日常编写自己的工作流时，如果忘记了某个语法细节或遇到了报错，请随时翻阅下一篇：**[第三篇：DSL 与 Python 协同开发手册 (03-DSL-HANDBOOK.md)](03-DSL-HANDBOOK.md)**。
