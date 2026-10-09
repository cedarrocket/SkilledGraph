"""Data-only ToolNode selection grammar; no runtime imports."""
import re

_NAME = re.compile(r"[A-Za-z0-9_-]+")


def parse_tool_selection(value):
    """Return None for all, otherwise an ordered tuple of exact tool names."""
    if value == "all":
        return None
    if not (value.startswith("[") and value.endswith("]")):
        raise ValueError("@tools requires all or [name, name]")
    body = value[1:-1].strip()
    names = tuple(part.strip() for part in body.split(",")) if body else ()
    if any(not _NAME.fullmatch(name) for name in names):
        raise ValueError("Tool names must contain ASCII letters, digits, underscores or hyphens")
    if len(set(names)) != len(names):
        raise ValueError("Duplicate name in @tools")
    return names
