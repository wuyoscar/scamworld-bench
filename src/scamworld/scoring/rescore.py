"""Offline re-scoring of a finished episode (`scamworld score <run dir>`).

The trace is scored again by the current scorer with the task's frozen contract and spec. The reason judge is replayed
from the verdict recorded in score.json (judge='cached': no API call), skipped (judge='none': keyword rules only), or
called again (judge='live', billed). Fields that the episode runner adds around the scorer (cost, model, stop, ...) are
not produced here; `compare` reports the scorer fields that differ from the recorded score.

`rescored_record` is the whole score.json again with the scorer fields replaced by the re-score (runner fields kept as
recorded; the final outcome fields recomputed, scoring/outcome.final_outcome), written next to the raw score as score-rescored.json (`scamworld score ... --write --out score-rescored.json`);
score.json itself is never rewritten.

With reparse=True (`scamworld score`), an episode that ended as protocol_error with a rejected final answer the current parser accepts exactly (scoring.reparse.plan,
status 'rescore') is re-scored on its answered trace (reparse.answered_trace), as score-reparsed.json is; the record then
carries the same `reparsed` block and stop "terminated". `rescore_causes` separates the two sources of a changed outcome by
re-scoring once more with `recorded_evaluator()`, the scorer the r8 episodes were recorded with.
"""
import copy
import json
from contextlib import contextmanager
from pathlib import Path

from scamworld.corpus import spec_at, spec_of, task_dir
from scamworld.scoring import evaluator as resolve_evaluator
from scamworld.scoring.evaluation import load_contract

RUNNER_FIELDS = {   # written by scamworld.episode.run_one around the scorer result
    'stop', 'cost_usd', 'cost_known', 'budget_state', 'known_cost_usd', 'agent_cost_usd', 'judge_cost_usd', 'model',
    'obs_modes', 'action_modes', 'coord_space', 'close_error', 'agent_protocol', 'effective_action_modes', 'evaluator',
    'projection_truncation', 'input_hashes', 'runtime_config', 'judge_config', 'task_version', 'rubric_hash',
    'freeze_input_hash', 'max_steps', 'max_calls', 'max_cost_usd', 'reply_format', 'dead_link_loop', 'system_note', 'interface_variant', 'tokens', 'task_overlay',
    # r8 runner fields (episode.run_one)
    'agent_max_tokens', 'code', 'interface', 'reasoning_profile', 'url_visibility', 'offsite', 'format_fallbacks',
    # direct provider API runs (agents/direct.py)
    'transport', 'provider',
    # OpenAI-compatible endpoint runs (agents/endpoint.py), a task folder outside tasks/, the gym runner (scamworld.gym)
    'endpoint', 'task_dir', 'runner',
    # added by `scamworld judge --runs` (judge v5, offline), with the final outcome derived from it (scoring/outcome.py)
    'judge_v5', 'outcome', 'outcome_strict', 'outcome_source', 'outcome_detail',
    # added to score.json after the episode by a judge re-run on a sample of episodes (the verdict used by the score stays
    # in reason_judge)
    'judge_sweep', 'judge_sweep_config', 'reason_judge_before_sweep',
}


class CachedJudge:
    """Replays the verdict recorded for one episode; callable like scamworld.scoring.judge.LLMJudge."""

    def __init__(self, verdict):
        self.recorded, self.last, self.calls = verdict, None, 0
        self.cost, self.cost_known = 0.0, True

    def __call__(self, text, rubric):
        from scamworld.scoring.judge import legacy_label
        if not isinstance(self.recorded, dict):
            raise ValueError('episode has no recorded judge verdict')
        self.calls += 1
        self.last = copy.deepcopy(self.recorded)
        for key in ('keywords', 'policy_category_only'):   # added by score.judge_reason after the call
            self.last.pop(key, None)
        return legacy_label(self.last.get('label')) == 'names_mechanism'


@contextmanager
def recorded_evaluator():
    """The scorer as r8 episodes were recorded: every evaluator change made since is switched off here.
    Today six: quotes spanning adjacent text regions (observations.joined_regions), the whitespace-insensitive
    clue/evidence matcher (text_match.NORMALISED), anchor support of a single-region quote with whitespace removed
    (observations.BARE_ANCHOR_SUPPORT), benign completion without evidence_met (score.BENIGN_COMPLETION_NEEDS_EVIDENCE),
    free-text answer values over their maxLength (structured.LONG_TEXT_ACCEPTED) and benign report facts by value alone
    (score.BENIGN_FACTS_NEED_EVIDENCE). A later evaluator change must be added here, or rescore_causes would credit it to
    the parser or to nothing."""
    import scamworld.scoring.evaluation.observations as O
    import scamworld.scoring.evaluation.structured as V
    from scamworld.scoring import score as S, text_match as TM
    saved = (O.joined_regions, TM.NORMALISED, O.BARE_ANCHOR_SUPPORT, S.BENIGN_COMPLETION_NEEDS_EVIDENCE, V.LONG_TEXT_ACCEPTED,
             S.BENIGN_FACTS_NEED_EVIDENCE)
    (O.joined_regions, TM.NORMALISED, O.BARE_ANCHOR_SUPPORT, S.BENIGN_COMPLETION_NEEDS_EVIDENCE, V.LONG_TEXT_ACCEPTED,
     S.BENIGN_FACTS_NEED_EVIDENCE) = (lambda *a: None), False, False, True, False, True
    try:
        yield
    finally:
        (O.joined_regions, TM.NORMALISED, O.BARE_ANCHOR_SUPPORT, S.BENIGN_COMPLETION_NEEDS_EVIDENCE, V.LONG_TEXT_ACCEPTED,
         S.BENIGN_FACTS_NEED_EVIDENCE) = saved


def reparse_decision(run_dir):
    """reparse.plan() when the current parser re-scores this episode (status 'rescore'), else None."""
    from scamworld.scoring.reparse import plan
    try:
        d = plan(run_dir)
    except (OSError, ValueError, KeyError):
        return None
    return d if d.get('status') == 'rescore' else None


def is_setup_failure(run_dir):
    """True for a run folder whose score.json records a setup failure (stop infra_error, infra_stage setup) and that has no
    trace.json: the episode never started, so there is nothing to score again."""
    run_dir = Path(run_dir)
    if (run_dir / 'trace.json').is_file():
        return False
    try:
        score = json.loads((run_dir / 'score.json').read_text())
    except (OSError, ValueError):
        return False
    return isinstance(score, dict) and score.get('stop') == 'infra_error' and score.get('infra_stage') == 'setup'


def rescore(run_dir, judge='cached', evaluator=None, reparse=False):
    run_dir = Path(run_dir)
    recorded = json.loads((run_dir / 'score.json').read_text())
    trace = json.loads((run_dir / 'trace.json').read_text())
    decision = reparse_decision(run_dir) if reparse else None
    if decision:   # the replay: cut back to the answer's step when actions followed it, plus the answer
        from scamworld.scoring.reparse import replay_trace, reparsed_block
        trace = replay_trace(trace, decision)
    task = recorded.get('case_id') or trace['case_id']
    overlay = recorded.get('task_overlay')   # a generated task condition's folder, relative to the repository
    if overlay:
        from scamworld.paths import REPO
        overlay = Path(overlay) if Path(overlay).is_absolute() else REPO / overlay
    own = Path(recorded['task_dir']) if recorded.get('task_dir') else None   # a task folder outside tasks/ (your own task): score.json records where it was
    own = own if own is not None and (own / 'task.json').is_file() else None
    contract = load_contract((own or task_dir(task)).resolve(), **({'overlay': overlay} if overlay else {}))
    spec = spec_at(own) if own else spec_of(task)
    llm = None
    verdict = recorded.get('reason_judge')
    failed = isinstance(verdict, dict) and verdict.get('label') == 'judge_error'   # a failed call, not a verdict
    if judge == 'cached' and verdict is not None and not failed:
        llm = CachedJudge(verdict)   # a run without a verdict (or with a failed call) stays llm None: keyword rules
    elif judge == 'live':
        from scamworld.paths import OPENWEIGHTS_ENV_FILE
        from scamworld.scoring.judge import LLMJudge
        llm = LLMJudge(env_file=OPENWEIGHTS_ENV_FILE, prompt='v4')
    result = resolve_evaluator(evaluator or recorded.get('evaluator') or 'v1')(contract, trace, spec, llm)
    result = {k: v for k, v in result.items() if k != 'shared_evaluation'}
    kept = ('tokens', 'max_steps', 'task_overlay') + (() if decision else ('judge_v5',))   # judge_v5 judged the unanswered episode
    for key in kept:   # recorded around the scorer: a re-score keeps them
        if key in recorded:
            result[key] = copy.deepcopy(recorded[key])
    if decision:
        result['reparsed'] = reparsed_block(recorded, decision)
    return recorded, result


def rescore_causes(run_dir, recorded, result, judge='cached'):
    """Why the re-score differs from the raw score.json: "parser" when the answer the current parser reads changes the
    outcome (OUTCOME_FIELDS) under the recorded scorer, "evaluator" when the current scorer changes the outcome on the same
    (answered) trace, "matcher" when the current clue/evidence matcher (text_match.py) changes MATCHER_FIELDS. An a11 episode
    (free-text final message) was recorded with today's scorer and parser: nothing to credit."""
    from scamworld.agents.interface_v11 import PROTOCOL_NAME
    if recorded.get('agent_protocol') == PROTOCOL_NAME:
        return []
    with recorded_evaluator():
        _, base = rescore(run_dir, judge=judge, reparse=True)
    out = lambda r: tuple(r.get(k) for k in OUTCOME_FIELDS)
    causes = []
    if 'reparsed' in result and out(base) != out(recorded):
        causes.append('parser')
    if out(result) != out(base):
        causes.append('evaluator')
    if any(result.get(k) != base.get(k) for k in MATCHER_FIELDS):
        causes.append('matcher')
    return causes


LATER_DIAGNOSTICS = {'not_found_opens'}   # scorer diagnostics older records lack; compared only when the record has them


def compare(recorded, result):
    """Scorer fields whose value differs between the recorded score and the re-score."""
    keys = (set(recorded) | set(result)) - RUNNER_FIELDS - (LATER_DIAGNOSTICS - set(recorded))
    return {k: (recorded.get(k), result.get(k)) for k in sorted(keys) if recorded.get(k) != result.get(k)}


OUTCOME_FIELDS = ('behavior_path', 'overall', 'verdict')   # what an episode's outcome is, for rescore_causes
MATCHER_FIELDS = ('decisive_clue_before_commit', 'evidence_encountered')   # what the clue/evidence matcher decides


def rescored_record(recorded, result, judge, causes):
    """score.json with the re-scored scorer fields; runner fields as recorded (stop "terminated" when re-parsed).
    rescore_causes: see rescore_causes; [] when the outcome and MATCHER_FIELDS are the raw score.json's. `rescore` names the
    code and judge mode."""
    from scamworld.episode import code_identity
    drop = {'judge_v5', 'judge_sweep', 'judge_sweep_config', 'reason_judge_before_sweep'} if 'reparsed' in result else set()
    kept = {k: copy.deepcopy(v) for k, v in recorded.items() if k in RUNNER_FIELDS and k not in result and k not in drop}
    if 'reparsed' in result:
        kept['stop'] = 'terminated'
    record = {**kept, **result, 'rescore_causes': causes,
              'rescore': {'from': 'score.json', 'judge': judge, 'code': code_identity(), 'changed': sorted(compare(recorded, result))}}
    # the final outcome of the record as it now stands (the same function `judge --write` uses): the kept
    # judge_v5 block (dropped when the episode was re-parsed: it judged the unanswered one) is read as it is, none is invented
    from scamworld.scoring.outcome import final_outcome
    return {**record, **final_outcome(record)}
