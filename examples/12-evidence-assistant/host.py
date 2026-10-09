import json
import re
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from skilledgraph import load_graph
from skilledgraph.binding import load_file_object


def create_graph(graph_path, model, data=None):
    directory = (data or graph_path.parent / "notes").resolve()
    if not directory.is_dir():
        raise ValueError("Notes directory does not exist")
    @tool
    def search_notes(query: str) -> str:
        """Search local Markdown notes. Return JSON with source filename and content."""
        terms = set(re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]{2}", query.lower()))
        found = []
        for path in sorted(directory.glob("*.md")):
            if path.is_symlink():
                continue
            text = path.read_text(encoding="utf-8")
            score = sum(term in text.lower() for term in terms)
            if score:
                found.append((score, {"source": path.name, "text": text[:4000]}))
        return json.dumps([item for _, item in sorted(found, key=lambda pair: -pair[0])[:4]], ensure_ascii=False)
    return load_graph(graph_path, model=model.bind_tools([search_notes]), tools=[search_notes])


def demo_reply(messages):
    tools = [m for m in messages if m.type == "tool"]
    if not tools:
        return AIMessage(content="", tool_calls=[{"name": "search_notes", "args": {"query": "发布 回滚"}, "id": "notes-1", "type": "tool_call"}])
    items = json.loads(tools[-1].content)
    return AIMessage(content="\n".join(f'[{item["source"]}] {item["text"]}' for item in items) or "无资料，不知道。")


def main(graph_path, argv):
    common = load_file_object("../support/practical.py:arguments", base_dir=graph_path.parent)
    helpers = {name: load_file_object(f"../support/practical.py:{name}", base_dir=graph_path.parent)
               for name in ("model_for", "request_text", "execute", "display")}
    args = common(argv, "本地笔记检索与引用检查")
    text = helpers["request_text"](args, "发布前需要哪些检查？什么时候需要回滚？")
    if not text.strip():
        return 0
    model = helpers["model_for"](graph_path, args, demo_reply)
    result = helpers["execute"](create_graph(graph_path, model, args.data), {"messages": [HumanMessage(content=text)]})
    helpers["display"](result)
    return 0
