import json
from langchain_core.messages import AIMessage, HumanMessage
from skilledgraph import load_graph
from skilledgraph.binding import load_file_object


def demo_reply(messages):
    metrics = json.loads(messages[-1].text)
    return AIMessage(content=json.dumps({k: metrics[k] for k in ("rows", "valid_total", "duplicate_ids", "invalid_rows")} |
        {"actions": ["Verify duplicate IDs before deduplication", "Correct invalid amounts", "Fill missing customers"]}, ensure_ascii=False))


def create_graph(graph_path, model):
    return load_graph(graph_path, model=model)


def main(graph_path, argv):
    helpers = {name: load_file_object(f"../support/practical_en.py:{name}", base_dir=graph_path.parent)
               for name in ("arguments", "model_for", "request_text", "execute", "display")}
    args = helpers["arguments"](argv, "CSV metrics, model suggestions and deterministic validation")
    text = helpers["request_text"](args, "Audit accounts and suggest cleaning.")
    if not text.strip():
        return 0
    model = helpers["model_for"](graph_path, args, demo_reply)
    result = helpers["execute"](create_graph(graph_path, model), {"messages": [HumanMessage(content=text)],
        "csv_path": str((args.data or graph_path.parent / "sample_en.csv").resolve())})
    helpers["display"](result)
    return 0
