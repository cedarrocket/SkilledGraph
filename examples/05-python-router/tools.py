from langchain_core.messages import AIMessage


def inspect(state):
    status = "ready" if state["messages"] else "missing"
    text = "已收到待处理输入。" if status == "ready" else "尚未收到输入。"
    return {"status": status, "messages": [AIMessage(content=text)]}


def route(state) -> str:
    return state["status"]
