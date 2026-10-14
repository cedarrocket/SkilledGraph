# sgraph_agent 实现与验收

日期：2026-10-09。已实现 [sgraph_agent](../../sgraph_agent/README_cn.md)，独立于 examples 展示模型：默认使用真实 API，提供持续会话、基础工具、逐次危险操作许可与节点驱动的上下文压缩。

## 分工和实现范围

现有 DSL 定义 CheckContext／CompactContext／Agent／PermissionGate／ExecuteTools／CheckAfter／CompactAfter 及转移。没有新增节点类型、设置键、路由条件或 Reducer DSL。

Host 提供真实模型、工作区与 InMemorySaver，延续同一 thread；局部 agent bindings 提供模型、压缩、许可和工具执行。压缩模型返回材料后，通过原生 Annotated messages Reducer 的完整快照替换接口执行历史管理。Reducer 不包含模型请求，Hardcode_Execution_Backend 不包装或注册 Reducer。

许可由单独的前置节点调用原生 interrupt；Host 识别 kind=tool_permission，展示调用参数并收集 bool。所有 Bash、写入、编辑都需要逐次明确许可；读取／搜索／目录列出通过受限路径检查，Monty 计算没有宿主回调。ExecuteTools 内部按请求顺序调用原生 ToolNode，仅执行指纹吻合且再次校验通过的调用，拒绝项也返回匹配的 ToolMessage。

核心新增的可选内置后端为 `monty:FILE`，节点返回 JSON State 更新、router 返回字符串。只改执行器注册及新增独立实现，现有解析／调度语义不变。agent 和 monty 依赖均为可选 extra；安装包额外发布 sgraph-agent 命令和 agent 的 workflow_cn.md。

## 离线测试

全量 **272 项 unittest 通过**；新增 [test_sgraph_agent_cn.py](../../tests/test_sgraph_agent_cn.py)共 **27 项**，最后针对终端转义、非法调用 ID、搜索目录过滤、编辑权限保持、Bash 正常退出码和摘要输入／预算保护调整，再次复跑完整 agent 的 27 项全部通过；随后有界 JSON 序列化和空工具列表输出调整也以 27 项回归通过。

覆盖范围：

- 真实文件读取／搜索／列出、真实 Monty 运算、ToolMessage 配对及多工具批次。
- 拒绝 Bash／写入不产生文件副作用；批准后执行；读与拒绝混合批次。
- 非终端默认拒绝，字符串 "yes" 不能当作 bool True；独立批次多次中断恢复不重复询问已恢复项。
- 私密、越界、符号链接、硬链接、特殊设备、过大文件和写入被拒绝；参数指纹与执行前路径复验。
- 未知工具／多余参数／空调用 ID 拒绝；调用预算停止循环。
- 多轮继承、压缩后继续使用摘要、不同线程隔离、失败后保护未完成 checkpoint。
- Monty 文件、环境变量与子进程／网络模块访问拒绝；CPU／内存／源码上限；print 捕获与截断；有界 JSON 序列化防止共享列表的指数展开；节点、消息更新、router 三种实际 DSL 接入。
- 终端控制字符／双向格式控制转义；Bash 超时、输出限制、正常退出码、进程组终止及不继承 API key。
- 真正 ChatOpenAI 配合 HTTP MockTransport 的 Responses 请求／结果序列化：函数调用、配对输出、加密推理项、store=False、无 previous_response_id。
- DeepSeek 明文 reasoning 的 stateless 请求适配；CLI 无 API 的 --help。

安全测试只操作独立临时目录，正常 unittest 不联网。使用完整测试集需安装 agent extra；未安装时本测试模块按可选依赖跳过。

## 真实 Responses 测试

使用 DeepSeek **deepseek-flash**，真实端点 https://api.deepseek.com，用户授权的 key 文件。凭据没有保存进报告。所有文件、命令和会话背景都是合成资料，工作目录为独立临时目录。

[四例原始记录](SGRAPH_AGENT_LIVE_RESULTS.json)：reasoning_effort=none、timeout=60、max_output_tokens=2048、max_retries=0；**4/4 通过，14 次请求、18776 tokens**。

| 案例 | 实际检查 |
| --- | --- |
| read_monty | read_file 读取合成项目说明、Monty python 算出 sum(range(10))=45 |
| deny_bash | Bash 调用触发许可；拒绝后 denied-marker 未创建 |
| approve_write_bash | 仅批准 approved.txt/approved 及精确 printf shell-ok；文件和实际工具结果均核实 |
| memory | 三轮继承；压缩两次；用 python 得出 42；压缩后仍回答“林”“中文” |

发现 LangChain 1.7.0 在 store=False 时省略没有 encrypted_content 的 reasoning。对于 DeepSeek 的明文 reasoning，增加局部 AgentChatOpenAI 适配：回传完整内容，移除消息／推理项的服务端 ID 引用，保持 store=False 与无 previous_response_id。该适配依赖固定版本的私有序列化函数，是升级复验点。

[Thinking 复测](SGRAPH_AGENT_THINKING_RESULTS.json)：reasoning_effort=low、max_output_tokens=4096，真实 read_monty 工具循环再次通过；**2 次请求、2326 tokens**。前四例发生在此 provider 适配加入前，Thinking 是加入后的针对性复测；没有把不同轮次伪称为同一次执行。

最终摘要改为只总结可见对话／工具记录，并拒绝超预算旧历史，避免把加密推理块当作事实资料。[最终记忆复测](SGRAPH_AGENT_MEMORY_FINAL_RESULTS.json)再次通过：压缩 1 次、姓名与偏好保留、真实 python 计算完成；**5 次请求、8387 tokens**。三轮受控监测合计 **21 次请求、29489 tokens**。

最终还从项目外 /tmp 运行安装后的 sgraph-agent CLI，以真实 Responses／Monty 完成 sum(range(100))=4950，**退出码 0、2 次 Agent 请求**，见 [CLI 记录](SGRAPH_AGENT_CLI_RESULTS.json)。该独立 CLI 没有 token 监测，不能计入上述 29489 tokens 总量。

这些验收证明有限场景中的真实执行和安全门生效，不保证任意指令、所有模型、所有平台和全部安全威胁都已覆盖。OpenAI 端点进行 HTTP 模拟验证，未用真实 OpenAI key 验收；DeepSeek 端点进行了真实测试。Monty 为实际本地执行，不是模拟沙箱。

## 打包与运行

pip install -e '.[agent]' 成功，sgraph-agent 帮助及项目外调用通过。构建 wheel 并检查包含 sgraph_agent/workflow_cn.md 与 skilledgraph/monty_execution.py；没有把密钥、测试报告或 examples 工具当作 runtime 依赖。

运行命令及参数见 [README](../../sgraph_agent/README_cn.md)。真实受控测试显式 opt-in：

```bash
export SGRAPH_API_KEY_FILE="$HOME/sys_prog/deepseek_api.txt"
export SGRAPH_TIMEOUT=60
export SGRAPH_MAX_TOKENS=2048
export SGRAPH_MAX_RETRIES=0
export LANGSMITH_TRACING=false
.venv/bin/python tests/live/run_sgraph_agent_cn.py --run --output /tmp/sgraph-agent-results.json
```

每例 Monitor 最多八次模型请求，可重复 --case 筛选；--reasoning-effort low 用于 Thinking 复测，应适当增加输出预算。测试脚本只精确预批准无害的合成写入／printf，未开放生产 Host 的全局自动批准选项。

## 明确边界

- 许可不是 Bash OS 沙箱；批准后的命令有运行用户的文件／网络权限。进程组管理、超时、输出限制和干净环境不等于全面资源隔离。
- 文件工具使用描述符和 no-follow 防止常见路径绕过，但凭据名单不能识别所有正常文件中的秘密，原子替换也不是多人编辑事务。
- Monty 是受限 Python 子集，不允许任意第三方 CPython 库，没有回退；并非支持所有 Python 程序。
- 历史压缩有损；字符估算不是精确 tokenizer，需预留系统／工具 Schema／输出空间。旧 checkpoints 保留原文，未提供磁盘持久化、脱离进程后的恢复或删除协议。
- 状态和 side effect 不保证整轮事务／exactly-once；失败后先检查已执行操作。未完成任务不能直接被新请求覆盖。
- 当前是 POSIX 终端 agent，无 MCP 自动加载、skills／插件系统、流式 token UI、后台任务或多用户部署。基础 chat Host 保持原有单轮默认行为。

外部依据：[OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling)、[DeepSeek Responses 兼容说明](https://api-docs.deepseek.com/guides/responses_api/)、[Monty Python 官方用法](https://github.com/pydantic/monty/blob/main/crates/monty-python/README_cn.md)。
