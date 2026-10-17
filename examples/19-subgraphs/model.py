"""Offline scripted model; no external requests / 离线脚本模型，不请求 API。"""
from langchain_core.messages import AIMessage

REPLIES = {'draft': '草稿：列出假设，并检查一个小例子。', 'examine': '审查：一个小例子不能证明一般命题。', 'suggest': '建议：补充证明，或提供已验证的反例。', 'revise': '修订：区分经验检查与需要证明的结论。', 'report': '结论：明确假设、检查例子，再证明一般命题或给出反例。'}


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
