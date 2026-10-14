"""Opt-in real model acceptance for the looping ReAct memory example."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from skilledgraph.binding import load_file_object
from sgraph_chat_host.host_en import create_model
from sgraph_chat_host.host_config_en import model_options

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
    Monitor=load_file_object('./run_practical_live_en.py:Monitor',base_dir=ROOT/'examples/support')
    path=ROOT/'examples/17-react-memory/workflow_en.md'
    calls=[]
    report={'date':datetime.now(timezone.utc).isoformat(),'model':name,'calls':calls,'turns':[]}
    secrets=[v for v in [model_options(base_dir=ROOT).get('api_key'),os.environ.get('DEEPSEEK_API_KEY'),os.environ.get('OPENAI_API_KEY')] if v]
    try:
        model=Monitor(create_model(name,base_dir=ROOT),calls)
        create=load_file_object('./host_en.py:create_graph',base_dir=path.parent)
        Session=load_file_object('./host_en.py:Session',base_dir=path.parent)
        session=Session(create(path,model),budget_chars=800)
        for text in ['My name is Lin and I prefer English. Irrelevant test background need not be summarized: '+'Repeated synthetic test background.'*120,
                     'Use a tool to calculate 17+25.','What is my name and preferred language?']:
            result=session.ask(text)
            report['turns'].append({'reply':result['messages'][-1].text,
                'message_count':len(result['messages']),'compressions':result.get('compressions',0)})
        assert result.get('compressions',0)>=1,'Compression did not run'
        assert any(call.get('tool_names')==['calculate'] for call in calls),'Tool was not used'
        assert '42' in report['turns'][1]['reply'],'Tool calculation missing'
        assert 'Lin' in report['turns'][2]['reply'] and 'English' in report['turns'][2]['reply'],'Facts lost after compression'
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
