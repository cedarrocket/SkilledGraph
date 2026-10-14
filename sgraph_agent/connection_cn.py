"""OpenAI Responses/Chat integration using user-owned Host profile and env."""
import os
from pathlib import Path
from urllib.parse import urlsplit
from .responses_cn import AgentChatOpenAI
from sgraph_chat_host.host_config_cn import model_options, opencode_go_options
from sgraph_chat_host.host_setup_cn import load_profile, run_setup


def create_model(args):
    explicit=args.model or os.environ.get('SGRAPH_MODEL')
    profile=None if explicit else load_profile()
    if not explicit and profile is None: profile=run_setup()
    name=explicit or profile['model']
    options={} if profile is None else dict(profile['options'])
    options.update(model_options(base_dir=Path.cwd()))
    if args.base_url: options['base_url']=args.base_url
    if args.key_file:
        options['api_key']=Path(args.key_file).expanduser().read_text().strip()
        if not options['api_key'] or any(c.isspace() for c in options['api_key']):
            raise ValueError('Key file must contain one nonempty key')
    provider,separator,identifier=name.partition(':')
    if not separator: identifier=name
    if separator and provider=='deepseek' and 'base_url' not in options:
        options['base_url']='https://api.deepseek.com'
    options.setdefault('timeout',60)
    options.setdefault('max_retries',0)
    options.setdefault('max_tokens',4096)
    options=opencode_go_options(options)
    if args.api=='responses':
        # Compaction must never be defeated by a server-side previous_response_id.
        options.update(use_responses_api=True,use_previous_response_id=False,store=False,output_version='responses/v1')
        deepseek=urlsplit(str(options.get('base_url',''))).hostname=='api.deepseek.com'
        options['deepseek_responses']=deepseek
        if not deepseek: options['include']=['reasoning.encrypted_content']
        if args.reasoning_effort: options['reasoning_effort']=args.reasoning_effort
    else:
        options.update(use_responses_api=False)
        if args.reasoning_effort: raise ValueError('--reasoning-effort is available in Responses mode')
    return AgentChatOpenAI(model=identifier,**options)
