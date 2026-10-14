from langchain_core.messages import AIMessage, HumanMessage
from skilledgraph import build_graph
from skilledgraph.binding import load_file_object


def create_graph(graph_path, model):
    builder = build_graph(graph_path, model=model)
    branches = ["Correctness", "Security", "Maintainability"]
    for name in branches:
        builder.add_edge("Start", name)
    builder.add_edge(branches, "Report")
    return builder.compile()


def demo_reply(messages):
    prompt = messages[0].text
    if "TASK: REVIEW_CORRECTNESS" in prompt:
        return AIMessage(content="[Correctness] average([]) divides by zero because len(values)=0.")
    if "TASK: REVIEW_SECURITY" in prompt:
        return AIMessage(content="[Security] os.system(user_command) can execute arbitrary commands when input is untrusted.")
    if "TASK: REVIEW_MAINTAINABILITY" in prompt:
        return AIMessage(content="[Maintainability] Define empty-input behavior and isolate command execution.")
    return AIMessage(content="Priorities: 1. untrusted os.system input; 2. average([]) division by zero. Add empty-input tests and explicit command parameters/allowlist.")


def main(graph_path, argv):
    helpers = {name: load_file_object(f"../support/practical_en.py:{name}", base_dir=graph_path.parent)
               for name in ("arguments", "model_for", "request_text", "execute", "display")}
    args = helpers["arguments"](argv, "Three-way concurrent code review with an explicit join")
    if args.data:
        text = args.data.read_text(encoding="utf-8")
    elif args.demo:
        text = (graph_path.parent / "sample_en.py").read_text(encoding="utf-8")
    else:
        text = helpers["request_text"](args, "")
    if not text.strip():
        return 0
    model = helpers["model_for"](graph_path, args, demo_reply)
    result = helpers["execute"](create_graph(graph_path, model), {"messages": [HumanMessage(content=text)]})
    helpers["display"](result)
    return 0
