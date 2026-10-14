# First-run API setup acceptance

Date: 2026-10-09. Only the standard Host changed; DSL was not extended.

host_setup handles interaction, profile loading/validation and atomic saving; host_locales provides Chinese/English strings and locale selection; terminal provides editing/hidden input; host_config validates static JSON headers and SGRAPH_HEADERS_JSON. host integrates automatic setup/--setup and forwards saved settings to native model initialization.

Supports OpenAI-style Chat Completions/Responses, custom URLs/model IDs/API keys/static headers. This milestone did not provide plan login, OAuth, dynamic session generation, discovery or multiple connections. chat explicitly includes langchain-openai 1.7.0.

Profiles are user-local. Tests use temporary directories/synthetic keys only. Hidden secrets are excluded from history/terminal output. Stored configuration is plaintext; POSIX atomic files are 0600. Environment keys can be reused without copying them into profiles. Automatic first-run setup continues graph execution; explicit --setup exits after saving. Pipes neither launch setup nor lose input. Explicit models/factories do not mix saved credentials/endpoints.

**206/206 tests passed**, including 15 new tests: locales/overrides/English fallback, XDG/explicit paths and permissions, retry/secret-safe JSON/UTF-8 errors, EOF/Ctrl+C nonmutation, pipe preservation, key/profile precedence, automatic versus explicit setup, actual LangChain/OpenAI clients using httpx.MockTransport for both API paths/Bearer/header/response handling, and actual CLI PTY hidden-key/header configuration.

No external requests or real plans were tested in this round. Linux was exercised; Windows APPDATA policy was implemented but terminal/permission behavior untested. No setlocale call is required, avoiding missing language-pack failures.

References: [OpenAI authentication/headers](https://developers.openai.com/api/reference/overview), [OpenCode Zen endpoints](https://opencode.ai/docs/zen/). Only endpoints using the supported APIs and API-key authentication are covered, not every plan. Later Go glm-5.3-flash coding/tool tests passed with an independent User-Agent/stable session: [Go acceptance](OPENCODE_GO_ACCEPTANCE_en.md). Mock results remain separate evidence.
