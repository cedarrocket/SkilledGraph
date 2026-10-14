from pathlib import Path
from uuid import uuid4
from langgraph.graph import MessagesState
from langchain_core.messages import AIMessage


class State(MessagesState):
    policy: str
    draft: str
    approved: bool
    output_dir: str
    artifact: str


def billing(state):
    return {"policy": "Billing policy: verify order and duplicate-charge records; refunds require human review, not a promise of completion."}


def technical(state):
    return {"policy": "Technical policy: collect reproduction steps, time and version; never request passwords or guarantee a fix deadline."}


def general(state):
    return {"policy": "General policy: respond concisely and request necessary clarification."}


def materials(state):
    return state["policy"]


def capture(state):
    return {"draft": state["messages"][-1].text}


def decide(state):
    return {"approved": state["messages"][-1].text.strip().lower() in {"yes", "是", "同意"}}


def route(state):
    return "approved" if state["approved"] else "rejected"


def save(state):
    if not state.get("approved"):
        raise ValueError("Draft has not been approved")
    directory = Path(state["output_dir"])
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / ("draft-" + str(uuid4()) + ".md")
    path.write_text(state["draft"], encoding="utf-8")
    return {"artifact": str(path), "messages": [AIMessage(content=f"Draft saved: {path}. No email sent.") ]}


def cancel(state):
    return {"messages": [AIMessage(content="Save cancelled; no file created and no email sent.") ]}
