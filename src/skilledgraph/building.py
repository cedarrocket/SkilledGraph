"""Bind GraphSpec to native LangGraph objects (loaded only by build/load)."""

from collections.abc import Mapping

from langchain_core.runnables import Runnable, RunnableConfig
from langgraph._internal._runnable import RunnableCallable, coerce_to_runnable
from langgraph.graph._branch import _get_branch_path_input_schema
from langgraph.graph import END, START, MessagesState, StateGraph

from .execution import ModelNode, RequestInputNode
from langgraph.prebuilt import ToolNode
from .tool_execution import tool_registry, select_tools, signal_router
from .binding import builtin_bindings, load_file_object
from .diagnostics import BindingError, BuildError, Diagnostic, RoutingError


def _error(cls, code, message, span, phase):
    return cls(Diagnostic(code, message, span, phase))


def _setting(node, key):
    return next(s for s in node.settings if s.key == key)


def _bind(node, key, registry, base_dir, model):
    setting = _setting(node, key)
    prefix, separator, payload = setting.value.partition(":")
    if not separator or prefix not in registry:
        raise _error(BindingError, "binding.backend", f"Unknown Hardcode_Execution_Backend in {setting.value!r}", setting.value_span, "bind")
    try:
        action = registry[prefix](payload, base_dir=base_dir, node=node, model=model)
        if not callable(action) and not isinstance(action, Runnable):
            raise TypeError("Binding must return a callable or native Runnable")
        return action
    except Exception as exc:
        raise _error(BindingError, "binding.callable", f"Cannot bind {setting.value!r}: {exc}", setting.value_span, "bind") from exc


def _checked_router(action, node, records):
    allowed = tuple(record.key for record in records)

    def validate(value):
        if not isinstance(value, str) or value not in allowed:
            raise _error(RoutingError, "routing.key", f"Node {node.name!r} returned route {value!r}; legal keys: {allowed!r}", _setting(node, "router").value_span, "run")
        return value

    # Preserve native signature injection and branch input-Schema inference.
    original = coerce_to_runnable(action, name=f"{node.name}_router", trace=True)

    def checked(state, config: RunnableConfig):
        key = validate(original.invoke(state, config))
        from .trace_integration import record_route
        record_route(config, key, [records[allowed.index(key)].target])
        return key

    async def achecked(state, config: RunnableConfig):
        key = validate(await original.ainvoke(state, config))
        from .trace_integration import arecord_route
        await arecord_route(config, key, [records[allowed.index(key)].target])
        return key

    schema = _get_branch_path_input_schema(original)
    if schema is not None:
        checked.__annotations__["state"] = schema
        achecked.__annotations__["state"] = schema
    return RunnableCallable(checked, achecked, name=f"{node.name}_checked_router", trace=True)


def build(spec, *, state_schema=None, input_schema=None, output_schema=None,
          context_schema=None, model=None, tools=None, bindings=None,
          _tree=None, _scope=()):
    from .subgraphs import resolve_tree
    _tree = resolve_tree(spec) if _tree is None else _tree
    from .trace_integration import enabled, metadata, guard_registered_node
    tracing = enabled(spec)
    registry = builtin_bindings()
    if bindings is not None:
        if not isinstance(bindings, Mapping):
            raise TypeError("bindings must be a mapping of names to binding callables")
        registry.update(bindings)

    if state_schema is None and spec.config and spec.config.setting("state") is not None:
        setting = _setting(spec.config, "state")
        prefix, separator, payload = setting.value.partition(":")
        try:
            if not separator or prefix != "python":
                raise ValueError("Builtin @state requires python:FILE:ENTRY")
            state_schema = load_file_object(payload, base_dir=spec.path.parent)
            if state_schema is None:
                raise TypeError("@state resolved to None, not a Schema")
        except Exception as exc:
            raise _error(BindingError, "binding.state", f"Cannot load @state {setting.value!r}: {exc}", setting.value_span, "bind") from exc
    elif state_schema is None:
        state_schema = MessagesState

    try:
        builder = StateGraph(state_schema, input_schema=input_schema,
                             output_schema=output_schema, context_schema=context_schema)
    except Exception as exc:
        raise _error(BuildError, "build.schema", str(exc), spec.nodes[0].header_span, "build") from exc

    try:
        available_tools = tool_registry(tools)
    except Exception as exc:
        raise _error(BindingError, "binding.tools", str(exc), spec.nodes[0].header_span, "bind") from exc
    actions = {}
    for node in spec.nodes:
        if node.kind == "Subgraph":
            child = _tree.children[node.name]
            # Each file owns its State; only build resources cross this boundary.
            # 文件自行定义 State，只向子图传递构建资源。
            child_builder = build(child.spec, context_schema=context_schema,
                                  model=model, tools=tuple(available_tools.values()),
                                  bindings=registry, _tree=child,
                                  _scope=(*_scope, node.name))
            try:
                action = child_builder.compile()
            except Exception as exc:
                raise _error(BuildError, "build.subgraph", f"Cannot compile subgraph {node.name!r}: {exc}",
                             _setting(node, "source").value_span, "compile") from exc
        elif node.kind == "ToolNode":
            try:
                action = ToolNode(select_tools(node.setting("tools"), available_tools))
            except Exception as exc:
                raise _error(BindingError, "binding.tools", str(exc), _setting(node, "tools").value_span, "bind") from exc
        elif node.setting("uses") is None:
            try:
                action = ModelNode(node, model)
            except Exception as exc:
                raise _error(BuildError, "build.model", str(exc), node.header_span, "build") from exc
        else:
            action = _bind(node, "uses", registry, spec.path.parent, model)
        if isinstance(action, (ModelNode, ToolNode, RequestInputNode)) and "messages" not in builder.channels:
            raise _error(BuildError, "build.messages", f"Node {node.name!r} requires a Schema with messages", node.header_span, "build")
        actions[node.name] = action
        try:
            destinations = tuple(set(action.routes.values())) if isinstance(action, ModelNode) and action.routes else None
            builder.add_node(node.name, action, destinations=destinations,
                             metadata=metadata(spec, node, scope=_scope) if tracing else
                             {"trace_graph_version": None, "trace_node": None})
            if tracing:
                guard_registered_node(builder, node.name)
        except Exception as exc:
            raise _error(BuildError, "build.node", f"Cannot add node {node.name!r}: {exc}", node.header_span, "build") from exc

    builder.add_edge(START, spec.entry)
    for node in spec.nodes:
        records = node.transitions.records if node.transitions else ()
        conditional = bool(records and records[0].key != "@Default")
        if node.setting("router") is not None and not conditional:
            raise _error(BuildError, "build.router", "@router requires a conditional transition table", _setting(node, "router").span, "build")
        if conditional and any(r.key in {"@ToolCalls", "@Otherwise"} for r in records):
            router = _bind(node, "router", registry, spec.path.parent, model) if node.setting("router") is not None else None
            ordinary = [r for r in records if not r.key.startswith("@")]
            if ordinary and router is None and not isinstance(actions[node.name], ModelNode):
                raise _error(BuildError, "build.route_source", "Named routes require @router for this execution binding", node.transitions.span, "build")
            builder.add_conditional_edges(
                node.name, signal_router(node, router, implicit_text=isinstance(actions[node.name], ModelNode)),
                {r.key: END if r.target == "@End" else r.target for r in records},
            )
        elif conditional:
            if node.setting("router") is None and isinstance(actions[node.name], ModelNode):
                continue  # The builtin returns native Command(update=..., goto=table[key]).
            if node.setting("router") is None:
                raise _error(BuildError, "build.route_source", f"Node {node.name!r} needs @router: this execution binding has no implicit route-key protocol", node.transitions.span, "build")
            router = _bind(node, "router", registry, spec.path.parent, model)
            path_map = {r.key: END if r.target == "@End" else r.target for r in records}
            try:
                builder.add_conditional_edges(node.name, _checked_router(router, node, records), path_map)
            except Exception as exc:
                raise _error(BuildError, "build.router", str(exc), _setting(node, "router").span, "build") from exc
        elif records:
            target = records[0].target
            builder.add_edge(node.name, END if target == "@End" else target)
        # No table adds no DSL successor; native Command.goto remains available.
    return builder
