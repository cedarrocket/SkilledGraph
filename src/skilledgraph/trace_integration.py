"""Trace adapters at DSL boundaries; no business State or reducer changes.

执行边界追踪适配，不修改业务 State 或 reducer。
"""
from hashlib import sha256

from langchain_core.callbacks.manager import adispatch_custom_event, dispatch_custom_event
from langchain_core.runnables import RunnableConfig
from langgraph._internal._runnable import RunnableCallable


def enabled(spec):
    return spec.config is not None and spec.config.setting("trace") == "on"


def require_recorder(config):
    from .tracing import TraceRecorder
    callbacks = config.get("callbacks")
    handlers = getattr(callbacks, "handlers", callbacks) or []
    if not any(isinstance(item, TraceRecorder) for item in handlers):
        raise ValueError("@trace: on requires a TraceRecorder receiver; use "
                         "load_graph(..., trace=recorder) or invoke the compiled "
                         "builder with config={'callbacks': [recorder]}")
    return {}


def metadata(spec, node, *, scope=()):
    records = node.transitions.records if node.transitions else ()
    return {
        "trace_graph_version": sha256(spec.source_text.encode("utf-8")).hexdigest(),
        "trace_node": node.name,
        "trace_graph_path": tuple(scope),
        "trace_graph_source": str(spec.path),
        "trace_default_targets": [r.target for r in records if r.key == "@Default"],
    }


def guard_registered_node(builder, name):
    # Keep native registration's inferred schemas/destinations and injection.
    # 保留原生注册得到的 Schema、跳转目标和参数注入。
    registered = builder.nodes[name]
    original = registered.runnable

    def checked(state, config: RunnableConfig):
        require_recorder(config)
        return original.invoke(state, config)

    async def achecked(state, config: RunnableConfig):
        require_recorder(config)
        return await original.ainvoke(state, config)

    # Establish interrupt context; preserve native closure subgraph discovery.
    # 建立 interrupt 上下文，保留原生对子图闭包的检查能力。
    registered.runnable = RunnableCallable(checked, achecked, name=name, trace=True)


def _active(config):
    return bool(config and config.get("metadata", {}).get("trace_graph_version"))


def record_route(config, key, targets):
    if _active(config):
        dispatch_custom_event("trace_route", {"key": key, "targets": list(targets),
                                               "source": "dsl"}, config=config)


async def arecord_route(config, key, targets):
    if _active(config):
        await adispatch_custom_event("trace_route", {"key": key, "targets": list(targets),
                                                    "source": "dsl"}, config=config)


def trace_summary(text, *, config):
    """Explicit opt-in short summary; never an automatic State/message dump.

    显式短摘要；不会自动读取 State 或消息内容。
    """
    if not isinstance(text, str):
        raise TypeError("Trace summary must be a string")
    if _active(config):
        dispatch_custom_event("trace_summary", {"summary": text}, config=config)


async def atrace_summary(text, *, config):
    """Async equivalent of trace_summary / trace_summary 的异步版本。"""
    if not isinstance(text, str):
        raise TypeError("Trace summary must be a string")
    if _active(config):
        await adispatch_custom_event("trace_summary", {"summary": text}, config=config)
