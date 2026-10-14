from operator import add
from typing import Annotated
from langgraph.graph import MessagesState
from langgraph.types import Command, Send
from langchain_core.messages import HumanMessage, RemoveMessage


class State(MessagesState):
    results: Annotated[list[dict], add]


def dispatch(state):
    original = state["messages"][-1]
    documents = [text.strip() for text in original.text.split("\n---\n") if text.strip()]
    if not documents:
        raise ValueError("No documents provided")
    # The original large batch is not forwarded to every worker or the final
    # model; summaries are retained separately by a native reducer.
    return Command(update={"messages": [RemoveMessage(id=original.id)]},
        goto=[Send("Summarize", {"messages": [HumanMessage(content=text)], "index": index})
              for index, text in enumerate(documents, 1)])


def ordered_results(state):
    return {"documents": sorted(state["results"], key=lambda item: item["index"])}
