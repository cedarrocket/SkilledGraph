"""Small real-model Host; connection comes from the standard environment."""
import os
from langchain_core.tools import tool
from skilledgraph import load_graph
from sgraph_chat_host.host import create_model, run_chat


@tool
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


def main(graph_path, argv):
    if argv:
        raise ValueError("This Host takes configuration from environment variables")
    model = create_model(os.environ.get("SGRAPH_MODEL", "deepseek:deepseek-chat"),
                         base_dir=graph_path.parent)
    tools = [add]
    graph = load_graph(graph_path, model=model.bind_tools(tools), tools=tools)
    return run_chat(graph)
