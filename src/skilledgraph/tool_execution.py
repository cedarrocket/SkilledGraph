"""Native tool execution and explicit signal routes."""
from collections.abc import Mapping

from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool, tool
from langchain_core.runnables import RunnableConfig
from langgraph._internal._runnable import RunnableCallable, coerce_to_runnable
from langgraph.graph._branch import _get_branch_path_input_schema

from .diagnostics import Diagnostic, RoutingError
from .tool_selection import parse_tool_selection


def tool_registry(tools):
    registry = {}
    for item in (() if tools is None else tools):
        value = item if isinstance(item, BaseTool) else tool(item)
        if value.name in registry:
            raise ValueError(f"Duplicate tool name: {value.name}")
        registry[value.name] = value
    return registry


def select_tools(value, registry):
    names = parse_tool_selection(value)
    names = tuple(registry) if names is None else names
    missing = [name for name in names if name not in registry]
    if missing:
        raise ValueError(f"Unknown tools: {missing}")
    return [registry[name] for name in names]


def signal_router(node, action=None, *, implicit_text=False):
    """Inspect merged State; a matched tool signal bypasses the user router."""
    keys = {r.key for r in node.transitions.records}
    ordinary = keys - {"@ToolCalls", "@Otherwise"}
    original = coerce_to_runnable(action, name=f"{node.name}_router", trace=True) if action is not None else None

    def latest(state):
        messages = state.get("messages") if isinstance(state, Mapping) else getattr(state, "messages", None)
        return messages[-1] if messages else None

    def signal(state):
        message = latest(state)
        return "@ToolCalls" in keys and isinstance(message, AIMessage) and bool(message.tool_calls)

    def resolve(value):
        if isinstance(value, str) and value in ordinary:
            return value
        if "@Otherwise" in keys:
            return "@Otherwise"
        raise RoutingError(Diagnostic("routing.key", f"Node {node.name!r} returned route {value!r}; legal keys: {sorted(keys)!r}", node.transitions.span, "run"))

    def text_key(state):
        message = latest(state)
        return message.text.strip() if implicit_text and isinstance(message, AIMessage) else None

    def invoke(state, config: RunnableConfig):
        key = "@ToolCalls" if signal(state) else resolve(original.invoke(state, config) if original else text_key(state))
        from .trace_integration import record_route
        record_route(config, key, [next(r.target for r in node.transitions.records if r.key == key)])
        return key

    async def ainvoke(state, config: RunnableConfig):
        key = "@ToolCalls" if signal(state) else resolve(await original.ainvoke(state, config) if original else text_key(state))
        from .trace_integration import arecord_route
        await arecord_route(config, key, [next(r.target for r in node.transitions.records if r.key == key)])
        return key

    if original:
        schema = _get_branch_path_input_schema(original)
        if schema is not None:
            invoke.__annotations__["state"] = schema
            ainvoke.__annotations__["state"] = schema
    return RunnableCallable(invoke, ainvoke, name=f"{node.name}_signal_router", trace=True)
