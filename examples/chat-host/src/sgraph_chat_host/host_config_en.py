"""Small environment-based connection configuration owned by the chat Host."""
import json
import re
import math
import os
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4


_HEADER_NAME = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+\Z")


def parse_headers(value):
    """Validate static headers without echoing potentially secret contents."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            raise ValueError("Headers must be a JSON object of string pairs") from None
    if not isinstance(value, dict):
        raise ValueError("Headers must be a JSON object of string pairs")
    seen = set()
    for name, item in value.items():
        if (not isinstance(name, str) or not _HEADER_NAME.fullmatch(name)
                or name.lower() in seen or not isinstance(item, str)
                or any(ord(c) < 32 or ord(c) > 126 for c in item)):
            raise ValueError("Invalid HTTP header name/value or duplicate name")
        seen.add(name.lower())
    return dict(value)


def opencode_go_options(options, *, base_url=None):
    """Add Go client identity once per model creation, without mutating inputs.

    The basic Host creates one model per run; tool loops and interrupt resumes
    reuse that model. Explicit case-insensitive headers remain user-controlled.
    """
    result = dict(options)
    url = urlsplit(str(options.get("base_url") or base_url or ""))
    if (url.scheme != "https" or url.netloc.lower() != "opencode.ai"
            or url.path.rstrip("/") != "/zen/go/v1"):
        return result
    headers = parse_headers(options.get("default_headers") or {})
    names = {name.lower() for name in headers}
    if "user-agent" not in names:
        headers["User-Agent"] = "sgraph-harness-agent/0.1.0.dev0"
    if "x-opencode-session" not in names:
        headers["x-opencode-session"] = "sgraph-harness-agent-" + str(uuid4())
    result["default_headers"] = headers
    return result


def model_options(*, base_dir: Path, environ=None):
    """Explicit SGRAPH options override provider defaults without mutating env.

    Providers still read their own standard credential variables when api_key
    is absent. Relative key-file paths are relative to the graph directory.
    """
    env = os.environ if environ is None else environ
    options = {}
    key = env.get("SGRAPH_API_KEY")
    key_file = env.get("SGRAPH_API_KEY_FILE")
    if key and key_file:
        raise ValueError("Choose SGRAPH_API_KEY or SGRAPH_API_KEY_FILE, not both")
    if key_file:
        path = Path(key_file).expanduser()
        if not path.is_absolute():
            path = base_dir / path
        key = path.read_text(encoding="utf-8").strip()
        if not key or any(char.isspace() for char in key):
            raise ValueError("SGRAPH_API_KEY_FILE must contain one nonempty API key")
    if key is not None:
        if not key.strip() or any(char.isspace() for char in key):
            raise ValueError("SGRAPH_API_KEY must contain one nonempty API key")
        options["api_key"] = key
    if env.get("SGRAPH_BASE_URL"):
        options["base_url"] = env["SGRAPH_BASE_URL"]
    for variable, option, kind in (
        ("SGRAPH_TEMPERATURE", "temperature", float),
        ("SGRAPH_TIMEOUT", "timeout", float),
        ("SGRAPH_MAX_TOKENS", "max_tokens", int),
        ("SGRAPH_MAX_RETRIES", "max_retries", int),
    ):
        if variable not in env:
            continue
        try:
            value = kind(env[variable])
        except (ValueError, TypeError):
            raise ValueError(f"{variable} must be a valid {kind.__name__}") from None
        if not math.isfinite(value):
            raise ValueError(f"{variable} must be finite")
        if option in {"timeout", "max_tokens"} and value <= 0:
            raise ValueError(f"{variable} must be positive")
        if option in {"temperature", "max_retries"} and value < 0:
            raise ValueError(f"{variable} must be nonnegative")
        options[option] = value
    if "SGRAPH_HEADERS_JSON" in env:
        options["default_headers"] = parse_headers(env["SGRAPH_HEADERS_JSON"])
    return options
