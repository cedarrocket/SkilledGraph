from langchain_core.messages import AnyMessage
from typing_extensions import TypedDict


class State(TypedDict):
    # No add_messages reducer: each new message update replaces the previous value.
    messages: list[AnyMessage]
