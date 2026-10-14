"""Approval gate runs before any tool has side effects; no model risk classification."""
import hashlib
import json
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.types import interrupt
from langgraph.prebuilt import ToolNode


def fingerprint(call):
    return hashlib.sha256(json.dumps(call,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def gate(toolkit):
    def run(state):
        message=state['messages'][-1]
        if not isinstance(message,AIMessage): raise ValueError('Expected an AI tool-call message')
        decisions={}; audit=[]
        calls=message.tool_calls
        ids=[call['id'] for call in calls]
        if any(not isinstance(value,str) or not value or len(value)>512 for value in ids):
            raise ValueError('Tool call IDs must be nonempty bounded strings')
        if len(set(ids))!=len(ids): raise ValueError('Duplicate tool call IDs')
        for call in calls:
            approved=False; reason=''
            try:
                if len(calls)>8: raise ValueError('At most eight calls per batch')
                if state['model_calls']>=state.get('max_model_calls',16):
                    raise ValueError('Turn model-call budget exhausted')
                needs_permission=toolkit.validate(call)
                if needs_permission:
                    response=interrupt({'kind':'tool_permission','workspace':str(toolkit.workspace.root),
                        'tool':call['name'],'arguments':call['args'],'call_id':call['id'],
                        'reason':'Bash has host privileges' if call['name']=='bash' else 'Workspace modification'})
                    approved=response is True
                    reason='Approved by user' if approved else 'User denied this operation'
                else:
                    approved=True; reason='Bounded read-only or sandbox operation'
            except (ValueError,OSError,TypeError):
                reason='Rejected: invalid arguments, private/outside path, or exhausted budget'
            decisions[call['id']]={'approved':approved,'fingerprint':fingerprint(call),'reason':reason}
            audit.append({'tool':call['name'],'call_id':call['id'],'approved':approved,'reason':reason})
        return {'decisions':decisions,'audit':[*state.get('audit',[]),*audit][-200:]}
    return run


def execution(toolkit):
    native=ToolNode(toolkit.tools,handle_tool_errors=lambda exc:'Tool failed: '+type(exc).__name__+': '+str(exc)[:800])
    def run(state, config):
        message=state['messages'][-1]
        allowed=[]; denied=[]
        for call in message.tool_calls:
            decision=state['decisions'].get(call['id'],{})
            if decision.get('approved') is True and decision.get('fingerprint')==fingerprint(call):
                # Revalidate the path just before actual use, independent of earlier approval.
                try: toolkit.validate(call)
                except (ValueError,OSError,TypeError):
                    denied.append(ToolMessage(content='Rejected: validation changed after approval',tool_call_id=call['id'],name=call['name']))
                else: allowed.append(call)
            else:
                denied.append(ToolMessage(content=decision.get('reason','Approval missing or stale'),tool_call_id=call['id'],name=call['name']))
        returned=[]
        for call in allowed:
            # Preserve request order; never race writes/commands in a single batch.
            filtered=message.model_copy(update={'tool_calls':[call]})
            returned.extend(native.invoke({'messages':[filtered]},config)['messages'])
        by_id={m.tool_call_id:m for m in [*returned,*denied]}
        # Original full AIMessage remains in State; every call gets exactly one paired output.
        return {'messages':[by_id[call['id']] for call in message.tool_calls], 'decisions':{}}
    # Explicit annotation is required for native RunnableConfig injection.
    from langchain_core.runnables import RunnableConfig
    run.__annotations__['config']=RunnableConfig
    return run
