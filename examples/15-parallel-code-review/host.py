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
        return AIMessage(content="[Correctness] average([]) 会因 len(values)=0 导致除零。")
    if "TASK: REVIEW_SECURITY" in prompt:
        return AIMessage(content="[Security] os.system(user_command) 在输入不可信时可执行任意 shell 命令。")
    if "TASK: REVIEW_MAINTAINABILITY" in prompt:
        return AIMessage(content="[Maintainability] 应定义空输入行为，并隔离命令执行接口。")
    return AIMessage(content="优先修复：1. os.system 的不可信输入风险；2. average 的空列表除零。补充空输入测试，命令调用改为明确参数与白名单。")


def main(graph_path, argv):
    helpers = {name: load_file_object(f"../support/practical.py:{name}", base_dir=graph_path.parent)
               for name in ("arguments", "model_for", "request_text", "execute", "display")}
    args = helpers["arguments"](argv, "三分支并行代码审查与显式等待汇合")
    if args.data:
        text = args.data.read_text(encoding="utf-8")
    elif args.demo:
        text = (graph_path.parent / "sample.py").read_text(encoding="utf-8")
    else:
        text = helpers["request_text"](args, "")
    if not text.strip():
        return 0
    model = helpers["model_for"](graph_path, args, demo_reply)
    result = helpers["execute"](create_graph(graph_path, model), {"messages": [HumanMessage(content=text)]})
    helpers["display"](result)
    return 0
