from typing import Literal

from langchain_core.messages import AIMessage
from langgraph.types import Command


def process(state) -> Command[Literal["Extra"]]:
    return Command(
        update={"messages": [AIMessage(content="Process 完成。", id="process")]},
        goto="Extra",
    )


def report(state):
    return {"messages": [AIMessage(content="Report 路径完成。", id="report")]}


def extra(state):
    return {"messages": [AIMessage(content="Extra 路径完成。", id="extra")]}
