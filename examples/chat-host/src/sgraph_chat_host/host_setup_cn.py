"""First-run connection setup; independent of graph parsing and scheduling."""
import json
import os
from pathlib import Path
import sys
import tempfile
from urllib.parse import urlsplit

from .host_config_cn import parse_headers
from .host_locales_cn import TEXT, language


def config_path(environ=None):
    env = os.environ if environ is None else environ
    if env.get("SGRAPH_HOST_CONFIG"):
        return Path(env["SGRAPH_HOST_CONFIG"]).expanduser()
    root = env.get("XDG_CONFIG_HOME")
    if not root and os.name == "nt":
        root = env.get("APPDATA")
    return (Path(root).expanduser() if root else Path.home() / ".config") / "skilledgraph" / "host.json"


def validate_address(value):
    url = urlsplit(value)
    if (url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password
            or url.query or url.fragment or any(c.isspace() for c in value)
            or url.path.rstrip("/").endswith(("/chat/completions", "/responses"))):
        raise ValueError("Expected an HTTP(S) API base URL, not a full request endpoint")
    return value.rstrip("/")


def validate_profile(profile):
    if not isinstance(profile, dict) or profile.get("version") != 1:
        raise ValueError("Unsupported Host configuration version")
    model = profile.get("model")
    if not isinstance(model, str) or not model.startswith("openai:") or not model[7:].strip() or any(c.isspace() for c in model):
        raise ValueError("Host configuration requires openai:MODEL_ID")
    options = profile.get("options")
    if not isinstance(options, dict) or set(options) - {"base_url", "api_key", "default_headers", "use_responses_api"}:
        raise ValueError("Invalid Host connection options")
    if not isinstance(options.get("base_url"), str):
        raise ValueError("Host configuration requires a base URL")
    validate_address(options["base_url"])
    if not isinstance(options.get("use_responses_api"), bool):
        raise ValueError("Host configuration requires a boolean API mode")
    if "api_key" in options and (not isinstance(options["api_key"], str) or not options["api_key"] or any(c.isspace() for c in options["api_key"])):
        raise ValueError("Invalid Host API key")
    if "default_headers" in options:
        parse_headers(options["default_headers"])
    return profile


def load_profile(path=None):
    path = config_path() if path is None else Path(path)
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except UnicodeDecodeError:
        raise ValueError(f"Invalid UTF-8 Host configuration: {path}; run sgraph GRAPH -- --setup") from None
    try:
        return validate_profile(json.loads(raw))
    except (ValueError, TypeError):
        raise ValueError(f"Invalid Host configuration: {path}; run sgraph GRAPH -- --setup to replace it") from None


def save_profile(profile, path):
    validate_profile(profile)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".host-", suffix=".json", dir=path.parent)
    try:
        # mkstemp uses owner-only permissions on POSIX. Atomic replacement also
        # prevents exposing a partially written config or following file symlinks.
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(profile, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def run_setup(*, input_stream=None, error_stream=None, environ=None, path=None):
    from .terminal_cn import terminal_reader
    env = os.environ if environ is None else environ
    input_stream = sys.stdin if input_stream is None else input_stream
    error_stream = sys.stderr if error_stream is None else error_stream
    text = TEXT[language(env)]
    if not input_stream.isatty():
        raise ValueError(text["terminal"])
    path = config_path(env) if path is None else Path(path)
    print(text["title"], file=error_stream)
    print(text["storage"] + str(path), file=error_stream)
    try:
        with terminal_reader(input_stream, error_stream) as read:
            def ask(key, convert, *, secret=False):
                while True:
                    value = read(text[key], is_password=secret).strip()
                    try:
                        return convert(value)
                    except (ValueError, TypeError):
                        print(text["invalid"], file=error_stream)
            address = ask("address", lambda v: validate_address(v or "https://api.openai.com/v1"))
            def model_id(value):
                if not value or any(c.isspace() for c in value):
                    raise ValueError("model ID required")
                return value
            model = ask("model", model_id)
            def protocol(value):
                if value not in {"", "1", "2"}:
                    raise ValueError("API mode required")
                return value == "2"
            responses = ask("protocol", protocol)
            while True:
                key = read(text["key"], is_password=True).strip()
                if key and not any(c.isspace() for c in key):
                    break
                if not key and any(env.get(k) for k in ("SGRAPH_API_KEY", "SGRAPH_API_KEY_FILE", "OPENAI_API_KEY")):
                    break
                print(text["key_required"], file=error_stream)
            headers = ask("headers", lambda v: parse_headers(v or "{}"), secret=True)
        options = {"base_url": address, "use_responses_api": responses}
        if key:
            options["api_key"] = key
        if headers:
            options["default_headers"] = headers
        profile = {"version": 1, "model": "openai:" + model, "options": options}
        save_profile(profile, path)
        print(text["saved"], file=error_stream)
        return profile
    except EOFError:
        raise ValueError(text["cancelled"]) from None
