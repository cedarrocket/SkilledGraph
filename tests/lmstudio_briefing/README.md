# LM Studio 短上下文摘要测试 agent

这是由 SkilledGraph 编排的小型测试 agent，测试当前加载的本地模型能否读懂 CORE.md，并生成可运行的图及配套 Python 文件。它不是聊天应用，也不是模型能力的完整 benchmark。

核心摘要是本地资料，不随 Git 仓库发布。默认读取本机 docs/agent-guide/CORE.md；在其他机器上需提供 `--core-file /path/to/CORE.md`。文件缺失会在连接模型前明确报错。

## 运行

LM Studio 启动本地服务器并加载模型。默认地址为 http://127.0.0.1:1234，默认要求已加载上下文为 8192。只选择已加载的 LLM；多于一个时必须指定 --model，不会猜测或加载其他模型。

```bash
.venv/bin/python tests/live/run_lmstudio_briefing.py --run \
  --output .local-docs/lmstudio-briefing-new-run
```

Windows 使用 `.venv\Scripts\python.exe`。也可以运行：

```bash
python -m skilledgraph tests/lmstudio_briefing/workflow.md -- --run \
  --model underdog-saluki-27b-1.0 --output .local-docs/lmstudio-briefing-new-run
```

输出目录必须新建或为空，避免覆盖旧结果。`--help` 不调用模型；`--run` 才进行真实本地推理。可用 `--repairs 0` 禁止反馈修正。默认最多三次模型请求：规则测验、首次文件生成、一次反馈修正。每次新请求重新提供完整 CORE，不累积聊天历史；不附加 RECIPES 或 EXTENSIONS。

默认 `--transport json` 要求模型返回包含两个文件字符串的 JSON。`--transport files` 改为两个 `### 文件名` 标题加完整代码围栏，减少嵌套字符串转义。`--generation-only` 跳过测验，专门用于独立记录的格式对照；这一模式通过不能被描述为 10 道题也通过。

## 编排与验收

ReadCore → Probe → Generate → Validate；Validate 按结果结束或最多重试一次。

- Probe：10 道规则选择题，结果由固定答案评分。格式错误不做人工修复。
- Generate：要求生成 workflow.md 和 actions.py，包含 State、Python inspect/router、pyfunction Report、缺失材料 Ask，以及明确 End。
- Validate：Python 语法检查、限制性 AST 检查、DSL 静态规则及原生构图执行。分别用非空与空 numbers 验证路由、模型调用次数、材料保存和历史保留。
- 框架执行时用离线模型替身，作者模型仅负责生成文件；真实测试规则理解与代码生成，不测试算术推理或工具调用能力。
- 首次结果和反馈修正分开报告；没有手工修改模型生成物。

生成文件使用两个固定文件名，验证只在新目录中执行，禁止文件/网络/子进程导入和不必要构造。此 AST allowlist 和子进程超时不是通用 Python 安全沙箱；本测试只接受狭窄的 State/路由/材料函数任务，不能拿它执行任意生成代码。

## 接口与预算

使用 [LM Studio 原生 /api/v1/chat](https://lmstudio.ai/docs/developer/rest/chat)，显式设置 context_length、reasoning=off、temperature=0、store=false。Native API 可回传 input_tokens、total_output_tokens 等统计。不是采用强制 JSON grammar decoding，而是测试模型能否自行按要求返回 JSON。

测验输出上限 450 tokens，文件生成默认 1800；达到上限记为潜在截断失败。输入统计加预留输出必须不超过已加载上下文；本测试不改变模型默认加载配置，不使用任何云模型或 key。请求仅允许本地 HTTP 地址，且不使用环境代理。

输出包含模型发现信息、CORE 快照、每次请求与原始响应、每次生成文件和验证 stdout/stderr，以及 report.json。默认保存到被 Git 忽略的 .local-docs 目录。报告中的核心摘要哈希可与 docs/agent-guide/manifest.json 核对。

一次通过只代表该模型、量化、上下文和指定任务的有限结果；选择题可能受猜测影响，不能据此宣称全部语言能力或任意工作流生成均可靠。
