# 中英文版本与维护约定

项目同时提供中文 `_cn` 与英文 `_en` 版本，后缀放在扩展名前：`README_cn.md`、`workflow_en.md`、`host_en.py`、`test_parser_cn.py`。原有无后缀文件保留为兼容入口，避免已有命令、文件引用和导入失效。

## 阅读与运行

- [中文首页](../README_cn.md)／[English](../README_en.md)。
- [中文标准](standard/v0.1/README_cn.md)／[English standards](standard/v0.1/README_en.md)。
- [中文示例](../examples/README_cn.md)／[English examples](../examples/README_en.md)。
- [中文终端 agent](../sgraph_agent/README_cn.md)／[English agent](../sgraph_agent/README_en.md)。

```bash
python -m pip install -e '.[chat,agent,mcp]'
python -m skilledgraph examples/10-tool-calling/workflow_cn.md
python -m skilledgraph examples/10-tool-calling/workflow_en.md
sgraph-agent-cn --help
sgraph-agent-en --help
```

两种语言的工作流分别引用同语言的 Python 文件；包内导入、测试 patch、默认资料和工具描述也已调整。DSL 的关键字、节点名、路由键、State 字段及 API 名称不翻译。默认资料目录只选择对应语言的笔记，用户指定目录仍按原规则读取所有 Markdown。

Host 的配置向导继续支持多语言 locale 选择：`SGRAPH_LANGUAGE=zh` 选择中文，`SGRAPH_LANGUAGE=en` 选择英文（具体支持值以 Host 使用指南为准）。文件语言不覆盖用户已有的环境设置。共享包的 `__init__.py`／`__main__.py` 保留兼容行为；英文 agent 使用 `sgraph-agent-en`、`python -m sgraph_agent.host_en` 或英文工作流。

## 共享与保留项

`src/skilledgraph/` 的 18 个核心文件保持逐字节不变，其中已有注释和 docstring 均为英文，不复制解释器或引入新的 DSL 语法。LICENSE、依赖配置、CI、包入口以及语言无关的检查工具共享。

语言解析样本的 `_cn`／`_en` 副本保留原始字节：中文 Unicode、精确正文、尾部空格、CRLF 都是测试内容。配套 manifest 只切换输入文件名，英文说明可翻译；测试中的 Unicode、中文 locale 字典和中文肯定回复别名也保留。它们不是遗漏的界面文案。

真实 API JSON 和历史原始模型回复不翻译、不复制成看似新运行的证据。英文验收文档说明同一历史结果；历史数量与限制保持原范围。翻译后的 live 脚本需要显式 `--run`，只有另行运行才代表英文 Prompt 的真实模型验收。此次仅执行离线模型测试及本地 MCP，没有新增付费 API 请求。

`docs/agent-guide/`、`.local-docs/`、`.local-history/` 继续留在本地且被 Git 忽略。本次不将这些个人摘要或讨论存档纳入发布。

## 验证与维护

```bash
python tools/check_localizations.py
python -m unittest discover -s tests -p 'test_*_cn.py' -q
python -m unittest discover -s tests -p 'test_*_en.py' -q
python -m unittest discover -s tests -q
python tests/mcp_demo/check_cn.py --output /tmp/mcp-cn.json
python tests/mcp_demo/check_en.py --output /tmp/mcp-en.json
```

Windows 请将输出路径改为自己的临时目录，Python 路径按安装方式选择。完整 discovery 同时运行原版、中文与英文测试；822 项来自每版 274 项，不代表新增了 822 种独立功能。

[文件清单](../tools/localization_manifest.json)列出兼容源、语言副本、共享和本地保留项；[检查工具](../tools/check_localizations.py)检查覆盖、Python 语法、相对链接、fixture 字节及 manifest 契约。它不是自动翻译器。修改示例或测试时，应同步对应语言文件、引用路径、预期输出及必要的文本预算；新增文件须更新清单。不要翻译协议名称或清理 byte-sensitive fixture。

本次验收见[中文记录](development/LOCALIZATION_ACCEPTANCE_cn.md)／[English report](development/LOCALIZATION_ACCEPTANCE_en.md)。
