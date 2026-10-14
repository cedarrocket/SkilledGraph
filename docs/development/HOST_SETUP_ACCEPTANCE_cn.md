# 首次 API 配置向导验收

日期：2026-10-09。不扩展 DSL，只修改基础 Host。

## 模块与范围

host_setup_cn.py 负责首次交互、用户配置加载、校验与原子写入；host_locales_cn.py 负责中英文提示及系统 locale 标识选择；terminal_cn.py 抽取原有终端编辑并提供隐藏输入。host_config_cn.py 增加静态头部 JSON 校验和 SGRAPH_HEADERS_JSON。host_cn.py 集成自动配置与 --setup，并允许已保存参数传给原生模型初始化。

支持 OpenAI 风格 Chat Completions 和 Responses、自定义基础 URL、模型 ID、API key、静态请求头。没有 provider 套餐登录协议、OAuth、动态 session 生成、自动模型发现或多连接管理。chat 可选依赖明确包含 langchain-openai 1.7.0。

配置在用户目录保存，测试只使用临时目录和合成密钥；未读取或修改真实用户配置。秘密隐藏输入，不进入编辑历史，不输出到终端；本地配置明文保存，POSIX 原子生成文件权限 0600。已有环境密钥可复用且不会复制进文件。首次自动配置完成后继续执行图；主动 --setup 完成退出。管道不启动向导或消耗初始输入。显式模型／factory 不混用已保存凭据与地址。

## 验证结果

全量 unittest 206/206 通过。15 项新增测试覆盖：

- 中英文 locale 选择、覆盖优先级、未知语言英文回退。
- XDG 与显式路径选择；配置加载保存及 POSIX 0600。
- 错误输入重试、不回显错误秘密、JSON／UTF-8 错误配置安全诊断。
- EOF／Ctrl-C 不写入或覆盖配置，管道不消费输入。
- 环境密钥复用、保存连接与显式模型选择的优先级。
- 自动向导继续执行图，--setup 仅配置后退出。
- 真实 LangChain/OpenAI 客户端通过 httpx.MockTransport 构造两种协议的请求，检查请求路径、Bearer 密钥和静态 session 头，解析合成响应。
- 实际 sgraph CLI 伪终端配置、隐藏密钥与头部输入、保存并正常退出。

没有外部 API 请求或真实套餐验收。操作系统实测 Linux；Windows 使用 APPDATA 的目录策略已实现，但本轮未进行 Windows 终端或文件权限验收。向导不调用 setlocale，避免系统缺少语言包导致启动失败。

官方背景：[OpenAI API 鉴权及请求头](https://developers.openai.com/api/reference/overview)、[OpenCode Zen 模型与端点表](https://opencode.ai/docs/zen/)。OpenCode 各模型协议不同，只有支持这两种接口及 API-key 鉴权的端点属于本功能适用范围；不能把它扩展为所有套餐均可接入的承诺。

后续真实验收补充：OpenCode Go glm-5.3-flash 的普通编码请求与工具循环已通过，使用自有 User-Agent 和稳定会话头；见[套餐验收](OPENCODE_GO_ACCEPTANCE_cn.md)。上述 mock 测试结果仍保留为独立确定性验证。
