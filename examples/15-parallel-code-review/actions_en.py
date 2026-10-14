import ast


def start(state):
    return {}


def static_findings(state):
    source = state["messages"][0].text
    try:
        tree = ast.parse(source)
        calls = [(node.lineno, ast.unparse(node.func)) for node in ast.walk(tree) if isinstance(node, ast.Call)]
        return {"static_calls": calls, "note": "AST parsing only; user code was not executed. A call name alone does not prove a vulnerability."}
    except SyntaxError as exc:
        return {"syntax_error": {"line": exc.lineno, "message": exc.msg}}
