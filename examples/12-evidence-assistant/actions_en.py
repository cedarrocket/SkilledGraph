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
    valid = searched and ((bool(citations) and citations <= sources) or (not sources and any(word in reply for word in ("do not know", "no evidence", "no evidence"))))
    status = "valid" if valid else "retry" if attempt < 3 else "failed"
    update = {"attempts": attempt, "validation": status}
    if status == "retry":
        update["messages"] = [HumanMessage(content="Citation validation failed: search first and cite only returned filenames; state no evidence if empty.")]
    return update


def route(state):
    return state["validation"]


def unverified(state):
    return {"messages": [AIMessage(content="Source citation validation failed; inspect original notes and retry. This answer is not verified.") ]}
