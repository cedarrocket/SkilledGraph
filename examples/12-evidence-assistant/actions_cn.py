import json
import re
from langgraph.graph import MessagesState
from langchain_core.messages import AIMessage, HumanMessage


class State(MessagesState):
    attempts: int
    validation: str


def verify(state):
    sources = set()
    searched = False
    for message in state["messages"]:
        if message.type == "tool" and message.name == "search_notes":
            searched = True
            for item in json.loads(message.content):
                sources.add(item["source"])
    reply = next(m.text for m in reversed(state["messages"]) if m.type == "ai")
    citations = set(re.findall(r"\[([^\]\n]+\.md)\]", reply))
    attempt = state.get("attempts", 0) + 1
    valid = searched and ((bool(citations) and citations <= sources) or (not sources and any(word in reply for word in ("不知道", "无资料", "no evidence"))))
    status = "valid" if valid else "retry" if attempt < 3 else "failed"
    update = {"attempts": attempt, "validation": status}
    if status == "retry":
        update["messages"] = [HumanMessage(content="引用校验失败：请先检索，再只引用工具实际返回的文件名；没有结果时说明无资料。")]
    return update


def route(state):
    return state["validation"]


def unverified(state):
    return {"messages": [AIMessage(content="未通过来源引用校验，请查看原始笔记后重试。当前答案不应作为已核实结论。") ]}
