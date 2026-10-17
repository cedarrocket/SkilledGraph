"""Read-only source dependency resolution, adapted from a DeepSeek draft.

只读子图依赖解析；基于 DeepSeek 草稿，修正路径、循环与诊断边界。
"""
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from .diagnostics import BuildError, Diagnostic
from .spec import GraphSpec


@dataclass(frozen=True)
class SourceTree:
    spec: GraphSpec
    children: Mapping[str, "SourceTree"]

    @property
    def requires_trace(self) -> bool:
        return bool(self.spec.config and self.spec.config.setting("trace") == "on") or any(
            child.requires_trace for child in self.children.values())


def resolve_tree(spec: GraphSpec) -> SourceTree:
    """Snapshot dependencies before importing bindings; no global graph cache.

    在导入绑定前读取所有依赖；不缓存跨构建的图或运行状态。
    """
    from .api import parse_graph

    # Cache lexical source paths: symlink aliases may have different relative
    # references. Canonical paths are used only to detect recursive inclusion.
    # 声明路径决定相对引用；规范路径只用于检测循环。
    cache = {spec.path: spec}

    def visit(current, ancestors):
        children = {}
        for node in current.nodes:
            if node.kind != "Subgraph":
                continue
            setting = next(s for s in node.settings if s.key == "source")
            path = (current.path.parent / Path(setting.value)).absolute()
            try:
                canonical = path.resolve()
            except OSError as exc:
                raise BuildError(Diagnostic("subgraph.source", str(exc), setting.value_span, "build")) from exc
            if canonical in ancestors:
                chain = " -> ".join(map(str, (*ancestors, canonical)))
                raise BuildError(Diagnostic("subgraph.cycle", f"Recursive subgraph reference: {chain}",
                                            setting.value_span, "build"))
            if path not in cache:
                try:
                    cache[path] = parse_graph(path)
                except OSError as exc:
                    raise BuildError(Diagnostic("subgraph.source", f"Cannot read subgraph {path}: {exc}",
                                                setting.value_span, "build")) from exc
            children[node.name] = visit(cache[path], (*ancestors, canonical))
        return SourceTree(current, MappingProxyType(children))

    return visit(spec, (spec.path.resolve(),))
