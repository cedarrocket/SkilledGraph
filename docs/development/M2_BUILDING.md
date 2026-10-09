# M2：文件绑定与原生图构建

> 非规范性阶段报告：本文保留当时的实现和测试状态；当前支持范围与运行方式见[项目状态](STATUS.md)和[使用指南](USAGE.md)。

日期：2026-10-09。本阶段实现纯 Python 图；默认 Prompt、pyfunction 执行和 CLI 尚未实现。

## 使用

```sh
python -m pip install -e '.[runtime]'
python -m unittest discover -s tests -v
```

从仓库目录运行：

```python
from skilledgraph import load_graph

graph = load_graph("examples/09-state-only/workflow.md")
assert graph.invoke({"value": 0, "events": []}) == {
    "value": 2, "events": ["incremented", "doubled"],
}
```

build_graph 接受文件路径或 parse_graph 返回的 GraphSpec，返回原生 StateGraph，可以继续 add_node／add_edge／compile。load_graph 返回原生编译图，compile_kwargs 直接传入 compile。两个入口均支持 state_schema、input_schema、output_schema、context_schema、model、bindings 关键字参数；不启动 @host。M2 不使用 model，但会将其交给自定义绑定函数。

## 绑定表示与加载生命周期

bindings 采用普通映射，值为绑定函数，无需继承类：

```python
def bind(payload, *, base_dir, node, model=None):
    # node 是不可变 NodeSpec；这里取得资源，不执行节点业务逻辑。
    return my_native_node

builder = build_graph(path, bindings={"custom": bind})
```

同一绑定入口用于 uses／router；返回 callable 或原生 Runnable。未覆盖的内置项保留，未知执行方式明确报错。内置 python 返回文件中的原始对象，不包装节点签名；pyfunction 的内置名称已保留，使用时明确报告 M3 尚未实现，也可以显式覆盖。

文件引用按最后一个冒号分离路径和对象名；相对路径基于 DSL 目录，不改变 cwd 或 sys.path。模块使用规范绝对路径的 SHA-256 生成独立导入名，在 sys.modules 中缓存。多个引用、多个图及并发构建共享同一路径的模块；不同目录同名文件互不冲突。加载失败移除未完成模块，保留异常原因。使用进程内重入锁串行加载。

缓存不自动热重载；编辑脚本后重启进程。普通导入仍按 Python 环境查找，不自动把脚本目录加进 sys.path，也不赋予独立文件包内相对导入语义。加载会执行模块顶层代码，因此业务操作应写在函数里。构建器不调用取得的函数，也不把 Schema 当工厂调用。

@state 使用独立对象加载，不经可覆盖的 python 绑定；显式 state_schema 覆盖时跳过文件声明。没有指定时使用 MessagesState；用户 Schema／Reducer 原样传给 LangGraph，不补字段或修复合并行为。

## 路由与原生通道

入口指向第一个节点；无表不增加 DSL 后继。唯一 @Default 挂载原生静态边。条件表必须取得 router 的单个字符串键，精确匹配且不裁剪；非法值报告节点、值、合法键和源码位置。有 router 但无条件表在构建期报告无效用途。

M2 的代码绑定没有隐式结果到键协议，条件表必须配 router。router 读取节点更新合并后的 State。验证包装保留原生 config/runtime 注入、同步／异步方法，以及 router 输入 Schema 推断；不会再次执行用户函数。这里依赖固定版本 LangGraph 的内部 RunnableCallable、coerce_to_runnable 和分支 Schema 推断函数，升级依赖必须复验这些接点。

原生 Command.goto 与 DSL 边同时生效；不封禁表外目标、不取消静态边。不捕获节点业务异常或原生中断；仅绑定、构建和编译阶段的错误增加源位置并保留 cause。BindingError、BuildError、RoutingError 与 ParseError 均继承 SkilledGraphError。

原生节点名约束仍可能比 DSL 更窄，例如与 State 字段重名；这类问题在 build.node 报告原生原因，不偷偷改名或收紧解析语法。

## 验证范围

依赖：markdown-it-py 3.0.0；可选 runtime extra 固定 langgraph 1.2.14、langchain-core 1.6.9。解析入口和包导入不加载这些运行依赖。Python 声明最低 3.11，本轮实际运行 3.14.4，未完成多版本矩阵。

103 项 unittest：79 项解析回归、24 项构建／运行集成测试。覆盖：

- 示例 08 的原生跳转与 DSL 边并行生效，示例 09 的无消息 State／原生 reducer。
- Schema 优先级、输入／输出／Context 原样传递、覆盖 reducer 不补历史、无效文件 Schema 不修复。
- 文件相对／绝对路径、空格和冒号、缓存、并发访问、同名隔离、导入失败清理、对象不自动调用。
- bindings 局部覆盖、独立 State 加载、未知方式失败、Host 不被加载。
- router 合并后读取、非法键诊断、dataclass 输入 Schema、异步节点及 router 的 config/runtime 注入。
- 原生 Builder 后续扩展、编译参数透传、Checkpointer 中断恢复、运行异常原样传播。
- 新进程验证 parse_graph 不导入 LangGraph／LangChain。

未声称覆盖全部 LangGraph 能力。真实模型、默认文本选路、pyfunction、Host／CLI、完整流式与持久化组合、多平台路径行为继续按 M3～M5 验收。上游 LangSmith 在 Python 3.14 有一条弃用提示，不影响本轮测试。
