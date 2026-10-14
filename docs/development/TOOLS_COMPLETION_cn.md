# 工具调用实现与验收

日期：2026-10-09。普通工具调用扩展完成；MCP 传输与会话、多模型选择不在本轮范围。

## 设计与实现

- 语言规则：[语言规范](../standard/v0.1/LANGUAGE_SPEC_cn.md)“工具调用扩展”；接口与执行职责：[白皮书](../standard/v0.1/IMPLEMENTATION_WHITEPAPER_cn.md)“工具执行扩展”。
- parser/spec：支持 ToolNode 类型、@tools 选择及特殊条件，保留 Markdown 围栏保护和源码位置。
- tool_selection：纯数据选择语法，不依赖 LangGraph。
- tool_execution/building：tools 参数绑定、原生 ToolNode、合并后消息信号、优先级与条件边。
- execution：带特殊条件的节点提交消息更新，不同时发出旧文本路由 Command。
- 不修改已有 Hardcode_Execution_Backend 绑定签名，不调用模型 bind_tools，不建立 MCP 连接。
- 标准示例：[workflow_cn.md](../../examples/10-tool-calling/workflow_cn.md)、[Host](../../examples/10-tool-calling/host_cn.py)。

## 验收

完整 unittest：160 项通过，包括原有 137 项回归、新增 6 项工具解析测试和 17 项运行测试。原有全示例测试已扩充为 10 组。

新增覆盖：同步完整循环、多个工具请求、混合同步/异步工具、按名称选择及空集合、缺失名称/重名诊断、Python 函数转换、messages Schema 要求、ToolNode 忽略正文、信号优先于 router、异步 router、普通键优先于兜底、字面信号不伪造请求、无隐式工具边、缺失兜底错误、checkpointer 暂停恢复、工具原生 Command、Python/pyfunction 输出接入、ToolNode router、reducer 合并后检测、无提前执行或模型重新绑定，以及未知调用名的原生错误消息。

本机沙箱下 asyncio.to_thread 的最小程序在线程池关闭时停住；工具异步循环已经返回正确结果。完整测试在获准的沙箱外环境运行并正常退出，没有通过修改产品代码或跳过测试规避。Python/依赖版本沿用 M3～M5 记录。

未验证：真实模型服务、MCP 适配器/服务/会话、跨平台，以及原生全部高级组合。不能从工具对象接口兼容推导出这些已通过集成验收。
