import argparse
import json
import sys
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig, RunnableLambda
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from skilledgraph import load_graph
from skilledgraph.binding import load_file_object
from sgraph_chat_host.terminal_cn import terminal_reader


@tool
def calculate(a: float, b: float, operation: str = 'add') -> float:
    """Calculate two numbers: operation is add, subtract, multiply or divide."""
    if operation == 'add': return a + b
    if operation == 'subtract': return a - b
    if operation == 'multiply': return a * b
    if operation == 'divide': return a / b
    raise ValueError('Unsupported operation')


def create_graph(path, model, *, summarizer=None, checkpointer=None):
    actions = {name: load_file_object(f'./actions_cn.py:{name}', base_dir=path.parent)
               for name in ('split_history', 'validate_history')}
    summarizer = summarizer if summarizer is not None else model
    def bind(payload, *, node, **kwargs):
        if payload != 'compact': raise ValueError('Unknown memory action')
        def prepare(state):
            actions['validate_history'](state['messages'])
            older, recent = actions['split_history'](state)
            if not older: raise ValueError('No older complete turns to compact')
            material = json.dumps([{'role': m.type, 'text': m.text,
                'tool_calls': getattr(m, 'tool_calls', []),
                'tool_call_id': getattr(m, 'tool_call_id', None)} for m in older], ensure_ascii=False)
            return recent, [SystemMessage(content=node.prompt), HumanMessage(content=material)]
        def finish(state, recent, answer):
            if not answer.text.strip() or answer.tool_calls:
                raise ValueError('Summary must be nonempty text without tool calls')
            summary = HumanMessage(content='历史摘要（有损，仅供参考）：\n' + answer.text,
                additional_kwargs={'memory_summary': True}, id=str(uuid4()))
            replacement = [summary, *recent]
            # A longer "summary" is not accepted as successful compression.
            if sum(len(m.text) for m in replacement) >= sum(len(m.text) for m in state['messages']):
                raise ValueError('Summary did not reduce history size')
            return {'messages': {'operation': 'compact',
                     'expected_messages': [m.model_dump(mode='json') for m in state['messages']], 'replacement': replacement},
                    'compressions': state.get('compressions', 0) + 1}
        def invoke(state, config: RunnableConfig):
            recent, messages = prepare(state)
            return finish(state, recent, summarizer.invoke(messages, config=config))
        async def ainvoke(state, config: RunnableConfig):
            recent, messages = prepare(state)
            return finish(state, recent, await summarizer.ainvoke(messages, config=config))
        return RunnableLambda(invoke, afunc=ainvoke, name=node.name)
    return load_graph(path, model=model.bind_tools([calculate]), tools=[calculate],
        bindings={'memory': bind}, compile_kwargs={'checkpointer': checkpointer if checkpointer is not None else InMemorySaver()})


class Session:
    """Only new input is submitted; native checkpointer retains this thread."""
    def __init__(self, graph, *, budget_chars=6000, keep_turns=1, thread_id=None):
        if budget_chars <= 0 or keep_turns < 1: raise ValueError('Positive memory settings required')
        self.graph = graph
        self.config = {'configurable': {'thread_id': thread_id or str(uuid4())}, 'recursion_limit': 40}
        self.settings = {'budget_chars': budget_chars, 'keep_turns': keep_turns}

    def ask(self, text):
        return self.graph.invoke({'messages': [HumanMessage(content=text)], **self.settings}, self.config)

    async def aask(self, text):
        return await self.graph.ainvoke({'messages': [HumanMessage(content=text)], **self.settings}, self.config)


def demo_reply(messages):
    if messages[0].text.startswith('TASK: MEMORY_COMPACT'):
        return AIMessage(content='用户名林，偏好中文。计算 17+25=42。')
    last = messages[-1]
    if last.type == 'tool': return AIMessage(content='计算结果：' + last.text)
    if '17+25' in last.text:
        return AIMessage(content='', tool_calls=[{'name': 'calculate', 'args': {'a':17,'b':25}, 'id':str(uuid4()), 'type':'tool_call'}])
    if '名字' in last.text: return AIMessage(content='你叫林，偏好中文。')
    return AIMessage(content='已记录你的偏好。')


def main(graph_path, argv):
    parser = argparse.ArgumentParser(description='多轮 ReAct 与原生自定义 Reducer 压缩示例')
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--model')
    parser.add_argument('--budget-chars', type=int, default=6000)
    parser.add_argument('--keep-turns', type=int, default=1)
    parser.add_argument('--turn', action='append', help='可重复，每项是独立一轮；不提供则进入终端循环')
    args = parser.parse_args(argv)
    model_for = load_file_object('../support/practical_cn.py:model_for', base_dir=graph_path.parent)
    session = Session(create_graph(graph_path, model_for(graph_path, args, demo_reply)),
                      budget_chars=args.budget_chars, keep_turns=args.keep_turns)
    def run(text):
        result = session.ask(text)
        replies = [m.text for m in result['messages'] if m.type == 'ai' and m.text]
        print(replies[-1] if replies else '')
        print(f"[memory messages={len(result['messages'])}, compressions={result.get('compressions',0)}]", file=sys.stderr)
    if args.turn:
        for text in args.turn: run(text)
    elif args.demo:
        for text in ['我叫林，请用中文。'+ '这是用于触发压缩的无关测试材料。'*30, '计算17+25', '我的名字是什么？']:
            run(text)
    else:
        if not sys.stdin.isatty():
            parser.error('循环输入需要终端，或使用可重复的 --turn')
        with terminal_reader(sys.stdin, sys.stderr) as read:
            while True:
                try: text = read('Agent> ')
                except (EOFError, KeyboardInterrupt): break
                if text.strip() == '/exit': break
                if text.strip(): run(text)
    return 0
