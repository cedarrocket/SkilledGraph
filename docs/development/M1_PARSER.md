# M1：只读解析原型

> 非规范性阶段报告：本文保留当时的实现和测试状态；当前支持范围与运行方式见[项目状态](STATUS.md)和[使用指南](USAGE.md)。

日期：2026-10-09。范围：文件 → GraphSpec／诊断；未包含引用绑定、图构建、模型执行或 Host。

## 1. 使用方式

从仓库根目录安装：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m unittest discover -s tests
```

包没有 CLI 子命令；Python 入口已可使用：

```python
from skilledgraph import parse_graph, ParseError

try:
    graph = parse_graph("examples/01-assistant/workflow.md")
except ParseError as error:
    print(error)  # 文件、行、列、阶段、诊断码和原因
else:
    print(graph.entry)
    for node in graph.nodes:
        print(node.name, node.prompt, node.setting("uses"))
```

示例路径相对于当前 cwd；GraphSpec.path 与源位置记录绝对源文件路径。引用只保留文本，不在 M1 解释相对脚本路径。

## 2. 模块与依赖选择

| 模块 | 职责 |
| --- | --- |
| api.py | 读取原始 UTF-8 文件，公开 parse_graph |
| spec.py | 冻结 dataclass 与元组形式的只读数据结果 |
| diagnostics.py | Diagnostic、ParseError |
| parsing/source.py | 原始文本、换行规范化、源位置映射 |
| parsing/markdown.py | Markdown 容器上下文及 DSL 块标记覆盖、严格围栏闭合检查 |
| parsing/parser.py | 区域／作用域、设置与说明提取、不可变结果生成 |
| parsing/transitions.py | 列表／表格的专用记录解析及原始单元格保留 |
| parsing/validation.py | 名称、重复节点／键、目标、Default 混用检查 |

使用 markdown-it-py==3.0.0 的 CommonMark 块解析与 table 扩展，固定版本以稳定规则接口。DSL 规则在 GFM 表头识别之前运行；它们仅在合法物理行首和 Markdown 上下文激活。围栏包装沿用库的容器识别并拒绝未闭合情况。参见其[规则扩展说明](https://markdown-it-py.readthedocs.io/en/latest/architecture.html)。

不渲染 Markdown、不使用渲染树重建正文、不执行行内反转义。来源换行由本项目规范化；跳过库的额外字符规范化，其他源字符原样保留。转移表自原文切列，沿用 GFM 转义竖线边界，但保留附加列中的反斜杠及超过表头的所有列。

测试使用 Python 标准库 unittest，不增加测试框架依赖。LangGraph、模型库或用户执行文件都不是解析依赖。

## 3. 数据表示与源位置

GraphSpec 保留 path、source_text、preamble、preamble_span、preamble_descriptions、可选 config、按顺序排列的 nodes。entry 为首节点名称。NodeSpec 保留名称、设置、prompt、说明、可选 transitions，以及完整节点／标题／正文范围。

设置和说明为冻结对象元组；Setting 保留 key、value、原始行和 value_span。Transition 保留键、目标、原始行、各执行字段位置和所有 extra_cells；TransitionBlock 保留列表／表格类型、原始区块及表头／分隔行单元格。原文可通过 graph.source_slice(span) 取得。

位置为一基行号／列号；offset 为零基 Unicode 字符偏移，不是 UTF-8 字节数。范围为左闭右开，针对原始解码文本计算，保留 CRLF／CR 的实际长度；正文单独规范化为 LF。制表符在位置列中按一个字符计算，不按显示宽度展开。

这些是 M1 的具体数据选择，公开表示仍可在后续原型显式修订。GraphSpec 中没有函数、模型、State 实例或图运行对象。

## 4. 诊断

ParseError.diagnostic 提供 phase（read／parse／validate）、code、message、span。错误码是当前实现的诊断标识，不扩大冻结语言范围。不报告所有错误，也不保证多错误输入的顺序；没有发现错误才返回完整 GraphSpec。

非法 UTF-8 产生带前缀位置的 read 诊断。文件不存在、权限等读取失败保留原生 OSError。绑定能力检查不在本阶段：未知执行器、缺少引用文件、只有正文的 python、无效 router 组合等不被语法阶段擅自拒绝。

## 5. 验证结果与范围

实际环境：Python 3.14.4、markdown-it-py 3.0.0。当前环境已有解析依赖，使用带系统包可见性的本地虚拟环境完成无网络的 editable 安装：

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install --no-build-isolation --no-deps -e .
.venv/bin/python -m unittest discover -s tests -v
```

结果：79项测试通过。包含全部45份 manifest 输入的接受／拒绝、必要结果投影与诊断原因校验，以及清单覆盖、源位置、原文、CR／CRLF、无末尾换行、容器围栏、HTML 原文、GFM 附加列、关键字优先级、无代码导入、并发解析隔离和9组完整示例解析。

敏感样本在解析前后逐字节相同；代码引用指向有顶层副作用的脚本也没有执行，解析不导入 LangGraph／LangChain。包 editable 构建与安装成功。

未运行全量 CommonMark 官方一致性套件；当前验证覆盖项目规范和已补充的上下文边界。Python 3.11～3.13 尚未运行测试矩阵。没有验证绑定、模型调用或原生图运行，不据 M1 宣称端到端可用。
