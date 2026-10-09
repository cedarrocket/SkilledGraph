"""Real terminal agent: no demo model, no automatic dangerous-tool permission."""
import argparse
import json
from pathlib import Path
import sys
from uuid import uuid4
from threading import Lock
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from sgraph_chat_host.terminal import terminal_reader
from sgraph_agent.connection import create_model
from sgraph_agent.graph import create_graph, DEFAULT_GRAPH
from sgraph_agent.memory import estimate_tokens


def terminal_text(text):
    return ''.join(c if c in '\n\t' or c.isprintable() else f'\\u{ord(c):04x}' for c in str(text))


class Session:
    def __init__(self,graph,*,context_budget=12000,keep_turns=1,max_model_calls=16,thread_id=None):
        if context_budget<100 or keep_turns<1 or not 1<=max_model_calls<=100:
            raise ValueError('context_budget >=100, keep_turns >=1, max_model_calls 1..100 required')
        self.graph=graph
        self.config={'configurable':{'thread_id':thread_id or str(uuid4())},'recursion_limit':max_model_calls*6+20}
        self.settings={'context_budget':context_budget,'keep_turns':keep_turns,'max_model_calls':max_model_calls}
        self._lock=Lock()

    def ask(self,text,*,approve=None):
        if not text.strip() or len(text)>100000: raise ValueError('Input must contain 1..100000 characters')
        if not self._lock.acquire(blocking=False): raise RuntimeError('A session turn is already running')
        try:
            previous=self.graph.get_state(self.config)
            if previous.next:
                raise RuntimeError('Previous turn did not finish; use a new session (/clear) rather than overwrite pending work')
            result=self.graph.invoke({'messages':[HumanMessage(content=text)],'model_calls':0,**self.settings},self.config)
            while result.get('__interrupt__'):
                replies={}
                for pending in result['__interrupt__']:
                    value=pending.value
                    if not isinstance(value,dict) or value.get('kind')!='tool_permission':
                        raise ValueError('Unknown interrupt protocol; requires custom host support')
                    replies[pending.id]=(approve(value) is True) if approve else False
                result=self.graph.invoke(Command(resume=replies),self.config)
            return result
        finally: self._lock.release()


def permission_reader(read,stream):
    def approve(request):
        # JSON escapes terminal controls in tool arguments; previews never run code.
        print('[Permission required]\n'+terminal_text(json.dumps(request,ensure_ascii=False,indent=2)),file=stream)
        try: answer=read('Allow this exact tool call? [y/N] ')
        except (EOFError,KeyboardInterrupt): return False
        return answer.strip().lower() in {'y','yes','是','同意'}
    return approve


def main(graph_path,argv):
    parser=argparse.ArgumentParser(description='SkilledGraph terminal ReAct agent')
    parser.add_argument('--workspace',type=Path,default=Path.cwd())
    parser.add_argument('--model',help='Model ID, optionally provider:model; Responses uses deepseek-flash/v4-pro for DeepSeek')
    parser.add_argument('--base-url')
    parser.add_argument('--key-file',type=Path)
    parser.add_argument('--api',choices=['responses','chat'],default='responses')
    parser.add_argument('--reasoning-effort',choices=['none','low','medium','high','max'])
    parser.add_argument('--context-budget',type=int,default=12000,help='Approximate history tokens, excludes tool/schema overhead')
    parser.add_argument('--keep-turns',type=int,default=1)
    parser.add_argument('--max-model-calls',type=int,default=16)
    parser.add_argument('--prompt',help='Single request; otherwise enter conversation loop')
    args=parser.parse_args(argv)
    model=create_model(args)
    graph=create_graph(model,workspace=args.workspace,graph_path=graph_path)
    def new_session():
        return Session(graph,context_budget=args.context_budget,keep_turns=args.keep_turns,max_model_calls=args.max_model_calls)
    session=new_session()
    def run(text,approve):
        result=session.ask(text,approve=approve)
        replies=[m.text for m in result['messages'] if m.type=='ai' and m.text]
        print(terminal_text(replies[-1] if replies else '(no text reply)'))
        print(f"[history≈{estimate_tokens(result['messages'])} tokens, compacted={result.get('compressions',0)}, calls={result['model_calls']}]",file=sys.stderr)
    if not sys.stdin.isatty():
        text=args.prompt if args.prompt is not None else sys.stdin.read()
        if not text.strip(): parser.error('Provide --prompt or pipe a nonempty request')
        def deny(request):
            print(f"[Permission denied: no terminal for {request['tool']}]",file=sys.stderr)
            return False
        run(text,deny)
        return 0
    print(f'Workspace: {args.workspace.resolve()} | API: {args.api} | /exit /clear /status',file=sys.stderr)
    with terminal_reader(sys.stdin,sys.stderr) as read:
        approve=permission_reader(read,sys.stderr)
        if args.prompt is not None:
            run(args.prompt,approve)
            return 0
        while True:
            try: text=read('Agent> ')
            except (EOFError,KeyboardInterrupt): break
            if text.strip()=='/exit': break
            if text.strip()=='/clear':
                session=new_session(); print('[New empty session]',file=sys.stderr); continue
            if text.strip()=='/status':
                state=graph.get_state(session.config).values
                print(f"thread={session.config['configurable']['thread_id']} messages={len(state.get('messages',[]))} compressions={state.get('compressions',0)}",file=sys.stderr)
                continue
            if not text.strip(): continue
            try: run(text,approve)
            except (Exception,KeyboardInterrupt) as exc:
                # Never display raw provider errors, which may contain credential/request data.
                print(f'[Turn failed: {type(exc).__name__}. Use /clear if work remains pending.]',file=sys.stderr)
    return 0


def cli():
    try: return main(DEFAULT_GRAPH,sys.argv[1:])
    except KeyboardInterrupt: return 130
    except Exception as exc:
        print(f'sgraph-agent: {type(exc).__name__}; check model, connection and workspace settings.',file=sys.stderr)
        return 1
