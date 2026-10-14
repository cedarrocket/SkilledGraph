# 标准 chat Host 示例

这是独立于 DSL 核心的标准 Host。源码在 `src/sgraph_chat_host/`，通过 SkilledGraph 的公开构图 API 加载图；不属于 `src/skilledgraph/`。

安装项目的 `chat` extra 后运行：

```bash
pip install -e '.[chat]'
sgraph examples/chat-host/workflow_cn.md
```

没有配置模型时，交互终端会启动中文／英文 API 配置向导。配置后读入一次请求，执行图、显示各节点回答并退出；图内动态 interrupt 会等待键盘回复并恢复。模型工厂、环境变量、管道输入和 `--setup` 的用法见[使用指南](../../docs/development/USAGE_cn.md)。

## 模块分工

| 文件 | 职责 |
| --- | --- |
| `host_cn.py` | 模型创建、一次图执行、动态中断恢复及 Host 参数 |
| `host_config_cn.py` | 环境连接参数、额外请求头及 OpenCode session ID |
| `host_setup_cn.py` | 首次 API 配置、用户配置读取及保存 |
| `host_locales_cn.py` | 中文／英文提示和 locale 选择 |
| `terminal_cn.py` | 终端行编辑和隐藏输入 |

这些模块使用独立命名空间 `sgraph_chat_host`，随当前项目安装，以便默认体验和其他示例复用。没有声明 `@host` 时，`sgraph` 启动器延迟选择本示例的 `main(graph_path, argv)`；不是 DSL 解析器执行聊天逻辑。

`workflow_cn.md` 演示显式文件引用：`@host: python:./host_cn.py:main`。根目录的 `host_cn.py` 只是这个文件引用的入口，具体实现在独立包中。编写自己的 Host 时可替换该入口；直接调用 `parse_graph()`、`build_graph()`、`load_graph()` 不会加载标准 Host。

其他示例及 `sgraph_agent` 可显式复用 `sgraph_chat_host.host.create_model`、配置或终端模块。这是应用层代码复用，不是 DSL 的要求。旧的 `skilledgraph.host*` 和 `skilledgraph.terminal` 导入已移除。

纯图运行依赖使用 `runtime` extra，终端编辑依赖由 `chat`、`deepseek`、`mcp` 和 `agent` extras 提供。
