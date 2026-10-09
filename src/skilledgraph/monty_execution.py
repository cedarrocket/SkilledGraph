"""Optional Monty execution: no host callbacks, mounts, or CPython fallback."""
import json
from pathlib import Path

DEFAULT_LIMITS = {'max_memory': 32 * 1024 * 1024, 'max_feed_duration_secs': 1.0,
                  'max_turn_duration_secs': 1.0, 'max_recursion_depth': 100,
                  'max_suspensions': 10, 'max_total_sleep_secs': 0.1}


def bounded_json(value, *, limit=1024*1024, default=None, truncate=False):
    """Stop JSON traversal at the output limit, including shared/exponential lists."""
    encoder=json.JSONEncoder(ensure_ascii=False,allow_nan=False,default=default)
    parts=[]; remaining=limit
    for chunk in encoder.iterencode(value):
        encoded=chunk.encode('utf-8')
        if len(encoded)>remaining:
            if not truncate: raise ValueError('Monty JSON data exceeds output/input limit')
            parts.append(encoded[:remaining].decode('utf-8',errors='ignore'))
            return ''.join(parts)+'\n[output truncated]'
        parts.append(chunk)
        remaining-=len(encoded)
    return ''.join(parts)


def run_monty(code, *, inputs=None, limits=None, capture_output=False):
    if not isinstance(code, str) or len(code.encode('utf-8')) > 20000:
        raise ValueError('Monty source must be at most 20000 UTF-8 bytes')
    from pydantic_monty import Monty
    # JSON data only: never grant sandbox code access to live host objects.
    values = json.loads(bounded_json(inputs or {}))
    output=[]; size=0; truncated=False
    def capture(stream, text):
        nonlocal size, truncated
        remaining=max(0,12000-size)
        output.append(text[:remaining]) if remaining else None
        size+=min(len(text),remaining)
        truncated=truncated or len(text)>remaining
    with Monty() as pool:
        with pool.checkout(limits=DEFAULT_LIMITS if limits is None else limits) as session:
            result=session.feed_run(code, inputs=values, print_callback=capture)
    return {'result':result,'stdout':''.join(output),'truncated':truncated} if capture_output else result


def bind_monty(payload, *, base_dir, node, model=None):
    """monty:FILE runs a bounded snippet with JSON state, returning a State patch or router key."""
    if not (payload.startswith(('./', '../')) or Path(payload).is_absolute()):
        raise ValueError('monty requires an explicit file path')
    path = (Path(base_dir) / payload).resolve()
    code = path.read_text(encoding='utf-8')
    if len(code.encode()) > 20000:
        raise ValueError('Monty source exceeds 20000 bytes')
    def encode(value):
        if hasattr(value, 'model_dump'):
            return value.model_dump(mode='json')
        raise TypeError('Monty state must contain JSON data or Pydantic messages')
    def execute(state):
        data = json.loads(bounded_json(state, default=encode))
        result = run_monty(code, inputs={'state': data})
        if result is None:
            return {}
        if not isinstance(result, (dict,str)):
            raise TypeError('Monty must return a State update dict, router string or None')
        return json.loads(bounded_json(result))
    return execute
