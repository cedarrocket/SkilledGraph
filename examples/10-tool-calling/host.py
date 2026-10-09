"""Offline, deterministic tool-calling example; no external model or MCP."""
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from skilledgraph import load_graph


@tool
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


class DemoModel:
    """Stand-in for a Host-provided model already bound to the add tool."""

    def invoke(self, messages, config=None):
        if isinstance(messages[-1], ToolMessage):
            return AIMessage(content=f"结果是 {messages[-1].content}")
        return AIMessage(content="", tool_calls=[
            {"name": "add", "args": {"a": 2, "b": 3}, "id": "demo-add", "type": "tool_call"},
        ])

    async def ainvoke(self, messages, config=None):
        return self.invoke(messages, config)


def main(graph_path, argv):
    if argv:
        raise ValueError("This offline example accepts no arguments")
    # Real model: bound_model = base_model.bind_tools([add])
    graph = load_graph(graph_path, model=DemoModel(), tools=[add])
    result = graph.invoke({"messages": [HumanMessage(content="2 + 3 等于多少？")]})
    for message in result["messages"]:
        print(f"{message.type}: {message.content}")
    return 0
