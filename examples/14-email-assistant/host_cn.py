import tempfile
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from skilledgraph import load_graph
from skilledgraph.binding import load_file_object


def demo_reply(messages):
    if "TASK: EMAIL_CLASSIFY" in messages[0].text:
        source = messages[1].text.lower()
        return AIMessage(content="billing" if any(word in source for word in ("收费", "退款", "billing")) else
                         "technical" if any(word in source for word in ("故障", "error")) else "general")
    if "技术政策" in messages[-1].text:
        return AIMessage(content="您好，请提供发生时间、版本和复现步骤，我们会据此调查；请不要提供密码。")
    if "账单政策" in messages[-1].text:
        return AIMessage(content="您好，我们会协助核实此问题。请提供订单号和收费记录；退款需要人工审核，核实后再与您确认。")
    return AIMessage(content="您好，请补充具体问题和必要背景，我们会据此协助处理。")


def create_graph(graph_path, model):
    return load_graph(graph_path, model=model, compile_kwargs={"checkpointer": InMemorySaver()})


def main(graph_path, argv):
    helpers = {name: load_file_object(f"../support/practical_cn.py:{name}", base_dir=graph_path.parent)
               for name in ("arguments", "model_for", "request_text", "execute", "display")}
    args = helpers["arguments"](argv, "邮件分类、政策材料、人工确认和本地草稿保存")
    text = helpers["request_text"](args, "你好，我被重复收费了，想申请退款。")
    if not text.strip():
        return 0
    model = helpers["model_for"](graph_path, args, demo_reply)
    output = args.output or tempfile.mkdtemp(prefix="sgraph-email-drafts-")
    approval = args.approval if args.approval is not None else "yes" if args.demo else None
    result = helpers["execute"](create_graph(graph_path, model), {"messages": [HumanMessage(content=text)],
        "output_dir": str(output)}, approval=approval)
    helpers["display"](result)
    return 0
