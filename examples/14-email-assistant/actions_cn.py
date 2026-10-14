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
    return {"policy": "账单政策：先核实订单号和重复收费记录；退款需要人工审核，不承诺已退款。"}


def technical(state):
    return {"policy": "技术政策：收集复现步骤、发生时间和版本；不要要求密码，不保证修复期限。"}


def general(state):
    return {"policy": "一般政策：简洁回应；不清楚的问题询问必要补充信息。"}


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
    return {"artifact": str(path), "messages": [AIMessage(content=f"已保存草稿：{path}。未发送邮件。") ]}


def cancel(state):
    return {"messages": [AIMessage(content="已取消保存，未生成文件，也未发送邮件。") ]}
