def increment(state):
    return {"value": state["value"] + 1, "events": ["incremented"]}


def double(state):
    return {"value": state["value"] * 2, "events": ["doubled"]}
