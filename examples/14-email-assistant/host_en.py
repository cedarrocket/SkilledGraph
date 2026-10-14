import tempfile
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from skilledgraph import load_graph
from skilledgraph.binding import load_file_object


def demo_reply(messages):
    if "TASK: EMAIL_CLASSIFY" in messages[0].text:
        source = messages[1].text.lower()
        return AIMessage(content="billing" if any(word in source for word in ("charge", "refund", "billing")) else
                         "technical" if any(word in source for word in ("fault", "error")) else "general")
    if "Technical policy" in messages[-1].text:
        return AIMessage(content="Hello, please provide time, version and reproduction steps for investigation; do not provide passwords.")
    if "Billing policy" in messages[-1].text:
        return AIMessage(content="Hello, we will investigate. Provide order and charge records; refunds require human review and confirmation after verification.")
    return AIMessage(content="Hello, please provide the issue and relevant context so we can help.")


def create_graph(graph_path, model):
    return load_graph(graph_path, model=model, compile_kwargs={"checkpointer": InMemorySaver()})


def main(graph_path, argv):
    helpers = {name: load_file_object(f"../support/practical_en.py:{name}", base_dir=graph_path.parent)
               for name in ("arguments", "model_for", "request_text", "execute", "display")}
    args = helpers["arguments"](argv, "Email classification, policy material, human confirmation and local drafts")
    text = helpers["request_text"](args, "Hello, I was charged twice and would like a refund.")
    if not text.strip():
        return 0
    model = helpers["model_for"](graph_path, args, demo_reply)
    output = args.output or tempfile.mkdtemp(prefix="sgraph-email-drafts-")
    approval = args.approval if args.approval is not None else "yes" if args.demo else None
    result = helpers["execute"](create_graph(graph_path, model), {"messages": [HumanMessage(content=text)],
        "output_dir": str(output)}, approval=approval)
    helpers["display"](result)
    return 0
