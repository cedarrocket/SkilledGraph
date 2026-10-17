"""Host-owned execution records; based on a DeepSeek-generated callback utility.

Host 持有的执行记录，基于 DeepSeek 生成的回调模块，经本地审查修正。
"""
import json
import threading
from dataclasses import asdict, dataclass, replace
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.callbacks import BaseCallbackHandler

from langgraph.types import Command, Send
from langgraph.errors import GraphInterrupt, ParentCommand

META_GRAPH_VERSION = "trace_graph_version"
META_NODE = "trace_node"
META_DEFAULT_TARGETS = "trace_default_targets"

EVENT_NODE_START = "node_start"
EVENT_NODE_END = "node_end"
EVENT_ROUTE = "route"
EVENT_SUMMARY = "summary"

STATUS_COMPLETED = "completed"
STATUS_ERROR = "error"
STATUS_INTERRUPTED = "interrupted"

SUMMARY_MAX = 300


def _meta(serialized: Optional[dict], metadata: Optional[dict]) -> dict:
    out: dict = {}
    if isinstance(serialized, dict):
        out.update(serialized)
    if isinstance(metadata, dict):
        out.update(metadata)
    return out


def _is_interrupt(err: BaseException) -> bool:
    return isinstance(err, GraphInterrupt)


def _normalize_summary(text: str) -> str:
    s = " ".join(str(text).splitlines())
    s = " ".join(s.split())
    if len(s) > SUMMARY_MAX:
        s = s[:SUMMARY_MAX]
    return s


def _targets_of(value: Any) -> List[str]:
    seq = value if isinstance(value, (list, tuple)) else (value,)
    out: List[str] = []
    for t in seq:
        if isinstance(t, str):
            out.append("@End" if t == "__end__" else t)
        elif Send is not None and isinstance(t, Send):
            node = getattr(t, "node", None)
            if isinstance(node, str):
                out.append(node)
    return out


def _command_parts(value: Any) -> Tuple[List[str], List[str], List[str], Optional[str]]:
    """Return (update_keys, goto_targets, send_nodes, graph_scope)."""
    updates: List[str] = []
    goto: List[str] = []
    sends: List[str] = []
    scope: Optional[str] = None

    if isinstance(value, dict):
        for k in value.keys():
            updates.append(str(k))
        return updates, goto, sends, scope

    items = value if isinstance(value, (list, tuple)) else (value,)
    for item in items:
        if not isinstance(item, Command):
            continue
        upd = item.update
        if isinstance(upd, dict):
            for k in upd.keys():
                updates.append(str(k))
        elif isinstance(upd, (list, tuple)):
            for pair in upd:
                if isinstance(pair, (list, tuple)) and pair:
                    updates.append(str(pair[0]))
        g = getattr(item, "goto", None)
        if g is not None:
            goto.extend(_targets_of(g))
        graph = getattr(item, "graph", None)
        if Command is not None and graph == Command.PARENT:
            scope = "PARENT"
    return updates, goto, sends, scope


def _find_commands(value: Any) -> List[Any]:
    """Only top-level control objects count; Command-valued State is data.

    只观察顶层控制对象，State 内的 Command 值仍是普通数据。
    """
    if isinstance(value, Command):
        return [value]
    if isinstance(value, (list, tuple)):
        return [item for item in value if isinstance(item, Command)]
    return []


@dataclass(frozen=True)
class TraceEvent:
    sequence: int
    invocation: str
    graph_version: Optional[str]
    node: str
    execution_id: str
    attempt: int
    event: str
    status: Optional[str] = None
    updates: Tuple[str, ...] = ()
    error_type: Optional[str] = None
    route_key: Optional[str] = None
    route_targets: Tuple[str, ...] = ()
    default_targets: Tuple[str, ...] = ()
    summary: Optional[str] = None
    graph_scope: Optional[str] = None
    source: Optional[str] = None
    explicit: bool = False
    graph_path: Tuple[str, ...] = ()
    graph_source: Optional[str] = None
    parent_execution_id: Optional[str] = None


@dataclass
class Frame:
    run_id: str
    parent_run_id: Optional[str]
    invocation: Optional[str]
    node: Optional[str]
    graph_version: Optional[str]
    execution_id: Optional[str]
    attempt: int = 0
    started: bool = False
    default_targets: Tuple[str, ...] = ()
    explicit_targets: Optional[Tuple[str, ...]] = None
    graph_path: Tuple[str, ...] = ()
    graph_source: Optional[str] = None
    parent_execution_id: Optional[str] = None


class TraceRecorder(BaseCallbackHandler):
    """Metadata-only LangGraph trace recorder."""

    raise_error = True
    run_inline = True

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._events: List[TraceEvent] = []
        self._seq = 0
        self._frames: Dict[str, Frame] = {}
        self._attempts: Dict[str, int] = {}

    @property
    def events(self) -> Tuple[TraceEvent, ...]:
        with self._lock:
            return tuple(self._events)

    def _record(self, event: TraceEvent) -> None:
        # Preserve hierarchical identity even when a source is used twice.
        # 同一源文件被多处调用时保留调用层级。
        frame = self._frames[event.execution_id]
        self._events.append(replace(event, graph_path=frame.graph_path,
                                    graph_source=frame.graph_source,
                                    parent_execution_id=frame.parent_execution_id))

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def _owner_for_run(self, run_id: str) -> Optional[Frame]:
        cur: Optional[str] = run_id
        seen: set = set()
        while cur and cur not in seen:
            seen.add(cur)
            f = self._frames.get(cur)
            if f is None:
                return None
            if f.started and f.execution_id is not None:
                return f
            cur = f.parent_run_id
        return None

    def on_chain_start(self, serialized, inputs, *, run_id, parent_run_id=None, metadata=None, tags=None, **kwargs):
        rid = str(run_id)
        pid = str(parent_run_id) if parent_run_id is not None else None
        md = _meta(serialized, metadata)
        cb_name = kwargs.get("name")

        graph_path = tuple(md.get("trace_graph_path") or ())
        graph_source = md.get("trace_graph_source")
        graph_version = md.get(META_GRAPH_VERSION)
        has_gv = isinstance(graph_version, str) and bool(graph_version)
        node = md.get(META_NODE) if isinstance(md.get(META_NODE), str) else None

        with self._lock:
            parent = self._frames.get(pid) if pid else None

            if parent is not None:
                invocation = parent.invocation or rid
            else:
                invocation = rid

            is_owner = (
                has_gv
                and isinstance(node, str)
                and bool(node)
                and isinstance(cb_name, str)
                and cb_name == node
            )
            if is_owner:
                lgn = md.get("langgraph_node")
                if lgn is not None and lgn != node:
                    is_owner = False

            # Nested runnables inherit node metadata; only the outer task owns it.
            # 内部 Runnable 继承元数据，但不代表节点再次执行。
            ancestor = self._owner_for_run(pid) if pid else None
            if (ancestor is not None and ancestor.graph_version == graph_version
                    and ancestor.graph_path == graph_path and ancestor.graph_source == graph_source):
                is_owner = False
            execution_id: Optional[str] = None
            attempt = 0
            default_targets: Tuple[str, ...] = ()
            if is_owner:
                execution_id = rid
                akey = f"{invocation}|{graph_source}|{graph_path}|{graph_version}|{node}"
                attempt = self._attempts.get(akey, 0) + 1
                self._attempts[akey] = attempt
                dt = md.get(META_DEFAULT_TARGETS)
                if isinstance(dt, (list, tuple)):
                    default_targets = tuple(str(t) for t in dt if isinstance(t, str))

            frame = Frame(
                run_id=rid,
                parent_run_id=pid,
                invocation=invocation,
                node=node if is_owner else None,
                graph_version=graph_version if has_gv else (
                    parent.graph_version if parent else None
                ),
                execution_id=execution_id,
                attempt=attempt,
                started=is_owner,
                default_targets=default_targets,
                graph_path=graph_path,
                graph_source=graph_source,
                parent_execution_id=ancestor.execution_id if ancestor else None,
            )
            self._frames[rid] = frame

            if is_owner:
                self._record(TraceEvent(
                    sequence=self._next_seq(),
                    invocation=invocation or "",
                    graph_version=graph_version,
                    node=node or "",
                    execution_id=execution_id or "",
                    attempt=attempt,
                    event=EVENT_NODE_START,
                ))

    def on_chain_end(self, outputs, *, run_id, parent_run_id=None, **kwargs):
        rid = str(run_id)
        with self._lock:
            frame = self._frames.get(rid)
            if frame is None:
                return
            if not frame.started:
                self._drop_frame(frame)
                return
            self._finish_node(frame, outputs, STATUS_COMPLETED, None)

    def on_chain_error(self, error, *, run_id, parent_run_id=None, **kwargs):
        rid = str(run_id)
        with self._lock:
            frame = self._frames.get(rid)
            if frame is None:
                return
            if not frame.started:
                self._drop_frame(frame)
                return
            if isinstance(error, ParentCommand):
                self._finish_node(frame, error.args[0], STATUS_COMPLETED, None)
                return
            interrupted = _is_interrupt(error)
            status = STATUS_INTERRUPTED if interrupted else STATUS_ERROR
            self._finish_node(frame, None, status, type(error).__name__)

    def _finish_node(self, frame: Frame, outputs, status: str, error_type: Optional[str]) -> None:
        updates: List[str] = []
        command_routes = []

        if outputs is not None:
            if isinstance(outputs, dict):
                for k in outputs.keys():
                    updates.append(str(k))
            commands = _find_commands(outputs)
            for cmd in commands:
                u, g, s, sc = _command_parts(cmd)
                updates.extend(u)
                if g or s or sc:
                    command_routes.append((g + s, sc))

        invocation = frame.invocation or ""
        gv = frame.graph_version
        node = frame.node or ""
        exec_id = frame.execution_id or ""
        attempt = frame.attempt

        self._record(TraceEvent(
            sequence=self._next_seq(),
            invocation=invocation,
            graph_version=gv,
            node=node,
            execution_id=exec_id,
            attempt=attempt,
            event=EVENT_NODE_END,
            status=status,
            updates=tuple(sorted(set(updates))),
            error_type=error_type,
        ))

        # Static default route on normal completion (independent of Command goto)
        if (status == STATUS_COMPLETED and frame.default_targets
                and not any(scope == "PARENT" for _, scope in command_routes)):
            self._record(TraceEvent(
                sequence=self._next_seq(),
                invocation=invocation,
                graph_version=gv,
                node=node,
                execution_id=exec_id,
                attempt=attempt,
                event=EVENT_ROUTE,
                route_key="@Default",
                route_targets=frame.default_targets,
                default_targets=frame.default_targets,
                source="default",
            ))

        for actual_clean, scope in command_routes:
            emit_route = bool(scope) or tuple(actual_clean) != frame.explicit_targets
            if emit_route:
                self._record(TraceEvent(
                    sequence=self._next_seq(),
                    invocation=invocation,
                    graph_version=gv,
                    node=node,
                    execution_id=exec_id,
                    attempt=attempt,
                    event=EVENT_ROUTE,
                    route_targets=tuple(actual_clean),
                    default_targets=frame.default_targets,
                    graph_scope=scope,
                    source="command",
                ))

        self._drop_frame(frame)

    def _drop_frame(self, frame):
        if frame.parent_run_id is None:
            self._frames = {k: v for k, v in self._frames.items()
                            if v.invocation != frame.invocation}
            prefix = f"{frame.invocation}|"
            self._attempts = {k: v for k, v in self._attempts.items()
                              if not k.startswith(prefix)}
        else:
            self._frames.pop(frame.run_id, None)

    def on_custom_event(self, name, data, *, run_id=None, tags=None, metadata=None, **kwargs):
        if run_id is None:
            return
        rid = str(run_id)
        with self._lock:
            owner = self._owner_for_run(rid)
            if owner is None or owner.execution_id is None:
                return
            invocation = owner.invocation or ""
            gv = owner.graph_version
            node = owner.node or ""
            exec_id = owner.execution_id
            attempt = owner.attempt

            if name == "trace_route":
                if not isinstance(data, dict):
                    return
                key = data.get("key") if isinstance(data.get("key"), str) else None
                targets = data.get("targets")
                tlist: List[str] = []
                if isinstance(targets, (list, tuple)):
                    for t in targets:
                        if isinstance(t, str):
                            tlist.append("@End" if t == "__end__" else t)
                source = data.get("source") if isinstance(data.get("source"), str) else None
                owner.explicit_targets = tuple(tlist)
                self._record(TraceEvent(
                    sequence=self._next_seq(),
                    invocation=invocation,
                    graph_version=gv,
                    node=node,
                    execution_id=exec_id,
                    attempt=attempt,
                    event=EVENT_ROUTE,
                    route_key=key,
                    route_targets=tuple(tlist),
                    default_targets=owner.default_targets,
                    source=source,
                    explicit=True,
                ))
            elif name == "trace_summary":
                if not isinstance(data, dict):
                    return
                summary = data.get("summary")
                if not isinstance(summary, str):
                    return
                self._record(TraceEvent(
                    sequence=self._next_seq(),
                    invocation=invocation,
                    graph_version=gv,
                    node=node,
                    execution_id=exec_id,
                    attempt=attempt,
                    event=EVENT_SUMMARY,
                    summary=_normalize_summary(summary),
                ))

    def render(self, invocation: Optional[str] = None) -> str:
        with self._lock:
            events = list(self._events)
        if invocation is not None:
            events = [e for e in events if e.invocation == invocation]
        lines: List[str] = []
        current_inv: Optional[str] = None
        grouped: Dict[Tuple[str, str, str, int], List[TraceEvent]] = {}
        order: List[Tuple[str, str, str, int]] = []
        for ev in events:
            k = (ev.invocation, ev.graph_version or "", ev.execution_id, ev.attempt)
            if k not in grouped:
                grouped[k] = []
                order.append(k)
            grouped[k].append(ev)
        for inv, gv, exec_id, attempt in order:
            if inv != current_inv:
                current_inv = inv
                lines.append(f"invocation {inv}")
            evs = grouped[(inv, gv, exec_id, attempt)]
            node = evs[0].node
            status = None
            error_type = None
            updates: List[str] = []
            summary = None
            routes: List[TraceEvent] = []
            for ev in evs:
                if ev.event == EVENT_NODE_END:
                    status = ev.status
                    error_type = ev.error_type
                    if ev.updates:
                        updates = list(ev.updates)
                elif ev.event == EVENT_SUMMARY:
                    summary = ev.summary
                elif ev.event == EVENT_ROUTE:
                    routes.append(ev)
            label = " / ".join((*evs[0].graph_path, node))
            parts = [f"  {label} attempt={attempt}"]
            if gv:
                short = gv[:8]
                parts.append(f"version={short}")
            parts.append(f"entry={evs[0].sequence}")
            if status:
                parts.append(f"status={status}")
            if error_type:
                parts.append(f"error={error_type}")
            if updates:
                parts.append("updates=" + ",".join(updates))
            if summary:
                parts.append(f"summary={summary}")
            lines.append(" ".join(parts))
            for ev in routes:
                r = ["    route"]
                if ev.route_key is not None:
                    r.append(f"key={ev.route_key}")
                r.append("targets=" + ",".join(ev.route_targets) if ev.route_targets else "targets=")
                if ev.source:
                    r.append(f"source={ev.source}")
                if ev.explicit:
                    r.append("explicit=true")
                if ev.graph_scope:
                    r.append(f"scope={ev.graph_scope}")
                lines.append(" ".join(r))
        return "\n".join(lines)

    def save_jsonl(self, path: str) -> None:
        with self._lock:
            events = list(self._events)
        with open(path, "w", encoding="utf-8") as fh:
            for ev in events:
                rec = asdict(ev)
                for k, v in list(rec.items()):
                    if isinstance(v, tuple):
                        rec[k] = list(v)
                fh.write(json.dumps(rec, sort_keys=True) + "\n")
