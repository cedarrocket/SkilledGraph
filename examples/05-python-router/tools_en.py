from langchain_core.messages import AIMessage


def inspect(state):
    status = "ready" if state["messages"] else "missing"
    text = "Input received for processing." if status == "ready" else "No input received yet."
    return {"status": status, "messages": [AIMessage(content=text)]}


def route(state) -> str:
    return state["status"]
