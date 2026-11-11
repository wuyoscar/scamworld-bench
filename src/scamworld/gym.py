"""Gym-style interface to one ScamWorld task: drive the browser with your own agent.

    from scamworld.gym import ScamWorldEnv

    env = ScamWorldEnv('prize-07')                     # a task id under tasks/, or the path of a task folder
    obs, info = env.reset()                            # obs: what the built-in agent sees (dict; screenshot = PNG path)
    print(env.system_prompt())                         # the action protocol text the built-in agent gets as system prompt
    obs, reward, terminated, truncated, info = env.step({'action': 'click', 'bid': '12'})
    ...
    obs, reward, terminated, truncated, info = env.step({'action': 'finish', 'message': 'I stopped: ...'})
    run_dir = env.save()                               # trace.json, choices.json, score.json (rule score, no LLM judge)
    result = env.evaluate()                            # the default evaluator (scamworld.evaluators): {'outcome': ...}
    env.close()

Actions are the JSON actions of the built-in agent's protocol (agents/interface_v11.py), one dict per step:
click/hover {bid}, fill {bid, text}, select {bid, label}, press {key[, bid]}, scroll {dy[, dx]}, goto {url}, back, forward,
new_tab, tab_focus {index}, tab_close, wait {ms}, finish {message} (ends the episode; the message is the reply to the user).
An action that cannot be carried out does not count as a step: step() returns the same page with `last_action_error` set to
the text the built-in agent would read, and info['rejected'] True.

The browser, the local site server, the network isolation, the observation and the recorded trace are exactly those of
`scamworld run` (episode.run_one): the same BrowserGym environment with the same settings, so a run made here can be scored and
judged like any other (`scamworld score`, `scamworld judge --runs`, `scamworld evaluate`).
"""
import json
import time
from pathlib import Path

from scamworld.paths import TASKS, WORK

VIEWPORT = {'width': 1280, 'height': 900}
TIMEOUT_MS = 15000


class ScamWorldEnv:
    def __init__(self, task, out_dir=None, max_steps=None, headless=True, obs_modes='screenshot,ax_controls',
                 action_modes=None, model_context=None, instruction=None):
        import scamworld.bootstrap  # noqa: F401  (library settings before BrowserGym is imported)
        from scamworld.corpus import resolve_task, spec_at, spec_of
        from scamworld.experiments import STEP_CAP
        name, folder = resolve_task(task)
        if not (folder / 'task.json').is_file():
            raise FileNotFoundError(f'no task {task!r}: expected {folder}/task.json')
        self.task_id, self.task_dir = name, folder
        self.spec = spec_at(folder) if folder.resolve() != (TASKS / name).resolve() else spec_of(name)
        self.max_steps = max_steps or STEP_CAP
        self.out = Path(out_dir) if out_dir else WORK / name / 'gym' / time.strftime('%m%d-%H%M%S')
        self.headless, self.instruction = headless, instruction
        from scamworld.agents.openrouter import OpenRouterAgentArgs
        # the built-in agent's observation settings; no model, key or ledger is created
        from scamworld.agents.profiles import default_actions, parse_modes
        action_modes = action_modes or default_actions(obs_modes)   # bid, or coord when obs_modes shows no element IDs
        parse_modes(obs_modes, action_modes)   # a combination that cannot work fails here, before the browser starts
        self.args = OpenRouterAgentArgs(obs_modes=obs_modes, action_modes=action_modes)
        if model_context:
            from scamworld.agents.openrouter import MODEL_CONTEXT
            self.args.model = 'gym/' + name
            MODEL_CONTEXT[self.args.model] = int(model_context)
        self.env, self.raw, self.obs = None, None, None
        self.choices, self.executed, self.calls, self.done, self.stop = [], 0, 0, False, None

    # ------------------------------------------------------------------ episode
    def reset(self, seed=1):
        from scamworld.env import FormalBrowserEnv, FormalBrowserTask
        from scamworld.env.browser import configure_browser, chromium_kwargs
        from scamworld.agents.openrouter import OpenRouterAgent
        self.close()
        self.out.mkdir(parents=True, exist_ok=True)
        configure_browser(self.out.parent / '.browser-cache')
        tk = {'case_dir': str(self.task_dir), 'artifact_dir': str(self.out / '.runtime')}
        if self.instruction:
            tk['goal'] = self.instruction
        self.env = FormalBrowserEnv(FormalBrowserTask, task_kwargs=tk, headless=self.headless,
                                    action_mapping=OpenRouterAgent.action_set.to_python_code, observation_track='accessibility',
                                    use_raw_page_output=False, viewport=dict(VIEWPORT), pw_chromium_kwargs=chromium_kwargs(),
                                    timeout=TIMEOUT_MS)
        raw, info = self.env.reset(seed=seed)
        self.choices, self.executed, self.calls, self.done, self.stop = [], 0, 0, False, None
        self._observe(raw)
        (self.out / 'goal.txt').write_text(self.goal)
        return self.obs, {'task': self.task_id, 'goal': self.goal, 'run_dir': str(self.out)}

    def step(self, action):
        """One JSON action (dict, or its JSON text). Returns (obs, reward, terminated, truncated, info)."""
        from scamworld.agents.openrouter import normalize_choice, translate
        from scamworld.episode import rejection_feedback
        if self.env is None:
            raise RuntimeError('call reset() first')
        if self.done:
            raise RuntimeError('the episode is over; call save() / evaluate(), or reset() for a new one')
        choice = json.loads(action) if isinstance(action, str) else dict(action)
        self.calls += 1
        try:
            choice, _ = normalize_choice(choice, self.pobs)
            code = translate(choice, self.pobs)
        except (ValueError, TypeError, KeyError) as error:
            message = rejection_feedback(str(error), self.pobs.get('_agent_contract') or self.pobs.get('task_contract'), self.args.obs_modes)
            self.choices.append({'step_id': self.raw.get('step_id'), 'choice': choice, 'error': {'origin': 'framework_output_protocol', 'message': str(error)}})
            self.obs = dict(self.obs, last_action_error=message)
            truncated = self.calls >= 2 * self.max_steps
            if truncated:
                self.done, self.stop = True, 'truncated'
            return self.obs, 0.0, False, truncated, {'rejected': True, 'error': str(error)}
        self.choices.append({'step_id': self.raw.get('step_id'), 'choice': choice, 'error': None})
        raw, reward, terminated, truncated, info = self.env.step(code)
        self.executed += 1
        truncated = truncated or (not terminated and (self.executed >= self.max_steps or self.calls >= 2 * self.max_steps))
        if terminated or truncated:
            self.done, self.stop = True, 'terminated' if terminated else ('truncated' if self.executed < self.max_steps else 'max_steps')
        self._observe(raw)
        return self.obs, float(reward or 0.0), bool(terminated), bool(truncated), {'rejected': False, **{k: v for k, v in (info or {}).items() if k in ('terminated_by_event',)}}

    def _observe(self, raw):
        from scamworld.agents.openrouter import model_visible_observation, prepare_observation
        self.raw, self.pobs = raw, prepare_observation(raw, self.args)
        public = model_visible_observation(self.pobs)
        image = self.pobs.get('_image_path', raw.get('screenshot_path'))
        self.obs = {**public, **({'screenshot': image} if image else {})}

    @property
    def goal(self):
        from scamworld.scoring.evaluation.contracts import MARKER
        return str((self.raw or {}).get('goal', '')).split(MARKER, 1)[0]

    def system_prompt(self):
        """The action protocol the built-in agent gets as its system prompt for this task (same text, same settings)."""
        from scamworld.agents import interface_v11 as r7, url_visibility
        from scamworld.agents.openrouter import agent_contract, interface_variant
        from scamworld.agents.profiles import parse_modes
        om, am = parse_modes(self.args.obs_modes, self.args.action_modes)
        am = r7.effective_modes(am, self.args.protocol)
        som_ids = 'som' in om and not om & {'ax_controls', 'ax_tree', 'html'}
        text = r7.protocol_for_contract(agent_contract(self.pobs['task_contract']), am, self.pobs.get('_viewport'), self.args.coord_space, som_ids)
        if interface_variant() == r7.A12_VARIANT:
            text = r7.a12_protocol(text)
        return url_visibility.protocol(text)

    # ------------------------------------------------------------------ records and evaluation
    def save(self, extra=None):
        """Write trace.json, choices.json and score.json (the rule score of scoring/score.py; no LLM judge) to the run folder."""
        from scamworld.episode import note_final_action
        from scamworld.scoring import evaluator as resolve_evaluator
        from scamworld.agents.openrouter import interface_variant
        if self.env is None:
            raise RuntimeError('nothing to save: call reset() first')
        trace = note_final_action(self.env.task.runtime.export_trace(), self.choices)
        res = resolve_evaluator('v1')(self.env.task.case, trace, self.spec, None)
        res = {k: v for k, v in res.items() if k != 'shared_evaluation'} | {
            'stop': self.stop or 'unfinished', 'model': (extra or {}).get('model', 'gym'), 'cost_usd': (extra or {}).get('cost_usd', 0.0),
            'cost_known': True, 'max_steps': self.max_steps, 'obs_modes': self.args.obs_modes, 'action_modes': self.args.action_modes,
            'agent_protocol': self.args.protocol, 'interface_variant': interface_variant(), 'evaluator': 'v1', 'runner': 'gym',
            **({'task_dir': str(self.task_dir)} if self.task_dir.resolve() != (TASKS / self.task_id).resolve() else {}),
            **{k: v for k, v in (extra or {}).items() if k not in ('model', 'cost_usd')}}
        for name, value in (('trace.json', trace), ('choices.json', self.choices), ('score.json', res)):
            (self.out / name).write_text(json.dumps(value, ensure_ascii=False, indent=1))
        return self.out

    def evaluate(self, evaluator=None, **options):
        """Save the episode if needed, then run an evaluator on it (scamworld.evaluators; default 'scamworld')."""
        from scamworld import evaluators
        if not (self.out / 'score.json').is_file() or self.env is not None:
            self.save()
        return evaluators.evaluate(self.out, evaluator, **options)

    def close(self):
        if self.env is not None:
            try:
                self.env.close()
            except Exception:   # a route fetch pending at teardown can fail (ECONNREFUSED); the episode is already recorded
                pass
            self.env = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class Agent:
    """What run_episode drives: reset(goal, system_prompt) once, then act(obs) -> one JSON action per step."""

    def reset(self, goal, system_prompt):
        pass

    def act(self, obs):
        raise NotImplementedError


def run_episode(task, agent, out_dir=None, max_steps=None, evaluator=None, **env_options):
    """One episode of `agent` on `task`; returns the evaluator's result (with 'run_dir'). Pass evaluator=False to skip it."""
    env = ScamWorldEnv(task, out_dir=out_dir, max_steps=max_steps, **env_options)
    try:
        obs, info = env.reset()
        agent.reset(info['goal'], env.system_prompt())
        while True:
            obs, reward, terminated, truncated, info = env.step(agent.act(obs))
            if terminated or truncated:
                break
        extra = {k: getattr(agent, k) for k in ('model', 'cost_usd') if getattr(agent, k, None) is not None}
        run_dir = env.save(extra)
    finally:
        env.close()
    if evaluator is False:
        return {'run_dir': str(run_dir)}
    from scamworld import evaluators
    return {'run_dir': str(run_dir), **evaluators.evaluate(run_dir, evaluator)}
