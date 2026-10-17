"""Default model execution policies, independent of Markdown parsing."""

import inspect
import json
from collections.abc import Mapping

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph._internal._runnable import RunnableCallable
from langgraph.graph import END
from langgraph.types import Command

from .diagnostics import Diagnostic, RoutingError


def material_messages(value):
    if value is None or (isinstance(value, list) and not value):
        return []
    if isinstance(value, BaseMessage):
        return [value]
    if isinstance(value, list) and all(isinstance(item, BaseMessage) for item in value):
        return value
    if isinstance(value, (dict, list)):
        try:
            value = json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            value = str(value)
    elif not isinstance(value, str):
        value = str(value)
    return [HumanMessage(content=value)]


class RequestInputNode(RunnableCallable):
    """Builtin text request; the Host supplies the native interrupt resume value."""

    def __init__(self, payload):
        if payload.startswith('"'):
            try:
                prompt = json.loads(payload)
            except json.JSONDecodeError as exc:
                raise ValueError("request_input quoted prompt must be a valid JSON string") from exc
            if not isinstance(prompt, str):
                raise ValueError("request_input prompt must be a string")
        else:
            prompt = payload
        if not prompt:
            raise ValueError("request_input requires a nonempty prompt")

        def request(state):
            from langgraph.types import interrupt
            answer = interrupt(prompt)
            if not isinstance(answer, str):
                raise TypeError("request_input resume value must be a string")
            return {"messages": [HumanMessage(content=answer)]}

        async def arequest(state):
            return request(state)

        super().__init__(request, arequest, name="request_input", trace=True)


class ModelNode(RunnableCallable):
    """A builtin policy; route decisions travel in native Command, never State."""

    def __init__(self, node, model, prepare=None):
        if model is None or not callable(getattr(model, "invoke", None)):
            raise ValueError(f"Node {node.name!r} requires a model with invoke(messages, config=...)")
        records = node.transitions.records if node.transitions else ()
        self.routes = ({r.key: END if r.target == "@End" else r.target for r in records}
                       if records and records[0].key != "@Default" and node.setting("router") is None
                       and not any(r.key in {"@ToolCalls", "@Otherwise"} for r in records) else {})

        routes = self.routes

        def inputs(state, materials):
            history = state.get("messages") if isinstance(state, Mapping) else getattr(state, "messages", None)
            if not isinstance(history, (list, tuple)):
                raise ValueError(f"Node {node.name!r} requires State.messages as a message sequence")
            return ([SystemMessage(content=node.prompt)] if node.prompt else []) + list(history) + materials

        def result(reply, materials):
            if not isinstance(reply, AIMessage):
                raise TypeError(f"Node {node.name!r}: model must return an AIMessage")
            update = {"messages": materials + [reply]}
            if not routes:
                return update
            key = reply.text.strip()
            if key not in routes:
                raise RoutingError(Diagnostic("routing.key", f"Node {node.name!r} returned route {key!r}; legal keys: {tuple(routes)!r}", node.transitions.span, "run"))
            return Command(update=update, goto=routes[key])

        def invoke(state, config: RunnableConfig):
            value = prepare(state) if prepare is not None else None
            if inspect.isawaitable(value):
                if inspect.iscoroutine(value):
                    value.close()
                raise TypeError("Async material function requires graph.ainvoke()")
            materials = material_messages(value)
            reply = model.invoke(inputs(state, materials), config=config)
            update = result(reply, materials)
            if routes:
                from .trace_integration import record_route
                key = reply.text.strip()
                record_route(config, key, [routes[key]])
            return update

        async def ainvoke(state, config: RunnableConfig):
            if not callable(getattr(model, "ainvoke", None)):
                raise TypeError("Async execution requires model.ainvoke()")
            value = prepare(state) if prepare is not None else None
            if inspect.isawaitable(value):
                value = await value
            materials = material_messages(value)
            reply = await model.ainvoke(inputs(state, materials), config=config)
            update = result(reply, materials)
            if routes:
                from .trace_integration import arecord_route
                key = reply.text.strip()
                await arecord_route(config, key, [routes[key]])
            return update

        super().__init__(invoke, ainvoke, name=node.name, trace=True)
