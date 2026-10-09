"""Bind a real model, tools and compact node to the Markdown graph."""
import json
from pathlib import Path
from uuid import uuid4
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig, RunnableLambda
from langgraph.checkpoint.memory import InMemorySaver
from skilledgraph import load_graph
from .memory import estimate_tokens, split_history, validate_history
from .policy import gate, execution
from .tools import Toolkit

DEFAULT_GRAPH=Path(__file__).with_name('workflow.md')


def create_graph(model, *, workspace, summarizer=None, checkpointer=None, graph_path=DEFAULT_GRAPH):
    toolkit=Toolkit(workspace)
    bound=model.bind_tools(toolkit.tools)
    summary_model=model if summarizer is None else summarizer
    def binder(payload, *, node, **kwargs):
        if payload=='permissions': return gate(toolkit)
        if payload=='tools': return execution(toolkit)
        if payload=='model':
            def prepare(state):
                if state['model_calls']>=state.get('max_model_calls',16):
                    return AIMessage(content='已达到本轮模型调用上限。已完成的工具操作不会回滚；请检查结果后再继续。')
                if estimate_tokens(state['messages'])>state.get('context_budget',12000):
                    return AIMessage(content='保留的当前轮次超过上下文预算。请缩短输入或增大 --context-budget；本轮停止，不丢弃历史。')
                return None
            def finish(state,reply):
                if reply.invalid_tool_calls:
                    raise ValueError('Invalid tool arguments; no tool was executed')
                if reply.response_metadata.get('finish_reason')=='length' or reply.response_metadata.get('status') in {'incomplete','failed'}:
                    raise ValueError('Model output truncated; increase output budget')
                return {'messages':[reply],'model_calls':state['model_calls']+1}
            def invoke(state, config: RunnableConfig):
                refusal=prepare(state)
                if refusal is not None: return {'messages':[refusal]}
                return finish(state,bound.invoke([SystemMessage(content=node.prompt),*state['messages']],config=config))
            async def ainvoke(state, config: RunnableConfig):
                refusal=prepare(state)
                if refusal is not None: return {'messages':[refusal]}
                return finish(state,await bound.ainvoke([SystemMessage(content=node.prompt),*state['messages']],config=config))
            return RunnableLambda(invoke,afunc=ainvoke,name=node.name)
        if payload=='compact':
            def prepare(state):
                validate_history(state['messages'])
                older,recent=split_history(state)
                if not older: raise ValueError('No old complete turns available')
                if estimate_tokens(older)>state.get('context_budget',12000):
                    raise ValueError('Old history exceeds summarizer budget; use a new session or larger budget')
                # Summarize visible facts and tool records, not opaque encrypted reasoning/usage metadata.
                material=json.dumps([{'role':m.type,'text':m.text,
                    'tool_calls':getattr(m,'tool_calls',[]),'tool_call_id':getattr(m,'tool_call_id',None),
                    'name':getattr(m,'name',None),'is_summary':bool(m.additional_kwargs.get('memory_summary'))}
                    for m in older],ensure_ascii=False)
                return recent,[SystemMessage(content=node.prompt),HumanMessage(content=material)]
            def finish(state,recent,reply):
                if reply.response_metadata.get('finish_reason')=='length' or reply.response_metadata.get('status') in {'incomplete','failed'}:
                    raise ValueError('Summary response incomplete; old history retained')
                if not reply.text.strip() or reply.tool_calls:
                    raise ValueError('Summary must be nonempty text without tools')
                summary=HumanMessage(content='历史摘要（有损资料）：\n'+reply.text,
                    id=str(uuid4()),additional_kwargs={'memory_summary':True})
                replacement=[summary,*recent]
                if estimate_tokens(replacement)>=estimate_tokens(state['messages']):
                    raise ValueError('Summary did not reduce context; old history retained')
                return {'messages':{'operation':'compact',
                        'expected_messages':[m.model_dump(mode='json') for m in state['messages']],
                        'replacement':replacement},'compressions':state.get('compressions',0)+1}
            def invoke(state, config: RunnableConfig):
                recent,messages=prepare(state)
                return finish(state,recent,summary_model.invoke(messages,config=config))
            async def ainvoke(state, config: RunnableConfig):
                recent,messages=prepare(state)
                return finish(state,recent,await summary_model.ainvoke(messages,config=config))
            return RunnableLambda(invoke,afunc=ainvoke,name=node.name)
        raise ValueError('Unknown agent binding')
    return load_graph(graph_path,model=bound,bindings={'agent':binder},
        compile_kwargs={'checkpointer':checkpointer if checkpointer is not None else InMemorySaver()})
