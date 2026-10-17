"""Offline scripted model; no external requests / 离线脚本模型，不请求 API。"""
from langchain_core.messages import AIMessage

REPLIES = {'draft': 'Draft: state assumptions and check a small example.', 'examine': 'Review: a small example cannot prove the general statement.', 'suggest': 'Suggestion: provide a proof or a verified counterexample.', 'revise': 'Revision: separate empirical checks from proof obligations.', 'report': 'Final: state assumptions, test examples, then prove the general claim or produce a counterexample.'}


class DemoModel:
    def invoke(self, messages, config=None):
        instruction = messages[0].content
        for tag, reply in REPLIES.items():
            if instruction.startswith("[" + tag + "]"):
                return AIMessage(content=reply)
        raise ValueError("Unexpected demo instruction")

    async def ainvoke(self, messages, config=None):
        return self.invoke(messages, config)


def create():
    return DemoModel()
