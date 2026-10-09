"""Narrow provider adaptation for stateless DeepSeek reasoning replay.

LangChain 1.7.0 normally drops unencrypted reasoning when store=False, as needed
by OpenAI. DeepSeek instead exposes plain reasoning content in a stateless API.
"""
from langchain_openai import ChatOpenAI
from langchain_openai.chat_models.base import _construct_responses_api_input


class AgentChatOpenAI(ChatOpenAI):
    deepseek_responses: bool = False

    def _get_request_payload(self,input_,*,stop=None,**kwargs):
        payload=super()._get_request_payload(input_,stop=stop,**kwargs)
        if self.deepseek_responses and self.use_responses_api:
            messages=self._convert_input(input_).to_messages()
            # Preserve full reasoning content, not ID-only server references.
            items=_construct_responses_api_input(messages,store=None)
            for item in items:
                if item.get('type') in {'message','reasoning'}:
                    item.pop('id',None)
            payload['input']=items
            payload.pop('previous_response_id',None)
            payload['store']=False
        return payload
