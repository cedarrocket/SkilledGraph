"""Concurrent business reducers: pure, order-independent, replay-idempotent."""
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.types import Overwrite


def merge_versions(left, right):
    result = dict(left)
    for key, value in right.items():
        previous = result.get(key)
        if previous is None or value['version'] > previous['version']:
            result[key] = dict(value)
        elif value['version'] == previous['version'] and value != previous:
            raise ValueError(f'Conflicting values at the same version: {key}')
    return {key: result[key] for key in sorted(result)}


def merge_events(left, right):
    result = dict(left)
    for key, value in right.items():
        if key in result and result[key] != value:
            raise ValueError(f'Event ID reused with different payload: {key}')
        result[key] = value
    return {key: result[key] for key in sorted(result)}


def union(left, right):
    return sorted(set(left) | set(right))


class State(TypedDict):
    records: Annotated[dict, merge_versions]
    events: Annotated[dict, merge_events]
    completed: Annotated[list[str], union]
    report: dict


def start(state): return {}


def source_a(state):
    return {'records': {'ticket': {'version':1,'status':'open'}},
            'events': {'e1': 3}, 'completed':['a']}


def source_b(state):
    return {'records': {'ticket': {'version':2,'status':'resolved'}},
            'events': {'e1': 3, 'e2': 5}, 'completed':['b']}


def report(state):
    return {'report': {'records':state['records'], 'total':sum(state['events'].values()),
            'completed':state['completed']}, 'events':Overwrite({})}
