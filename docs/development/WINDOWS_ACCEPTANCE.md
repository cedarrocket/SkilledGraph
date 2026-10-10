# Windows 跨平台测试验收

日期：2026-10-11。本次只调整测试、测试资料的 Git 换行约定、本地 MCP 验收脚本和 CI 配置；未修改 src/skilledgraph/、sgraph_agent/ 或标准 Host 实现。

## 本机结果

Windows 10（10.0.19041）、64 位 Python 3.14.0，完整安装 skilledgraph[chat,agent,mcp]，pip check 通过。Windows 默认文本编码为 GBK，未依赖全局 PYTHONUTF8=1。

全量 unittest：**274 项，248 项通过，26 项跳过，0 失败、0 报错**。其中非 agent 测试为 247 项：245 项通过，2 项 POSIX PTY 测试跳过。agent 的 27 项测试中，24 项依赖 POSIX 工作区而跳过，3 项平台无关的连接配置、请求构造及 CLI 帮助测试通过。skip 不代表相应功能获得 Windows 验收。

本地 stdio MCP：**4/4 通过**，涵盖工具发现、直接调用、两轮图执行和子进程清理；直接调用还检查子进程存活。未调用真实模型 API。

## 修复范围

- 测试读写文本显式使用 UTF-8，文件清单使用 POSIX 格式相对路径。
- 示例子进程使用当前 Python 的模块入口，含中文输出时明确启用和解码 UTF-8，消除 .venv/bin/ 假设。
- .gitattributes 固定语言 Markdown 资料为 LF；原始 crlf.md 禁用 Git 文本转换。新增测试在每个平台生成 LF 与 CRLF 输入，验证解析内容一致且原始字节不变。
- Windows MCP 清理检查使用 Windows 进程句柄等待状态；POSIX 保持信号 0 检查。Windows 不再调用 os.kill(pid, 0)。
- agent 测试明确标记所需 POSIX 能力；保留平台无关测试，未改变 agent 实现。

## CI 与验收边界

.github/workflows/tests.yml 配置 Ubuntu、macOS、Windows × Python 3.11、3.14 共六组任务。每组安装完整依赖，检查依赖一致性、运行全量离线测试、验证安装后的 CLI 入口，并验收本地 MCP。CI 使用 PYTHONUTF8=0，避免 UTF-8 模式掩盖默认编码依赖。

当前仅实际执行了上述 Windows / Python 3.14 测试。Linux、macOS 和 Python 3.11 的新 CI 配置尚未实际执行，不能据此宣称所有平台已验收。Windows 真实终端交互、agent 工作区、远程 MCP 和真实模型连接也不属于本次已通过范围。

## 复现

在项目根目录安装完整依赖后运行：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tests/mcp_demo/check.py --output .local-docs/mcp-results.json
```

Linux/macOS 使用 .venv/bin/python 执行相同的模块和脚本。开发环境说明见[开发与验收指南](../standard/v0.1/DEVELOPMENT_GUIDE.md)。
