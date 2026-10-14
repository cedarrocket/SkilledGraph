# M2: File Binding and Native Graph Construction

> Non-normative stage report. Current scope: [status](STATUS_en.md), [usage](USAGE_en.md).

Date: 2026-10-09. This stage implemented pure Python graphs; Prompt, pyfunction execution, and CLI were not yet implemented.

## Usage

```sh
python -m pip install -e '.[runtime]'
python -m unittest discover -s tests -v
```

```python
from skilledgraph import load_graph
graph = load_graph("examples/09-state-only/workflow_en.md")
assert graph.invoke({"value": 0, "events": []}) == {
    "value": 2, "events": ["incremented", "doubled"],
}
```

build takes path/GraphSpec and returns StateGraph for further add_node/add_edge/compile. load returns compiled graph and forwards compile_kwargs. Both accept native schemas/model/bindings without starting @host. M2 passed model to bindings, but did not yet invoke it.

## Binding and import lifetime

Mappings contain ordinary functions, not subclasses:

```python
def bind(payload, *, base_dir, node, model=None):
    # Immutable NodeSpec; acquire resources, not execute business work.
    return my_native_node
builder = build_graph(path, bindings={"custom": bind})
```

Same entry for uses/router; returns callable/native Runnable. Partial override retains builtins; unknown names fail. python returns original object/signature. pyfunction name was reserved and reported M3 incomplete unless explicitly overridden.

Last colon separates file/object. Graph-relative paths do not change cwd/sys.path. SHA256 of canonical absolute path creates isolated sys.modules names. Same-path references/graphs/concurrent builds share one cached import; same basename in different directories does not collide. Failures remove partial imports and preserve cause; RLock serializes loading.

No hot reload; restart after edits. Normal Python imports use existing environment, without adding file directory or package-relative semantics. Imports execute top-level code, so put business actions in functions. Builder invokes neither loaded callable nor Schema factories.

@state uses independent object loading, unaffected by registry overrides; explicit schema skips file declaration. Default is MessagesState. Schemas/reducers pass unchanged.

## Routing/native access

First node is entry; missing table adds no successor. Sole Default installs static edge. Router returns one exact string key without trimming; errors include node/value/legal keys/location. Router without conditional table fails construction.

Code binding had no implicit key protocol. Router reads merged State; wrapping preserves config/runtime injection, sync/async and input-Schema inference without rerunning callable. This depends on pinned internal RunnableCallable/coerce_to_runnable/branch inference; upgrades require reverification.

Command.goto and DSL edges both execute; no target-boundary restriction or cancellation. Business errors/interrupts propagate. Binding/build/compile add positions/cause; their errors and ParseError inherit SkilledGraphError.

Native node-name restrictions may be narrower, e.g. State-field collision; report build.node instead of renaming or narrowing syntax.

## Verification

markdown-it-py 3.0.0; optional langgraph 1.2.14/langchain-core 1.6.9. Core import/parser do not load runtime. Minimum Python 3.11, tested 3.14.4 only at this stage.

103 checks: 79 parser +24 integrations, covering native/DSL dual paths (08), message-free reducers (09), schema/context/input/output precedence, reducer replacement, invalid schemas, path spaces/colons, cache/concurrency/isolation/failure cleanup, no auto invocation, partial bindings, independent State, no Host loading, post-merge router/errors/dataclass inference/config/runtime async, editable Builder, compile parameters, checkpoint resume, error propagation, and fresh-process import isolation.

No blanket native compatibility claim. Models, text routes, pyfunction, Host/CLI, streaming/persistence/platform combinations awaited M3–M5. A Python 3.14 LangSmith deprecation warning did not affect results.
