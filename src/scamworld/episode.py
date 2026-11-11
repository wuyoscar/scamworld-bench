"""Live-agent run of one task: one agent episode, scored (for example to check that an agent understands a new task's
instruction).

Uses the OpenRouter agent (scamworld.agents.openrouter, cost-capped per episode by --max-cost) on the local BrowserGym
environment; nothing leaves the machine except the model API calls (the agent's and, with a judge, the reason judge's).

  scamworld run <task> [--runs N] [--tag T]          (same as: python -m scamworld.episode <task> ...)
Writes results/sitekit/<task>/pilot/<tag>-<i>/{trace,score,choices}.json
"""
import argparse, contextvars, functools, hashlib, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

from scamworld.agents import url_visibility
from scamworld.env import offsite
from scamworld.agents.interface_v11 import LEGACY_NAME, PROTOCOL_NAME
from scamworld.agents.model_settings import INTERFACE
from scamworld.agents.profiles import default_actions, parse_modes
from scamworld.paths import OPENWEIGHTS_ENV_FILE, REPO, TASKS, WORK


def evaluator_output_dir(out, evaluator):
    """Keep optional evaluator artifacts away from existing v1 run bytes."""
    out = Path(out)
    if evaluator == 'v1':
        return out
    if evaluator != 'v2':
        raise ValueError('Unknown evaluator: ' + str(evaluator))
    return out if out.parent.name == evaluator else out.parent / evaluator / out.name


def answer_envelope(contract):
    """Public answer envelope for a rejected final answer: declared field names and types only (same placeholders as the
    agent protocol), never rubric, evidence or clue text."""
    if contract.get('information_contract_version') != '3':
        return None
    def placeholder(rule):
        kind = rule.get('type')
        if isinstance(kind, list) and 'null' in kind: return None
        if kind == 'boolean': return False
        if kind == 'number': return 0
        if kind == 'array': return []
        if 'enum' in rule: return rule['enum'][0]
        return 'REPLACE WITH OBSERVED LITERAL'
    fields = contract['answer_schema']['properties']['answers']['properties']
    values = {name: placeholder(rule) for name, rule in fields.items()}
    if 'citations' not in contract['answer_schema']['properties']:   # a task's generic reply has none
        return {'action': 'answer', 'answer': {'answers': {name: ' or '.join(rule['enum']) if 'enum' in rule else
                                                           'REPLACE WITH YOUR ANSWER' if rule.get('type') == 'string' else placeholder(rule)
                                                           for name, rule in fields.items()}}}
    item = ((contract['answer_schema']['properties'].get('citations') or {}).get('items') or {}).get('properties') or {}
    ref = 'page_ref' if 'page_ref' in item else 'step_id'   # a10: the reply format the agent reads (openrouter.agent_contract)
    return {'action': 'answer', 'answer': {'answers': values,
            'citations': [{'field': name, ref: 0, 'quote': 'REPLACE WITH VISITED QUOTE'} for name in values]}}


PROGRESS_FILE = 'progress'


def touch_progress(out, executed, k):
    """<run dir>/progress after the reset and after every step, executed or rejected, so that a driver can tell a stuck episode from
    a slow one by the file's mtime. {"step": executed actions, "k": model replies so far, "t": UTC time}. Kept after the
    episode; the agent never sees it."""
    try:
        tmp = Path(out) / (PROGRESS_FILE + '.tmp')
        tmp.write_text(json.dumps({'step': executed, 'k': k, 't': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}))
        os.replace(tmp, Path(out) / PROGRESS_FILE)
    except OSError:
        pass


# JSON decode / output-format rejections from openrouter.decode_model_output and json.
DECODE_ERRORS = ('Expecting value', 'Expecting property name', "Expecting ','", "Expecting ':'", 'Extra data', 'Unterminated string',
                 'Invalid control character', 'Invalid \\escape', 'Expected one whole JSON fence', 'Duplicate JSON object key',
                 'Model JSON must be an object', 'Model output must be text', 'Nonstandard JSON number',
                 'The reply must be a single JSON object')   # used by every protocol (openrouter._decode_model_output)
                                                             # ('Model JSON must be an object' is earlier wording,
                                                             # still in older run records)


# a11 feedback on an undecodable reply: it says that nothing happened and where a message to the user goes. A reply in plain
# text is not read by the user, so the feedback must not leave the model believing that it was.
DECODE_FEEDBACK = ('No valid JSON action found in your reply, so nothing was done and nothing was sent to the user. '
                   'End your reply with exactly one JSON action; to tell the user something and end the session, use finish.')


FINAL_MESSAGE_ERRORS = ('The message is empty', 'The message is too long')   # interface_v11.final_message (a11)
# a11: the rejections about the element an action named, which get the control hint (interface_v11, openrouter.legacy_translate)
CONTROL_ERRORS = ('Target must be one observed matching element', 'Target is not an observed matching control',
                  'Hover target must be an observed control', 'Select requires', 'Input point must identify')


def rejection_feedback(message, contract, obs_modes):
    """Text sent back after a protocol rejection. Four branches: a rejected final answer gets the required envelope; an
    undecodable reply gets format advice; a run whose observation has no control IDs (screenshot only) is told to use
    coordinates; everything else keeps the original bid hint. a10: "the reply_format" names what r8 called
    task_contract.answer_schema; given openrouter.agent_contract, the envelope has the names the agent reads."""
    om = {m.strip() for m in (obs_modes or 'screenshot,ax_controls').split(',') if m.strip()}
    head = 'Your last action was rejected by the action protocol: ' + str(message) + '. '
    if (contract or {}).get('agent_interface_protocol') == PROTOCOL_NAME:   # a11: no reply format to resend
        # plain wording: what failed, and a control hint only where an element was the problem
        if str(message).startswith('Your reply contained more than one action'):   # openrouter.multi_action_message
            return str(message)
        if str(message).startswith(DECODE_ERRORS):   # notes may come first (a11): only the closing JSON action is required
            # never the parser's own text ("Expecting value: line 1 column 1 (char 0)")
            return DECODE_FEEDBACK
        head = 'Your last action could not be carried out: ' + str(message).rstrip('. ') + '.'
        if str(message).startswith(FINAL_MESSAGE_ERRORS) or not str(message).startswith(CONTROL_ERRORS):
            return head
        head += ' '
    if str(message).startswith('Expected the final answer in the reply_format'):
        env = answer_envelope(contract or {})
        return head + ('Please resend your reply in the reply_format'
                       + (', i.e. ' + json.dumps(env, ensure_ascii=False) + ' with the placeholders replaced by your own answers'
                          + (' and quotes' if 'citations' in env['answer'] else '') if env else '') + '.')
    if str(message).startswith(DECODE_ERRORS):   # undecodable reply -> format advice, not control advice
        env = answer_envelope(contract or {})
        return head + ('Reply with exactly one JSON object and no prose: one action, or the final answer in the reply_format'
                       + (', i.e. ' + json.dumps(env, ensure_ascii=False) + ' with the placeholders replaced by your own answers'
                          + (' and quotes' if 'citations' in env['answer'] else '') if env else '') + '.')
    if not om & {'som', 'ax_controls', 'ax_tree', 'html'}:
        return head + 'This observation supplies no control IDs; act with click_xy, fill_xy or press_xy at screenshot coordinates and try again.'
    where = ('in the observation (by its bid)' if 'ax_controls' in om else
             'by its bid label (set-of-marks numbers / [bid] in the text observation); match the action to the control type')
    return head + 'Choose a control ' + where + ' and try again.'


CODE_ENV = {'commit': 'SCAMWORLD_CODE_COMMIT', 'tag': 'SCAMWORLD_CODE_TAG', 'tree_shas_sha256': 'SCAMWORLD_TREE_SHAS_SHA256'}
_CODE = None


def code_identity():
    """Repository version this process runs, recorded in score.json (`code`), computed once from the first source that
    applies: the driver's variables SCAMWORLD_CODE_COMMIT / SCAMWORLD_CODE_TAG / SCAMWORLD_TREE_SHAS_SHA256 (when the
    commit or the tree hash is set); else <repo>/TREE-SHAS.json (when the file exists); else this checkout's git HEAD
    with the first of its tags in sort order and the number of tracked files that differ."""
    global _CODE
    if _CODE is None:
        env = {k: os.environ.get(v) or None for k, v in CODE_ENV.items()}
        tree = REPO / 'TREE-SHAS.json'
        if env['commit'] or env['tree_shas_sha256']:
            _CODE = {**env, 'source': 'TREE-SHAS.json (driver)'}
        elif tree.is_file():
            doc = json.loads(tree.read_text())
            _CODE = {'commit': doc.get('git_head'), 'tag': doc.get('git_tag'), 'tree_shas_sha256': hashlib.sha256(tree.read_bytes()).hexdigest(),
                     'dirty_files': doc.get('git_dirty_files'), 'source': 'TREE-SHAS.json'}
        else:
            git = lambda *args: subprocess.run(['git', '-C', str(REPO), *args], capture_output=True, text=True, timeout=60)
            try:
                head = git('rev-parse', 'HEAD')
                tags = sorted(git('tag', '--points-at', 'HEAD').stdout.split())
                dirty = [l for l in git('status', '--porcelain', '--untracked-files=no').stdout.splitlines() if l.strip()]
                _CODE = {'commit': head.stdout.strip() if head.returncode == 0 else None,
                         'tag': tags[0] if tags else None,
                         'tree_shas_sha256': None, 'dirty_files': len(dirty), 'source': 'git'}
            except (OSError, subprocess.SubprocessError):
                _CODE = {'commit': None, 'tag': None, 'tree_shas_sha256': None, 'source': 'unknown'}
    return _CODE


TOKEN_KEYS = ('agent_input', 'agent_output', 'agent_reasoning', 'agent_api_calls', 'judge_input', 'judge_output')


def token_block(agent, judge):
    """score.json `tokens`: the agent's token totals over every model call it made and the judge's over its calls, all ints;
    an absent agent, judge or usage counts 0 (the field is kept)."""
    have = {**(getattr(agent, 'tokens', None) or {}), **(getattr(judge, 'tokens', None) or {})}
    return {k: int(have.get(k) or 0) for k in TOKEN_KEYS}


INFRA_ORIGINS = ('transport_error', 'provider_http_error', 'provider_response_format')   # empty/non-string provider reply: retried like an HTTP error


class EpisodeSetupError(RuntimeError):
    """The episode stopped before the agent's first model call (the task or evaluator, the agent's key or model id, a
    budget ledger that SCAMWORLD_BUDGET_REQUIRED=1 asks for and that is missing, the reason judge's key, the browser,
    env.reset, building the first request (prompt, screenshot) before it is sent): nothing was billed. WRAP records it as an infrastructure error with a known cost of 0, so a paid run replays it
    instead of halting on unknown billing; a crash after a model call keeps cost_known False."""


JUDGE_STARTED = contextvars.ContextVar('judge_started', default=False)


def tag_judge_bill(fn):
    """A failure after the reason judge was called may follow a paid call: tag it for WRAP (judge_may_be_billed)."""
    @functools.wraps(fn)
    def run(*a, **k):
        JUDGE_STARTED.set(False)
        try:
            return fn(*a, **k)
        except Exception as e:
            if JUDGE_STARTED.get(): e.judge_may_be_billed = True
            raise
    return run


def check_tree():
    """Checked before each episode of a driver that runs many episodes on one tree and sets SCAMWORLD_TREE_SHAS_SHA256 to
    the hash of the tree's TREE-SHAS.json. If that file now hashes differently, the tree changed after the driver started
    and the episode would run other code than the driver recorded: it stops before the agent's first call as a setup error
    (cost 0)."""
    expected, tree = os.environ.get(CODE_ENV['tree_shas_sha256']), REPO / 'TREE-SHAS.json'
    if expected and tree.is_file() and hashlib.sha256(tree.read_bytes()).hexdigest() != expected:
        raise EpisodeSetupError('TREE-SHAS.json changed since this run started; restart it on the new tree')


def error_stop(origin):
    """Stop reason of an episode whose agent call returned no action, from the error origin (openrouter.error_origin).
    reasoning_exhausted: the output cap ended two calls of one step before any answer; a model outcome, not rerun."""
    return ('infra_error' if origin in INFRA_ORIGINS else 'protocol_error' if origin == 'framework_output_protocol' else
            'reasoning_exhausted' if origin == 'reasoning_exhausted' else
            'provider_refused' if origin == 'provider_refused' else 'agent_error_or_budget')   # 403 twice, not re-run


def repo_relative(path):
    """A path as recorded in score.json: relative to the repository when inside it, else absolute."""
    path = Path(path).resolve()
    return path.relative_to(REPO.resolve()).as_posix() if path.is_relative_to(REPO.resolve()) else str(path)


def step_text(extra_info):
    """What the model returned at this step, kept in choices.json only - `model_output` (content, reasoning text,
    finish_reason; agents/openrouter.model_output) and, when the output cap cut a call before any answer,
    `exhausted_outputs` of those calls. The next observation never carries it."""
    from scamworld.agents.openrouter import model_output
    out = {'model_output': model_output(extra_info.get('api_response'))}
    cut = [e.get('model_output') for e in extra_info.get('reasoning_exhausted') or [] if isinstance(e, dict)]
    return out | ({'exhausted_outputs': cut} if cut else {})


def parsed_from(format_normalization, action_normalization):
    """choices.json `parsed_from` of a step read through a format fallback: "dsml" (a DSML tool call,
    openrouter.dsml_action), "answer_nesting" (answer fields one level too high, openrouter.renest_answer),
    "brace_repair" (a final answer missing only its closing brackets, openrouter.brace_repair), "citations_hoisted"
    (valid JSON with citations inside answers, openrouter.hoist_citations), "empty_field_dropped" (undeclared empty
    answer keys, openrouter.drop_empty_undeclared), "dsml_hybrid" (one DSML invoke written with JSON key/value pairs,
    openrouter.dsml_hybrid), the layout repairs of openrouter.relaxed_answer ("bare_answers", "answers_wrapped",
    "citations_moved", "citations_merged", "citations_absent", "undeclared_field_dropped"), "long_text_accepted" (a
    free-text answer value over its maxLength) or several joined by "+"; None for every other step."""
    tags = [n.get('parsed_from') for n in (format_normalization, action_normalization) if isinstance(n, dict) and n.get('parsed_from')]
    return '+'.join(tags) or None


def format_fallbacks(choices):
    """Per episode, for score.json: steps read through each fallback and steps whose reply carried DSML markup at all (converted
    or not), so that conversion rates can be reported."""
    from scamworld.agents.openrouter import DSML
    tags = [str(c.get('parsed_from') or '').split('+') for c in choices]
    from scamworld.agents.openrouter import REPAIR_TAGS
    return {'dsml': sum('dsml' in t for t in tags), 'answer_nesting': sum('answer_nesting' in t for t in tags),
            **{k: sum(k in t for t in tags) for k in REPAIR_TAGS},
            'dsml_markup_steps': sum(DSML in ((c.get('model_output') or {}).get('content') or '') for c in choices)}


# The agent's per-episode backstops; neither is a budget the agent is told of.
# Model calls: the step loop makes at most 2 x max_steps agent turns (rejected actions included) and a turn at most 2
# calls (one reasoning-exhausted resend), so 4 x max_steps never ends an episode before the loop does (a lower cap,
# such as the 30-call default of OpenRouterAgentArgs, would end episodes before the step cap, experiments.STEP_CAP,
# takes effect).
# Cost: 5 USD for every model, above 1.5 x the 60-step estimate of each paid backbone (configs/agent-models.json
# prices) except moonshotai/kimi-k3, which is above 1.5 x the measured p99 of its episodes; a lower cap would stop a
# paid model before its 60 steps. Spend of an experiment is bounded by
# `scamworld exp run --budget`; this cap only stops a runaway.
# choices.json records which cap ended an episode (stop_reason call_budget / cost_budget).
MAX_CALLS_PER_STEP = 4
MAX_COST_USD = 5.0
DEAD_LINK_LOOP = 3   # 404 pages opened by an episode that stopped at the step cap: dead_link_loop


def note_agent_controls(runtime, obs, pobs):
    """Which accessibility nodes the agent's list left out at this observation, for the trace only:
    `agent_controls_dropped` (indices of public_accessibility_nodes, [] when nothing was cut) and `agent_controls_chars`
    {shown, total} (openrouter.prepare_observation _controls_dropped / _controls_chars)."""
    if '_controls_chars' not in pobs:
        return
    record = next((o for o in reversed(runtime.observations) if o.get('observation_id') == obs.get('observation_id')), None)
    if record is not None:
        record.update(agent_controls_dropped=list(pobs['_controls_dropped']), agent_controls_chars=dict(pobs['_controls_chars']))


def note_final_action(trace, choices):
    """The action name the agent ended with is noted in the trace: final_answer `via` (finish, or what is read as
    finish: send_msg_to_user / stop / answer / report_infeasible; None for a reply with no action) and `written_as_json` (an
    object written into the text as JSON; interface_v11.final_message_text)."""
    from scamworld.agents.interface_v11 import is_final, final_message_text, final_message_value
    final = trace.get('final_answer')
    last = next((c.get('choice') for c in reversed(choices) if isinstance(c, dict) and c.get('choice') and not c.get('error')), None)
    if not isinstance(final, dict) or set(final) != {'message'} or not is_final(last):
        return trace
    if final_message_text(last) == final['message']:
        final.update(via=last.get('action'), written_as_json=not isinstance(final_message_value(last), str))
    return trace


@tag_judge_bill
def run_one(cid, out, max_steps, model=None, max_cost=MAX_COST_USD, judge=True, obs_modes=None, action_modes=None, instruction=None, coord_space=None, task_path=None, evaluator='v1', agent_protocol=PROTOCOL_NAME, overlay=None, base_url=None, api_key_env=None, endpoints_file=None):
    try:   # everything up to the agent's first model call is setup: a failure is an EpisodeSetupError (nothing was billed)
        from scamworld.scoring import evaluator as resolve_evaluator
        from scamworld.agents.openrouter import interface_variant
        interface_variant()   # an unknown SCAMWORLD_INTERFACE_VARIANT fails here, before the browser starts
        score_episode = resolve_evaluator(evaluator)
        out = evaluator_output_dir(out, evaluator)
        if task_path is not None and instruction is not None:
            raise ValueError('External tasks cannot use an unreviewed instruction override')
        import scamworld.bootstrap  # noqa: F401
        from scamworld.env import FormalBrowserEnv, FormalBrowserTask
        from scamworld.env.browser import configure_browser, chromium_kwargs
        from scamworld.agents.openrouter import OpenRouterAgentArgs, OpenRouterAgent
        from scamworld.corpus import resolve_task, spec_at, spec_of
        from scamworld.scoring.judge import LLMJudge
        # a task folder given by its path
        if (Path(cid).expanduser() / 'task.json').is_file() and not (TASKS / str(cid)).is_dir():
            cid, d = resolve_task(cid); spec = spec_at(d)
        else:
            d = TASKS / cid
            spec = spec_of(cid)   # adds the derived prefix
        out.mkdir(parents=True, exist_ok=True)
        args = OpenRouterAgentArgs(max_cost_usd=max_cost, protocol=agent_protocol, max_calls=MAX_CALLS_PER_STEP * max_steps)
        if model: args.model = model; args.agent_name = 'ScamWorld-' + model.split('/')[-1]
        if base_url: args.base_url, args.api_key_env = base_url, api_key_env   # your own OpenAI-compatible API (endpoint.py)
        if endpoints_file: args.endpoints_file = str(endpoints_file)
        if args.model.startswith(('google/gemma', 'qwen/', 'z-ai/', 'deepseek/', 'meta-llama/', 'mistralai/')):
            args.env_file = str(OPENWEIGHTS_ENV_FILE)
        if obs_modes: args.obs_modes = obs_modes
        if action_modes: args.action_modes = action_modes
        elif obs_modes: args.action_modes = default_actions(obs_modes)   # coord when the observation has no element IDs
        if isinstance(getattr(args, 'obs_modes', None), str) and isinstance(getattr(args, 'action_modes', None), str):
            parse_modes(args.obs_modes, args.action_modes)   # a bad combination fails here, before the browser starts
        if coord_space: args.coord_space = coord_space   # per-model pointing convention (experiments.coord_space)
        agent = args.make_agent()   # a missing key or a model that cannot run fails here
        if not args.model.startswith('cz/'):   # SCAMWORLD_BUDGET_REQUIRED=1, no ledger: refused before the browser
            from scamworld.budget import require_budget
            require_budget(args.model, getattr(agent, 'budget_transport', None))
        reason_judge = LLMJudge(env_file=OPENWEIGHTS_ENV_FILE, prompt='v4') if judge else None   # reads its key here
        configure_browser(out.parent / '.browser-cache')
        tk = {'case_dir': str(d), 'artifact_dir': str(out / '.runtime')}
        if task_path is not None: tk['task_path'] = str(Path(task_path).resolve())
        if overlay is not None: tk['overlay'] = str(Path(overlay).resolve())   # generated task condition (option overlay)
        if instruction: tk['goal'] = instruction   # template instance: same site and contract, other instruction text
        if agent_protocol == LEGACY_NAME: tk['final_reply'] = 'structured'   # a11: every other run ends with a message
        env = FormalBrowserEnv(FormalBrowserTask, task_kwargs=tk,
                               headless=True, action_mapping=OpenRouterAgent.action_set.to_python_code,
                               observation_track='accessibility', use_raw_page_output=False,
                               viewport={'width': 1280, 'height': 900}, pw_chromium_kwargs=chromium_kwargs(),
                               timeout=15000)   # 15 s (BrowserGym default 5 s): heavy captures under load
    except EpisodeSetupError:
        raise
    except Exception as e:   # the key is never in these messages: they name the key file, not its content
        raise EpisodeSetupError(f'{type(e).__name__}: {e}') from e
    choices, stop, retries = [], 'max_steps', 0
    try:
        try:   # no model call before the loop: a failure here is a setup failure (EpisodeSetupError)
            obs, _ = env.reset(seed=1)
            # Keep the task text identical to what the model sees; the response/input
            # contract is a separate engineering artifact, not user instructions.
            from scamworld.scoring.evaluation.contracts import MARKER, contract_from_goal
            (out / 'goal.txt').write_text(obs.get('goal', '').split(MARKER, 1)[0])
            (out / 'public-task-contract.json').write_text(json.dumps(contract_from_goal(obs.get('goal', '')), ensure_ascii=False, indent=2) + '\n')
            from scamworld.agents.openrouter import generic_fields
            reply_format = ('message' if agent_protocol == PROTOCOL_NAME else   # one free-text message
                            'generic' if generic_fields(contract_from_goal(obs.get('goal', ''))) else 'fields')
            touch_progress(out, 0, 0)
        except Exception as e:
            raise EpisodeSetupError(f'{type(e).__name__}: {e}') from e
        executed = 0
        for _ in range(max_steps * 2):   # step budget counts executed actions; rejected ones only use the outer cap
            if executed >= max_steps:
                break
            try:   # agent.calls counts each model request before it is sent: 0 after an exception means nothing was sent
                pobs = agent.obs_preprocessor(obs)
                note_agent_controls(env.task.runtime, obs, pobs)
                action, info = agent.get_action(pobs)
            except Exception as e:
                if getattr(agent, 'calls', 1):
                    raise
                raise EpisodeSetupError(f'{type(e).__name__}: {e}') from e
            ex = getattr(info, 'extra_info', None) or {}
            fn, an = ex.get('format_normalization') or {}, ex.get('action_normalization') or {}   # persist applied normalisations per step
            choices.append({**({'projection_truncation': pobs['_projection_truncation']} if pobs.get('_projection_truncation') else {}),
                            **({'format_normalization': {k: fn[k] for k in ('reason', 'duplicate_identical_key') if k in fn}} if fn.get('applied') else {}),
                            **({'parsed_from': parsed_from(fn, an)} if parsed_from(fn, an) else {}),   # format fallbacks of the parser
                            # resends of this step: timeouts and resets on the free gateway (transport_retry);
                            # timeouts, resets and transient HTTP statuses on a direct API (agents/direct.py)
                            **({'transport_retries': ex['transport_retries']} if ex.get('transport_retries') else {}),
                            **({'call_sec': ex['call_sec']} if ex.get('call_sec') else {}),   # wall seconds of each model HTTP call
                            **({'stop_reason': ex['stop_reason']} if ex.get('stop_reason') else {}),   # the agent's own stop: call_budget, cost_budget, billing_unknown
                            **({'action_normalization': an.get('reason')} if an.get('applied') else {}),
                            **({'repair_reason': an['repair_reason'], **({'repair_details': an['repair_details']} if an.get('repair_details') else {})} if an.get('repair_reason') else {}),   # parser repairs
                            **({'notes': fn['notes']} if fn.get('notes') else {}),   # a11: plain-text notes before the action
                            'step_id': obs.get('step_id'), 'choice': ex.get('controller_choice'),
                            'error': ex.get('api_or_protocol_error'), 'cost_known': ex.get('cost_known', True), 'budget_receipt': ex.get('budget_receipt'), 'raw': (ex.get('format_normalization') or {}).get('raw_text') if ex.get('api_or_protocol_error') else None, 'cost': (getattr(info, 'stats', None) or {}).get('cost_usd'), 'in_tok': (getattr(info, 'stats', None) or {}).get('input_tokens'), 'out_tok': (getattr(info, 'stats', None) or {}).get('output_tokens'), 'reason_tok': (getattr(info, 'stats', None) or {}).get('reasoning_tokens'), 'provider': (getattr(info, 'stats', None) or {}).get('provider') or (ex.get('provider') if ex.get('transport') else None),
                            **({'transport': ex['transport']} if ex.get('transport') else {}),   # 'direct': the vendor's own API (agents/direct.py)
                            **step_text(ex)})
            err = ex.get('api_or_protocol_error') or {}
            if action is None and err.get('origin') == 'framework_output_protocol' and retries < 3:
                # report the rejected action back (like BrowserGym last_action_error) instead of ending; the limit counts
                # CONSECUTIVE rejections (reset after an executed action), so SoM-only agents can learn control types.
                retries += 1
                from scamworld.scoring.evaluation.contracts import contract_from_goal as _cfg
                # a10: the contract with the reply format the agent reads (field names, page_ref)
                agent.messages.append({'role': 'user', 'content': rejection_feedback(err.get('message'), pobs.get('_agent_contract') or pobs.get('task_contract') or _cfg(obs.get('goal', '')), obs_modes)})
                touch_progress(out, executed, len(choices))
                continue
            if action is not None:
                retries = 0
            if action is None:
                stop = error_stop(err.get('origin')); break
            obs, _, term, trunc, _ = env.step(action); executed += 1
            if fn.get('notes') and env.task.runtime.actions:   # a11: the agent's notes before its action, trace only
                env.task.runtime.actions[-1]['agent_notes'] = fn['notes']
            touch_progress(out, executed, len(choices))
            if term or trunc:
                stop = 'terminated' if term else 'truncated'; break
        trace = env.task.runtime.export_trace()
        note_final_action(trace, choices)
        (out / 'trace.json').write_text(json.dumps(trace, ensure_ascii=False, indent=1))
        (out / 'choices.json').write_text(json.dumps(choices, ensure_ascii=False, indent=1))
        context = env.task.case.get('layer_context')
        if context:
            spec = context['scoring_spec']
        JUDGE_STARTED.set(reason_judge is not None)   # from here a failure may follow a paid judge call
        res = score_episode(env.task.case, trace, spec, reason_judge)
        judge_cost = reason_judge.cost if reason_judge else 0.0
        if context:
            raise RuntimeError('layer_context comes only from the retired external task packages')
        res['agent_protocol'] = agent.args.protocol
        res['effective_action_modes'] = sorted(agent._modes()[1])
        res['evaluator'] = evaluator
        trunc = [c['projection_truncation'] for c in choices if c.get('projection_truncation')]
        if trunc:   # ax_tree/html projection cut: how often and how much of the page was shown
            fr = [v['shown'] / v['total'] for t in trunc for v in t.values() if v['total']]
            res['projection_truncation'] = {'steps': len(trunc), 'steps_truncated': sum(any(v['shown'] < v['total'] for v in t.values()) for t in trunc),
                                            'min_shown_fraction': round(min(fr), 4) if fr else None}
    finally:
        close_error = None
        try:
            env.close()
        except Exception as e:   # pending route fetches can fail at teardown (ECONNREFUSED); the episode is already scored
            close_error = str(e)[:200]
    cost_known = agent.cost_known and (reason_judge.cost_known if reason_judge else True)
    budget_state = None
    if agent.budget_transport:
        budget_state = {k:v for k,v in agent.budget_transport.ledger.snapshot().items() if k != 'calls'}
        cost_known = cost_known and budget_state['held_microusd'] == 0
    # agents/endpoint.py: the configured endpoint (name, base_url, model; price and extra_body when set; never the key)
    endpoint_entry = ({'transport': 'endpoint', 'endpoint': agent.endpoint.record()}
                      if getattr(agent, 'transport', None) == 'endpoint' else {})
    # reply_format: 'message' (one free-text message), 'generic' {status, reason} or 'fields' (the task's fields)
    res = {k: v for k, v in res.items() if k != 'shared_evaluation'} | {'stop': stop, 'cost_usd': round(agent.cost + judge_cost, 6) if cost_known else None,
                                                                         'cost_known': cost_known, 'budget_state': budget_state,
                                                                         'known_cost_usd': round(agent.cost + judge_cost, 6),
                                                                         'agent_cost_usd': agent.cost if agent.cost_known else None, 'judge_cost_usd': judge_cost if not reason_judge or reason_judge.cost_known else None, 'model': agent.args.model,
                                                                         'obs_modes': agent.args.obs_modes, 'action_modes': agent.args.action_modes, 'coord_space': agent.args.coord_space,
                                                                         'interface': INTERFACE, 'reasoning_profile': getattr(agent, 'settings', {}).get('profile'), 'url_visibility': url_visibility.mode(),
                                                                         'agent_max_tokens': getattr(agent, 'max_tokens', None), 'code': code_identity(),
                                                                         'max_steps': max_steps, 'max_calls': getattr(agent.args, 'max_calls', None), 'max_cost_usd': getattr(agent.args, 'max_cost_usd', None), 'tokens': token_block(agent, reason_judge),
                                                                         'format_fallbacks': format_fallbacks(choices),
                                                                         'reply_format': reply_format,
                                                                         # a 404 is a diagnostic only; an episode that kept opening
                                                                         # 404 pages until the step cap is flagged on its own
                                                                         'dead_link_loop': stop == 'max_steps' and (res.get('not_found_opens') or 0) >= DEAD_LINK_LOOP,
                                                                         **({'transport': 'direct', 'provider': agent.args.model.partition(':')[0]} if getattr(agent, 'transport', None) == 'direct' else {}),   # openai:/anthropic:/google: models
                                                                         # provider = the endpoint(s) that
                                                                         # served the calls (served_by)
                                                                         **({'transport': 'openrouter', 'provider': served_by(choices)} if getattr(agent, 'transport', None) == 'openrouter' else {}),
                                                                         **endpoint_entry,
                                                                         **({'system_note': os.environ['SCAMWORLD_SYSTEM_NOTE']} if os.environ.get('SCAMWORLD_SYSTEM_NOTE') else {}),   # experiment option system_note
                                                                         **({'interface_variant': interface_variant()} if agent_protocol == PROTOCOL_NAME else {}),   # a12 default, a11 for the layout of the paper's runs
                                                                         **({'offsite': offsite.mode()} if offsite.on() else {}),   # experiment option offsite
                                                                         **({'task_overlay': repo_relative(overlay)} if overlay is not None else {}),
                                                                         **({'task_dir': str(d)} if Path(d).resolve() != (TASKS / cid).resolve() else {}),   # a task folder outside tasks/
                                                                         **({'close_error': close_error} if close_error else {})}
    (out / 'trace.json').write_text(json.dumps(trace, ensure_ascii=False, indent=1))
    (out / 'choices.json').write_text(json.dumps(choices, ensure_ascii=False, indent=1))
    (out / 'score.json').write_text(json.dumps(res, ensure_ascii=False, indent=1))
    return res


def has_judge_key():
    """An OpenRouter key for the in-episode judge is configured (OPENWEIGHTS_ENV_FILE)."""
    from dotenv import dotenv_values
    return OPENWEIGHTS_ENV_FILE.is_file() and bool((dotenv_values(OPENWEIGHTS_ENV_FILE, interpolate=False).get('OPENROUTER_API_KEY') or '').strip())


def served_by(choices):
    """The provider that served an OpenRouter episode's model calls (choices.json `provider`): one name, a sorted list when the calls
    went to more than one endpoint, None when no call returned."""
    names = sorted({c['provider'] for c in choices if isinstance(c.get('provider'), str)})
    return names[0] if len(names) == 1 else names or None


def build_parser():
    ap = argparse.ArgumentParser(prog='scamworld run', description='Run one agent episode on a task and score it.'); ap.add_argument('case', metavar='task', help='task id under tasks/, or the path of a task folder'); ap.add_argument('--runs', type=int, default=1, help='number of episodes (default 1)')
    from scamworld.experiments import STEP_CAP
    ap.add_argument('--tag', default=time.strftime('%m%d-%H%M'), help='name for the run folder (default: the current time)'); ap.add_argument('--max-steps', type=int, default=STEP_CAP, help='step limit per episode (default %(default)s)')
    ap.add_argument('--model', default=None,
                    help='model id (default: google/gemma-4-31b-it via OpenRouter). Paid closed models (Gemini, OpenAI, '
                         'Anthropic, xAI ids on OpenRouter; openai:/anthropic:/google:<id> on the vendor\'s own API) are '
                         'refused unless --allow-paid.')
    ap.add_argument('--allow-paid', action='store_true',
                    help='allow paid closed models (billed to your OpenRouter key, or to the vendor key of '
                         'openai:/anthropic:/google: ids)')
    ap.add_argument('--max-cost', type=float, default=MAX_COST_USD, help='stop an episode when its cost reaches this many USD (default %(default)s)')
    ap.add_argument('--protocol', choices=[LEGACY_NAME, PROTOCOL_NAME], default=PROTOCOL_NAME, help=argparse.SUPPRESS)
    ap.add_argument('--obs', default=None, help='obs modes, e.g. screenshot,som,ax_controls,ax_tree,html (default screenshot,ax_controls)')
    ap.add_argument('--actions', default=None, help='action modes, e.g. bid,coord,hover,nav,tabs (default bid; coord when --obs shows no element IDs, e.g. --obs screenshot)')
    ap.add_argument('--task', type=Path, help=argparse.SUPPRESS)
    ap.add_argument('--evaluator', default='v1', choices=['v1', 'v2'], help=argparse.SUPPRESS)
    ap.add_argument('--base-url', help='any OpenAI-compatible API for --model, e.g. http://localhost:8000/v1 (agents/endpoint.py)')
    ap.add_argument('--api-key-env', help='environment variable holding the key of --base-url (none: no key sent)')
    ap.add_argument('--endpoints', help='endpoints file for --model endpoint:<name> (default configs/endpoints.json)')
    ap.add_argument('--judge', choices=['auto', 'v4', 'off'], default='auto',
                    help='in-episode reason judge: v4 (OpenRouter key in .env.openweights), off, or auto (v4 when that key exists)')
    ap.add_argument('--out', type=Path, help='run folder (default results/sitekit/<task>/pilot/<tag>-<i>)')
    return ap


def _last_error(out):
    """The last choices.json entry is a model-server error (it has a non-null `error`)."""
    try:
        entries = json.loads((Path(out) / 'choices.json').read_text())
    except (OSError, ValueError):
        return False
    return bool(entries) and isinstance(entries[-1], dict) and entries[-1].get('error') is not None


def model_error_note(out):
    """Where the model server's error reply of a finished episode is recorded: the last choices.json entry that has an `error`
    object (error_type, stage, origin, message, and for an HTTP error http_status and body)."""
    path = Path(out) / 'choices.json'
    try:
        entries = json.loads(path.read_text())
    except (OSError, ValueError):
        return f'no model reply was recorded ({path} is missing or unreadable)'
    for i in range(len(entries) - 1, -1, -1):
        err = entries[i].get('error') if isinstance(entries[i], dict) else None
        if isinstance(err, dict):
            detail = {k: err[k] for k in ('error_type', 'origin', 'http_status', 'message', 'body') if err.get(k) not in (None, '')}
            where = f'{path}: entry {i} (0-based, the last with an error)'
            origin = err.get('origin')
            if entries[i].get('model_output') is None and origin == 'provider_response_format':
                head = f'the reply had no message and was not kept (model_output is null); field error.message of {where} has what could be read'
            elif origin == 'provider_http_error':
                head = f"the server's HTTP reply is in {where}, field error.body (status in error.http_status)"
            elif origin == 'transport_error':
                head = f'no reply was received; the failure is in {where}, field error'
            elif origin == 'provider_response_format':
                head = f'the reply could not be read; field error of {where} has the reason, field model_output what the server sent'
            else:
                head = f'the failure is recorded in {where}, field error'
            return head + ': ' + json.dumps(detail, ensure_ascii=False)
    return f'{path} has no entry with an "error" field'


def judge_failure_note(score, run_dir):
    """One line for stderr when the in-episode reason judge call failed (score.json reason_judge label judge_error), else
    None. That stop has no verdict: the rules evaluator leaves it pending and `scamworld judge --runs` judges it again."""
    from scamworld.scoring.outcome import STOP_PATHS
    verdict = score.get('reason_judge')
    if (score.get('reason_method') != 'llm' or score.get('behavior_path') not in STOP_PATHS
            or not isinstance(verdict, dict) or verdict.get('label') != 'judge_error'):
        return None
    why = ' '.join(str(verdict.get('why') or 'no reason given').split())
    why = re.sub(r'sk-[A-Za-z0-9_-]{8,}', '[REDACTED]', why)   # key-shaped text
    return (f'the reason judge failed ({why[:200]}): this stop is not judged; '
            f'run scamworld judge --runs {run_dir} --write to judge it')


def drop_unused_run_dir(path):
    """After a setup failure: remove the run folder when it holds no result, that is no file or only empty ones (a setup
    failure writes no score.json; the files of a failure after env.reset are not empty and stay). True when removed."""
    path = Path(path)
    if not path.is_dir() or any(f.stat().st_size for f in path.rglob('*') if f.is_file()):
        return False
    shutil.rmtree(path, ignore_errors=True)
    return not path.exists()


def main(argv=None):
    a = build_parser().parse_args(argv)
    from scamworld.agents.direct import is_direct
    from scamworld.agents.endpoint import is_endpoint
    own_api = bool(a.base_url) or is_endpoint(a.model)
    if a.model and not own_api and (is_direct(a.model) or any(k in a.model for k in ('gemini', 'openai/', 'anthropic/', 'x-ai/'))) and not a.allow_paid:
        from scamworld.agents.direct import KEY_NAMES
        route = ("the vendor's own API (billed to the " + KEY_NAMES.get(a.model.partition(':')[0], 'vendor key')
                 + ' in SCAMWORLD_DIRECT_ENV)' if is_direct(a.model)
                 else 'OpenRouter (billed to your OpenRouter key)')
        sys.exit(f'refusing paid model {a.model}: it is called through {route}; paid closed models need --allow-paid')
    judge = a.judge == 'v4' or (a.judge == 'auto' and has_judge_key())
    if a.judge == 'v4' and not has_judge_key():
        print(f'scamworld run: --judge v4 needs an OpenRouter key: no OPENROUTER_API_KEY in {OPENWEIGHTS_ENV_FILE}',
              file=sys.stderr)
        sys.exit(2)
    if a.judge == 'auto' and not judge:
        print('note: no OpenRouter key in ' + str(OPENWEIGHTS_ENV_FILE) + ', so no in-episode judge; score the run with '
              '`scamworld evaluate <run dir>` (docs/evaluators.md)', file=sys.stderr)
    base = WORK / Path(a.case).name / 'pilot'
    infra_errors = 0
    created = set()   # folders this call creates; the empty ones are removed again when every run failed at setup
    only_setup = True
    for i in range(a.runs):
        out = (a.out if a.runs == 1 else a.out / str(i)) if a.out else base / f'{a.tag}-{i}'
        run_dir = evaluator_output_dir(out, a.evaluator)
        existed = run_dir.exists()
        created.update(q for q in (run_dir, *run_dir.parents) if not q.exists())
        try:
            r = run_one(a.case, out, a.max_steps, a.model, a.max_cost, judge=judge, obs_modes=a.obs, action_modes=a.actions, task_path=a.task, evaluator=a.evaluator, agent_protocol=a.protocol,
                        base_url=a.base_url, api_key_env=a.api_key_env, endpoints_file=a.endpoints)
        except Exception as e:  # e.g. reset timeout on a heavy capture: record, keep going
            infra_errors += 1
            setup = isinstance(e, EpisodeSetupError)   # nothing was billed before the first model call
            only_setup = only_setup and setup
            if setup and not existed:
                drop_unused_run_dir(evaluator_output_dir(out, a.evaluator))   # no empty run folder is left behind
            print(json.dumps({'behavior_path': 'run_crashed', 'overall': None, 'reason_met': None, 'stop': 'infra_error',
                              'cost_usd': 0.0 if setup else None,
                              **({'cost_known': True, 'infra_stage': 'setup'} if setup else {}),
                              'error': str(e)}, ensure_ascii=False))
            print(f'scamworld run: episode {i} failed before it finished ({type(e).__name__}): {e}', file=sys.stderr); continue
        only_setup = False
        print(json.dumps({k: r.get(k) for k in ('behavior_path', 'overall', 'deceived', 'reported', 'report_truthful', 'reason_met',
                                                 'pages_opened', 'steps', 'stop', 'cost_usd', 'model')}, ensure_ascii=False))
        stopped = r.get('stop')
        where = evaluator_output_dir(out, a.evaluator)
        note = judge_failure_note(r, where)
        if note:
            print(f'scamworld run: episode {i}: {note}', file=sys.stderr)
        if stopped == 'infra_error':
            infra_errors += 1
            print(f'scamworld run: episode {i} stopped with infra_error; ' + model_error_note(where), file=sys.stderr)
        elif stopped == 'provider_refused' or (stopped == 'agent_error_or_budget' and _last_error(where)):
            print(f'scamworld run: episode {i} stopped with {stopped}; ' + model_error_note(where), file=sys.stderr)
    if only_setup:
        for q in sorted(created, key=lambda q: len(q.parts), reverse=True):
            if q.is_dir() and not any(q.iterdir()):
                q.rmdir()
    return 1 if infra_errors else 0


if __name__ == '__main__':
    sys.exit(main())
