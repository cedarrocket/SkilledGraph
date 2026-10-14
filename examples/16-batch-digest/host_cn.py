from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig, RunnableLambda
from skilledgraph import load_graph
from skilledgraph.binding import load_file_object


def create_graph(graph_path, model):
    def bind_worker(payload, *, node, **kwargs):
        if payload != "summary":
            raise ValueError("Unknown worker action")
        def invoke(state, config: RunnableConfig):
            reply = model.invoke([SystemMessage(content=node.prompt), *state["messages"]], config=config)
            return {"results": [{"index": state["index"], "summary": reply.text, "evidence": state["messages"][-1].text[:600]}]}
        async def ainvoke(state, config: RunnableConfig):
            reply = await model.ainvoke([SystemMessage(content=node.prompt), *state["messages"]], config=config)
            return {"results": [{"index": state["index"], "summary": reply.text, "evidence": state["messages"][-1].text[:600]}]}
        return RunnableLambda(invoke, afunc=ainvoke, name=node.name)
    return load_graph(graph_path, model=model, bindings={"worker": bind_worker})


def demo_reply(messages):
    if "TASK: DIGEST_WORKER" in messages[0].text:
        return AIMessage(content=messages[-1].text)
    return AIMessage(content="待办：完成发布前测试 [文档1]；检查回滚预案 [文档1]；核实订单记录 [文档2]；增加空输入测试 [文档3]。\n未知：核实订单的完成日期、空输入测试负责人和完成日期。\n原文依据：Alice 负责周二发布；Bob 周一检查回滚预案；Carol 负责核实订单记录；评审日期为周五。")


def main(graph_path, argv):
    helpers = {name: load_file_object(f"../support/practical_cn.py:{name}", base_dir=graph_path.parent)
               for name in ("arguments", "model_for", "request_text", "execute", "display")}
    args = helpers["arguments"](argv, "动态批量文档摘要：--- 分隔文档")
    if args.data:
        text = args.data.read_text(encoding="utf-8")
    elif args.demo:
        text = (graph_path.parent / "sample_cn.md").read_text(encoding="utf-8")
    else:
        text = helpers["request_text"](args, "")
    if not text.strip():
        return 0
    model = helpers["model_for"](graph_path, args, demo_reply)
    result = helpers["execute"](create_graph(graph_path, model), {"messages": [HumanMessage(content=text)], "results": []})
    helpers["display"](result)
    return 0
