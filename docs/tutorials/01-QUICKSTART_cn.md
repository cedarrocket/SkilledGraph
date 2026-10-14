# 第一篇：10 分钟快速上手 (Quickstart)

[中文](01-QUICKSTART_cn.md) | [English](01-QUICKSTART_en.md) | [返回教程首页](README_cn.md) | [下一篇：循序渐进实战教程 →](02-STEP-BY-STEP_cn.md)

本篇教程将带你在 10 分钟内搞懂 SkilledGraph 的核心工作方式，并在本地运行起你的第一个 Markdown 工作流。**即使你手头暂时没有大模型 API Key，也可以全程使用内置的离线演示模型跑通所有步骤。**

---

## 1. 为什么要用 SkilledGraph？

写 LLM 工作流（比如基于 LangGraph）时，我们常遇到两个痛点：
1. **Prompt 淹没在代码里**：几百行的长 Prompt 塞在 Python 字符串里，改个排版或调整提示词非常难受。
2. **图的连线不直观**：要在 `add_node`、`add_edge`、`add_conditional_edges` 之间来回跳转，才能看懂工作流到底怎么走。

**SkilledGraph 的解法很简单：职责分离。**

```text
+------------------------+       +------------------------+
|     workflow.md        |       |      actions.py        |
|------------------------|       |------------------------|
| 1. 有哪些节点 (# Node) | <---> | 1. 怎么读取本地数据    |
| 2. 节点 Prompt 写什么  |       | 2. 怎么校验模型输出    |
| 3. 下一步跳去哪 (->)   |       | 3. 自定义 State 数据   |
+------------------------+       +------------------------+
            \                               /
             \                             /
              v                           v
        +---------------------------------------+
        |   编译为 100% 原生 LangGraph 状态图   |
        +---------------------------------------+
```

- **Markdown (`.md`)** 只管两件事：**给模型说什么话（Prompt）**、**节点之间怎么跳（Transitions）**。
- **Python (`.py`)** 只管代码擅长的事：读写文件、请求 API、校验格式、管理宿主环境（Host）。

---

## 2. 安装环境

在项目根目录下创建虚拟环境并安装（推荐安装 `[chat]` 扩展，它包含了运行工作流所需的 LangGraph 运行时与交互式终端）：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[chat]'
```

安装完成后，你的终端里就多了一个命令：`sgraph`（也可以用 `python -m skilledgraph` 代替）。

我们先跑一条无需任何 API Key 的内置纯计算图，验证安装是否成功：

```bash
sgraph examples/09-state-only/workflow_cn.md
```

如果看到终端输出了 `{'value': 2, 'events': ['incremented', 'doubled']}`，恭喜你，环境已经就绪！

---

## 3. 你的第一个工作流：单节点助手

新建一个文件 `hello.md`，写入以下 6 行内容：

```markdown
# [Node] Assistant

你是一位幽默的程序员助手。请用一句话回答用户的问题。

## [Transitions]
- @Default -> @End
```

### 拆解这 6 行代码：
1. **`# [Node] Assistant`**：声明一个名为 `Assistant` 的节点。**文件中的第一个节点永远是整个工作流的起点（入口）**。
2. **中间的正文**：即发给大模型的系统提示词（`SystemMessage`）。只要节点没有声明特殊的代码执行方式，它默认就是一个“调用一次大模型”的普通节点。
3. **`## [Transitions]`**：声明当前节点执行完后，下一步去哪里。
4. **`- @Default -> @End`**：`@Default` 表示“无条件跳转”，`@End` 表示“整个工作流结束”。

### 第一步：静态语法检查 (`--check`)

在真正运行前，你可以让 SkilledGraph 帮你检查 Markdown 语法有没有写错：

```bash
sgraph --check hello.md
```

输出：
```text
OK: /你的路径/hello.md (1 nodes)
```
> **小贴士**：`--check` 是纯静态检查，速度极快，不会导入任何 Python 文件，也不会消耗任何 API Token。

### 第二步：离线试跑（无需 API Key）

项目自带了一个离线回声模型（位于 `examples/support/demo_model_cn.py`），它会把收到的最后一条消息原样加上前缀返回，专门用来测试流程是否畅通：

```bash
printf '什么是递归？\n' | sgraph hello.md -- --model-factory python:./examples/support/demo_model_cn.py:create
```
*(注意：如果 `hello.md` 在项目根目录下，上面的相对路径 `./examples/support/demo_model_cn.py` 可以直接找到离线模型。中间的 `--` 用来把 `sgraph` 自身的参数和传给 Host 的参数隔开。)*

你会看到输出：
```text
[Assistant] 演示回复（共 2 条输入消息）：什么是递归？
```
为什么显示“共 2 条输入消息”？因为 SkilledGraph 自动把节点的正文包装成了第 1 条 `SystemMessage`，再加上你输入的第 2 条 `HumanMessage`，一起发给了模型！

---

## 4. 连接真实大模型

想让真正的 LLM 来回答？你不需要修改 `hello.md` 的哪怕一个字符——**在 SkilledGraph 中，模型配置永远属于运行环境（Host），而不写死在 Markdown 里。**

你有两种最常用的连接方式：

### 方式 A：使用交互式配置向导（推荐）

直接运行：

```bash
sgraph hello.md
```

如果你还没有配置过模型，终端会自动弹出中文配置向导（你也可以随时通过 `sgraph hello.md -- --setup` 重新打开向导）：
1. **API 基础 URL**：例如 OpenAI 的 `https://api.openai.com/v1`，或 DeepSeek、硅基流动、本地 Ollama/LM Studio 的 `/v1` 兼容地址。
2. **模型 ID**：例如 `gpt-4o-mini`、`deepseek-chat` 等。
3. **接口模式**：通常选 `chat_completions`（如果是 OpenAI 新版 Responses 接口可选 `responses`）。
4. **API Key**：隐藏输入（本地无密码服务可填 `not-needed`）。

配置会安全地保存在 `~/.config/skilledgraph/host.json`（权限 `0600`）。保存后再次运行 `sgraph hello.md`，出现 `Input>` 提示符，输入你的问题按回车即可！

### 方式 B：使用环境变量

如果你习惯用环境变量，也可以直接指定：

```bash
# 示例：使用已配置的保存连接，或配合对应 Provider 的包
export SGRAPH_MODEL="openai:gpt-4o-mini"
export SGRAPH_BASE_URL="https://api.openai.com/v1"
export SGRAPH_API_KEY="sk-xxx"
export SGRAPH_TEMPERATURE=0

sgraph hello.md
```

---

## 5. 把两个节点串起来：多步流水线

理解了单节点，我们来写一个包含两个节点的流水线 `chain.md`：先分析问题，再生成精简报告。

```markdown
# [Node] Analyze

请列出用户问题中最核心的 3 个要点。

## [Transitions]
- @Default -> Summarize

# [Node] Summarize

请把刚才列出的要点浓缩成一句不超 20 字的口号。

## [Transitions]
- @Default -> @End
```

### 这里的核心机制一定要记住：

1. **书写顺序 ≠ 执行顺序**：
   `Analyze` 之所以是入口，是因为它是文件里的第一个节点；但 `Analyze` 执行完之所以去 `Summarize`，**完全是因为写了 `- @Default -> Summarize`**，而不是因为 `Summarize` 排在它下面！如果你忘了写 `Transitions`，`Analyze` 执行完就会直接停住。
2. **对话历史是自动继承的（默认 `MessagesState`）**：
   - 当 `Analyze` 运行时，模型看到的是：`[Analyze 的系统提示词, 用户的提问]`。
   - `Analyze` 的回答会自动追加到图的共享消息列表（`State.messages`）里。
   - 当跳到 `Summarize` 运行时，模型看到的是：`[Summarize 的系统提示词, 用户的提问, Analyze 的回答]`。
3. **节点正文（Prompt）不会污染历史记录**：
   注意到了吗？`Analyze` 的系统提示词只在 `Analyze` 这一步临时生效，**不会被存进 `State.messages` 历史里**。到了 `Summarize` 节点时，系统提示词会干净地切换成 `Summarize` 自己的正文。

你可以直接查看并运行仓库自带的示例 02 来验证这一点：

```bash
printf '请分析远程办公的利弊\n' | sgraph examples/02-chain/workflow_cn.md -- --model-factory python:../support/demo_model_cn.py:create
```

输出：
```text
[Analyze] 演示回复（共 2 条输入消息）：请分析远程办公的利弊
[Report] 演示回复（共 3 条输入消息）：演示回复（共 2 条输入消息）：请分析远程办公的利弊
```
看！`Analyze` 收到了 2 条消息，而第二个节点 `Report` 收到了 3 条消息（多了 `Analyze` 的回复），且每个节点的回复都会按顺序打印出来。

---

## 6. 小结与下一步

到这里，你已经掌握了 SkilledGraph 最基础的骨架：
- `# [Node] 节点名` 定义节点，正文就是当前节点的 `SystemMessage`。
- `## [Transitions]` 定义跳转，`- @Default -> 目标节点` 或 `@End`。
- `sgraph --check` 做语法体检，`sgraph xxx.md` 启动运行。

但只有固定顺序的流水线还远远不够。如果我们需要：
- **根据不同情况走不同分支**（条件路由）？
- **在调用模型前，先用 Python 读取本地文件或数据库**（`pyfunction`）？
- **让模型调用外部工具**（`ToolNode`）？
- **运行到一半停下来，等人类输入确认后再继续**（`request_input`）？

请继续阅读 **[第二篇：循序渐进实战教程 (02-STEP-BY-STEP_cn.md)](02-STEP-BY-STEP_cn.md)**，我们一站一站把这些能力加进来！
