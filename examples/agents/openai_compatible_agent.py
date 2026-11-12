"""A complete LLM agent in ~80 lines over any OpenAI-compatible chat API (vLLM, Ollama, LiteLLM, OpenAI, OpenRouter, ...).

It uses the environment's own system prompt (the action protocol of the built-in agent), sends each observation as text plus
the screenshot, and reads the last JSON object of the reply as the action. A starting point for your own agent
(docs/custom-agents.md); the built-in agent (`scamworld run --base-url`) adds history compaction, format repairs and cost caps.
This one keeps the last 4 observations as text and the last 2 screenshots; of an older step it keeps the page address
and the error of the action before it, so write what you need to remember into the model's replies or raise `keep_obs`.

    export OPENAI_BASE_URL=http://localhost:8000/v1 OPENAI_MODEL=Qwen/Qwen3-VL-8B-Instruct OPENAI_API_KEY=...
    uv run python examples/agents/openai_compatible_agent.py examples/tasks/parcel-fee-01
"""
import base64
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

from scamworld.gym import Agent, run_episode


class OpenAICompatibleAgent(Agent):
    def __init__(self, base_url, model, api_key=None, max_tokens=2048, images=True, keep_images=2, keep_obs=4):
        self.url = base_url.rstrip('/') + '/chat/completions'
        self.model, self.key, self.max_tokens, self.images, self.keep_images = model, api_key, max_tokens, images, keep_images
        self.keep_obs = keep_obs
        self.cost_usd = 0.0

    def reset(self, goal, system_prompt):
        self.messages = [{'role': 'system', 'content': system_prompt}]

    def _call(self):
        body = {'model': self.model, 'messages': self.messages, 'temperature': 0, 'max_tokens': self.max_tokens}
        headers = {'Content-Type': 'application/json', **({'Authorization': 'Bearer ' + self.key} if self.key else {})}
        req = urllib.request.Request(self.url, json.dumps(body).encode(), headers)
        with urllib.request.urlopen(req, timeout=300) as r:
            reply = json.load(r)
        self.cost_usd += float((reply.get('usage') or {}).get('cost') or 0)
        return reply['choices'][0]['message'].get('content') or ''

    def act(self, obs):
        text = {k: v for k, v in obs.items() if k != 'screenshot'}
        content = [{'type': 'text', 'text': json.dumps(text, ensure_ascii=False)}]
        if self.images and obs.get('screenshot'):
            png = base64.b64encode(Path(obs['screenshot']).read_bytes()).decode()
            content.append({'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + png}})
        self.messages.append({'role': 'user', 'content': content})
        # the conversation stays small: only the last few observations keep their screenshot, and older ones keep only
        # their address and the error of the action before them
        seen = [m for m in self.messages if isinstance(m.get('content'), list)]
        for m in seen[:max(len(seen) - self.keep_images, 0)]:
            m['content'] = [p for p in m['content'] if p['type'] == 'text']
        for m in seen[:max(len(seen) - self.keep_obs, 0)]:
            old = json.loads(m['content'][0]['text'])
            kept = {k: old[k] for k in ('url', 'last_action_error') if old.get(k)}
            m['content'] = [{'type': 'text', 'text': json.dumps({**kept, 'observation': 'omitted (older step)'}, ensure_ascii=False)}]
        raw = self._call()
        self.messages.append({'role': 'assistant', 'content': raw})
        # no JSON action: the environment rejects it and tells the model so in the next observation (last_action_error)
        return last_json_object(raw) or {'action': 'none'}


def last_json_object(text):
    """The last {...} in the reply that parses as a JSON object with an 'action' key."""
    for m in reversed(list(re.finditer(r'\{', text))):
        try:
            obj, _ = json.JSONDecoder().raw_decode(text[m.start():])
        except ValueError:
            continue
        if isinstance(obj, dict) and 'action' in obj:
            return obj
    return None


if __name__ == '__main__':
    agent = OpenAICompatibleAgent(os.environ['OPENAI_BASE_URL'], os.environ['OPENAI_MODEL'], os.environ.get('OPENAI_API_KEY'))
    task = sys.argv[1] if len(sys.argv) > 1 else 'examples/tasks/parcel-fee-01'
    print(json.dumps(run_episode(task, agent, max_steps=int(os.environ.get('MAX_STEPS', 20)), evaluator=os.environ.get('EVALUATOR', 'rules')), indent=1))
