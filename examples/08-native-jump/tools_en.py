from typing import Literal

from langchain_core.messages import AIMessage
from langgraph.types import Command


def process(state) -> Command[Literal["Extra"]]:
    return Command(
        update={"messages": [AIMessage(content="Process finished.", id="process")]},
        goto="Extra",
    )


def report(state):
    return {"messages": [AIMessage(content="Report path finished.", id="report")]}


def extra(state):
    return {"messages": [AIMessage(content="Extra path finished.", id="extra")]}
