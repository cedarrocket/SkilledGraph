"""Offline plumbing demo, not an LLM. No keys, providers, or network required."""
from langchain_core.messages import AIMessage


class EchoModel:
    def invoke(self, messages, config=None):
        text = messages[-1].text if messages else ""
        return AIMessage(content=f"Offline demo: {text}")

    async def ainvoke(self, messages, config=None):
        return self.invoke(messages, config)


def create():
    return EchoModel()
