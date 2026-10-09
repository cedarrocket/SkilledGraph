# DeepSeek 真实环境验收

日期：2026-10-09。Host 环境配置已实现；最终真实验收 **15/15 通过**，离线 unittest **170 项通过**。MCP 本轮未测试。

## 修改范围

基础 Host 新增 SGRAPH_API_KEY / SGRAPH_API_KEY_FILE、SGRAPH_BASE_URL、TEMPERATURE、TIMEOUT、MAX_TOKENS 和 MAX_RETRIES 配置。通过 LangChain init_chat_model 传递，provider 标准凭据环境变量仍然有效。key 文件仅在 Host 中读取，不写入 State、DSL、日志或报告，不修改系统环境。模型 factory 自行管理配置。

使用环境变量入口，不自动加载 OpenCode 配置或 auth.json。无需新增 DSL 属性。复杂工具 Host 使用现有 Python 入口，显式 bind_tools 后将工具对象传给 load_graph。

实际安装 langchain-deepseek 1.1.1、langchain-openai 1.7.0；保留 langgraph 1.2.14、langchain-core 1.6.9、langchain 1.4.4。已增加 deepseek 可选依赖组。

官方依据：[LangChain DeepSeek 集成](https://docs.langchain.com/oss/python/integrations/chat/deepseek)、[DeepSeek 工具调用](https://api-docs.deepseek.com/guides/tool_calls/)。没有把特定提供方模型配置写入 DSL。

## 最终结果

请求模型为 deepseek:deepseek-chat，所有记录中的服务实际 model_name 为 deepseek-flash；这是本次响应观察，不保证别名映射以后不变。temperature=0，timeout=45 秒，max_tokens=256，max_retries=0。工具循环 recursion_limit=12。

| 用例 | 结果 | 模型请求数 | 耗时（秒） |
| --- | --- | --- | --- |
| 普通 Prompt 精确回答 | 通过 | 1 | 0.647 |
| 两节点历史传递与实际模型输入 | 通过 | 2 | 2.092 |
| 列表路由 yes | 通过 | 2 | 2.404 |
| 列表路由 no | 通过 | 2 | 2.048 |
| 表格路由 yes | 通过 | 2 | 2.245 |
| 表格路由 no | 通过 | 2 | 1.835 |
| 函数材料注入与保存 | 通过 | 1 | 0.867 |
| 同步单工具循环 | 通过 | 2 | 2.003 |
| 一轮两个工具请求 | 通过 | 2 | 2.400 |
| 依赖结果的两轮工具调用 | 通过 | 3 | 3.022 |
| 异步工具循环 | 通过 | 2 | 2.303 |
| 参数校验错误回传并恢复 | 通过 | 3 | 4.293 |
| 工具业务异常向外传播 | 通过 | 1 | 1.188 |
| 基础 Host 管道输出 | 通过 | 1 | 1.366 |
| 独立 CLI 环境配置 | 通过 | 1（子进程） | 2.809 |

最终一轮：26 次进程内模型请求，加 1 次 CLI 子进程请求；进程内 5292 input tokens、608 output tokens，共 5900 tokens。CLI 子进程 token 未采集，不包括在合计内。耗时为用例端到端时间，不是单次请求延迟；不是性能基准。

[最终原始结果](DEEPSEEK_LIVE_RESULTS.json)记录合成输入、回复、工具请求、调用 ID、耗时和服务用量。工具协议检查要求请求与 ToolMessage ID 匹配、全部结果回传后才有下一次 AI 回复、最后得到无 tool_calls 的 AI 回答。

单工具结果为 42；双工具在同一 AIMessage 中发出 add 和 multiply 请求，两条 ToolMessage 均成功；依赖调用先查询合成值 37，再 add 5，最终 42；异步路径成功。参数校验失败生成 status=error 的 ToolMessage，模型随后修正参数；业务 ValueError 则向外传播。

## 第一轮失败与分析

[第一轮](DEEPSEEK_LIVE_INITIAL.json)为 12/14：
1. 历史测试要求逐字复述 SG_HISTORY_731，模型把标记改写为 SG_HISTORY_<answer>731</answer>，第二次回答也未精确复述。
2. 工具函数抛 ValueError，测试原先期待自动转成错误消息后恢复，实际原生 ToolNode 默认向外传播业务异常。

[首次复测](DEEPSEEK_LIVE_FOLLOWUP.json)使用 SG_HISTORY_SENTINEL 仍失败，模型改写标记并声称未收到上一条回复。这说明模型叙述不能作为消息传递是否正确的证据。

[历史专项复测](DEEPSEEK_LIVE_HISTORY.json)改用自然语言“蓝鲸”，并记录第二次实际模型输入，确认包含 system、原 human 和前节点 AIMessage；回复正确引用蓝鲸。最终全套再次通过。原有离线精确历史传递测试继续通过。未通过字符串清洗掩盖模型回复，也未修改框架消息合并规则。

错误测试修订为两个独立契约：参数校验错误可回传并恢复，业务异常默认传播。真实测试和新增离线回归均通过。没有为通过测试修改 ToolNode 默认错误策略。

精确特殊标记输出的不稳定属于本次观察到的模型行为风险。temperature=0 不保证逐字遵循指令；命名路由仍可能返回非法键，应继续保留运行时诊断。最终 15/15 是一次受控验收结果，不代表任意提示词、工具及任务的成功率。

## 验证边界与复现

离线 170 项通过；不安装 runtime 的基础环境测试仍可运行，118 项被发现、27 项跳过，实际执行 91 项。代码语法编译和 live demo DSL 检查通过。

当前 .venv 使用 system-site-packages；全环境 pip check 报告系统继承包的既有缺包/冲突（如 cffi、部分类型桩、google-auth/cachetools），没有将其修复或声称依赖环境完全干净。没有报告本轮 LangChain/DeepSeek 包的依赖冲突。需要另行做干净环境和跨平台验收。

全部阶段合计有 60 次已知 API 请求（含最初连接探针、复测、最终测试及两次 CLI 子进程），已采集的 token 共 12321，不含 CLI token。不计算费用。

没有测试 MCP、真实文件工具、真实外部写操作、全部 provider、多模型选择、长上下文或长期持久化。所有发送的任务数据均为合成测试内容。

运行入口：[测试说明](../../tests/live/README.md)、[测试脚本](../../tests/live/run_deepseek.py)、[真实工具 Host](../../tests/live/demo/host.py)、[工具 DSL](../../tests/live/demo/workflow.md)。命令使用 SGRAPH_API_KEY_FILE 引用本地文件，密钥不进入源码。
