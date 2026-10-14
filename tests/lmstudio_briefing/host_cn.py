"""Opt-in local model authoring test, orchestrated by a SkilledGraph graph."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys
import time
from typing_extensions import TypedDict
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, ProxyHandler

from skilledgraph import load_graph

ROOT = Path(__file__).resolve().parents[2]
QUESTIONS = {
    'q1': '@uses python with body: automatic model calls? A one, B zero, C two.',
    'q2': 'pyfunction returns dict: A HumanMessage containing JSON, B State patch, C route key.',
    'q3': 'Router reads State: A before execution, B before merge, C after reducer merge.',
    'q4': 'Missing Transitions means: A no DSL successor, B next declared node, C parser error.',
    'q5': '@Default with named keys: A fallback, B invalid, C runs all targets.',
    'q6': 'Tool model binding belongs to: A parser, B ToolNode, C Host.',
    'q7': 'Valid function reference: A python:actions.run, B python:./actions_cn.py:run, C python:actions_cn.py:run.',
    'q8': 'Config required for @state: A yes, B no, C any header works.',
    'q9': 'ToolNode automatically returns to caller: A always, B only for add, C no.',
    'q10': 'Current agent integration via builtin harness backend: A implemented, B not implemented, C default behavior.',
}
EXPECTED = dict(zip(QUESTIONS, ['B','A','C','A','B','C','B','A','C','B']))
AUTHOR_TASK = '''Create a complete runnable SkilledGraph example from the briefing, without retrieving other files or using a recipe.
Return ONLY one JSON object: {"files":{"workflow_cn.md":"complete text","actions_cn.py":"complete text"}}.
Create exactly these two files. No Host file or @host; evaluator supplies its own offline model.
Config declares native State in actions_cn.py. State extends MessagesState and adds numbers: list[int], status: str.
First node Inspect runs Python inspect(state), returning status ready if numbers is nonempty, otherwise missing. It must not mutate input State in place. Its explicit Python route(state) reads merged status and returns ready/missing.
Table or list routes ready to Report and missing to Ask.
Report uses pyfunction materials(state), which returns ordinary dict {"numbers": state["numbers"]}; its body asks for the sum and it explicitly ends.
Ask is a plain prompt asking for numbers and explicitly ends.
Use exactly node names Inspect, Report, Ask and Python names State, inspect, route, materials. Functions accept state. Imports only MessagesState from langgraph.graph; no other imports are needed.
Do not return the whole history, invoke a model inside Python, invent syntax or add an executable main program. Keep code short. No markdown fences around your JSON output.'''


class State(TypedDict):
    core: str
    probe: dict
    attempts: int
    candidate: str
    error: str
    verdict: str
    validation: dict


def read_json(text):
    # No prose/fence removal: output-format failure is part of the result.
    value=json.loads(text)
    if not isinstance(value,dict):
        raise ValueError('Expected JSON object')
    return value


def read_files(text, transport):
    if transport == 'json':
        return read_json(text).get('files')
    pattern = r'^### (workflow\.md|actions\.py)\n```(?:markdown|python)\n(.*?)\n```[ \t]*(?:\n|$)'
    records = re.findall(pattern, text, flags=re.M | re.S)
    if len(records) != 2 or len({name for name, _ in records}) != 2:
        raise ValueError('Exactly two named file code blocks required')
    if re.sub(pattern, '', text, flags=re.M | re.S).strip():
        raise ValueError('Unexpected prose outside file blocks')
    return {name: body + '\n' for name, body in records}


class Client:
    def __init__(self, base_url, model, context_length, max_output, timeout, output):
        parsed=urlsplit(base_url)
        if parsed.scheme!='http' or parsed.hostname not in {'127.0.0.1','localhost','::1'}:
            raise ValueError('This opt-in test only connects to local HTTP LM Studio')
        self.base=base_url.rstrip('/')
        self.model=model
        self.context=context_length
        self.max_output=max_output
        self.timeout=timeout
        self.output=output
        self.calls=[]
        self.opener=build_opener(ProxyHandler({}))

    def request(self, path, payload=None):
        raw=None if payload is None else json.dumps(payload).encode()
        request=Request(self.base+path,data=raw,headers={'Content-Type':'application/json'})
        with self.opener.open(request,timeout=self.timeout) as response:
            return json.load(response)

    def complete(self, phase, core, prompt, maximum=None):
        limit=self.max_output if maximum is None else maximum
        payload={'model':self.model,'input':prompt,'system_prompt':core+'\nApply these rules to the task. Follow the requested output format exactly.',
                 'context_length':self.context,'temperature':0,'max_output_tokens':limit,'reasoning':'off','store':False,'stream':False}
        number=len(self.calls)+1
        (self.output/f'{number:02d}-{phase}-request.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
        print(f'[{phase}] local request {number}; context={self.context}, output limit={limit}',flush=True)
        start=time.monotonic()
        response=self.request('/api/v1/chat',payload)
        (self.output/f'{number:02d}-{phase}-response.json').write_text(json.dumps(response,indent=2,ensure_ascii=False),encoding='utf-8')
        text=''.join(item.get('content','') for item in response.get('output',[]) if item.get('type')=='message')
        stats=response.get('stats',{})
        self.calls.append({'phase':phase,'seconds':round(time.monotonic()-start,2),'stats':stats,'output_limit':limit})
        print(f'[{phase}] returned; stats={stats}',flush=True)
        if stats.get('input_tokens',0)+limit>self.context:
            raise ValueError('Measured input plus reserved output exceeds configured context')
        if stats.get('total_output_tokens',0)>=limit:
            raise ValueError('Output reached token cap; treat as potentially truncated')
        if not text:
            raise ValueError('No message output')
        return text


def main(graph_path, argv):
    parser=argparse.ArgumentParser(description='Load CORE into an 8k local model, probe rules, author files, verify, optionally repair once.')
    parser.add_argument('--run',action='store_true',help='explicitly enable local inference')
    parser.add_argument('--base-url',default='http://127.0.0.1:1234')
    parser.add_argument('--model',help='default: sole already loaded LLM; no model guessing')
    parser.add_argument('--context-length',type=int,default=8192)
    parser.add_argument('--max-output',type=int,default=1800)
    parser.add_argument('--timeout',type=float,default=300)
    parser.add_argument('--repairs',type=int,choices=(0,1),default=1)
    parser.add_argument('--core-file', type=Path, default=ROOT/'docs/agent-guide/CORE.md', help='local-only briefing file; not distributed with the repository')
    parser.add_argument('--transport', choices=('json','files'), default='json')
    parser.add_argument('--generation-only', action='store_true', help='skip rules probe for a separately recorded transport comparison')
    parser.add_argument('--output',type=Path,default=ROOT/'.local-docs/lmstudio-briefing')
    args=parser.parse_args(argv)
    if not args.run:
        parser.error('--run is required; this performs actual local inference')
    core_file=args.core_file.resolve()
    if not core_file.is_file():
        parser.error('Briefing is local-only and missing; supply --core-file /path/to/CORE.md')
    if not 256<=args.max_output<args.context_length or args.timeout<=0:
        parser.error('Invalid output/context budget or timeout')
    output=args.output.resolve()
    if output.exists() and any(output.iterdir()):
        parser.error('Output directory must be new or empty; previous results will not be overwritten')
    output.mkdir(parents=True,exist_ok=True)
    client=Client(args.base_url,args.model,args.context_length,args.max_output,args.timeout,output)
    discovery=client.request('/api/v1/models')
    (output/'model-info.json').write_text(json.dumps(discovery,indent=2),encoding='utf-8')
    loaded=[(m,i) for m in discovery['models'] if m.get('type')=='llm' for i in m.get('loaded_instances',[])]
    selected=[(m,i) for m,i in loaded if args.model is None or args.model in {m['key'],i['id']}]
    if len(selected)!=1:
        raise ValueError('Select exactly one already loaded LLM with --model')
    info,instance=selected[0]
    if instance['config']['context_length']!=args.context_length:
        raise ValueError('Requested context differs from loaded context; configure LM Studio explicitly first')
    client.model=instance['id']
    outcomes=[]

    def bind(payload,**kwargs):
        if payload=='read':
            def read(state):
                core=core_file.read_text(encoding='utf-8')
                (output/'CORE.md').write_text(core,encoding='utf-8')
                return {'core':core}
            return read
        if payload=='probe':
            def probe(state):
                if args.generation_only:
                    return {'probe': {'skipped': True}}
                raw=client.complete('probe',state['core'],'Return ONLY JSON {"answers":{"q1":"A/B/C",...}}. Choose ONE letter per question:\n'+json.dumps(QUESTIONS),maximum=450)
                try:
                    answers=read_json(raw).get('answers',{})
                    if not isinstance(answers,dict): raise ValueError('answers must be an object')
                    correct={k:answers.get(k)==value for k,value in EXPECTED.items()}
                    result={'answers':answers,'expected':EXPECTED,'correct':correct,'score':sum(correct.values()),'total':len(EXPECTED)}
                except Exception as exc:
                    result={'score':0,'total':len(EXPECTED),'error':str(exc)}
                print('[probe] score',result['score'],'/',result['total'],flush=True)
                return {'probe':result}
            return probe
        if payload=='generate':
            def generate(state):
                prompt=AUTHOR_TASK
                if args.transport == 'files':
                    prompt=prompt.replace('Return ONLY one JSON object: {"files":{"workflow_cn.md":"complete text","actions_cn.py":"complete text"}}.',
                        'Return ONLY two named file blocks, exactly in this format:\n### workflow_cn.md\n```markdown\ncomplete file\n```\n### actions_cn.py\n```python\ncomplete file\n```')
                    prompt=prompt.replace('No markdown fences around your JSON output.', 'No extra prose outside the two file blocks.')
                if state['attempts']:
                    # Fresh request: full CORE + same task + concise validator feedback.
                    prompt+='\nPrior candidate failed independent verification: '+state['error'][:1000]+'\nGenerate a replacement from scratch.'
                raw=client.complete('generate',state['core'],prompt)
                return {'candidate':raw,'attempts':state['attempts']+1}
            return generate
        if payload=='validate':
            def validate(state):
                attempt=output/f'attempt-{state["attempts"]}'
                attempt.mkdir()
                try:
                    files=read_files(state['candidate'], args.transport)
                    if not isinstance(files,dict) or set(files)!={'workflow_cn.md','actions_cn.py'} or not all(isinstance(v,str) for v in files.values()):
                        raise ValueError('Exactly workflow_cn.md and actions_cn.py string contents required')
                    if any(len(v.encode())>16000 for v in files.values()): raise ValueError('Generated file exceeds test size cap')
                    for name,body in files.items(): (attempt/name).write_text(body,encoding='utf-8')
                    verify=Path(__file__).with_name('verify_generated_cn.py')
                    result=subprocess.run([sys.executable,str(verify),str(attempt/'workflow_cn.md')],capture_output=True,text=True,encoding='utf-8',timeout=12)
                    (attempt/'validator.stdout').write_text(result.stdout,encoding='utf-8')
                    (attempt/'validator.stderr').write_text(result.stderr,encoding='utf-8')
                    verdict=read_json(result.stdout)
                    if result.returncode or not verdict.get('passed'): raise ValueError(verdict.get('error') or result.stderr[-1000:])
                    outcomes.append({'attempt':state['attempts'],'passed':True,'validation':verdict})
                    print('[validate] generated files passed both branches',flush=True)
                    return {'verdict':'passed','error':'','validation':verdict}
                except Exception as exc:
                    error=f'{type(exc).__name__}: {exc}'
                    outcomes.append({'attempt':state['attempts'],'passed':False,'error':error})
                    verdict='retry' if state['attempts']<=args.repairs else 'failed'
                    print('[validate]',verdict,error,flush=True)
                    return {'verdict':verdict,'error':error,'validation':{'passed':False,'error':error}}
            return validate
        if payload=='route': return lambda state:state['verdict']
        raise ValueError('Unknown local binding')

    report={'model':client.model,'model_key':info['key'],'quantization':info.get('quantization'),'architecture':info.get('architecture'),
            'context_length':args.context_length,'reasoning':'off','max_output':args.max_output,'repairs_allowed':args.repairs,
            'baseline':'CORE only; no recipes, no constrained JSON decoder, no manual patching','transport':args.transport,
            'generation_only':args.generation_only,'started_at':time.strftime('%Y-%m-%dT%H:%M:%S%z')}
    result=None
    try:
        graph=load_graph(graph_path,state_schema=State,bindings={'local':bind})
        result=graph.invoke({'core':'','probe':{},'attempts':0,'candidate':'','error':'','verdict':'','validation':{}},{'recursion_limit':12})
        report.update(probe=result['probe'],generation_passed=result['verdict']=='passed',attempts=result['attempts'])
        report['passed']=report['generation_passed'] and (args.generation_only or result['probe'].get('score')==len(EXPECTED))
    except KeyboardInterrupt:
        report.update(passed=False,aborted=True,error='Cancelled by operator; not a scored model result')
    except Exception as exc:
        report.update(passed=False,error=f'{type(exc).__name__}: {exc}')
    finally:
        report.update(calls=client.calls,outcomes=outcomes)
        if result:
            report['core_sha256']=hashlib.sha256(result['core'].encode()).hexdigest()
        (output/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
    return 130 if report.get('aborted') else 0 if report['passed'] else 1
