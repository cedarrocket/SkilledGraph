"""Reducers are native Python, exercised through real DSL graphs/checkpoints."""
import asyncio
from itertools import permutations
from pathlib import Path
import subprocess
import sys
import unittest
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, RemoveMessage
from langgraph.graph.message import add_messages, REMOVE_ALL_MESSAGES
from langgraph.types import Overwrite
from langgraph.errors import InvalidUpdateError
from skilledgraph import build_graph
from skilledgraph.binding import load_file_object

ROOT = Path(__file__).resolve().parents[1]
MEMORY = ROOT/'examples/17-react-memory/workflow_cn.md'
LAB = ROOT/'examples/18-reducer-lab/workflow_cn.md'


def obj(path, name, file='actions_cn.py'):
    return load_file_object(f'./{file}:{name}',base_dir=path.parent)


class ScriptedModel:
    def __init__(self): self.calls=[]; self.summaries=0
    def bind_tools(self, tools): return self
    def invoke(self, messages, config=None):
        self.calls.append(list(messages))
        if messages[0].text.startswith('TASK: MEMORY_COMPACT'):
            self.summaries+=1
            return AIMessage(content='用户名林，偏好中文。17+25=42。')
        last=messages[-1]
        if last.type=='tool': return AIMessage(content='计算结果：'+last.text)
        if '17+25' in last.text:
            return AIMessage(content='',tool_calls=[{'name':'calculate','args':{'a':17,'b':25},'id':str(uuid4()),'type':'tool_call'}])
        if '名字' in last.text:
            history=' '.join(m.text for m in messages[:-1])
            return AIMessage(content='你叫林。' if '林' in history else '不知道。')
        return AIMessage(content='已记录。')
    async def ainvoke(self,messages,config=None): return self.invoke(messages,config)


class AdvancedReducerTests(unittest.TestCase):
    def session(self, model=None, **kwargs):
        model=model or ScriptedModel()
        graph=obj(MEMORY,'create_graph','host_cn.py')(MEMORY,model)
        return obj(MEMORY,'Session','host_cn.py')(graph,**kwargs),model

    def test_turns_inherit_history_without_duplicate_resubmission(self):
        session,model=self.session(budget_chars=10000)
        first=session.ask('我叫林。')
        second=session.ask('我的名字是什么？')
        self.assertEqual(second['messages'][-1].text,'你叫林。')
        self.assertEqual(len(second['messages']),4)
        self.assertEqual(second['messages'][:2],first['messages'])
        self.assertEqual(len(model.calls[-1]),4)  # system + two old + new human

    def test_tool_loop_and_compaction_preserve_complete_recent_turn(self):
        session,model=self.session(budget_chars=120)
        session.ask('我叫林。'+'无关背景。'*100)
        result=session.ask('计算17+25')
        self.assertEqual(result['compressions'],1)
        self.assertTrue(result['messages'][0].additional_kwargs['memory_summary'])
        self.assertEqual([m.type for m in result['messages'][1:]],['human','ai','tool','ai'])
        self.assertIn('42',result['messages'][-1].text)
        obj(MEMORY,'validate_history')(result['messages'])
        result=session.ask('我的名字是什么？')
        self.assertEqual(result['messages'][-1].text,'你叫林。')
        self.assertTrue(any(m.additional_kwargs.get('memory_summary') for m in model.calls[-1]))

    def test_after_reply_can_trigger_compression(self):
        session,model=self.session(budget_chars=150)
        session.ask('我叫林。'+'背景'*40)
        original=model.invoke
        def verbose(messages,config=None):
            if messages[0].text.startswith('TASK: MEMORY_AGENT') and messages[-1].text=='第二轮':
                return AIMessage(content='长回答'*100)
            return original(messages,config)
        model.invoke=verbose
        result=session.ask('第二轮')
        self.assertEqual(result['compressions'],1)
        self.assertEqual(result['messages'][-1].text,'长回答'*100)
        # Keeping the latest turn can still exceed the budget. No infinite recompression.
        self.assertGreater(sum(len(m.text) for m in result['messages']),150)

    def test_repeated_compaction_includes_previous_summary(self):
        session,model=self.session(budget_chars=80)
        session.ask('我叫林。'+'资料'*80)
        session.ask('第二轮'+'背景'*60)
        result=session.ask('我的名字是什么？')
        self.assertGreaterEqual(result['compressions'],2)
        self.assertEqual(result['messages'][-1].text,'你叫林。')
        calls=[c for c in model.calls if c[0].text.startswith('TASK: MEMORY_COMPACT')]
        self.assertIn('历史摘要',calls[-1][-1].text)
        self.assertEqual(sum(bool(m.additional_kwargs.get('memory_summary')) for m in result['messages']),1)

    def test_threads_do_not_share_memory(self):
        first,model=self.session()
        first.ask('我叫林。')
        second=obj(MEMORY,'Session','host_cn.py')(first.graph)
        self.assertEqual(second.ask('我的名字是什么？')['messages'][-1].text,'不知道。')

    def test_async_memory_and_compaction(self):
        async def run():
            session,_=self.session(budget_chars=100)
            await session.aask('我叫林。'+'背景'*100)
            result=await session.aask('我的名字是什么？')
            self.assertEqual(result['compressions'],1)
            self.assertEqual(result['messages'][-1].text,'你叫林。')
        asyncio.run(run())

    def test_stale_compaction_refuses_to_drop_new_messages(self):
        reducer=obj(MEMORY,'memory_reducer')
        history=add_messages([],[HumanMessage(content='old',id='h')])
        patch={'operation':'compact','expected_messages':[m.model_dump(mode='json') for m in history],'replacement':[HumanMessage(content='summary')]}
        updated=reducer(history,[AIMessage(content='new',id='a')])
        with self.assertRaisesRegex(ValueError,'Stale'): reducer(updated,patch)
        self.assertEqual([m.id for m in updated],['h','a'])
        edited=reducer(history,[HumanMessage(content='edited',id='h')])
        with self.assertRaisesRegex(ValueError,'Stale'): reducer(edited,patch)

    def test_compaction_rejects_orphan_and_unresolved_tools(self):
        reducer=obj(MEMORY,'memory_reducer')
        bad=[[ToolMessage(content='42',tool_call_id='missing')],
             [AIMessage(content='',tool_calls=[{'name':'calculate','args':{},'id':'x','type':'tool_call'}])]]
        for replacement in bad:
            with self.subTest(replacement=replacement):
                with self.assertRaises(ValueError):
                    reducer([],{'operation':'compact','expected_messages':[],'replacement':replacement})

    def test_parallel_tool_results_are_kept_together(self):
        history=add_messages([],[HumanMessage(content='calc'),AIMessage(content='',tool_calls=[
            {'name':'calculate','args':{},'id':key,'type':'tool_call'} for key in ['x','y']]),
            ToolMessage(content='2',tool_call_id='y'),ToolMessage(content='1',tool_call_id='x'),AIMessage(content='done')])
        obj(MEMORY,'validate_history')(history)
        obj(MEMORY,'memory_reducer')([],{'operation':'compact','expected_messages':[],'replacement':history})

    def test_summary_failure_does_not_commit_replacement(self):
        session,model=self.session(budget_chars=100)
        before=session.ask('我叫林。'+'背景'*100)['messages']
        old=model.invoke
        model.invoke=lambda messages,config=None: AIMessage(content='') if messages[0].text.startswith('TASK: MEMORY_COMPACT') else old(messages,config)
        with self.assertRaisesRegex(ValueError,'nonempty'): session.ask('第二轮')
        state=session.graph.get_state(session.config).values
        self.assertEqual(state['messages'][:len(before)],before)
        self.assertNotIn('compressions',state)

    def test_parallel_versioned_records_idempotent_events_and_overwrite(self):
        result=obj(LAB,'create_graph','host_cn.py')(LAB).invoke({'records':{},'events':{},'completed':[]})
        self.assertEqual(result['report'],{'records':{'ticket':{'version':2,'status':'resolved'}},'total':8,'completed':['a','b']})
        self.assertEqual(result['events'],{})

    def test_version_merge_permutations_and_associativity(self):
        merge=obj(LAB,'merge_versions')
        updates=[{'x':{'version':1,'value':'old'}},{'x':{'version':3,'value':'new'}},{'y':{'version':2,'value':'other'}}]
        expected={'x':{'version':3,'value':'new'},'y':{'version':2,'value':'other'}}
        for order in permutations(updates):
            value={}
            for update in order: value=merge(value,update)
            self.assertEqual(value,expected)
        a,b,c=updates
        self.assertEqual(merge(merge(a,b),c),merge(a,merge(b,c)))
        self.assertEqual(merge(expected,expected),expected)

    def test_equal_version_conflict_is_not_silently_last_writer_wins(self):
        merge=obj(LAB,'merge_versions')
        with self.assertRaisesRegex(ValueError,'Conflicting'):
            merge({'x':{'version':1,'value':'a'}},{'x':{'version':1,'value':'b'}})

    def test_replayed_events_do_not_double_count_and_conflicts_raise(self):
        merge=obj(LAB,'merge_events')
        original={'job-1':3,'job-2':5}
        self.assertEqual(sum(merge(original,{'job-1':3}).values()),8)
        with self.assertRaisesRegex(ValueError,'Event ID'): merge(original,{'job-1':4})

    def test_native_message_update_delete_and_reset(self):
        reducer=obj(MEMORY,'memory_reducer')
        state=reducer([],[HumanMessage(content='old',id='h'),AIMessage(content='answer',id='a')])
        state=reducer(state,[HumanMessage(content='edited',id='h')])
        self.assertEqual(len(state),2)
        state=reducer(state,[RemoveMessage(id='a')])
        self.assertEqual(state[0].text,'edited')
        state=reducer(state,[RemoveMessage(id=REMOVE_ALL_MESSAGES),HumanMessage(content='reset')])
        self.assertEqual([m.text for m in state],['reset'])
        with self.assertRaises(ValueError): reducer(state,[RemoveMessage(id='unknown')])

    def test_checkpoint_rebuild_retains_compacted_thread(self):
        from langgraph.checkpoint.memory import InMemorySaver
        saver=InMemorySaver()
        create=obj(MEMORY,'create_graph','host_cn.py')
        Session=obj(MEMORY,'Session','host_cn.py')
        model=ScriptedModel()
        first=Session(create(MEMORY,model,checkpointer=saver),budget_chars=100,thread_id='retained')
        first.ask('我叫林。'+'背景'*100)
        first.ask('第二轮')
        second=Session(create(MEMORY,model,checkpointer=saver),budget_chars=100,thread_id='retained')
        result=second.ask('我的名字是什么？')
        self.assertEqual(result['messages'][-1].text,'你叫林。')
        self.assertTrue(result['messages'][0].additional_kwargs['memory_summary'])

    def test_too_long_summary_is_rejected_without_truncating(self):
        session,model=self.session(budget_chars=100)
        session.ask('我叫林。'+'背景'*100)
        original=model.invoke
        model.invoke=lambda messages,config=None: AIMessage(content='摘要'*1000) if messages[0].text.startswith('TASK: MEMORY_COMPACT') else original(messages,config)
        with self.assertRaisesRegex(ValueError,'reduce history'): session.ask('第二轮')
        self.assertIn('背景',session.graph.get_state(session.config).values['messages'][0].text)

    def test_keep_multiple_turns_and_single_huge_turn(self):
        session,_=self.session(budget_chars=100,keep_turns=2)
        first=session.ask('我叫林。'+'背景'*100)
        self.assertNotIn('compressions',first)
        second=session.ask('第二轮')
        self.assertNotIn('compressions',second)
        third=session.ask('第三轮')
        self.assertEqual(third['compressions'],1)
        self.assertEqual([m.text for m in third['messages'] if m.type=='human'][1:],['第二轮','第三轮'])

    def test_native_overwrite_collision_is_rejected(self):
        # Two resets in one superstep are ambiguous; native LangGraph rejects them.
        def bind(payload, **kwargs):
            if payload.rsplit(':',1)[-1] in {'source_a','source_b'}:
                return lambda state: {'events':Overwrite({})}
            return lambda state: {}
        builder=build_graph(LAB,bindings={'python':bind})
        builder.add_edge('Start','SourceA').add_edge('Start','SourceB')
        with self.assertRaises(InvalidUpdateError): builder.compile().invoke({'events':{}})

    def test_two_example_clis(self):
        for path,arguments in [(MEMORY,['--','--demo','--budget-chars','120']),(LAB,[])]:
            result=subprocess.run([sys.executable,'-X','utf8','-m','skilledgraph',str(path),*arguments],capture_output=True,text=True,encoding="utf-8",timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue(result.stdout.strip())
