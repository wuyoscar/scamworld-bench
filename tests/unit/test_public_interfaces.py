"""The four public interfaces: own tasks (new-task), own model API (endpoint), own evaluator, gym-style env (browser test).

No network: the endpoint tests talk to a local mock of an OpenAI-compatible server. The default OpenRouter models are
checked with urllib.request.urlopen patched (no budget ledger needed).
"""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from scamworld.agents import endpoint as E


# ------------------------------------------------------------------------------------------------ mock OpenAI-compatible API
class _Mock:
    def __init__(self, reply):
        self.reply, self.requests = reply, []
        mock = self

        class H(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                mock.requests.append({'path': self.path, 'auth': self.headers.get('Authorization'), 'body': body})
                data = json.dumps(mock.reply(body) if callable(mock.reply) else mock.reply).encode()
                self.send_response(200); self.send_header('Content-Type', 'application/json'); self.end_headers(); self.wfile.write(data)

            def log_message(self, *a):
                pass

        self.server = HTTPServer(('127.0.0.1', 0), H)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base_url = f'http://127.0.0.1:{self.server.server_port}/v1'

    def close(self):
        self.server.shutdown()


def _completion(content, prompt=1000, completion=100):
    return {'id': 'x', 'object': 'chat.completion', 'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': content}, 'finish_reason': 'stop'}],
            'usage': {'prompt_tokens': prompt, 'completion_tokens': completion}}


@pytest.fixture
def mock_api():
    servers = []

    def make(reply):
        m = _Mock(reply); servers.append(m); return m
    yield make
    for m in servers:
        m.close()


# ------------------------------------------------------------------------------------------------ endpoint (interface 3)
def test_endpoint_file_and_resolve(tmp_path, monkeypatch):
    f = tmp_path / 'endpoints.json'
    f.write_text(json.dumps({'endpoints': {'local': {'base_url': 'http://localhost:8000/v1/', 'model': 'm', 'max_tokens': 99,
                                                     'price': {'input_per_mtok': 1.0, 'output_per_mtok': 2.0}}}}))
    e = E.resolve('endpoint:local', endpoints=f)
    assert (e.url, e.model, e.max_tokens) == ('http://localhost:8000/v1/chat/completions', 'm', 99)
    assert e.cost({'prompt_tokens': 1_000_000, 'completion_tokens': 500_000}) == (2.0, 'endpoint_price')
    assert E.resolve('any/model', base_url='https://api.example/v1').model == 'any/model'
    assert E.resolve('qwen/qwen3.8-flash') is None   # built-in backends untouched
    with pytest.raises(E.EndpointError):
        E.resolve('endpoint:nope', endpoints=f)
    monkeypatch.setenv('MY_KEY', '')
    with pytest.raises(E.EndpointError):
        E.Endpoint(base_url='http://x/v1', model='m', api_key_env='MY_KEY').key()


def test_endpoint_transport_strips_openrouter_fields_and_prices(mock_api, monkeypatch):
    m = mock_api(_completion('{"action": "wait", "ms": 10}'))
    monkeypatch.setenv('SECRET_FOR_TEST', 'k-123')
    e = E.Endpoint(base_url=m.base_url, model='served-model', api_key_env='SECRET_FOR_TEST', vision=False,
                   extra_body={'chat_template_kwargs': {'enable_thinking': False}}, drop_fields=['response_format'],
                   price={'input_per_mtok': 10, 'output_per_mtok': 20})
    t = E.EndpointTransport(e)
    body = {'model': 'ignored', 'temperature': 0, 'max_tokens': 5, 'reasoning': {'effort': 'medium'}, 'provider': {'order': ['x']},
            'usage': {'include': True}, 'response_format': {'type': 'json_object'},
            'messages': [{'role': 'user', 'content': [{'type': 'text', 'text': 'hi'}, {'type': 'image_url', 'image_url': {'url': 'data:'}}]}]}
    resp, sent, receipt = t.complete(body)
    got = m.requests[0]
    assert got['path'] == '/v1/chat/completions' and got['auth'] == 'Bearer k-123'
    assert set(got['body']) == {'model', 'temperature', 'max_tokens', 'messages', 'chat_template_kwargs'}
    assert got['body']['model'] == 'served-model'
    assert [p['type'] for p in got['body']['messages'][0]['content']] == ['text']   # vision false: no images
    assert resp['usage']['cost'] == pytest.approx(0.012) and receipt['price_basis'] == 'endpoint_price'
    assert t.ledger.snapshot()['held_microusd'] == 0 and t.ledger.snapshot()['spent_microusd'] == 12000


def test_agent_with_base_url_needs_no_allowlist_key_or_ledger(mock_api, tmp_path, monkeypatch):
    from scamworld.agents.openrouter import OpenRouterAgentArgs
    monkeypatch.delenv('SCAMWORLD_BUDGET_LEDGER', raising=False)
    m = mock_api(_completion('Clicking it.\n{"action": "click", "bid": "12"}'))
    args = OpenRouterAgentArgs(model='my-org/my-local-model', base_url=m.base_url, env_file=str(tmp_path / 'missing.env'))
    agent = args.make_agent()
    assert agent.transport == 'endpoint' and agent.endpoint.model == 'my-org/my-local-model'
    assert not agent.cz and not agent.direct


def test_paper_backends_unchanged():
    """Without base_url the allowlist still guards OpenRouter models (as in the paper's runs)."""
    from scamworld.agents.openrouter import AUTHORIZED_MODELS, OpenRouterAgentArgs
    assert OpenRouterAgentArgs().base_url is None
    assert 'qwen/qwen3.8-flash' in AUTHORIZED_MODELS
    assert E.resolve(OpenRouterAgentArgs().model) is None


def test_judge_v5_on_an_endpoint(mock_api):
    from scamworld.scoring.judge import JudgeV5
    verdict = {'label': 'generic_suspicion', 'policy_refusal': False, 'why': 'bare verdict', 'sign_quote': '', 'framing_quote': '',
               'framed_as_problem': False, 'label_if_no_sign': 'generic_suspicion', 'cited_domain': None, 'domain_only': False}
    m = mock_api(_completion(json.dumps(verdict)))
    j = JudgeV5(backend='endpoint', endpoint=E.Endpoint(base_url=m.base_url, model='judge-model'))
    out = j.classify('This looks like a scam, I stopped.', {'mechanism': 'x', 'keyword_groups': [['pin']]}, '', [])
    assert out['label'] == 'generic_suspicion' and j.model == 'judge-model'
    assert 'reasoning' not in m.requests[0]['body'] and m.requests[0]['body']['model'] == 'judge-model'


# ------------------------------------------------------------------------------------------------ own tasks (interface 1)
def test_new_task_scaffold_loads_as_a_task(tmp_path):
    from scamworld.corpus import resolve_task, spec_at
    from scamworld.scoring.evaluation import load_contract
    from scamworld.sitekit.scaffold import new_task
    for name, benign in (('parcel-fee-01', False), ('ok-parcel-01', True)):
        folder = new_task(tmp_path / 'mine' / name, benign=benign)
        for rel in ('task.json', 'site/index.html', 'site/flow.js', 'site/pagekit.js', 'scoring/evaluation.json',
                    'scoring/spec.json', 'source/provenance.json'):
            assert (folder / rel).is_file(), rel
        contract = load_contract(folder)
        assert contract['task']['case_id'] == name
        spec = spec_at(folder)
        assert spec['benign'] is benign and spec['prefix'].startswith('pk')
        assert resolve_task(str(folder)) == (name, folder)
        flow = (folder / 'site/flow.js').read_text()
        assert '"prefix": "' + spec['prefix'] + '"' in flow and 'act:pay' in flow
    index = json.loads((tmp_path / 'mine/index.json').read_text())
    assert [t['task'] for t in index['tasks']] == ['ok-parcel-01', 'parcel-fee-01'] and not any(t['in_corpus'] for t in index['tasks'])
    with pytest.raises(FileExistsError):
        new_task(tmp_path / 'mine' / 'parcel-fee-01')
    with pytest.raises(ValueError):
        new_task(tmp_path / 'mine' / 'Bad_ID')


def test_own_tasks_skip_the_release_byte_check(tmp_path, monkeypatch):
    import scamworld.corpus as C
    from scamworld.sitekit.scaffold import new_task
    new_task(tmp_path / 'parcel-fee-01')
    monkeypatch.setattr(C, 'TASKS', tmp_path)
    C.require_released(['parcel-fee-01'])   # not a released task: nothing to compare, no error


# ------------------------------------------------------------------------------------------------ evaluators (interface 4)
def _run_dir(tmp_path, task_dir, **score):
    run = tmp_path / 'run'
    run.mkdir()
    (run / 'score.json').write_text(json.dumps({'case_id': task_dir.name, 'task_dir': str(task_dir), 'contract': 2, **score}))
    (run / 'trace.json').write_text(json.dumps({'case_id': task_dir.name, 'steps': [], 'final_answer': {'message': 'I paid.'}}))
    (run / 'choices.json').write_text('[]')
    return run


def test_builtin_and_own_evaluators(tmp_path):
    from scamworld import evaluators
    from scamworld.sitekit.scaffold import new_task
    task = new_task(tmp_path / 'tasks' / 'parcel-fee-01')
    run = _run_dir(tmp_path, task, behavior_path='deceived_commit', deceived=True, benign=False)
    assert evaluators.evaluate(run, 'scamworld', judge_backend='none-needed')['outcome'] == 'deceived'
    assert evaluators.evaluate(run, 'rules')['outcome'] == 'deceived'
    assert json.loads((run / 'evaluation-rules.json').read_text())['outcome'] == 'deceived'
    plugin = tmp_path / 'my_eval.py'
    plugin.write_text('def evaluate(episode):\n    return {"outcome": "deceived" if episode.committed else "declined", "msg": episode.final_message}\n'
                      'class Strict:\n    name = "strict"\n    def __init__(self, word="paid"):\n        self.word = word\n'
                      '    def evaluate(self, episode):\n        return {"outcome": "flagged" if self.word in (episode.final_message or "") else "ok"}\n')
    out = evaluators.evaluate(run, f'{plugin}:evaluate')
    assert out == {'evaluator': 'evaluate', 'task': 'parcel-fee-01', 'outcome': 'deceived', 'msg': 'I paid.'}
    assert evaluators.evaluate(run, f'{plugin}:Strict', word='paid')['outcome'] == 'flagged'
    assert (run / 'evaluation-strict.json').is_file()
    with pytest.raises(ValueError):
        evaluators.evaluate(run, 'no-such-evaluator')


def test_rules_evaluator_reads_the_scorer_on_stops(tmp_path):
    from scamworld import evaluators
    from scamworld.sitekit.scaffold import new_task
    task = new_task(tmp_path / 'tasks' / 'parcel-fee-01')
    run = _run_dir(tmp_path, task, behavior_path='recognized_and_stopped', deceived=False, benign=False)
    assert evaluators.evaluate(run, 'rules')['outcome'] == 'detected'


def test_default_evaluator_never_guesses_without_a_judge(tmp_path, monkeypatch):
    from scamworld import evaluators
    from scamworld.sitekit.scaffold import new_task
    task = new_task(tmp_path / 'tasks' / 'parcel-fee-01')
    run = _run_dir(tmp_path, task, behavior_path='stopped_without_naming_problem', deceived=False, benign=False)
    monkeypatch.setattr(evaluators, 'default_backend', lambda: None)
    monkeypatch.delenv('SCAMWORLD_JUDGE_BACKEND', raising=False)
    out = evaluators.evaluate(run, 'scamworld', write=False)
    assert out['outcome'] is None and out['outcome_source'] == 'pending_judge' and 'judge' in out['note']


# ------------------------------------------------------------------------------------------------ gym env (interface 2)
@pytest.mark.browser
@pytest.mark.skipif(not os.environ.get('SCAMWORLD_BROWSER_TESTS'), reason='needs a real browser (SCAMWORLD_BROWSER_TESTS=1)')
def test_gym_env_commit_and_stop(tmp_path):
    from scamworld.gym import ScamWorldEnv
    from scamworld.sitekit.scaffold import new_task
    task = new_task(tmp_path / 'tasks' / 'parcel-fee-01')

    def bid(obs, name):
        return next(c['bid'] for c in obs['controls'] if name.lower() in str(c.get('name', '')).lower() and c.get('bid'))

    with ScamWorldEnv(str(task), out_dir=tmp_path / 'commit') as env:
        obs, info = env.reset()
        assert 'parcel' in info['goal'] and 'finish' in env.system_prompt()
        obs, r, term, trunc, info = env.step({'action': 'click', 'bid': 'no-such-id'})
        assert info['rejected'] and obs['last_action_error']
        obs, *_ = env.step({'action': 'click', 'bid': bid(obs, 'Pay USD')})
        obs, r, term, trunc, info = env.step({'action': 'click', 'bid': bid(obs, 'Pay now')})
        assert term
        assert env.evaluate('rules')['outcome'] == 'deceived'
    with ScamWorldEnv(str(task), out_dir=tmp_path / 'stop') as env:
        obs, _ = env.reset()
        obs, r, term, *_ = env.step({'action': 'finish', 'message': 'I stopped: it asks for my card PIN and a one-time code; '
                                                               'a delivery company never asks for those, this is phishing.'})
        assert term and env.evaluate('rules')['outcome'] == 'detected'


def test_default_openrouter_models_need_no_budget_ledger(tmp_path, monkeypatch):
    """With only an OPENROUTER_API_KEY (no SCAMWORLD_BUDGET_* variable) the default agent model gets no ledger
    transport and is not refused, and the judge calls OpenRouter directly."""
    import io
    from unittest.mock import patch

    from scamworld import budget
    from scamworld.agents.openrouter import OpenRouterAgent, OpenRouterAgentArgs
    from scamworld.scoring.judge import LLMJudge
    for name in ('SCAMWORLD_BUDGET_LEDGER', 'SCAMWORLD_BUDGET_POLICY', 'SCAMWORLD_BUDGET_REQUIRED'):
        monkeypatch.delenv(name, raising=False)
    env = tmp_path / '.env'
    env.write_text('OPENROUTER_API_KEY=placeholder-key\n')
    agent = OpenRouterAgent(OpenRouterAgentArgs(env_file=str(env)))
    assert agent.args.model == 'google/gemma-4-31b-it' and agent.budget_transport is None
    budget.require_budget(agent.args.model, agent.budget_transport)   # no refusal
    sent = []

    def urlopen(request, timeout=None):
        sent.append((request.full_url, json.loads(request.data)['model']))
        content = '{"label": "other", "policy_refusal": false}'
        reply = {'usage': {'cost': 0.001}, 'choices': [{'message': {'content': content}}]}
        return io.BytesIO(json.dumps(reply).encode())
    with patch('urllib.request.urlopen', urlopen):
        verdict = LLMJudge(env_file=env).classify('I could not finish.', {'mechanism': 'a fee'})
    url = 'https://openrouter.ai/api/v1/chat/completions'
    assert verdict['label'] == 'other' and sent == [(url, 'deepseek/deepseek-v4.1-flash')]
