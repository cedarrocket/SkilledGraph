"""Opt-in real model acceptance for the looping ReAct memory example."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from skilledgraph.binding import load_file_object
from sgraph_chat_host.host import create_model
from sgraph_chat_host.host_config import model_options

ROOT=Path(__file__).resolve().parents[2]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',action='store_true')
    parser.add_argument('--output',type=Path,default=ROOT/'docs/development/ADVANCED_REDUCERS_LIVE_RESULTS.json')
    args=parser.parse_args()
    if not args.run: parser.error('--run required for real API calls')
    name=os.environ.get('SGRAPH_MODEL')
    if not name: parser.error('Set SGRAPH_MODEL and explicit connection settings')
    if 'opencode.ai/zen/go' in os.environ.get('SGRAPH_BASE_URL',''):
        parser.error('Use a general-purpose API for this noncoding memory test')
    Monitor=load_file_object('./run_practical_live.py:Monitor',base_dir=ROOT/'examples/support')
    path=ROOT/'examples/17-react-memory/workflow.md'
    calls=[]
    report={'date':datetime.now(timezone.utc).isoformat(),'model':name,'calls':calls,'turns':[]}
    secrets=[v for v in [model_options(base_dir=ROOT).get('api_key'),os.environ.get('DEEPSEEK_API_KEY'),os.environ.get('OPENAI_API_KEY')] if v]
    try:
        model=Monitor(create_model(name,base_dir=ROOT),calls)
        create=load_file_object('./host.py:create_graph',base_dir=path.parent)
        Session=load_file_object('./host.py:Session',base_dir=path.parent)
        session=Session(create(path,model),budget_chars=800)
        for text in ['我叫林，偏好中文。以下是无关测试背景，不需要在摘要中保留：'+'这是重复的合成测试背景。'*120,
                     '请调用工具计算17加25。','我的名字是什么？我偏好什么语言？']:
            result=session.ask(text)
            report['turns'].append({'reply':result['messages'][-1].text,
                'message_count':len(result['messages']),'compressions':result.get('compressions',0)})
        assert result.get('compressions',0)>=1,'Compression did not run'
        assert any(call.get('tool_names')==['calculate'] for call in calls),'Tool was not used'
        assert '42' in report['turns'][1]['reply'],'Tool calculation missing'
        assert '林' in report['turns'][2]['reply'] and '中文' in report['turns'][2]['reply'],'Facts lost after compression'
        report['passed']=True
    except Exception as exc:
        error=str(exc)
        for secret in secrets: error=error.replace(secret,'[REDACTED]')
        report.update(passed=False,error=error[:1200])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('ReAct memory:', 'PASS' if report['passed'] else 'FAIL')
    return 0 if report['passed'] else 1


if __name__=='__main__': raise SystemExit(main())
