"""Verify a restricted generated example, not a general Python sandbox."""
import ast
import json
from pathlib import Path
import sys

from langchain_core.messages import AIMessage, HumanMessage
from skilledgraph import load_graph, parse_graph

ALLOWED_IMPORTS = {
    'langgraph.graph': {'MessagesState'},
    'langchain_core.messages': {'HumanMessage', 'AIMessage'},
    'typing': {'Annotated', 'TypedDict'},
    'typing_extensions': {'TypedDict'},
}
ALLOWED_CALLS = {'len', 'sum', 'bool', 'str', 'int', 'list', 'dict', 'HumanMessage', 'AIMessage'}


def check_python(text):
    tree = ast.parse(text)
    for node in tree.body:
        if not isinstance(node, (ast.ImportFrom, ast.FunctionDef, ast.ClassDef)):
            raise ValueError('Only imports, State definition and functions at module scope')
        if isinstance(node, ast.ClassDef) and node.name != 'State':
            raise ValueError('Only State class allowed')
        if isinstance(node, ast.FunctionDef):
            if node.name not in {'inspect', 'route', 'materials'} or node.decorator_list:
                raise ValueError('Only undecorated inspect/route/materials functions allowed')
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level or node.module not in ALLOWED_IMPORTS:
                raise ValueError('Import outside this test allowlist')
            if any(n.name not in ALLOWED_IMPORTS[node.module] for n in node.names):
                raise ValueError('Imported symbol outside allowlist')
        elif isinstance(node, (ast.Import, ast.While, ast.For, ast.AsyncFunctionDef, ast.With)):
            raise ValueError('Unsupported construct in restricted test')
        elif isinstance(node, ast.Name) and node.id.startswith('__'):
            raise ValueError('Dunder names blocked')
        elif isinstance(node, ast.Attribute):
            if node.attr != 'get':
                raise ValueError('Only mapping.get attributes allowed')
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in ALLOWED_CALLS:
                continue
            if isinstance(node.func, ast.Attribute) and node.func.attr == 'get':
                continue
            raise ValueError('Function call outside test allowlist')
    return tree


class DemoModel:
    def __init__(self, numbers):
        self.numbers = numbers
        self.calls = []

    def invoke(self, messages, config=None):
        self.calls.append(messages)
        if self.numbers:
            material = json.loads(messages[-1].text)
            assert material == {'numbers': self.numbers}, material
            return AIMessage(content='sum:' + str(sum(self.numbers)))
        return AIMessage(content='Please supply numbers.')


def main():
    path = Path(sys.argv[1]).resolve()
    check_python((path.parent / 'actions_en.py').read_text(encoding='utf-8'))
    spec = parse_graph(path)
    assert spec.entry == 'Inspect'
    by_name = {n.name: n for n in spec.nodes}
    assert set(by_name) == {'Inspect', 'Report', 'Ask'}
    assert spec.config.setting('state') == 'python:./actions_en.py:State'
    assert spec.config.setting('host') is None
    inspect, report, ask = (by_name[name] for name in ('Inspect', 'Report', 'Ask'))
    assert inspect.setting('uses') == 'python:./actions_en.py:inspect'
    assert inspect.setting('router') == 'python:./actions_en.py:route'
    assert {(r.key, r.target) for r in inspect.transitions.records} == {('ready', 'Report'), ('missing', 'Ask')}
    assert report.setting('uses') == 'pyfunction:./actions_en.py:materials'
    assert ask.setting('uses') is None
    for node in (report, ask):
        assert [(r.key, r.target) for r in node.transitions.records] == [('@Default', '@End')]
    details=[]
    for numbers, expected_status, expected_text in [([1, 2, 3], 'ready', 'sum:6'), ([], 'missing', 'Please supply numbers.')]:
        model=DemoModel(numbers)
        graph=load_graph(spec, model=model)
        initial={'messages':[HumanMessage(content='Test request.')], 'numbers':numbers, 'status':'pending'}
        result=graph.invoke(initial, {'recursion_limit':8})
        assert result['status']==expected_status, result
        assert result['messages'][-1].text==expected_text
        assert len(model.calls)==1  # Inspect did not invoke; selected model node did.
        assert result['messages'][0].text=='Test request.'
        if numbers:
            assert len(result['messages'])==3  # initial + material + AI
            assert json.loads(result['messages'][-2].text)=={'numbers':numbers}
        else:
            assert len(result['messages'])==2  # initial + Ask AI, no material
        details.append({'numbers':numbers,'status':result['status'],'reply':expected_text,'model_calls':len(model.calls),'message_count':len(result['messages'])})
    print(json.dumps({'passed':True,'cases':details},ensure_ascii=False))


if __name__=='__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'passed':False,'error':f'{type(exc).__name__}: {exc}'},ensure_ascii=False))
        raise SystemExit(1)
