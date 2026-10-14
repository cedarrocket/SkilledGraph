"""Opt-in Responses acceptance using only an isolated synthetic workspace."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import tempfile
from skilledgraph.binding import load_file_object
from sgraph_chat_host.host_config_cn import model_options
from sgraph_agent.connection_cn import create_model
from sgraph_agent.graph_cn import create_graph
from sgraph_agent.host_cn import Session

ROOT=Path(__file__).resolve().parents[2]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',action='store_true')
    parser.add_argument('--model',default='deepseek-flash')
    parser.add_argument('--base-url',default='https://api.deepseek.com')
    parser.add_argument('--reasoning-effort',default='none',choices=['none','low','high'])
    parser.add_argument('--output',type=Path,default=ROOT/'docs/development/SGRAPH_AGENT_LIVE_RESULTS.json')
    parser.add_argument('--case',action='append',choices=['read_monty','deny_bash','approve_write_bash','memory'])
    args=parser.parse_args()
    if not args.run:parser.error('--run required for real API calls')
    if 'opencode.ai/zen/go' in args.base_url:parser.error('Use a general-purpose API for mixed tasks')
    config=argparse.Namespace(model=args.model,base_url=args.base_url,key_file=None,api='responses',reasoning_effort=args.reasoning_effort)
    raw=create_model(config)
    Monitor=load_file_object('./run_practical_live_cn.py:Monitor',base_dir=ROOT/'examples/support')
    secrets=[v for v in [model_options(base_dir=ROOT).get('api_key'),os.environ.get('OPENAI_API_KEY')] if v]
    report={'date':datetime.now(timezone.utc).isoformat(),'model':args.model,'api':'responses','reasoning_effort':args.reasoning_effort,'cases':[]}
    for case in args.case or ['read_monty','deny_bash','approve_write_bash','memory']:
        calls=[];item={'name':case,'calls':calls};report['cases'].append(item)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'notes.txt').write_text('project alpha\nrelease requires regression tests\n')
            session=Session(create_graph(Monitor(raw,calls),workspace=root),context_budget=2500 if case=='memory' else 12000,max_model_calls=6)
            try:
                if case=='read_monty':
                    result=session.ask('调用 read_file 读取 notes.txt，然后必须调用 python 工具计算 sum(range(10))，最后报告项目名和总和。')
                    names=[x['tool'] for x in result['audit'] if x['approved']]
                    assert 'read_file' in names and 'python' in names
                    assert any(m.type=='tool' and m.name=='python' and '45' in m.text for m in result['messages'])
                elif case=='deny_bash':
                    requests=[]
                    result=session.ask('只通过 bash 工具执行命令 touch denied-marker，不要使用其他文件工具。',approve=lambda request:requests.append(request) or False)
                    assert requests and all(r['tool']=='bash' for r in requests)
                    assert not (root/'denied-marker').exists()
                    assert not any(x['approved'] for x in result['audit'])
                elif case=='approve_write_bash':
                    def approve(request):
                        name=request['tool'];arguments=request['arguments']
                        return (name=='write_file' and arguments.get('path')=='approved.txt' and arguments.get('content')=='approved') or (name=='bash' and arguments.get('command')=='printf shell-ok')
                    result=session.ask('用 write_file 创建 approved.txt，content 必须精确为 approved。再用 bash 执行精确命令 printf shell-ok（不要加引号或其他命令），最后读取 approved.txt 验证。',approve=approve)
                    assert (root/'approved.txt').read_text()=='approved'
                    assert any(x['tool']=='bash' and x['approved'] for x in result['audit'])
                    assert any(m.type=='tool' and m.name=='bash' and 'shell-ok' in m.text for m in result['messages'])
                else:
                    first=session.ask('我叫林，偏好中文。请简短记住即可。以下重复背景可丢弃：'+'这是可丢弃的重复背景。'*280)
                    second=session.ask('必须用 python 工具计算17+25，告诉我结果。')
                    result=session.ask('我的名字是什么，偏好什么语言？')
                    assert result.get('compressions',0)>=1
                    assert '林' in result['messages'][-1].text and '中文' in result['messages'][-1].text
                    assert any(x['tool']=='python' and x['approved'] for x in result['audit'])
                    item['turns']=[{'reply':r['messages'][-1].text,'compressions':r.get('compressions',0)} for r in [first,second,result]]
                item.update(passed=True,reply=result['messages'][-1].text,audit=result.get('audit',[]),compressions=result.get('compressions',0))
            except Exception as exc:
                error=str(exc)
                for secret in secrets:error=error.replace(secret,'[REDACTED]')
                item.update(passed=False,error=error[:1200])
            print(case+(': PASS' if item['passed'] else ': FAIL'),flush=True)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return 0 if all(c['passed'] for c in report['cases']) else 1


if __name__=='__main__':raise SystemExit(main())
