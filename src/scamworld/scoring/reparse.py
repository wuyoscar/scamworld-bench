"""Offline re-score of finished protocol_error episodes with the current parser (PARSER).

The current parser reads these unambiguous alternative formats as the same action: one DSML tool call (openrouter.dsml_action),
answer fields one level too high (openrouter.renest_answer), a final answer missing only its closing brackets in a reply
that ended with finish_reason "stop" (openrouter.brace_repair; the recorded finish_reason of the step is used), citations
written inside "answers" in valid JSON (openrouter.hoist_citations) and undeclared answer keys with an empty value
(openrouter.drop_empty_undeclared). Episodes that
ended as protocol_error under an earlier parser may hold a rejected final answer that the new parser accepts. Such an
episode is re-scored only when the replay is exact:
  - k = the first rejected step (choices.json entry) where a fallback of the new parser fires (parsed_from); the new parser
    reads it as a final answer (answer, or stop with an answer object) that validates against the task contract;
  - every step before k parses the same under the new parser (nothing earlier would have gone another way).
The replay ends at k. When actions were executed after k (for example an agent whose answer is rejected clicks once and
answers again), the trace is cut back to the state the answer was given in:
its steps, observations, actions and events up to k's step_id (truncate_trace); an episode with environment errors is left.
The trace then gets the final_answer step the runtime would have recorded (same page, observation carried over) and the
task's scorer runs on it, as `scamworld score` does. score-reparsed.json is written next to score.json, never over it: the
recorded score with the scorer fields recomputed, stop "terminated" and a "reparsed" block. judge_v5 / judge_sweep fields are
dropped (they judged the episode without an answer); tokens and costs stay as recorded (what the run spent).
    uv run python -m scamworld.scoring.reparse [--dry-run] <runs folder or episode folder> [...]
Counts: protocol_error episodes, eligible (a rejected final answer the new parser accepts), re-scored, left as is (with reasons).
"""
import argparse
import copy
import json
import sys
from collections import Counter
from pathlib import Path

from scamworld.scoring.rescore import RUNNER_FIELDS

# The parser new_parse runs (written into score files as "parser"; nothing compares it): the DSML and renest fallbacks plus
# brace_repair, hoist_citations, drop_empty_undeclared, dsml_hybrid, relaxed_answer, long_text_accepted.
PARSER = 'brace-repair-7'
DROPPED = ('judge_v5', 'judge_sweep', 'judge_sweep_config', 'reason_judge_before_sweep')


def _reply(step):
    content = (step.get('model_output') or {}).get('content') if isinstance(step.get('model_output'), dict) else None
    return content if isinstance(content, str) else step.get('raw') if isinstance(step.get('raw'), str) else None


def _finish_reason(step):
    return (step.get('model_output') or {}).get('finish_reason') if isinstance(step.get('model_output'), dict) else None


def new_parse(raw, contract, finish_reason=None, protocol=None):
    """(choice, parsed_from) under the current parser, or (None, error text) when it rejects the reply. `protocol` is the
    episode's recorded agent_protocol (score.json; r8 when absent): under a10 the reply is written in the names the agent read
    (page_ref, renamed answer fields) and is read with the internal ones, as at run time (openrouter.agent_reply_names)."""
    from scamworld.agents import openrouter as O
    from scamworld.agents.interface_v11 import A10_PROTOCOL_NAME, R8_PROTOCOL_NAME
    from scamworld import episode as E
    if raw is None:
        return None, 'no recorded reply'
    protocol = protocol or R8_PROTOCOL_NAME
    obs = {'task_contract': contract, '_protocol': protocol, 'controls': [],
           '_agent_names': O.agent_names(contract) if protocol == A10_PROTOCOL_NAME else {}}   # a11 replies are free text: nothing to re-parse
    try:
        value, fmt = O.decode_model_output(raw, finish_reason=finish_reason, obs=obs)
        choice, norm = O.normalize_choice(value, obs)
    except Exception as e:
        return None, f'{type(e).__name__}: {e}'
    return choice, E.parsed_from(fmt, norm)


def is_final_answer(choice, contract):
    from scamworld.agents import openrouter as O
    if not isinstance(choice, dict) or choice.get('action') not in ('answer', 'stop') or not isinstance(choice.get('answer'), dict):
        return False
    return not O.answer_errors(choice['answer'], contract)


def plan(run_dir):
    """What the new parser makes of one finished episode: {'status': ...} plus k and the answer when it can be re-scored."""
    run_dir = Path(run_dir)
    score = json.loads((run_dir / 'score.json').read_text())
    if score.get('stop') != 'protocol_error':
        return {'status': 'not_protocol_error'}
    steps = json.loads((run_dir / 'choices.json').read_text())
    contract = json.loads((run_dir / 'public-task-contract.json').read_text())
    for k, step in enumerate(steps):
        rejected = step.get('choice') is None and step.get('error') is not None
        choice, how = new_parse(_reply(step), contract, _finish_reason(step), score.get('agent_protocol'))
        if not rejected or choice is None or how is None:
            continue   # parsed as recorded: the new parser differs only where a fallback fires (parsed_from), after a failure
        if not is_final_answer(choice, contract):
            return {'status': 'left', 'reason': 'first changed step is not a final answer', 'k': k, 'parsed_from': how}
        executed = [i for i in range(k + 1, len(steps)) if steps[i].get('choice') is not None and steps[i].get('error') is None]
        out = {'k': k, 'step_id': step.get('step_id'), 'parsed_from': how, 'choice': choice, 'eligible': True}
        if executed:   # the replay ends at k: the trace is cut back to k's step (rescore_answered, truncate_trace)
            if truncate_trace(json.loads((run_dir / 'trace.json').read_text()), step.get('step_id')) is None:
                return out | {'status': 'left', 'reason': f'{len(executed)} action(s) executed after the answer and the trace cannot be cut back (environment errors)'}
            return out | {'status': 'rescore', 'actions_after_answer': len(executed)}
        return out | {'status': 'rescore'}
    return {'status': 'not_eligible', 'reason': 'no rejected final answer the new parser accepts'}


def truncate_trace(trace, step_id):
    """The recorded trace as it stood when the observation of step `step_id` was given: later steps, observation records,
    actions and events dropped (an event's "step" is the action it belongs to). None when the trace has environment errors
    (they carry no step) or no step `step_id`."""
    if trace.get('environment_errors') or not any(s.get('step_id') == step_id for s in trace['steps']):
        return None
    trace = copy.deepcopy(trace)
    trace['steps'] = [s for s in trace['steps'] if s['step_id'] <= step_id]
    diagnostics = trace.get('runtime_diagnostics') or {}
    for key, field in (('observations', 'step_id'), ('actions', 'step'), ('events', 'step')):
        if isinstance(diagnostics.get(key), list):
            diagnostics[key] = [r for r in diagnostics[key] if not isinstance(r.get(field), int) or r[field] <= step_id]
    trace['final_answer'] = None
    trace['status'] = 'running'
    return trace


def answered_trace(trace, answer):
    """The recorded trace plus the final_answer step the runtime records after send_msg_to_user (runtime.export_trace)."""
    trace = copy.deepcopy(trace)
    last = trace['steps'][-1]
    obs = copy.deepcopy(last.get('observation') or {})
    n = len(trace.get('runtime_diagnostics', {}).get('observations') or trace['steps'])
    if isinstance(obs.get('observation_id'), str) and '-obs' in obs['observation_id']:
        obs['observation_id'] = obs['observation_id'].rsplit('-obs', 1)[0] + f'-obs{n:04d}'
    trace['steps'].append({'step_id': last['step_id'] + 1, 'action': {'type': 'final_answer', 'value': copy.deepcopy(answer)},
                           'execution': 'succeeded', 'before_state_id': last.get('after_state_id'), 'after_state_id': last.get('after_state_id'),
                           'observation': obs, 'events': [], 'error': None, 'transition_observed': False, 'reparsed': True})
    trace['final_answer'] = copy.deepcopy(answer)
    if not trace.get('environment_errors'):
        trace['status'] = 'completed'
    return trace


def replay_trace(trace, decision):
    """The trace the replay ends with: cut back to the answer's step when actions followed it, plus the final_answer step."""
    if decision.get('actions_after_answer'):
        cut = truncate_trace(trace, decision['step_id'])
        if cut is None:
            raise ValueError(f'cannot cut the trace back to step {decision["step_id"]} (environment errors or no such step)')
        trace = cut
    return answered_trace(trace, decision['choice']['answer'])


def reparsed_block(recorded, decision):
    """score.json "reparsed" block of an offline re-score (score-reparsed.json and rescore(reparse=True))."""
    block = {'from_stop': recorded.get('stop'), 'choices_index': decision['k'], 'step_id': decision['step_id'],
             'parsed_from': decision['parsed_from'], 'answer': decision['choice']['answer'], 'parser': PARSER,
             'note': f'offline re-score: the recorded trace plus the final answer the {PARSER} parser accepts at this step'}
    if decision.get('actions_after_answer'):
        block |= {'actions_after_answer': decision['actions_after_answer'],
                  'note': f'offline re-score: the recorded trace cut back to step {decision["step_id"]} (the replay ends there; '
                          f'{decision["actions_after_answer"]} later action(s) dropped) plus the final answer the {PARSER} parser accepts'}
    return block


def rescore_answered(run_dir, decision):
    """score-reparsed.json content for one episode whose plan() status is 'rescore'."""
    from scamworld.corpus import spec_of, task_dir
    from scamworld.paths import REPO
    from scamworld.scoring import evaluator as resolve_evaluator
    from scamworld.scoring.evaluation import load_contract
    run_dir = Path(run_dir)
    recorded = json.loads((run_dir / 'score.json').read_text())
    trace = json.loads((run_dir / 'trace.json').read_text())
    task = recorded.get('case_id') or trace['case_id']
    overlay = recorded.get('task_overlay')
    if overlay:
        overlay = Path(overlay) if Path(overlay).is_absolute() else REPO / overlay
    contract = load_contract(task_dir(task).resolve(), **({'overlay': overlay} if overlay else {}))
    result = resolve_evaluator(recorded.get('evaluator') or 'v1')(contract, replay_trace(trace, decision), spec_of(task), None)
    result = {k: v for k, v in result.items() if k != 'shared_evaluation'}
    keep = set(RUNNER_FIELDS) - set(DROPPED)   # every other field is the scorer's: only from the re-score
    out = {k: copy.deepcopy(v) for k, v in recorded.items() if k in keep} | result
    out['stop'] = 'terminated'
    out['reparsed'] = reparsed_block(recorded, decision)
    return out


def episodes(paths):
    for p in paths:
        p = Path(p)
        if (p / 'score.json').is_file():
            yield p
        else:
            yield from sorted(s.parent for s in p.rglob('score.json'))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--dry-run', action='store_true', help='count only; write nothing')
    ap.add_argument('paths', nargs='+')
    a = ap.parse_args(argv)
    counts, reasons, written = Counter(), Counter(), []
    for run_dir in episodes(a.paths):
        try:
            d = plan(run_dir)
        except (OSError, ValueError) as e:
            counts['unreadable'] += 1
            reasons[f'unreadable: {type(e).__name__}'] += 1
            continue
        if d['status'] == 'not_protocol_error':
            continue
        counts['protocol_error'] += 1
        counts['eligible'] += bool(d.get('eligible'))
        if d['status'] == 'rescore':
            counts['rescored'] += 1
            if not a.dry_run:
                (run_dir / 'score-reparsed.json').write_text(json.dumps(rescore_answered(run_dir, d), ensure_ascii=False, indent=1))
                written.append(str(run_dir))
        elif d.get('eligible'):
            counts['left_as_is'] += 1
            reasons[d['reason']] += 1
        else:
            reasons[d['reason']] += 1
        if d['status'] == 'rescore':
            counts['rescored_parsed_from:' + str(d.get('parsed_from'))] += 1
            counts['rescored_trace_cut_back'] += bool(d.get('actions_after_answer'))
    print(json.dumps({'counts': dict(counts), 'reasons': dict(reasons), 'written': len(written), 'dry_run': a.dry_run}, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
