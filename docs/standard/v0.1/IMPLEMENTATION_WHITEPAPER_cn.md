# SkilledGraph v0.1 功能实现白皮书

> 2026-10-09：工具调用扩展已实现；本文件末尾扩展章节更新原有白名单、接口和范围约定。

状态：当前功能设计及实现契约。日期：2026-10-09。M1～M5 当前范围已实现并完成确定性验收；状态见[开发指南](DEVELOPMENT_GUIDE_cn.md)。语言输入规则见[语言规范](LANGUAGE_SPEC_cn.md)。本文区分框架职责与内置实现策略；策略不自动推广为所有执行器必须遵守的规则。

阅读顺序：§1～§4 定义架构、数据及公共接口；§5～§7 定义绑定与执行权；§8～§11 定义内置实现；§12～§13 定义扩展边界及暂缓事项。

术语：Schema 指原生数据结构定义；State 指一次原生图执行中的状态；Reducer 指字段更新的原生合并函数；节点正文是 DSL 提取的静态字符串；模型消息是一次调用输入或输出的数据对象；两者不等同于持久化 State 历史。Hardcode_Execution_Backend 指 python／pyfunction 等代码执行方式及适配实现，不指模型提供方或 Host。

## 1. 架构与责任边界

```text
DSL 文件
  → 只读解析与静态验证
  → GraphSpec
  → 选择 Schema、绑定引用与模型依赖
  → 原生 StateGraph Builder
  → 原生 compile()
  → 原生编译图，由 Host 使用 invoke／ainvoke／stream 等运行
```

| 组件 | 负责 | 不承担 |
| --- | --- | --- |
| 解析器 | Markdown 上下文、DSL 结构、精确正文、源位置、静态边检查 | 导入脚本、校验对象存在、模型调用 |
| 绑定与构建 | 选择原生定义、绑定资源、挂载节点和边、返回 Builder | 运行节点、启动文件 Host |
| 默认 Prompt 实现 | 未声明 uses 时的模型调用及消息更新 | 自动工具能力、全部 State 字段注入 |
| Hardcode_Execution_Backend | 解释自己的引用、适配代码执行与返回、处理正文 | 拥有全图 Schema 或替代 LangGraph 调度 |
| Host | 模型配置、I/O、初始 State、资源与图运行生命周期 | 改写 DSL 语法、必需的自定义 Runtime 包装 |
| LangGraph | State／Reducer、图调度及原生持久化、中断、流式等能力 | 自动解释 SkilledGraph 的文本与引用 |

核心库是图编译与绑定工具，不建立第二套 Runtime。执行资源由 Host 管理，已有原生 Checkpointer、Store、Context、Interrupt 和 Streaming 通道应保留。基础 chat Host 是独立的[标准示例](../../../examples/chat-host/README_cn.md)，源码位于 examples/chat-host/src/sgraph_chat_host，随项目安装但不属于 src/skilledgraph；不为其引入任意任务配置语言。

## 2. 只读数据契约：GraphSpec

parse_graph 返回纯数据，至少保留：

| 数据 | 必须支持的用途 |
| --- | --- |
| 源文件路径、原文、源位置 | 相对路径和诊断定位 |
| 前言、Config 设置及位置 | 审计、Host 与定义选择 |
| 节点声明顺序、名称及位置 | 入口确定和结构检查 |
| 节点设置、精确正文、说明及位置 | 绑定与审查 |
| 转移格式、原文、逐条键／目标及位置 | 构建边与诊断 |

不得存放已导入函数、模型、State 实例或编译图。引用以原始字符串保留到绑定阶段。原文与规范化正文不同，不得只存渲染结果。具体 dataclass／字典表示、字段命名、位置坐标约定留给解析原型；选定后须统一并记录，不能丢失上述用途。

## 3. 公开库接口

以下是暂时确认的整体契约。parse_graph、build_graph、load_graph 已可调用；当前运行范围见[M3～M5 记录](../../development/M3_M5_COMPLETION_cn.md)，M1 数据表示和诊断见[实现记录](../../development/M1_PARSER_cn.md)。

| 接口 | 职责 | 返回值 |
| --- | --- | --- |
| parse_graph(path) | 只读文件并完成语言静态检查 | GraphSpec |
| build_graph(path_or_spec, ...) | 绑定依赖、采用 Schema、挂载节点和边 | 原生 StateGraph Builder |
| load_graph(path_or_spec, ...) | 使用同样构建过程并 compile | 原生编译图 |

build／load 可导入所选用户文件，但不得执行节点业务函数、调用模型或启动 @host。load 不增加自研图运行对象包装。

构建依赖使用独立关键字参数：

```python
builder = build_graph(
    path_or_spec,
    state_schema=MyState,
    input_schema=MyInput,
    output_schema=MyOutput,
    context_schema=MyContext,
    model=my_model,
    bindings=my_bindings,
)
```

上述参数可以省略，实际使用的能力必须有相应依赖。load 接受相同参数，额外 compile_kwargs 原样交给原生 compile()；更复杂构建可使用 Builder。不要求创建 SkilledGraph 配置对象或继承框架类型。

### 3.1 Schema 选择

state_schema 选择为显式参数 → 文件 @state → 默认消息 State。未传或 None 表示无覆盖。被覆盖的文件引用不先导入，原声明仍在 GraphSpec 中。其他 Schema 无对应 DSL 声明，未传时采用原生默认行为。context_schema 定义结构，实际 Context 值在原生执行阶段提供。

所有 Schema 原样接入原生图，不自动拼接默认字段、不恢复 Reducer、不改写注解。Host 应先尊重文件声明，只有有意覆盖时才传显式 state_schema。

保留 state_schema 与 @state 的原生 Schema 接入。Reducer 由用户在 Python 中定义并由 LangGraph 执行，不经过 node／router 的 Hardcode_Execution_Backend，不新增包装、注册或自动兼容修复层。首版默认实现围绕默认消息 State 验证，不承诺任意自定义 Reducer 都维持全部便利行为。

### 3.2 模型依赖

model 由 Host 提供，默认 Prompt／pyfunction 采用 LangChain 聊天模型或兼容对象，调用 invoke(messages)，异步使用 ainvoke(messages)，取得原生模型消息。不引入自定义模型基类，不要求结构化输出，也不保证兼容任意返回类型的 Runnable。

构建 API 不自行选模型、读取密钥、设置 temperature 或启动 Host。纯 Python 图可没有模型；实际需要但未提供时明确失败。用户 Python 节点可自行使用其他 SDK。运行配置透传和提供方兼容性需验证；仅有同步方法不意味着具有异步能力。

## 4. Host 与启动器

首版文件 Host 入口为外部 Python 函数：

```python
def main(graph_path: Path, argv: list[str]) -> int | None:
    ...
```

启动器只读解析文件以选择 @host，未声明时延迟导入标准 chat Host 示例的 sgraph_chat_host.host.main。显式文件 Host 和只读 --check 不导入该示例。将本次 DSL 文件的绝对路径及 Host 参数 argv 传入入口。该路径不是安装目录，Host 不需要猜 cwd 或从 argv 寻找图文件。整数为退出码，None 表示成功。

Host 提供模型、Schema 和资源，并自己调用 build／load，组织初始输入、输出和生命周期；启动器不预先构建图。不要求 Host 基类、插件生命周期或 I/O 映射协议。启动器为 sgraph；文件名后剩余参数交给 Host，可用一个 -- 分隔。标准 Host 示例通过 --model／--model-factory 或对应环境变量选择模型；具体命令见[使用指南](../../development/USAGE_cn.md)。首版入口同步，Host 可在内部组织异步；独立异步 Host 协议未定义。

直接调用 parse／build／load 从不自动启动文件 Host。模型参数和简单管道／复杂 I/O 行为由 Host 配套落实，不反向加入 Config。

### 4.1 基础 chat Host 的默认运行行为

基础 Host 读取一次输入，从首节点执行一次图后退出；交互终端读取一行，管道读取完整 stdin，终端 EOF 或空白行不执行。一次图运行内部的节点仍按所选 State／Reducer 共享并更新消息历史。Host 不再循环接受后续输入。

Host 显示本次运行中所有节点的回复，不只显示最终节点回复。默认条件节点返回的文本键也是模型回复，不默认隐藏。显示消息不意味着将上一轮显示内容重新作为下一轮输入。

基础 Host 现提供动态中断的字符串交互，详见本文末尾补充；不把“每次从首节点开始”推广为对用户原生 API 恢复执行的限制。用户仍可通过原生图 API 使用中断相关能力，具体兼容性由实现验证。此处不冻结逐 token 流式、输出排版或原生特殊事件的显示规则。

## 5. 执行器注册与统一绑定

bindings 是执行方式名称到 Hardcode_Execution_Backend 实现的映射。省略时提供内置 python／pyfunction；部分映射替换同名项、加入新项，未提及内置项保留。不存在执行方式时绑定失败，不回退到 python。

完整引用的第一个冒号前名称用于选择实现，之后的完整文本交给该实现解释。解析器保留整条原始引用。普通 Prompt 经 model 接入，不要求注册 prompt 执行器。

M2 采用普通绑定函数作为映射值，入口为：

```python
def bind(payload, *, base_dir, node, model=None):
    ...
    return callable
```

payload 是前缀之后的引用文本；base_dir 为 DSL 目录；node 为只读节点描述，包含名称、设置、提取后的正文和源位置；model 等外部依赖另行提供。M2 已采用此签名，node 为不可变 NodeSpec。它们是执行器的绑定资源，不要求业务函数增加这些参数。绑定阶段取得对象或形成闭包／适配对象，运行阶段才由原生执行机制传入 State 和支持的原生参数。不得把构建资源混作运行 State。只读节点描述替代此前仅传 prompt 的较窄示意，不向执行器暴露整个可变构建器。

uses／router 共用入口，不要求 bind_node／bind_router 双方法，不增加必需 role 参数。构建器根据设置位置挂载返回的 Callable／原生可运行对象。引用接入相同不代表节点更新与路由返回契约相同。

内置 pyfunction 面向用户的是材料函数调用及其适配，不提供 router 返回协议。首版不为其增加路由适配，也不因该能力边界增加语法级封禁或阻止用户自行扩展。用于 router 的执行结果仍须遵守键返回契约。默认 pyfunction 节点从模型回复取得条件键，属于默认节点选路，不等同于材料函数充当 router。

执行器可直接持有已有 Python 对象，自定义实现不必经文件导入。该通道不能因模块引用暂缓而被堵住。完整节点属性采用 NodeSpec；不得为此提前发明通用 Context 或统一结果封套。

Host／State 引用加载负责取得入口与原生定义，逻辑上不同于节点执行器。可以复用文件加载工具，但替换 bindings 中的 python 不改变 @host／@state 加载行为。此接入方式仅在具体功能发现冲突时复查，不预先增加配置层。

## 6. 内置文件引用

当前内置形式：

```text
python:FILE:ENTRY
pyfunction:FILE:ENTRY
```

python 可取得节点 Callable、router、State 对象或 Host 入口；用途由槽位决定，Host／State 的加载不使用可覆盖的节点执行器注册项。pyfunction 当前用于材料节点；其他槽位的 pyfunction 适配未定义，不凭统一加载机制自动推导。

FILE 必须是 ./ 或 ../ 开始的相对路径，或平台识别的绝对路径。不支持裸文件名或模块路径，不增加 shell 引号、环境变量或 ~ 展开。路径内部空格保留，外侧 HWS 已由语言裁剪。

移除前缀后，以最后一个冒号分离 FILE 与 ENTRY，保留路径其余冒号，包括 Windows 盘符。ENTRY 是非空简单 Python 对象名，取得对象而非自动调用工厂；不解析点链或调用表达式。这只是内置约定，自定义实现可另行解释 payload。

相对路径基于 DSL 目录，不改变进程 cwd。只读解析不检查文件存在或导入。实际绑定加载选中文件，检查入口及用途兼容；失效明确失败，不猜模块、不静默降级。Python 导入会执行顶层代码，必须与解析隔离；M2 按规范绝对路径缓存模块、隔离同名文件并清理失败导入；具体生命周期见[M2 记录](../../development/M2_BUILDING_cn.md)。该机制不是沙箱或权限保证。

## 7. 节点执行与框架调度

未声明 uses 时调用默认 Prompt；声明后节点执行完全交给选定执行器。框架提供资源与运行 State、等待结果，不替执行器组织默认模型输入，不在其前后额外 invoke。

正文是否存在不是执行器专属语法错误。执行器自行使用、忽略或拒绝正文；内置 python 默认不因此报错。用户函数不必接收 prompt／model 形参。

节点结果按原生规则合并，随后运行有效 router，再查转移表。无 router 的条件节点仍必须有明确键来源。内置模型节点用本次回复查表，再以原生 Command 携带更新和目标，不增加 State 字段；外部 router 走原生条件边。不得用共享全局值或并发串键的闭包传递路由结果。

## 8. 默认 Prompt 实现

默认 State 为消息 State，messages 使用原生 add_messages 合并。默认 Prompt 读取当前 State 的全部 messages，以正文作为当前静态指令调用模型一次，只返回新的 AI 消息更新。正文不保存，已有历史不重新提交，其他 State 字段不自动注入模型。

空正文／只有说明不会关闭模型调用；模型输入不兼容须明确报告。默认 Prompt 没有因自然语言要求而获得搜索、文件或工具能力，也不新增自动 ReAct 循环。具体消息布局属于默认实现，不能变成解析器行为。

## 9. 内置 python 执行器

取得并执行用户原生 Callable／可运行对象，不自动调用模型；用户代码可以自行调用模型。支持原生 State 更新及特殊返回的通道，不将其统一收窄为材料文本，不强制 state-only 签名。同步／异步、config／runtime 注入、中断等具体兼容性以原型验证为准。

存在正文不报框架错误；执行器可忽略正文，不修改用户函数参数。仅有说明的节点同样执行。若自定义实现拒绝正文，由其自身契约报告。

有 router 时使用合并后 State 选键。条件表无 router 时需要执行器明确提供键协议；内置 python 首版未定义该协议，必须搭配 router。普通字典、字符串或 Command.goto 不自动解释为表内键，也不因此引入模型调用。

## 10. 内置 pyfunction 执行器

### 10.1 正常执行步骤

1. 材料函数接收当前 State 并返回结果，不要求返回整份 State。
2. 按本节规则转换材料消息。
3. 非空正文包装为 SystemMessage，随后为当前历史，最后为本次材料，保留历史与材料顺序；空正文不新增空 SystemMessage。
4. 调用模型一次，取得回复。
5. 返回本次材料消息及模型回复作为新增 messages 更新，由原生 Reducer 合入 State。

这些步骤是当前内置 pyfunction 的硬编码选择，不是 DSL 解析器或所有执行器的通用要求。材料不在模型前单独提交、不预先运行 Reducer；自定义 Reducer 决定后续 State，当前模型直接读取当前历史和新增材料。正文不保存，已有历史不重新提交。不据此声明失败原子性、重试或外部副作用事务保证。

### 10.2 材料转换

| 返回值 | 默认处理 |
| --- | --- |
| 原生消息对象 | 保留角色、内容、元数据 |
| 非空原生消息对象列表 | 保留消息及顺序 |
| 字符串 | 包装为 HumanMessage |
| 普通字典／数据列表 | 可序列化时 JSON 文本，否则 str(value)，再包装为 HumanMessage |
| 其他对象 | str(value)，再包装为 HumanMessage |
| None／空列表 | 无新增材料，仍调用模型 |

空字符串保留为空文本消息。普通字典不因 role／content 字段而猜为消息，不解释为 State 字段更新。JSON 是消息文本，不是 DSL 类型或强制下游解析协议。非消息列表中的混合数据不逐项猜角色，遵循数据转换路径。

简单材料直接返回字符串即可；需要角色、多模态内容或元数据时推荐原生消息对象／列表，不强制新手学习消息类型。其他原生消息表示不自动视为兼容承诺。JSON 编码参数、异常文本等实现细节不在此冻结。取消材料保存选项暂缓。

## 11. 默认文本选路

默认 Prompt／pyfunction 有条件表但无 router 时，用户正文说明判断规则，并要求模型只返回一个表内键。执行实现对本次模型回复文本去掉首尾空白，以结果精确查表；不从解释中找词，不移除引号或代码围栏，不强制结构化输出，不追加第二次模型调用。

模型回复仍作为原始 AI 消息照常提交；裁剪仅取得键，不改历史消息。选路值不能被用户 Reducer 对回复的变换意外替代，应保留本次回复选路的语义；实现使用原生 Command(update=新增消息, goto=查表目标)，同一 DSL 条件边不再重复挂载一次。非法键按语言诊断要求失败。

M3～M5 已验证一次模型调用、同步／异步并发隔离、消息被 reducer 改写时的选路，以及检查点暂停恢复。此实现是内置执行策略，不要求用户 callable 返回新的统一结果封套；细节见[完成记录](../../development/M3_M5_COMPLETION_cn.md)。

有 router 时默认模型不同时选键；router 读取合并后 State，复杂回答的解析规则由用户代码提供。无表／无条件表直接结束或走唯一边，不把业务回答猜成键。

```markdown
# [Node] Evaluate

检查已有材料是否足够。
足够时只返回 enough，否则只返回 insufficient，不输出其他内容。

## [Transitions]
- enough -> Report
- insufficient -> Ask
```

这是片段，完整示例见[示例目录](../../../examples/README_cn.md)。默认不同时产生业务回答与独立私有键，该旧提议已撤回。

## 12. 原生扩展与兼容边界

构建前可提供原生 Schema，构建后可修改原生 Builder，自行 compile；load 返回原生图，宿主直接使用其运行 API。不得重建 State 合并引擎、隐藏 Runtime 包装、吞掉原生中断，或在方便包装中丢失原生参数／异步能力。

原生 goto 与 DSL 边叠加，不取消已声明边、不默认封禁表外跳转。两条路径同目标的调度行为遵循所选原生实现验证，不偷偷声称去重。@End 只结束自身 DSL 路径。声明条件表仍须满足选路契约。

自定义 Schema 可完全替换默认字段与 Reducer，甚至使默认便利行为不再成立；框架不自动修复。缺失 messages 的纯代码图仍合法；默认模型调用所需契约应明确检查或适配。

官方原生能力背景：[Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)、[消息合并](https://reference.langchain.com/python/langgraph/graph/message/add_messages)、[模型接口](https://docs.langchain.com/oss/python/langchain/models)。这些链接用于理解原生机制，不把未锁定的外部版本自动变成项目兼容承诺。

## 13. 首版暂缓与实现未定

普通节点直接声明模型输出 Schema 的方向保留，未来可考虑类似 router 的特殊执行引用接入原生结构；首版不定义关键字、签名或阶段，也不自动按字段名判断路由／State 更新。模型输出 Schema 与 State Schema 是不同概念。

文件级执行器选择、模块引用、材料保存关闭及语言规范列出的扩展保持暂缓。绑定对象、节点属性和导入生命周期已在 M2 落实；CLI 与精选运行兼容已验收，更广的提供方／持久化组合和异常／重试能力仍按开发指南及实际需求验证，不靠本文提前创建插件协议。

## 工具执行扩展（2026-10-09）

build_graph/load_graph 新增可选关键字 tools=None，接受原生 BaseTool 或可经 LangChain tool 转换的 Python callable 序列；不接受 MCP 服务配置。绑定阶段按工具自身名称建立注册表并拒绝重名。不会调用工具或模型。NodeSpec 新增 kind 字段，默认 Node，ToolNode 标题产生 ToolNode。

Host 向 model 传入已完成工具绑定的模型，同时向 tools 提供实际可执行工具。框架不调用 bind_tools、不重新选择模型。普通 Prompt 与 pyfunction 继续调用传入模型。多模型选择暂缓。

ToolNode 编译为原生 langgraph.prebuilt.ToolNode(selected_tools)，通过 add_node 加入图，不使用 Hardcode_Execution_Backend 文件加载协议。保留原生多调用执行、异步、ToolMessage ID 对应、State/Config/Runtime 注入、Command 和原生错误处理默认策略，不自行字符串化工具结果，也不包装为 pyfunction 材料。ToolNode 要求 Schema 有 messages 通道；正文不参与执行。

带 @ToolCalls 或 @Otherwise 的表编译为原生 conditional edges，读取 reducer 合并后的 State。对应内置模型节点只返回更新，不再同时产生旧的文本路由 Command，防止双重跳转。显式 router 的原生签名注入继续保留；命中工具信号时不调用 router。

MCP 客户端/适配器应由 Host 管理连接、异步会话和资源释放；转换得到兼容 BaseTool 后可以走相同工具图。该兼容方向不等于已验证所有 MCP 适配器或生命周期，本轮不做 MCP 集成测试。同步/异步使用由具体工具能力决定。

可运行标准示例见 examples/10-tool-calling/workflow_cn.md 及同目录 Host。示例使用确定性模型模拟真实 tool_calls，执行真实 LangChain add 工具，无网络或密钥。真实 Host 只需用 base_model.bind_tools([add]) 替换模型，并传 tools=[add]；基本 chat Host 暂不增加工具加载 CLI 参数，自定义 Host 通过现有 @host 接入。

## 基础 Host 连接配置扩展（2026-10-09）

基础 Host 通过环境变量传递连接参数，参见[使用指南](../../development/USAGE_cn.md)“环境变量配置模型连接”。新增 host_config 为纯配置组件；读取显式 key 文件，不修改进程环境，不扩展 Config 或 Node 语法。Provider 标准环境变量仍由原生集成读取。模型 factory 优先并拥有自己的全部配置。DeepSeek 可选依赖提供官方 LangChain 集成；没有实现 OpenCode 配置继承或凭据库读取。

## 单次 Host 与 MCP 验证补充（2026-10-09）

基础 Host 已改为读取一次输入后执行并退出。MCP 接入不新增 DSL 或运行核心：示例 Host 使用 langchain.mcp.MCPAdapter 取得工具，保持会话直到 graph.ainvoke 完成，再关闭本地 stdio 子进程。该适配器为可选依赖，目前为 beta。已验收本地 MCP + DeepSeek，远程 HTTP 等能力不在承诺范围；详见[MCP 验收](../../development/MCP_ACCEPTANCE_cn.md)。

## 基础 Host 动态中断与终端编辑（2026-10-09）

不新增 DSL 语法。基础 Host main 编译时传入 InMemorySaver；run_chat 为每次调用生成新的 thread_id，保持单次图执行。消费原生 updates 流中的动态中断，展示 value，使用 prompt-toolkit 接收字符串回复，并以中断 ID 到回复的映射构造 Command(resume=...)，继续执行直到完成或再次中断。恢复值不自动转为 messages，节点及其 Reducer 决定 State 更新。

多个同时中断分别取得回复后统一恢复；连续中断重复执行同一流程。EOF 取消等待并返回 1，不提交未完成的回复集；空字符串是合法回复。Ctrl-C 由 CLI 处理为 130。管道输入耗尽后不尝试自动恢复；静态断点、类型化表单和跨进程恢复由自定义 Host／原生 API 处理。自定义 Host 复用 run_chat 必须自行提供已启用 checkpointer 的图。

终端使用 PromptSession，保留本次进程内的输入历史及默认编辑键；不持久化输入历史。注入的无文件描述符文本流使用 readline 以便测试。普通 Prompt、python、pyfunction、ToolNode 的执行与 DSL 选路语义不变。中断节点原生重跑语义继续适用，节点作者应避免重跑前置副作用。

验收范围与示例见 [Host 中断验收](../../development/HOST_INTERRUPT_ACCEPTANCE_cn.md)。

## 内置 request_input 执行器（2026-10-09）

使用 `- **@uses**: request_input:提示文本`，沿用现有执行引用机制，不新增设置或节点类型。冒号按首次出现切分，后续冒号及管道字符属于提示；引用保持单个物理行。参数非空，默认直接作为文字；如果以双引号开始，则由此执行器按 JSON 字符串解码，引号去掉，`\n` 成为换行，`\"` 成为引号。未闭合／非法 JSON 或空字符串在绑定阶段报错。解析器仍保留原始引用，不解码、不执行；双引号不允许物理跨行设置。

执行器直接调用原生 interrupt(提示字符串)，不引入通用中断封套。基础 Host 按既有策略收集字符串回复，其他 Host 自行处理原生中断。恢复值必须是字符串，主动空回复允许；其他类型运行时报错，不隐式字符串化。执行器返回一条 HumanMessage 的 messages 更新，交给所选原生 Reducer 合并；不重交历史，不调用模型，不保存提示，不使用节点正文。存在正文不报错。构建要求 Schema 有 messages 通道，Reducer 仍由用户决定。

恢复后才完成节点更新，再执行 router 和跳转表。普通命名条件边需要显式 router；request_input 不把回复自动当路由键。同步和异步执行均支持；原生 checkpointer、thread_id 及恢复重跑语义保持不变。通过 bindings 同名覆盖仍遵循既有原生接入机制。

最小完整示例为 examples/11-interrupt/workflow_cn.md。长提示可直接写很长的一行；需要换行时写 JSON 字符串，例如：

```markdown
# [Node] AskUser
- **@uses**: request_input:"请补充以下信息：\n1. 输出格式\n2. 目标读者"

## [Transitions]
- @Default -> @End
```

## 基础 Host 首次配置向导（2026-10-09）

不改变 DSL。host_setup 管理用户目录连接配置及首次交互，host_locales 提供中文／英文文案与 locale 标识选择，terminal 提供共享 PromptSession 输入；host 保留模型创建、图运行和 CLI 调度。没有显式 CLI／环境模型选择时，基础 main 加载单个保存的 OpenAI 兼容连接；缺失配置且处于终端时启动向导，管道则报错。--setup 强制进入配置，完成后退出。

支持基础 URL、模型 ID、Chat Completions／Responses 两种原生 ChatOpenAI 模式、密钥及静态 default_headers。配置 model 固定为 openai:MODEL_ID；langchain-openai 加入 chat 可选依赖。SGRAPH_HEADERS_JSON 为连接环境变量扩展，校验为字符串到字符串的 HTTP 请求头映射，不回显非法值。显式模型／factory 不继承保存连接，选中保存连接时 SGRAPH 连接变量覆盖保存参数。

不执行自动 API 探测，不建立提供方／套餐登录适配器，不接管原生 OAuth。locale 只读标识、不调用 setlocale。保存配置为本地 JSON，凭据明文、POSIX 权限 0600、原子替换；密钥与头部隐藏输入且不进入编辑历史。--check 与解析路径不触发任何配置。跨平台目录策略与具体验收见[配置向导验收](../../development/HOST_SETUP_ACCEPTANCE_cn.md)。

## OpenCode Go 会话头补充（2026-10-09）

基础 Host 创建模型时，对有效 Go API 基础地址补充缺失的客户端身份和随机会话头。会话 ID 为 sgraph-harness-agent-<UUID>，同一模型请求复用；基础 Host 单次运行只创建一个模型，因此图内并行节点、工具循环与中断恢复不会生成不同 ID。模型 factory 不受此规则介入，自定义 Host 复用模型跨会话时自行维护会话边界。

用户显式头部按大小写无关的名称优先，不改写已保存配置，也不向非 Go 地址附加 Go 特定身份。自动能力属于连接策略，不新增 DSL 或 State 字段。验收见 [OpenCode Go](../../development/OPENCODE_GO_ACCEPTANCE_cn.md) 的自动会话补充。

## 可选内置 monty 执行器（2026-10-09）

`- **@uses**: monty:./program.py` 沿用已有执行引用语法。payload 是显式相对或绝对文件路径，没有 :ENTRY；文件最后表达式是结果。绑定读取源码但不执行；运行以 JSON 数据传入 state（Pydantic 消息按 model_dump(mode="json") 转换）。节点返回 State 更新 dict 或 None，router 返回路由字符串；其他类型执行器报错。正常图合并及 router 字符串查表仍由原生执行与已有路由规则处理。

依赖可选 `skilledgraph[monty]`，固定 pydantic-monty 1.1.0。没有模型调用、不使用节点正文，不提供 LangGraph API／Config／Runtime 对象、原生 Command、宿主回调、文件挂载或 CPython 回退。普通 JSON 更新的 Reducer 仍来自 State Schema，执行器不包装 Reducer。

每次独立 Monty：源码至多 20000 bytes、输入至多 1 MiB、堆 32 MiB、执行时间 1 秒、递归深度 100、累计休眠最多 0.1 秒。输入／返回 JSON 更新序列化上限为 1 MiB，不把共享对象无限展开。打印被截获而非直接进入终端，节点接口不把 stdout 视为返回更新。异常按运行失败传播，不能假定具备 CPython 的模块和语法全集。同步 Callable 可由原生图调度至异步线程执行，未自建调度器。

例如 program.py：

```python
{"value": state["value"] * 2}
```

或者用于 router 的 route.py：

```python
"ready" if state["value"] > 0 else "missing"
```

完整实际 harness 见 [sgraph_agent](../../../sgraph_agent/README_cn.md)，它的工具许可、会话和上下文策略由自己的 Host／绑定负责，不改变普通节点及基础 Host 的默认行为。
