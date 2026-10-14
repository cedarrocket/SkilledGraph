from operator import add
from time import perf_counter, sleep
from typing import Annotated
from typing_extensions import TypedDict


class State(TypedDict):
    events: Annotated[list[dict], add]
    summary: str


def start(state):
    return {"events": [{"node": "Start", "at": perf_counter()}]}


def work(name, delay):
    started = perf_counter()
    sleep(delay)
    return {"events": [{"node": name, "start": started, "end": perf_counter()}]}


def left(state):
    return work("Left", 0.3)


def right(state):
    return work("Right", 0.3)


def right_last(state):
    return work("RightLast", 0.1)


def join(state):
    names = sorted(e["node"] for e in state["events"])
    return {"summary": "Joined: " + ", ".join(names),
            "events": [{"node": "Join", "at": perf_counter()}]}
