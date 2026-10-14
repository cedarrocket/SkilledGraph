from langchain_core.messages import AnyMessage
from typing_extensions import TypedDict


class State(TypedDict):
    # 不声明 add_messages：节点的新消息更新覆盖原值。
    messages: list[AnyMessage]
