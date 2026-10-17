"""Trace contracts exercised through real graphs / 真实图执行的追踪契约。"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import importlib.util
import io
import json
from operator import add
from pathlib import Path
import tempfile
from typing import Annotated
import unittest
from unittest.mock import patch

from skilledgraph import ParseError, parse_graph


class TraceSyntaxTests(unittest.TestCase):
    def test_config_values_and_scopes(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'g.md'
            for value in ('on', 'off'):
                p.write_text(f'# [Config]\n- **@trace**: {value}\n# [Node] A\n')
                self.assertEqual(parse_graph(p).config.setting('trace'), value)
            for text in ('# [Config]\n- **@trace**: true\n# [Node] A',
                         '# [Config]\n- **@trace**: ON\n# [Node] A',
                         '# [Config]\n- **@trace**: "on"\n# [Node] A',
                         '# [Config]\n- **@trace**: on\n- **@trace**: off\n# [Node] A',
                         '# [Node] A\n- **@trace**: on',
                         '- **@trace**: on\n# [Node] A'):
                p.write_text(text)
                with self.assertRaises(ParseError): parse_graph(p)


@unittest.skipUnless(importlib.util.find_spec('langgraph'), 'requires runtime')
class TraceTests(unittest.TestCase):
    def setUp(self):
        from skilledgraph import TraceRecorder
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'g.md'
        self.recorder = TraceRecorder()

    def graph(self, body, actions, *, trace='on', **kwargs):
        from skilledgraph import load_graph
        from typing_extensions import TypedDict
        class State(TypedDict):
            value: int
            items: Annotated[list, add]
        prefix = f'# [Config]\n- **@trace**: {trace}\n' if trace else ''
        self.path.write_text(prefix + body)
        return load_graph(self.path, state_schema=kwargs.pop('state_schema', State),
                          trace=self.recorder, bindings={'native':lambda payload, **kw: actions[payload]}, **kwargs)

    def node(self, name, transitions='- @Default -> @End', router=False):
        return (f'# [Node] {name}\n- **@uses**: native:{name}\n' +
                ('- **@router**: native:route\n' if router else '') +
                ('## [Transitions]\n' + transitions + '\n' if transitions else ''))

    def ends(self):
        return [e for e in self.recorder.events if e.event == 'node_end']

    def test_static_updates_privacy_and_off(self):
        g=self.graph(self.node('A'), {'A':lambda s:{'value':'SECRET_STATE_VALUE'}})
        self.assertEqual(g.invoke({'value':0}), {'value':'SECRET_STATE_VALUE','items':[]})
        self.assertEqual([(e.node,e.status,e.updates) for e in self.ends()], [('A','completed',('value',))])
        self.assertTrue(any(e.route_targets==('@End',) for e in self.recorder.events))
        self.assertNotIn('SECRET_STATE_VALUE', json.dumps([asdict(e) for e in self.recorder.events]))
        size=len(self.recorder.events)
        for mode in ('off',None):
            self.graph(self.node('A'),{'A':lambda s:{}},trace=mode).invoke({'value':0})
        self.assertEqual(len(self.recorder.events),size)
        out=Path(self.tmp.name)/'trace.jsonl';self.recorder.save_jsonl(out)
        self.assertEqual(len(out.read_text().splitlines()),size)
        self.assertIn('A',self.recorder.render())

    def test_required_receiver_and_native_builder(self):
        from skilledgraph import load_graph,build_graph
        from typing_extensions import TypedDict
        class S(TypedDict): value:int
        self.path.write_text('# [Config]\n- **@trace**: on\n'+self.node('A'))
        bindings={'native':lambda payload,**kw:lambda s:{'value':s['value']+1}}
        with self.assertRaisesRegex(ValueError,'TraceRecorder'):
            load_graph(self.path,state_schema=S,bindings=bindings)
        b=build_graph(self.path,state_schema=S,bindings=bindings)
        g=b.compile()
        with self.assertRaisesRegex(ValueError,'TraceRecorder'):g.invoke({'value':0})
        self.assertEqual(g.invoke({'value':0},config={'callbacks':[self.recorder]})['value'],1)
        self.assertEqual(len(self.ends()),1)

    def test_loop_routes_and_concurrent_invocations(self):
        actions={'A':lambda s:{'value':s['value']+1},'route':lambda s:'again' if s['value']<3 else 'done'}
        g=self.graph(self.node('A','- again -> A\n- done -> @End',True),actions)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:g.invoke({'value':0}),range(2)))
        self.assertEqual([r['value'] for r in results],[3,3])
        invocations={e.invocation for e in self.ends()};self.assertEqual(len(invocations),2)
        for inv in invocations:
            self.assertEqual([e.attempt for e in self.ends() if e.invocation==inv],[1,2,3])
            self.assertEqual([e.route_key for e in self.recorder.events if e.invocation==inv and e.event=='route'],['again','again','done'])

    def test_error_and_explicit_summary(self):
        from skilledgraph import trace_summary
        from langchain_core.runnables import RunnableConfig
        def action(state,config:RunnableConfig):
            trace_summary('checked rank\n'+('x'*400),config=config)
            raise ValueError('SECRET_EXCEPTION_TEXT')
        g=self.graph(self.node('A'),{'A':action})
        with self.assertRaisesRegex(ValueError,'SECRET_EXCEPTION_TEXT'):g.invoke({})
        self.assertEqual(self.ends()[0].status,'error')
        self.assertEqual(self.ends()[0].error_type,'ValueError')
        summary=next(e.summary for e in self.recorder.events if e.event=='summary')
        self.assertLessEqual(len(summary),300)
        self.assertNotIn('\n',summary)
        self.assertNotIn('SECRET_EXCEPTION_TEXT',self.recorder.render())

    def test_interrupt_resume(self):
        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.types import interrupt,Command
        def action(s):return {'value':interrupt('private prompt')}
        g=self.graph(self.node('A'),{'A':action},compile_kwargs={'checkpointer':InMemorySaver()})
        config={'configurable':{'thread_id':'trace-test'}}
        result=g.invoke({},config)
        self.assertIn('__interrupt__',result)
        self.assertEqual(self.ends()[0].status,'interrupted')
        self.assertEqual(g.invoke(Command(resume=7),config)['value'],7)
        self.assertEqual([e.status for e in self.ends()],['interrupted','completed'])
        self.assertNotIn('private prompt',self.recorder.render())

    def test_async_native_command_send(self):
        from langgraph.types import Command,Send
        async def dispatch(s):return Command(goto=[Send('Worker',{'item':'a'}),Send('Worker',{'item':'b'})])
        async def worker(s):return {'items':[s['item']]}
        g=self.graph(self.node('Dispatch','')+self.node('Worker',''), {'Dispatch':dispatch,'Worker':worker})
        result=asyncio.run(g.ainvoke({}))
        self.assertEqual(sorted(result['items']),['a','b'])
        self.assertEqual(sorted(e.attempt for e in self.ends() if e.node=='Worker'),[1,2])
        route=next(e for e in self.recorder.events if e.event=='route')
        self.assertEqual(route.route_targets,('Worker','Worker'))

    def test_model_implicit_route(self):
        from skilledgraph import load_graph
        from langchain_core.messages import AIMessage
        class Model:
            def invoke(self,messages,config=None):return AIMessage(content='ready')
            async def ainvoke(self,messages,config=None):return self.invoke(messages,config)
        self.path.write_text('# [Config]\n- **@trace**: on\n# [Node] Think\nsecret prompt\n## [Transitions]\n- ready -> @End\n')
        g=load_graph(self.path,model=Model(),trace=self.recorder)
        asyncio.run(g.ainvoke({'messages':[]}))
        routes=[e for e in self.recorder.events if e.event=='route']
        self.assertEqual(len(routes),1)
        self.assertEqual(routes[0].route_key,'ready')
        self.assertEqual(len(self.ends()),1)
        self.assertNotIn('secret prompt',self.recorder.render())

    def test_default_chat_host_collects(self):
        from sgraph_chat_host import host
        from langchain_core.messages import AIMessage
        class Model:
            def invoke(self,messages,config=None):return AIMessage(content='answer')
        self.path.write_text('# [Config]\n- **@trace**: on\n# [Node] Talk\n## [Transitions]\n- @Default -> @End\n')
        err=io.StringIO();out=io.StringIO()
        with patch.object(host,'create_model',return_value=Model()),patch('sys.stdin',io.StringIO('hello')),patch('sys.stdout',out),patch('sys.stderr',err):
            self.assertEqual(host.main(self.path,['--model','fake:model']),0)
        self.assertIn('[Talk] answer',out.getvalue());self.assertIn('[Trace]',err.getvalue());self.assertIn('Talk',err.getvalue())

    def test_tool_node_and_signal_routes(self):
        from skilledgraph import load_graph
        from langchain_core.messages import AIMessage
        from langchain_core.tools import tool
        @tool
        def increment(value:int)->int:
            """Increment a number."""
            return value+1
        class Model:
            def __init__(self):self.calls=0
            def invoke(self,messages,config=None):
                self.calls+=1
                return (AIMessage(content='',tool_calls=[{'id':'t1','name':'increment','args':{'value':1}}])
                        if self.calls==1 else AIMessage(content='done'))
        self.path.write_text('# [Config]\n- **@trace**: on\n# [Node] Think\n## [Transitions]\n- @ToolCalls -> Tools\n- @Otherwise -> @End\n# [ToolNode] Tools\n- **@tools**: all\n## [Transitions]\n- @Default -> Think\n')
        g=load_graph(self.path,model=Model(),tools=[increment],trace=self.recorder)
        result=g.invoke({'messages':[]})
        self.assertEqual(result['messages'][-1].content,'done')
        self.assertEqual([e.node for e in self.ends()],['Think','Tools','Think'])
        self.assertEqual([e.route_key for e in self.recorder.events if e.event=='route'],['@ToolCalls','@Default','@Otherwise'])

    def test_native_injection_schema_and_existing_callbacks(self):
        from dataclasses import dataclass
        from langgraph.runtime import Runtime
        from langchain_core.runnables import RunnableConfig
        from langchain_core.callbacks import BaseCallbackHandler
        from typing_extensions import TypedDict
        class Input(TypedDict): value:int
        @dataclass
        class Context: offset:int
        seen=[]
        def action(state:Input,config:RunnableConfig,runtime:Runtime[Context]):
            self.assertEqual(set(state),{'value'})
            return {'value':state['value']+runtime.context.offset+config['configurable']['extra']}
        class Other(BaseCallbackHandler):
            def on_chain_start(self,*args,**kwargs):seen.append(kwargs.get('name'))
        g=self.graph(self.node('A'),{'A':action},context_schema=Context)
        result=g.invoke({'value':1,'items':['unchanged']},context=Context(2),config={'callbacks':[Other()],'configurable':{'extra':3}})
        self.assertEqual(result['value'],6);self.assertEqual(len(self.ends()),1);self.assertIn('A',seen)

    def test_dictionary_control_objects_are_only_data(self):
        from langgraph.types import Command
        from typing_extensions import TypedDict
        class State(TypedDict):goto:str; payload:object
        g=self.graph(self.node('A',''),{'A':lambda s:{'goto':'FAKE','payload':Command(goto='NOT_AN_EDGE')}},state_schema=State)
        g.invoke({})
        self.assertFalse(any(e.event=='route' for e in self.recorder.events))
        self.assertEqual(self.ends()[0].updates,('goto','payload'))

    def test_off_subgraph_does_not_leak_inherited_trace_metadata(self):
        from skilledgraph import load_graph
        from typing_extensions import TypedDict
        from langchain_core.messages import AIMessage
        from langchain_core.runnables import RunnableConfig
        class Model:
            def invoke(self,messages,config=None):return AIMessage(content='end')
        inner=Path(self.tmp.name)/'inner.md'
        inner.write_text('# [Config]\n- **@trace**: off\n# [Node] Inside\n## [Transitions]\n- end -> @End\n')
        child=load_graph(inner,model=Model())
        def outer(s,config:RunnableConfig):
            child.invoke({'messages':[]},config=config)
            return {}
        g=self.graph(self.node('A'),{'A':outer});g.invoke({})
        self.assertEqual([e.node for e in self.ends()],['A'])
        self.assertEqual([e.route_key for e in self.recorder.events if e.event=='route'],['@Default'])

    def test_receiver_failure_is_not_silenced(self):
        from skilledgraph import TraceRecorder
        class Broken(TraceRecorder):
            def on_chain_start(self,*args,**kwargs):raise RuntimeError('receiver failed')
        self.recorder=Broken()
        g=self.graph(self.node('A'),{'A':lambda s:{}})
        with self.assertRaisesRegex(RuntimeError,'receiver failed'):g.invoke({})

    def test_native_subgraph_discovery_and_parent_command(self):
        from langgraph.graph import StateGraph, START, END
        from langgraph.types import Command
        from typing_extensions import TypedDict
        class State(TypedDict): value: int
        def escape(state):
            return Command(graph=Command.PARENT, goto='Finish', update={'value':9})
        child=self.graph(self.node('Escape',''), {'Escape':escape}, state_schema=State)
        outer=StateGraph(State)
        outer.add_node('Child',child)
        outer.add_node('Finish',lambda s:{'value':s['value']+1})
        outer.add_edge(START,'Child');outer.add_edge('Finish',END)
        graph=outer.compile()
        self.assertEqual(graph.invoke({'value':0})['value'],10)
        route=next(e for e in self.recorder.events if e.event=='route')
        self.assertEqual((route.route_targets,route.graph_scope),(('Finish',),'PARENT'))
        self.assertEqual(self.ends()[0].status,'completed')

    def test_traced_node_retains_native_checkpointed_subgraph(self):
        from langgraph.graph import StateGraph, START, END
        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.types import Command, interrupt
        from typing_extensions import TypedDict
        class State(TypedDict): value: int
        native=StateGraph(State)
        native.add_node('Ask',lambda s:{'value':interrupt('subgraph prompt')})
        native.add_edge(START,'Ask');native.add_edge('Ask',END)
        child=native.compile()
        graph=self.graph(self.node('Child'),{'Child':child},state_schema=State,
                         compile_kwargs={'checkpointer':InMemorySaver()})
        self.assertIn('Child',dict(graph.get_subgraphs()))
        config={'configurable':{'thread_id':'subgraph-test'}}
        self.assertIn('__interrupt__',graph.invoke({'value':0},config))
        self.assertEqual(graph.invoke(Command(resume=42),config)['value'],42)
        self.assertEqual([e.status for e in self.ends()],['interrupted','completed'])

    def test_stream_apis_and_async_summary(self):
        from skilledgraph import atrace_summary
        from langchain_core.runnables import RunnableConfig
        graph=self.graph(self.node('A'),{'A':lambda s:{'value':1}})
        self.assertTrue(list(graph.stream({})))
        self.assertEqual(len(self.ends()),1)
        async def action(state, config: RunnableConfig):
            await atrace_summary('async check passed',config=config)
            return {'value':2}
        graph=self.graph(self.node('A'),{'A':action})
        async def run():
            return [chunk async for chunk in graph.astream({})]
        self.assertTrue(asyncio.run(run()))
        self.assertEqual(len(self.ends()),2)
        self.assertIn('async check passed',self.recorder.render())
