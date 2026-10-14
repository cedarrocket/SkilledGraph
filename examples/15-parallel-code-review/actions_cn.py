import ast


def start(state):
    return {}


def static_findings(state):
    source = state["messages"][0].text
    try:
        tree = ast.parse(source)
        calls = [(node.lineno, ast.unparse(node.func)) for node in ast.walk(tree) if isinstance(node, ast.Call)]
        return {"static_calls": calls, "note": "仅 AST 解析，没有执行用户代码；调用名本身不证明存在漏洞。"}
    except SyntaxError as exc:
        return {"syntax_error": {"line": exc.lineno, "message": exc.msg}}
