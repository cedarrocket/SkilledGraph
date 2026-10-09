"""Small bilingual setup catalog; no OS locale installation is required."""
import locale
import os


TEXT = {
    "en": {
        "title": "LLM API setup — OpenAI-compatible endpoint",
        "address": "API base URL [https://api.openai.com/v1]: ",
        "model": "Model ID (required): ",
        "protocol": "API: 1) Chat Completions  2) Responses [1]: ",
        "key": "API key (hidden; Enter reuses an existing environment key): ",
        "headers": 'Extra HTTP headers as JSON (hidden; Enter skips), e.g. {"X-Session-ID":"..."}: ',
        "invalid": "Invalid value; please try again.",
        "key_required": "Enter an API key, or set an existing key environment variable. For a local server without auth, enter not-needed.",
        "storage": "Connection settings, including entered credentials, will be saved locally to: ",
        "saved": "Saved. The connection has not been tested yet.",
        "cancelled": "Setup cancelled; configuration was not changed.",
        "terminal": "Set SGRAPH_MODEL=provider:model and connection variables, or run with an interactive terminal to configure the API.",
    },
    "zh": {
        "title": "LLM API 初始化 — OpenAI 兼容接口",
        "address": "API 基础地址 [https://api.openai.com/v1]：",
        "model": "模型 ID（必填）：",
        "protocol": "接口：1) Chat Completions  2) Responses [1]：",
        "key": "API key（隐藏输入；直接回车复用已有环境变量密钥）：",
        "headers": '额外 HTTP 请求头 JSON（隐藏输入；回车跳过），例如 {"X-Session-ID":"..."}：',
        "invalid": "输入无效，请重试。",
        "key_required": "请输入 API key 或先设置密钥环境变量。无鉴权本地服务可填写 not-needed。",
        "storage": "连接设置及本次输入的凭据将保存到本地：",
        "saved": "已保存。尚未验证连接是否可用。",
        "cancelled": "已取消配置，配置文件未改变。",
        "terminal": "请设置 SGRAPH_MODEL=provider:model 和连接变量，或在交互终端中运行以配置 API。",
    },
}


def language(environ=None):
    env = os.environ if environ is None else environ
    value = next((env[k] for k in ("SGRAPH_LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG") if env.get(k)), None)
    if value is None:
        value = locale.getlocale()[0] or "en"
    return "zh" if value.lower().replace("-", "_").startswith("zh") else "en"
