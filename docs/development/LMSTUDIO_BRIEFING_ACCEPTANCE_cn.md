# LM Studio / 8k 模型摘要验收

日期：2026-10-13。测试入口：[测试 agent](../../tests/lmstudio_briefing/README_cn.md)。代码基线 ba49197，摘要 CORE 的 SHA256 为 d865afc47fab3c6171f88c6f5b9e8660f1858ed524e1e4e11989a282f032bcce。

## 环境与方法

用户授权访问 http://127.0.0.1:1234。LM Studio 返回唯一已加载 LLM 为 underdog-saluki-27b-1.0（ConwayResearch，27B，IQ2，architecture=qwen35），实际 loaded context_length=8192。按已加载实例测试，没有按用户口述型号猜测或加载另一个模型。

使用 /api/v1/chat，temperature=0、reasoning=off、store=false。完整 CORE 作为系统输入，每次请求重新提供；不加载 RECIPES 或 EXTENSIONS、不使用受约束 JSON 解码、不人工修改生成物。规则测验输出上限 450 tokens，文件生成上限 1800。生成后使用独立子进程及固定离线模型验证；这不是由被测模型自评。

## 第一组：选择题与 JSON 文件交付

- 10 题 **8 题正确**。错误为 q1：认为有正文的 @uses python 自动调用模型；q8：认为 @state 不需要显式 Config。
- 首次文件生成返回 JSON 少一个结尾括号，无法提取文件。
- 给出 JSON 解析错误后重新生成，仍然缺少括号。两次都作为失败保留，没有补括号后算通过。
- 该组整体失败；它首先暴露的是文件交付格式问题，不能从 JSON 失败直接推导 DSL 运行错误。

| 请求 | 输入 tokens | 输出 tokens | 秒 |
| --- | ---: | ---: | ---: |
| 测验 | 3372 | 55 | 59.27 |
| 首次生成 | 3379 | 258 | 62.13 |
| 反馈修正 | 3417 | 348 | 84.18 |

## 第二组：完整文件代码块交付

同一 CORE、同一任务、同一模型和推理设置；要求两个具名文件代码块，取消嵌套 JSON 的字符串转义。此组跳过测验，不能描述为选择题也通过。

**首次生成通过，无反馈修正。** 实际创建 workflow_cn.md 和 actions_cn.py，通过 Python AST、限制性代码检查、DSL 解析、原生构图及两条分支运行：

| 输入 | 路由／最终结果 | 模型调用 | 消息数量 |
| --- | --- | ---: | ---: |
| numbers=[1,2,3] | ready → Report → sum:6 | 1 | 3：初始输入、材料、回答 |
| numbers=[] | missing → Ask → 请求补充 | 1 | 2：初始输入、回答 |

Inspect 未自动调用模型；router 读取更新后的 status；材料按 pyfunction 规则保存。该模型在选择题中答错部分规则，却在这份具体代码中使用了正确写法，说明两种测量不能互相替代。

输入 3395 tokens，输出 281 tokens，耗时 73.46 秒，生成速度约 4.47 tokens/s。没有达到输出上限。输入加预留 1800 输出仍小于 8192，未发现需要截断核心摘要的情况。

有效四次请求共 **13563 输入 tokens、942 输出 tokens**。另有一次格式对照因测试端残留“必须返回 JSON”的系统约束而被主动取消；原始请求和 ABORTED 标记保留，不计为模型成功／失败，也没有完整 token 统计。随后纠正输出约束后完成上述第二组。

## 记录与复现

原始资料位于本地 Git 忽略目录：

- .local-docs/lmstudio-briefing-8k-20261013：第一组全部请求、响应及 report.json。
- .local-docs/lmstudio-briefing-8k-files-20261013：已取消的无效对照及 ABORTED.json。
- .local-docs/lmstudio-briefing-8k-files-control-20261013：第二组请求、响应、report.json、attempt-1 中的两个原始生成文件及独立验证记录。

使用新目录复测完整流程、采用文件代码块交付：

```bash
.venv/bin/python tests/live/run_lmstudio_briefing_cn.py --run \
  --transport files --output .local-docs/lmstudio-briefing-next
```

默认包含一次反馈修正；--repairs 0 只测首次生成。--transport json 可复现 JSON 交付模式；--generation-only 只测文件生成。

## 结论与边界

完整核心摘要可送入该已配置的 8k 实例，输入不足 3.5k tokens，仍有生成余量。这个有限例子显示它能生成可运行的普通 State／路由／材料工作流，但不是完全掌握规则的证据。建议采用无需嵌套转义的文件交付，并保留程序验证和错误反馈。

此次没有测试独立智能推理、tools/MCP 生成、并行、复杂 reducer、跨平台生成或大量随机任务。没有提高上下文，没有训练或修改模型，没有改变核心摘要。一次成功不代表任意 8k 模型都能完成，也不能据此宣称稳定可靠的自动文件创建。

测试 agent 使用 AST allowlist 和超时，只接受狭窄示例；不是通用安全沙箱。离线验证检查框架行为而不是模型答案质量。新增测试脚本完成语法与 CLI 检查、有效参考例验证和错误路由／危险导入拒绝检查；未修改框架运行代码，未复跑全量框架测试。
