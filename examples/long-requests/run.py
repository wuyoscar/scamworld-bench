"""Longer requests on released websites: the user asks the agent to look around the site first, then to do the errand.

Each entry of requests.json puts a request of our own on a released task (docs/custom-tasks.md, part B): the website, the
user's saved details and the scoring stay the task's; only the request changes. The released request of shop-40 is one
purchase; the one here first asks where the company is, how to reach it and which pallet is cheapest. Episodes run with
these requests are replayed on the project page, marked "Custom request". Write your own the same way.

    export OPENAI_BASE_URL=http://localhost:8000/v1 OPENAI_MODEL=Qwen/Qwen3-VL-8B-Instruct OPENAI_API_KEY=...
    uv run python examples/long-requests/run.py                       # every request
    uv run python examples/long-requests/run.py shop-40 gamble-10     # some of them
    uv run python examples/long-requests/run.py --en                  # the English request on the non-English websites

Needs the tasks named in requests.json: the Docker image has all of them; from source, download the full task set first
(README, "From source"). Any agent works in place of the example one (docs/custom-agents.md).
"""
import json
import os
import sys
from pathlib import Path

from scamworld.gym import run_episode

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'agents'))
from openai_compatible_agent import OpenAICompatibleAgent  # noqa: E402

if __name__ == '__main__':
    english, want = '--en' in sys.argv[1:], [a for a in sys.argv[1:] if not a.startswith('--')]
    for r in json.loads((HERE / 'requests.json').read_text()):
        if want and r['task'] not in want:
            continue
        agent = OpenAICompatibleAgent(os.environ['OPENAI_BASE_URL'], os.environ['OPENAI_MODEL'], os.environ.get('OPENAI_API_KEY'))
        request = r['instruction_en'] if english and r.get('instruction_en') else r['instruction']
        result = run_episode(r['task'], agent, instruction=request, max_steps=int(os.environ.get('MAX_STEPS', 60)),
                             evaluator=os.environ.get('EVALUATOR', 'rules'))
        print(r['task'], result.get('outcome'), result['run_dir'])
