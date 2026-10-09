"""A custom non-chat Host, also callable directly from Python."""
from skilledgraph import load_graph


def main(graph_path, argv):
    if argv:
        raise ValueError("This example Host takes no arguments")
    graph = load_graph(graph_path)
    print(graph.invoke({"value": 0, "events": []}))
    return 0
