"""File loading and builtin execution bindings; no graph runtime imports."""

import hashlib
import importlib.util
import keyword
from pathlib import Path
import sys
from threading import RLock

_import_lock = RLock()


def load_file_object(payload: str, *, base_dir: Path):
    """Load FILE:ENTRY once per canonical path, like a regular Python import.

    Does not change cwd or sys.path, expand variables, or call the loaded object.
    Exceptions retain their original cause when reported by the graph builder.
    """
    filename, separator, entry = payload.rpartition(":")
    if not separator or not entry.isidentifier() or keyword.iskeyword(entry):
        raise ValueError("Expected FILE:ENTRY with a simple Python object name")
    path = Path(filename)
    if not (filename.startswith(("./", "../")) or path.is_absolute()):
        raise ValueError("FILE must start with ./ or ../, or be an absolute path")
    path = (base_dir / path).resolve()
    module_name = "_skilledgraph_file_" + hashlib.sha256(str(path).encode()).hexdigest()
    with _import_lock:
        module = sys.modules.get(module_name)
        if module is None:
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot load Python file: {path}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            try:
                spec.loader.exec_module(module)
            except BaseException:
                sys.modules.pop(module_name, None)
                raise
        return getattr(module, entry)


def bind_python(payload, *, base_dir, node, model=None):
    """Return the original native node/router object, without invoking it."""
    return load_file_object(payload, base_dir=base_dir)


def bind_pyfunction(payload, *, base_dir, node, model=None):
    from .execution import ModelNode

    prepare = load_file_object(payload, base_dir=base_dir)
    if not callable(prepare):
        raise TypeError("pyfunction entry must be callable")
    return ModelNode(node, model, prepare)


def bind_request_input(payload, *, base_dir, node, model=None):
    from .execution import RequestInputNode

    return RequestInputNode(payload)


def bind_monty(payload, **kwargs):
    from .monty_execution import bind_monty as bind
    return bind(payload, **kwargs)


def builtin_bindings():
    return {"python": bind_python, "pyfunction": bind_pyfunction,
            "request_input": bind_request_input, "monty": bind_monty}
