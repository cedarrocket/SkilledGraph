"""Executable subgraph contracts / 子图语法、状态边界与原生执行验收。"""
import asyncio
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from skilledgraph import BuildError, ParseError, parse_graph


class GraphFiles:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def subgraph(self, name='Research', source='./child.md', target='@End'):
        return (f'# [Subgraph] {name}\n- **@source**: {source}\n'
                f'## [Transitions]\n- @Default -> {target}\n')


class SourceTests(GraphFiles, unittest.TestCase):
    def test_syntax_and_local_names(self):
        path = self.write('main.md', '# [Config]\n- **@trace**: off\n' +
                          self.subgraph(target='Report') + '# [Node] Report\nAnswer\n')
        spec = parse_graph(path)
        self.assertEqual(spec.entry, 'Research')
        self.assertEqual(spec.nodes[0].kind, 'Subgraph')
        self.assertEqual(spec.nodes[0].setting('source'), './child.md')
        # Parsing never opens the child / 纯解析不读取子文件。
        self.assertFalse((self.root / 'child.md').exists())
        for text in ('# [Subgraph]\n', '# [Subgraph] Missing\n',
                     self.subgraph(source='child.md'),
                     self.subgraph(source='~/child.md'),
                     '# [Node] A\n- **@source**: ./child.md\n',
                     '# [Config]\n- **@source**: ./child.md\n# [Node] A\n',
                     '# [Subgraph] A\n- **@source**: ./child.md\n- **@uses**: python:./x.py:f\n',
                     '# [Subgraph] A\n- **@source**: ./child.md\n- **@state**: python:./x.py:S\n',
                     '# [Subgraph] A\n- **@source**: ./child.md\n- **@trace**: on\n',
                     '# [Subgraph] A\n- **@source**: ./child.md\nUnexpected prompt\n',
                     self.subgraph()+self.subgraph(),
                     self.subgraph(target='Child.Internal')):
            with self.subTest(text=text), self.assertRaises(ParseError):
                parse_graph(self.write('bad.md',text))

    def test_literal_markers_and_descriptions(self):
        spec=parse_graph(self.write('main.md','# [Node] Explain\n```markdown\n'+
                                    self.subgraph()+'```\n'+
                                    '# [Subgraph] Child\n>>> description\n- **@source**: ./child.md\n'))
        self.assertEqual(len(spec.nodes),2)
        self.assertIn('# [Subgraph]',spec.nodes[0].prompt)
        self.assertEqual(spec.nodes[1].prompt,'')

    def test_source_resolution_snapshot_diamond_and_cycles(self):
        from skilledgraph.subgraphs import resolve_tree
        leaf=self.write('nested/leaf.md','# [Node] A\n')
        self.write('nested/child.md',self.subgraph('Leaf','./leaf.md'))
        main=self.write('main.md',self.subgraph('Left','./nested/child.md','Right')+
                        self.subgraph('Right','./nested/child.md'))
        tree=resolve_tree(parse_graph(main))
        self.assertIsNot(tree.children['Left'],tree.children['Right'])
        self.assertIs(tree.children['Left'].spec,tree.children['Right'].spec)
        self.assertEqual(tree.children['Left'].children['Leaf'].spec.path,leaf)
        self.write('nested/leaf.md',self.subgraph('Back','../main.md'))
        with self.assertRaisesRegex(BuildError,'subgraph.cycle'):
            resolve_tree(parse_graph(main))
        # Previous snapshot stays unchanged / 已构建源快照不受编辑影响。
        self.assertEqual(tree.children['Left'].children['Leaf'].spec.nodes[0].kind,'Node')
        with self.assertRaisesRegex(BuildError,'subgraph.source'):
            resolve_tree(parse_graph(self.write('missing.md',self.subgraph(source='./absent.md'))))

    def test_symlink_cycle(self):
        from skilledgraph.subgraphs import resolve_tree
        root=self.write('main.md',self.subgraph(source='./alias.md'))
        try:(self.root/'alias.md').symlink_to(root)
        except OSError:self.skipTest('symlinks unavailable')
        with self.assertRaisesRegex(BuildError,'subgraph.cycle'):
            resolve_tree(parse_graph(root))


@unittest.skipUnless(importlib.util.find_spec('langgraph'),'requires runtime')
class ExecutionTests(GraphFiles, unittest.TestCase):
    def setUp(self):
        super().setUp()
        from skilledgraph import TraceRecorder
        self.recorder=TraceRecorder()
        self.actions={}
        self.bindings={'test':lambda payload,**kw:self.actions[payload]}

    def node(self, name, target='@End', router=None):
        text=f'# [Node] {name}\n- **@uses**: test:{name}\n'
        if router:text+=f'- **@router**: test:{router}\n'
        return text+f'## [Transitions]\n- @Default -> {target}\n'

    def load(self,path,**kwargs):
        from skilledgraph import load_graph
        return load_graph(path,bindings=self.bindings,trace=self.recorder,**kwargs)

    def test_shared_messages_nested_end_and_trace_identity(self):
        from langchain_core.messages import AIMessage, HumanMessage
        trace='# [Config]\n- **@trace**: on\n'
        self.actions={'Work':lambda s:{'messages':[AIMessage(content=f"count={len(s['messages'])}")]},
                      'Report':lambda s:{'messages':[AIMessage(content='done')]}}
        self.write('child.md',trace+self.node('Work'))
        root=self.write('main.md',trace+self.subgraph('First',target='Second')+
                        self.subgraph('Second',target='Report')+self.node('Report'))
        graph=self.load(root)
        result=graph.invoke({'messages':[HumanMessage(content='question')]})
        self.assertEqual([m.content for m in result['messages']],['question','count=1','count=2','done'])
        ends=[e for e in self.recorder.events if e.event=='node_end']
        self.assertEqual([(*e.graph_path,e.node) for e in ends],
                         [('First','Work'),('First',),('Second','Work'),('Second',),('Report',)])
        parents={e.node:e.execution_id for e in ends if not e.graph_path}
        for event in ends:
            if event.graph_path:
                self.assertEqual(event.parent_execution_id,parents[event.graph_path[0]])
                self.assertEqual(event.attempt,1)
        self.assertIn('First / Work',self.recorder.render())
        self.assertEqual(set(dict(graph.get_subgraphs())),{'First','Second'})

    def test_child_owns_schema_and_host_never_runs(self):
        from typing_extensions import TypedDict
        class Parent(TypedDict):value:int
        self.write('parts/state.py','from typing_extensions import TypedDict\nclass State(TypedDict):\n value:int\n private:str\n')
        self.actions['Work']=lambda s:{'value':s['value']+1,'private':'child only'}
        self.actions['Report']=lambda s:{'value':s['value']*2}
        self.write('parts/child.md','# [Config]\n- **@state**: python:./state.py:State\n'
                   '- **@host**: python:./must_not_import.py:main\n'+self.node('Work'))
        root=self.write('main.md',self.subgraph(source='./parts/child.md',target='Report')+self.node('Report'))
        graph=self.load(root,state_schema=Parent)
        self.assertEqual(graph.invoke({'value':2}),{'value':6})
        child=dict(graph.get_subgraphs())['Research']
        self.assertIn('private',child.channels)
        self.assertNotIn('private',graph.channels)
        # No parent-Schema inheritance when child omits @state.
        self.write('parts/child.md',self.node('Work'))
        graph=self.load(root,state_schema=Parent)
        child=dict(graph.get_subgraphs())['Research']
        self.assertIn('messages',child.channels)
        self.assertNotIn('value',child.channels)

    def test_router_reads_merged_parent_state(self):
        from typing_extensions import TypedDict
        class State(TypedDict):value:int
        self.write('state.py','from typing_extensions import TypedDict\nclass State(TypedDict):\n value:int\n')
        self.write('child.md','# [Config]\n- **@state**: python:./state.py:State\n'+self.node('Work'))
        self.actions.update(Work=lambda s:{'value':s['value']+1}, route=lambda s:'ready' if s['value']==3 else 'wrong',
                            Report=lambda s:{'value':s['value']*2})
        root=self.write('main.md','# [Subgraph] Research\n- **@source**: ./child.md\n'
                        '- **@router**: test:route\n## [Transitions]\n- ready -> Report\n'+self.node('Report'))
        self.assertEqual(self.load(root,state_schema=State).invoke({'value':2})['value'],6)
        self.write('main.md',root.read_text().replace('- **@router**: test:route\n',''))
        with self.assertRaisesRegex(BuildError,'route_source'):self.load(root,state_schema=State)

    def test_child_trace_without_parent_trace_requires_receiver(self):
        from skilledgraph import load_graph,build_graph
        self.actions['Work']=lambda s:{}
        self.write('child.md','# [Config]\n- **@trace**: on\n'+self.node('Work'))
        root=self.write('main.md',self.subgraph())
        with self.assertRaisesRegex(ValueError,'TraceRecorder'):
            load_graph(root,bindings=self.bindings)
        graph=build_graph(root,bindings=self.bindings).compile()
        with self.assertRaisesRegex(ValueError,'TraceRecorder'):graph.invoke({'messages':[]})
        self.load(root).invoke({'messages':[]})
        starts=[e for e in self.recorder.events if e.event=='node_start']
        self.assertEqual([(e.graph_path,e.node) for e in starts],[(('Research',),'Work')])

    def test_parent_trace_does_not_enable_child_trace(self):
        self.actions['Work']=lambda s:{}
        self.write('child.md',self.node('Work'))
        root=self.write('main.md','# [Config]\n- **@trace**: on\n'+self.subgraph())
        self.load(root).invoke({'messages':[]})
        self.assertEqual([e.node for e in self.recorder.events if e.event=='node_start'],['Research'])

    def test_interrupt_resume_sync_and_async_stream(self):
        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.types import Command
        self.write('child.md','# [Config]\n- **@trace**: on\n# [Node] Ask\n'
                   '- **@uses**: request_input:Continue?\n## [Transitions]\n- @Default -> @End\n')
        root=self.write('main.md','# [Config]\n- **@trace**: on\n'+self.subgraph())
        for asynchronous in (False,True):
            with self.subTest(asynchronous=asynchronous):
                graph=self.load(root,compile_kwargs={'checkpointer':InMemorySaver()})
                config={'configurable':{'thread_id':'child-interrupt'}}
                if asynchronous:
                    async def run():
                        chunks=[c async for c in graph.astream({'messages':[]},config)]
                        self.assertTrue(any('__interrupt__' in c for c in chunks))
                        return await graph.ainvoke(Command(resume='approved'),config)
                    result=asyncio.run(run())
                else:
                    result=graph.invoke({'messages':[]},config)
                    self.assertIn('__interrupt__',result)
                    result=graph.invoke(Command(resume='approved'),config)
                self.assertEqual(result['messages'][-1].content,'approved')
        self.assertTrue(any(e.status=='interrupted' and e.graph_path==('Research',) for e in self.recorder.events))

    def test_rebuild_refreshes_sources_no_runtime_reload(self):
        from langchain_core.messages import AIMessage
        self.actions={'Before':lambda s:{'messages':[AIMessage(content='old')]},
                      'After':lambda s:{'messages':[AIMessage(content='new')]}}
        self.write('child.md',self.node('Before'))
        root=self.write('main.md',self.subgraph())
        old=self.load(root)
        self.write('child.md',self.node('After'))
        self.assertEqual(old.invoke({'messages':[]})['messages'][-1].content,'old')
        self.assertEqual(self.load(root).invoke({'messages':[]})['messages'][-1].content,'new')

    def test_cycle_preflight_does_not_import_state(self):
        self.write('bad.py','raise RuntimeError("must not import")\n')
        root=self.write('main.md','# [Config]\n- **@state**: python:./bad.py:State\n'+
                        self.subgraph(source='./main.md'))
        with self.assertRaisesRegex(BuildError,'subgraph.cycle'):self.load(root)

    def test_native_reducer_semantics_are_not_rewritten(self):
        from typing import Annotated
        from typing_extensions import TypedDict
        from operator import add
        class State(TypedDict):items:Annotated[list[str],add]
        self.write('state.py','from typing import Annotated\nfrom typing_extensions import TypedDict\nfrom operator import add\nclass State(TypedDict):\n items:Annotated[list[str],add]\n')
        self.actions['Work']=lambda s:{'items':['new']}
        self.write('child.md','# [Config]\n- **@state**: python:./state.py:State\n'+self.node('Work'))
        root=self.write('main.md',self.subgraph())
        result=self.load(root,state_schema=State).invoke({'items':['old']})
        # Native child output includes old input; additive parent reducer repeats it.
        # 子图完整输出经父图累加 reducer 合并，已有项会再次累加。
        self.assertEqual(result['items'],['old','old','new'])

    def test_host_collects_child_only_trace(self):
        from sgraph_chat_host import host
        from langchain_core.messages import AIMessage
        class Model:
            def invoke(self,messages,config=None):return AIMessage(content='child reply')
        self.write('child.md','# [Config]\n- **@trace**: on\n# [Node] Answer\n## [Transitions]\n- @Default -> @End\n')
        root=self.write('main.md',self.subgraph())
        out=io.StringIO();err=io.StringIO()
        with patch.object(host,'create_model',return_value=Model()),patch('sys.stdin',io.StringIO('hello')),patch('sys.stdout',out),patch('sys.stderr',err):
            self.assertEqual(host.main(root,['--model','fake:model']),0)
        self.assertIn('child reply',out.getvalue())
        self.assertIn('Research / Answer',err.getvalue())

    def test_parallel_child_invocations_preserve_context_and_trace_parent(self):
        from typing import Annotated
        from typing_extensions import TypedDict
        from operator import add
        from langgraph.types import Command, Send
        from langgraph.runtime import Runtime
        from langchain_core.runnables import RunnableConfig
        class State(TypedDict):items:Annotated[list[str],add]
        class Context(TypedDict):prefix:str
        self.write('state.py','from typing import Annotated\nfrom typing_extensions import TypedDict\nfrom operator import add\nclass State(TypedDict):\n task:str\n items:Annotated[list[str],add]\n')
        async def dispatch(state):
            return Command(goto=[Send('Worker',{'task':'a'}),Send('Worker',{'task':'b'})])
        async def work(state,config:RunnableConfig,runtime:Runtime[Context]):
            from skilledgraph import atrace_summary
            await asyncio.sleep(0.01 if state['task']=='a' else 0)
            await atrace_summary('checked '+state['task'],config=config)
            return {'items':[runtime.context['prefix']+state['task']]}
        self.actions.update(Dispatch=dispatch,Work=work)
        trace='# [Config]\n- **@trace**: on\n'
        self.write('child.md',trace+'- **@state**: python:./state.py:State\n'+self.node('Work'))
        root=self.write('main.md',trace+'# [Node] Dispatch\n- **@uses**: test:Dispatch\n'+
                        self.subgraph('Worker'))
        result=asyncio.run(self.load(root,state_schema=State,context_schema=Context).ainvoke({},context={'prefix':'job-'}))
        self.assertEqual(sorted(result['items']),['job-a','job-b'])
        children=[e for e in self.recorder.events if e.event=='node_end' and e.graph_path]
        self.assertEqual(len(children),2)
        self.assertEqual(len({e.parent_execution_id for e in children}),2)
        self.assertEqual(sorted(e.attempt for e in children),[1,2])
        parents={e.execution_id for e in self.recorder.events if e.event=='node_start' and e.node=='Worker'}
        self.assertEqual({e.parent_execution_id for e in children},parents)

    def test_tools_model_and_custom_bindings_reach_nested_child(self):
        from langchain_core.messages import AIMessage
        from langchain_core.tools import tool
        @tool
        def double(value:int)->int:
            """Double an integer."""
            return value*2
        class Model:
            def invoke(self,messages,config=None):
                if messages[-1].type=='tool':return AIMessage(content='answer:'+messages[-1].content)
                return AIMessage(content='',tool_calls=[{'name':'double','args':{'value':3},'id':'call-1','type':'tool_call'}])
        self.actions['Prepare']=lambda s:{}
        self.write('parts/tools.md',self.node('Prepare','Think')+'# [Node] Think\nUse tools.\n'
                   '## [Transitions]\n- @ToolCalls -> Execute\n- @Otherwise -> @End\n'
                   '# [ToolNode] Execute\n- **@tools**: all\n## [Transitions]\n- @Default -> Think\n')
        self.write('child.md',self.subgraph('Tools','./parts/tools.md'))
        root=self.write('main.md',self.subgraph())
        from langchain_core.messages import HumanMessage
        result=self.load(root,model=Model(),tools=iter([double])).invoke({'messages':[HumanMessage(content='double 3')]})
        self.assertEqual(result['messages'][-1].content,'answer:6')
        self.assertEqual([m.type for m in result['messages']],['human','ai','tool','ai'])

    def test_host_streams_nested_replies_once_before_parent_completion(self):
        from sgraph_chat_host.host import run_chat
        from langchain_core.messages import AIMessage
        self.actions={'First':lambda s:{'messages':[AIMessage(content='first')]},
                      'Second':lambda s:{'messages':[AIMessage(content='second')]},
                      'Report':lambda s:{'messages':[AIMessage(content='report')]}}
        self.write('child.md',self.node('First','Second')+self.node('Second'))
        root=self.write('main.md',self.subgraph(target='Report')+self.node('Report'))
        output=io.StringIO()
        run_chat(self.load(root),input_stream=io.StringIO('hello'),output_stream=output)
        self.assertEqual(output.getvalue(),'[Research / First] first\n[Research / Second] second\n[Report] report\n')

    def test_bilingual_example_clis(self):
        import subprocess
        import sys
        repository=Path(__file__).resolve().parents[1]
        for suffix in ('','_cn','_en'):
            with self.subTest(suffix=suffix):
                path=repository/f'examples/19-subgraphs/workflow{suffix}.md'
                result=subprocess.run([sys.executable,'-m','skilledgraph',str(path),'--',
                                       '--model-factory',f'python:./model{suffix}.py:create'],
                                      input='Explain how to check a claim.\n',text=True,
                                      encoding='utf-8',capture_output=True,timeout=20)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(len(result.stdout.strip().splitlines()),7)
                self.assertIn('[InitialReview / Examine]',result.stdout)
                self.assertIn('[FinalReview / Suggest]',result.stdout)
                self.assertIn('InitialReview / Examine',result.stderr)
                self.assertIn('FinalReview / Examine',result.stderr)

    def test_default_host_resumes_nested_interrupt_once(self):
        from sgraph_chat_host.host import run_chat
        from langgraph.checkpoint.memory import InMemorySaver
        from langchain_core.messages import AIMessage
        class Terminal(io.StringIO):
            def isatty(self):return True
        self.actions['Reply']=lambda s:{'messages':[AIMessage(content='reply:'+s['messages'][-1].content)]}
        self.write('child.md','# [Node] Ask\n- **@uses**: request_input:Need input\n'
                   '## [Transitions]\n- @Default -> Reply\n'+self.node('Reply'))
        root=self.write('main.md',self.subgraph())
        output=io.StringIO();errors=io.StringIO()
        graph=self.load(root,compile_kwargs={'checkpointer':InMemorySaver()})
        self.assertEqual(run_chat(graph,input_stream=Terminal('initial\nanswer\n'),
                                  output_stream=output,error_stream=errors),0)
        self.assertEqual(errors.getvalue().count('[Interrupt] Need input'),1)
        self.assertEqual(output.getvalue(),'[Research / Reply] reply:answer\n')
