"""Native State and pure reducer; model work belongs to the compression node."""
from typing import Annotated
from typing_extensions import TypedDict
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, AnyMessage
from langgraph.graph.message import add_messages


def validate_history(messages):
    pending = set()
    for message in messages:
        if isinstance(message, ToolMessage):
            if message.tool_call_id not in pending:
                raise ValueError("Orphan or duplicate tool result")
            pending.remove(message.tool_call_id)
        elif pending:
            raise ValueError("Tool calls must be resolved before another message")
        elif isinstance(message, AIMessage):
            calls = [c['id'] for c in message.tool_calls]
            if len(set(calls)) != len(calls):
                raise ValueError("Duplicate tool call IDs")
            pending.update(calls)
    if pending:
        raise ValueError("Cannot compact an unresolved tool call")


def memory_reducer(left, right):
    """Normally add_messages; compact updates replace an exact known snapshot."""
    if isinstance(right, dict) and right.get('operation') == 'compact':
        if [m.model_dump(mode='json') for m in left] != right['expected_messages']:
            raise ValueError("Stale compaction: history changed; do not discard new writes")
        replacement = add_messages([], right['replacement'])
        validate_history(replacement)
        return replacement
    return add_messages(left, right)


class State(TypedDict):
    messages: Annotated[list[AnyMessage], memory_reducer]
    context_budget: int
    keep_turns: int
    needs_compaction: bool
    compressions: int
    model_calls: int
    decisions: dict
    audit: list
    max_model_calls: int


def split_history(state):
    messages = state['messages']
    starts = [i for i, m in enumerate(messages)
              if isinstance(m, HumanMessage) and not m.additional_kwargs.get('memory_summary')]
    keep = state.get('keep_turns', 1)
    if keep < 1:
        raise ValueError('keep_turns must be positive')
    if len(starts) <= keep:
        return [], messages
    boundary = starts[-keep]
    return messages[:boundary], messages[boundary:]


def estimate_tokens(messages):
    import json
    # Includes non-text content/reasoning/tool arguments, unlike m.text alone.
    return sum((len(json.dumps(m.model_dump(mode='json'), ensure_ascii=False)) + 1) // 2 for m in messages)


def check(state):
    older, _ = split_history(state)
    return {'needs_compaction': bool(older) and estimate_tokens(state['messages']) > state.get('context_budget', 12000) * 0.7}


def route(state):
    return 'compact' if state['needs_compaction'] else 'keep'
