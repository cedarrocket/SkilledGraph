import argparse
import asyncio
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

try:
    import pydantic_monty
    import langchain_openai
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
except ImportError as exc:
    raise unittest.SkipTest('requires skilledgraph[agent]') from exc
from skilledgraph import load_graph
from sgraph_agent.filesystem import Workspace
from sgraph_agent.graph import create_graph
from sgraph_agent.host import Session, permission_reader, terminal_text
from sgraph_agent.policy import fingerprint, execution
from sgraph_agent.tools import Toolkit
from skilledgraph.monty_execution import run_monty

ROOT=Path(__file__).resolve().parents[1]


def call(name,args,identifier='call-1'):
    return {'name':name,'args':args,'id':identifier,'type':'tool_call'}


class Model:
    def __init__(self,plans): self.plans=iter(plans); self.calls=[]
    def bind_tools(self,tools): self.tools=tools; return self
    def invoke(self,messages,config=None):
        self.calls.append(list(messages))
        reply=next(self.plans)
        result=reply(messages) if callable(reply) else reply
        return result.model_copy(deep=True,update={'id':None})
    async def ainvoke(self,messages,config=None): return self.invoke(messages,config)


@unittest.skipUnless(os.name == "posix", "agent workspace requires POSIX dir-fd APIs")
class AgentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/'notes.txt').write_text('project alpha\nneed regression tests\n')

    def session(self,plans,**kwargs):
        model=Model(plans)
        return Session(create_graph(model,workspace=self.root),**kwargs),model

    def test_read_search_list_and_monty_complete_real_tools(self):
        calls=[call('read_file',{'path':'notes.txt'},'read'),call('search_files',{'query':'regression'},'search'),
               call('list_files',{},'list'),call('python',{'code':'sum(data["values"])','data':{'values':[2,3,5]}},'python')]
        session,model=self.session([AIMessage(content='',tool_calls=calls),AIMessage(content='done')])
        result=session.ask('inspect')
        outputs=[m for m in result['messages'] if m.type=='tool']
        self.assertEqual([m.tool_call_id for m in outputs],['read','search','list','python'])
        self.assertIn('project alpha',outputs[0].text)
        self.assertIn('regression',outputs[1].text)
        self.assertIn('notes.txt',outputs[2].text)
        self.assertEqual(outputs[3].text,'10')
        self.assertEqual(len(model.calls),2)

    def test_denied_mutation_and_bash_never_execute(self):
        session,_=self.session([AIMessage(content='',tool_calls=[call('write_file',{'path':'new.txt','content':'x'},'write'),
            call('bash',{'command':'touch side-effect'},'shell')]),AIMessage(content='denied')])
        seen=[]
        result=session.ask('request',approve=lambda request:seen.append(request) or False)
        self.assertEqual([r['tool'] for r in seen],['write_file','bash'])
        self.assertFalse((self.root/'new.txt').exists())
        self.assertFalse((self.root/'side-effect').exists())
        self.assertEqual(sum(m.type=='tool' for m in result['messages']),2)
        self.assertTrue(all(not item['approved'] for item in result['audit']))

    def test_approval_is_strict_bool_and_noninteractive_default_deny(self):
        for approve in [None,lambda request:'yes']:
            session,_=self.session([AIMessage(content='',tool_calls=[call('write_file',{'path':'new.txt','content':'x'})]),AIMessage(content='done')])
            session.ask('request',approve=approve)
            self.assertFalse((self.root/'new.txt').exists())

    def test_approved_write_edit_and_bash_execute_in_request_order(self):
        calls=[call('write_file',{'path':'new.txt','content':'hello'},'write'),call('bash',{'command':'cat new.txt'},'shell')]
        session,_=self.session([AIMessage(content='',tool_calls=calls),AIMessage(content='done'),
            AIMessage(content='',tool_calls=[call('edit_file',{'path':'new.txt','old_text':'hello','new_text':'goodbye'},'edit')]),AIMessage(content='edited')])
        seen=[]
        first=session.ask('create',approve=lambda request:seen.append(request) or True)
        self.assertIn('hello',[m.text for m in first['messages'] if m.type=='tool'][-1])
        second=session.ask('edit',approve=lambda request:seen.append(request) or True)
        self.assertEqual((self.root/'new.txt').read_text(),'goodbye')
        self.assertEqual([request['tool'] for request in seen],['write_file','bash','edit_file'])
        self.assertTrue(all(item['approved'] for item in second['audit']))

    def test_tool_batch_mixed_allow_and_denial_preserves_protocol(self):
        requests=[call('read_file',{'path':'notes.txt'},'read'),call('bash',{'command':'touch bad'},'bad')]
        session,model=self.session([AIMessage(content='',tool_calls=requests),AIMessage(content='done')])
        result=session.ask('inspect',approve=lambda request:False)
        self.assertEqual([m.tool_call_id for m in result['messages'] if m.type=='tool'],['read','bad'])
        self.assertEqual(len(model.calls[-1][-3].tool_calls),2)
        self.assertFalse((self.root/'bad').exists())

    def test_private_and_outside_paths_are_rejected_without_approval(self):
        for name in ['../outside','/etc/passwd','.env','deepseek_api.txt','.git/config','secret.pem']:
            with self.subTest(name=name):
                session,_=self.session([AIMessage(content='',tool_calls=[call('write_file',{'path':name,'content':'x'})]),AIMessage(content='done')])
                requests=[]
                result=session.ask('write',approve=lambda request:requests.append(request) or True)
                self.assertFalse(requests)
                self.assertFalse(result['audit'][-1]['approved'])

    def test_unknown_tool_and_extra_arguments_fail_closed(self):
        session,_=self.session([AIMessage(content='',tool_calls=[call('delete_all',{},'unknown'),
            call('read_file',{'path':'notes.txt','escape':True},'extra')]),AIMessage(content='done')])
        result=session.ask('bad')
        self.assertEqual(sum(m.type=='tool' for m in result['messages']),2)
        self.assertTrue(all(not x['approved'] for x in result['audit']))
        bad,_=self.session([AIMessage(content='',tool_calls=[call('write_file',{'path':'bad.txt','content':'x'},'')])])
        approvals=[]
        with self.assertRaisesRegex(ValueError,'IDs'):
            bad.ask('bad',approve=lambda request:approvals.append(request) or True)
        self.assertFalse(approvals)
        self.assertFalse((self.root/'bad.txt').exists())

    def test_path_and_arguments_revalidated_after_approval(self):
        toolkit=Toolkit(self.root)
        request=call('write_file',{'path':'new.txt','content':'x'})
        state={'messages':[AIMessage(content='',tool_calls=[request])],
               'decisions':{'call-1':{'approved':True,'fingerprint':fingerprint(request)}}}
        state['messages'][0].tool_calls[0]['args']['content']='changed'
        result=execution(toolkit)(state,{})
        self.assertFalse((self.root/'new.txt').exists())
        self.assertIn('stale',result['messages'][0].text)
        original=call('read_file',{'path':'notes.txt'})
        state={'messages':[AIMessage(content='',tool_calls=[original])],
               'decisions':{'call-1':{'approved':True,'fingerprint':fingerprint(original)}}}
        (self.root/'notes.txt').unlink()
        (self.root/'notes.txt').symlink_to('/etc/passwd')
        self.assertIn('validation changed',execution(toolkit)(state,{})['messages'][0].text)

    def test_gate_resume_does_not_repeat_completed_permissions_or_side_effects(self):
        session,_=self.session([AIMessage(content='',tool_calls=[call('write_file',{'path':'a.txt','content':'a'},'a'),
            call('write_file',{'path':'b.txt','content':'b'},'b')]),AIMessage(content='done')])
        requested=[]
        session.ask('write',approve=lambda request:requested.append(request['call_id']) or True)
        self.assertEqual(requested,['a','b'])
        self.assertEqual((self.root/'a.txt').read_text(),'a')
        self.assertEqual((self.root/'b.txt').read_text(),'b')

    def test_loop_has_finite_model_budget(self):
        tool_message=AIMessage(content='',tool_calls=[call('read_file',{'path':'notes.txt'})])
        session,model=self.session([tool_message]*5,max_model_calls=2)
        result=session.ask('loop')
        self.assertEqual(len(model.calls),2)
        self.assertIn('上限',result['messages'][-1].text)
        self.assertIn('budget',result['audit'][-1]['reason'])

    def test_context_compaction_and_subsequent_turn_memory(self):
        model=Model([AIMessage(content='noted'),AIMessage(content='用户名林，偏好中文。'),AIMessage(content='second'),
                     lambda messages:AIMessage(content='林' if any('用户名林' in m.text for m in messages) else 'unknown')])
        session=Session(create_graph(model,workspace=self.root),context_budget=1000)
        session.ask('我叫林。'+'重复背景'*270)
        result=session.ask('第二轮')
        self.assertEqual(result['compressions'],1)
        result=session.ask('我的名字？')
        self.assertEqual(result['messages'][-1].text,'林')
        self.assertFalse(any('重复背景' in m.text for m in result['messages']))

    def test_huge_current_turn_stops_without_model_call_or_data_loss(self):
        session,model=self.session([],context_budget=100)
        result=session.ask('很长的输入'*100)
        self.assertFalse(model.calls)
        self.assertIn('预算',result['messages'][-1].text)
        self.assertIn('很长的输入',result['messages'][0].text)
        with self.assertRaisesRegex(ValueError,'summarizer budget'):session.ask('short followup')
        self.assertFalse(model.calls)

    def test_terminal_permission_defaults_no_and_escapes_controls(self):
        stream=io.StringIO()
        approve=permission_reader(lambda prompt:'',stream)
        self.assertFalse(approve({'kind':'tool_permission','arguments':{'command':'\x1b[2J'}}))
        self.assertNotIn('\x1b',stream.getvalue())
        self.assertIn('\\u001b',stream.getvalue())
        self.assertNotIn('\x1b',terminal_text('hello\x1b[2J'))
        self.assertNotIn('\x9b',terminal_text('hello\x9b2J'))
        self.assertNotIn('\u202e',terminal_text('hello\u202e'))

    def test_separate_threads_and_failed_pending_turn(self):
        session,_=self.session([AIMessage(content='one')])
        session.ask('first')
        another=Session(session.graph)
        self.assertFalse(another.graph.get_state(another.config).values)
        broken,_=self.session([])
        with self.assertRaises(RuntimeError): broken.ask('request')
        with self.assertRaisesRegex(RuntimeError,'Previous turn'): broken.ask('retry')


@unittest.skipUnless(os.name == "posix", "agent workspace requires POSIX dir-fd APIs")
class MontyAndFilesystemTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.workspace=Workspace(self.root)

    def test_monty_calculation_no_host_access(self):
        self.assertEqual(run_monty('sum(data)',inputs={'data':[2,3,5]}),10)
        for code in ['open("/etc/passwd").read()','import subprocess\nsubprocess.run(["true"])','import socket\nsocket.socket()', 'import os\nos.environ', 'import os\nos.getenv("SGRAPH_API_KEY")']:
            with self.subTest(code=code):
                with self.assertRaises(Exception):run_monty(code)

    def test_monty_cpu_memory_and_source_limits(self):
        with self.assertRaises(Exception):run_monty('while True:\n    pass',limits={'max_feed_duration_secs':0.05,'max_memory':32*1024*1024})
        with self.assertRaises(Exception):run_monty('"x" * 100000000',limits={'max_memory':1024*1024,'max_feed_duration_secs':1})
        with self.assertRaises(ValueError):run_monty('1+'*10001+'1')
        from skilledgraph.monty_execution import bounded_json
        shared=[0]
        for _ in range(35):shared=[shared,shared]
        self.assertIn('truncated',bounded_json(shared,limit=100,truncate=True))
        with self.assertRaises(ValueError):bounded_json(shared,limit=100)

    def test_monty_dsl_backend_returns_patch_and_does_not_invoke_model(self):
        from typing_extensions import TypedDict
        class State(TypedDict): value:int
        (self.root/'program.py').write_text('{"value": state["value"] * 2}')
        path=self.root/'graph.md'
        path.write_text('# [Node] Compute\n- **@uses**: monty:./program.py\nThis body is not invoked.\n## [Transitions]\n- @Default -> @End\n')
        model=Model([])
        self.assertEqual(load_graph(path,state_schema=State,model=model).invoke({'value':21}),{'value':42})
        self.assertFalse(model.calls)
        (self.root/'bad.py').write_text('42')
        path.write_text(path.read_text().replace('program.py','bad.py'))
        with self.assertRaises(TypeError):load_graph(path,state_schema=State).invoke({'value':21})

    def test_monty_router_and_native_message_patch(self):
        (self.root/'node.py').write_text('{"messages":[{"role":"assistant","content":state["messages"][-1]["content"]+" processed"}]}')
        (self.root/'route.py').write_text('"done" if state["messages"][-1]["content"].endswith("processed") else "retry"')
        path=self.root/'graph.md'
        path.write_text('# [Node] Compute\n- **@uses**: monty:./node.py\n- **@router**: monty:./route.py\n## [Transitions]\n- done -> @End\n- retry -> Compute\n')
        result=load_graph(path).invoke({'messages':[HumanMessage(content='request')]})
        self.assertEqual(result['messages'][-1].text,'request processed')

    def test_monty_print_is_captured_bounded_and_not_written_to_terminal(self):
        captured=run_monty('print("hello")\n42',capture_output=True)
        self.assertEqual(captured['stdout'],'hello\n')
        self.assertEqual(captured['result'],42)
        self.assertTrue(run_monty('print("x"*15000)',capture_output=True)['truncated'])
        toolkit=Toolkit(self.root)
        self.assertIn('hello',toolkit.by_name['python'].invoke({'code':'print("hello")'}))
        self.assertIn('truncated',toolkit.by_name['python'].invoke({'code':'"x"*50000'}))

    def test_paths_symlinks_hardlinks_and_devices(self):
        (self.root/'plain').write_text('safe')
        (self.root/'symlink').symlink_to('/etc/passwd')
        os.link(self.root/'plain',self.root/'hardlink')
        os.mkfifo(self.root/'fifo')
        for name in ['../outside','/etc/passwd','symlink','hardlink','fifo']:
            with self.subTest(name=name):
                with self.assertRaises((OSError,ValueError)):self.workspace.read(name)
        (self.root/'dir').symlink_to('/tmp',target_is_directory=True)
        with self.assertRaises(OSError):self.workspace.write('dir/new','x')
        self.assertEqual(self.workspace.entries(),[])

    def test_private_entries_excluded_and_file_bounds(self):
        (self.root/'.env').write_text('secret')
        (self.root/'auth.json').write_text('secret')
        (self.root/'notes').write_text('visible')
        self.assertEqual(self.workspace.entries(),[{'path':'notes','kind':'file'}])
        with self.assertRaises(ValueError):self.workspace.write('big','x'*(1024*1024+1))
        (self.root/'big').write_bytes(b'x'*(1024*1024+1))
        with self.assertRaises(ValueError):self.workspace.read('big')

    def test_atomic_write_and_literal_edit_guard(self):
        tools=Toolkit(self.root)
        tools.by_name['write_file'].invoke({'path':'notes','content':'abc abc'})
        with self.assertRaises(ValueError):tools.by_name['edit_file'].invoke({'path':'notes','old_text':'abc','new_text':'x'})
        self.assertEqual((self.root/'notes').read_text(),'abc abc')
        os.chmod(self.root/'notes',0o755)
        tools.by_name['edit_file'].invoke({'path':'notes','old_text':'abc abc','new_text':'new'})
        self.assertEqual((self.root/'notes').read_text(),'new')
        self.assertEqual((self.root/'notes').stat().st_mode & 0o777,0o755)

    def test_shell_timeout_output_limit_and_no_inherited_secrets(self):
        from sgraph_agent.shell import bash
        with patch.dict(os.environ,{'SGRAPH_API_KEY':'must-not-leak'}):
            result=bash('printf "%s" "${SGRAPH_API_KEY-unset}"',cwd=self.root)
        self.assertEqual(result['output'],'unset')
        self.assertEqual(result['returncode'],0)
        self.assertEqual(bash('exec 1>&-; sleep 0.1; exit 7',cwd=self.root)['returncode'],7)
        self.assertEqual(bash('sleep 5',cwd=self.root,timeout=0.1)['stopped'],'timeout')
        self.assertEqual(bash('while true; do printf abcdef; done',cwd=self.root,output_limit=100)['stopped'],'output_limit')


class ConnectionTests(unittest.TestCase):
    def arguments(self,**updates):
        values=dict(model='deepseek:deepseek-flash',base_url=None,key_file=None,api='responses',reasoning_effort='none')
        values.update(updates);return argparse.Namespace(**values)

    def test_responses_disables_server_history_and_chat_is_explicit(self):
        from sgraph_agent.connection import create_model
        with patch.dict(os.environ,{},clear=True),patch('sgraph_agent.connection.AgentChatOpenAI') as factory:
            create_model(self.arguments())
            options=factory.call_args.kwargs
            self.assertEqual(options['model'],'deepseek-flash')
            self.assertEqual(options['base_url'],'https://api.deepseek.com')
            self.assertTrue(options['use_responses_api'])
            self.assertFalse(options['use_previous_response_id']);self.assertFalse(options['store'])
            create_model(self.arguments(api='chat',reasoning_effort=None))
            self.assertFalse(factory.call_args.kwargs['use_responses_api'])

    @unittest.skipUnless(os.name == "posix", "toolkit requires POSIX workspace APIs")
    def test_real_chatopenai_responses_serializes_calls_outputs_and_reasoning(self):
        import httpx
        from langchain_openai import ChatOpenAI
        payloads=[]
        def respond(request):
            payload=json.loads(request.content);payloads.append(payload)
            output=[{'type':'message','id':'msg_1','role':'assistant','status':'completed',
                'content':[{'type':'output_text','text':'done','annotations':[]}]}]
            return httpx.Response(200,json={'id':'resp_1','object':'response','created_at':1,'status':'completed',
                'model':'test','error':None,'incomplete_details':None,'output':output,'usage':{'input_tokens':1,'output_tokens':1,'total_tokens':2}})
        client=httpx.Client(transport=httpx.MockTransport(respond))
        self.addCleanup(client.close)
        model=ChatOpenAI(model='test',api_key='test-key',http_client=client,use_responses_api=True,
            use_previous_response_id=False,store=False,output_version='responses/v1')
        messages=[HumanMessage(content='calc'),AIMessage(content=[{'type':'reasoning','id':'rs_test','summary':[],'encrypted_content':'synthetic-encrypted-item'}],tool_calls=[call('python',{'code':'1+1'})]),
                  ToolMessage(content='2',tool_call_id='call-1',name='python')]
        result=model.bind_tools(Toolkit(Path.cwd()).tools).invoke(messages)
        self.assertEqual(result.text,'done')
        self.assertFalse(payloads[0]['store'])
        self.assertNotIn('previous_response_id',payloads[0])
        self.assertEqual([item['type'] for item in payloads[0]['input']],['message','reasoning','function_call','function_call_output'])
        self.assertEqual(payloads[0]['input'][-1]['call_id'],'call-1')
        self.assertTrue(any(tool['name']=='python' for tool in payloads[0]['tools']))

    def test_deepseek_preserves_plain_reasoning_without_server_references(self):
        from sgraph_agent.responses import AgentChatOpenAI
        model=AgentChatOpenAI(model='deepseek-flash',api_key='test-key',base_url='https://api.deepseek.com',
            deepseek_responses=True,use_responses_api=True,use_previous_response_id=False,store=False,output_version='responses/v1')
        messages=[HumanMessage(content='calc'),AIMessage(content=[{'type':'reasoning','id':'rs_1',
            'summary':[],'content':[{'type':'reasoning_text','text':'synthetic reasoning input'}]}],
            tool_calls=[call('python',{'code':'1+1'})]),ToolMessage(content='2',tool_call_id='call-1')]
        payload=model._get_request_payload(messages)
        self.assertFalse(payload['store'])
        self.assertNotIn('previous_response_id',payload)
        reasoning=next(item for item in payload['input'] if item['type']=='reasoning')
        self.assertEqual(reasoning['content'][0]['text'],'synthetic reasoning input')
        self.assertNotIn('id',reasoning)

    def test_agent_cli_help_no_network(self):
        result=subprocess.run([sys.executable,'-m','sgraph_agent','--help'],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('--workspace',result.stdout)
