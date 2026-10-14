# OpenCode Go live-plan acceptance

Date: 2026-10-09. The user authorized limited requests with existing local opencode-go credentials. ~/.local/share/opencode/auth.json was read only; credentials were neither copied, printed nor written to Host/repository configuration.

## Request contract

Synthetic coding tasks followed [official Go client requirements](https://opencode.ai/docs/go/), using User-Agent `skilledgraph/0.1.0.dev0` and one stable x-opencode-session per independent session. No OpenCode impersonation or unrelated provider credentials/endpoints were used. Two requests in a tool loop shared an ID; a separate test used another.

Tested model: glm-5.3-flash; endpoint: https://opencode.ai/zen/go/v1; Chat Completions. Existing host.create_model created the LangChain model, and SkilledGraph executed the graph. default_headers required no new DSL/authentication wrapper. This observation does not cover all Go models.

## Initial results

**2/2 passed; 3 POST requests.** A Prompt produced an AST-valid add(a,b) function (179 tokens). A tool loop actually invoked read_snippet, returned matching ToolMessage and produced the corrected function (226 and 281 tokens). Total **686 tokens: 457 input, 229 output**. All content was synthetic; no repository/private files were sent. max_tokens=1024, timeout=60, max_retries=0.

[Raw results](OPENCODE_GO_LIVE_RESULTS.json). Explicit runner:

```bash
.venv/bin/python tests/live/run_opencode_go_en.py --run
```

This runner explicitly reads Go credentials; runtime does not automatically import OpenCode configuration. The wizard still allows manual endpoint/model/headers. Initial tests used explicit session values. Only this model's Chat Completions/tool calling was tested, not Responses, all plans or noncoding traffic.

## Automatic session headers

For effective base URL https://opencode.ai/zen/go/v1, create_model fills absent User-Agent `sgraph-harness-agent/0.1.0.dev0` and `x-opencode-session: sgraph-harness-agent-<UUID>`. Generation happens once per model creation; the standard Host creates a model per run, retaining its session through graph calls, tools and resumption. IDs are neither regenerated per request nor saved in configuration.

Explicit headers are preserved case-insensitively; factories are untouched. Other endpoints receive no automatic headers. Custom Hosts reusing models across sessions must manage IDs themselves; native graph APIs are not wrapped.

Four local tests cover new/reused model IDs, input nonmutation, case-insensitive overrides, unrelated endpoints and stable headers on repeated actual-client mock requests. **210/210 unittest tests passed.** The live runner then removed manual headers: **2/2 passed, 3 calls, 643 tokens**. Independent cases had different UUIDs; two tool-loop requests shared one. [Automatic-session results](OPENCODE_GO_AUTO_SESSION_RESULTS.json). The initial 686 tokens remain a separate round.
