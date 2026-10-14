# Windows cross-platform acceptance

Date: 2026-10-11. Changes affected tests, fixture Git line endings, local MCP checker and CI only, without modifying core, agent or standard Host implementation.

## Local results

Windows 10 (10.0.19041), 64-bit Python 3.14.0, skilledgraph[chat,agent,mcp], pip check passed. Default GBK encoding was used without global PYTHONUTF8=1.

**274 tests: 248 passed, 26 skipped, zero failures/errors.** Non-agent: 247 total, 245 passed, two POSIX PTY skips. Agent: 27 total, 24 POSIX workspace skips and three platform-independent connection/request/help passes. Skips do not validate those features on Windows.

Local stdio MCP: **4/4 passed** for discovery, direct invocation, two graph rounds and cleanup, including a child-alive assertion. No live model API was called.

## Changes

- Explicit UTF-8 text I/O and POSIX manifest paths.
- Subprocesses use the active Python/module entry, explicit UTF-8 for Chinese output and no .venv/bin assumption.
- .gitattributes fixes fixture Markdown to LF; crlf.md disables conversion. A new test generates LF/CRLF on each platform and checks equivalent parsing without changing bytes.
- Windows cleanup checks use process-handle waits, never os.kill(pid, 0); POSIX retains signal-zero checks.
- POSIX agent requirements are explicitly marked, preserving portable tests without changing implementation.

## CI and limits

.github/workflows/tests.yml defines six Ubuntu/macOS/Windows × Python 3.11/3.14 jobs, each installing full dependencies, checking consistency, running offline tests, installed CLIs and local MCP. PYTHONUTF8=0 exposes default-encoding assumptions.

Only Windows/Python 3.14 was actually run at this milestone. New Linux/macOS/Python 3.11 CI configuration had not run; all-platform success was not claimed. Real Windows terminal interaction, agent workspace, remote MCP and live model connections were excluded.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tests/mcp_demo/check_en.py --output .local-docs/mcp-results.json
```

Linux/macOS use .venv/bin/python. See [development guide](../standard/v0.1/DEVELOPMENT_GUIDE_en.md). Counts above describe the historical original suite, not a new translated Windows run.
