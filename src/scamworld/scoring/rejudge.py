"""Offline judge v5 over finished episodes (`scamworld judge --runs <run dir>... [--write]`).

The text judged per episode is the one the paper's analysis judges, so the labels agree item by item:
  * a contract-2 scam task whose behavior_path is recognized_and_stopped or stopped_without_naming_problem: the reason
    field of the last answer in choices.json, else of trace.json final_answer;
  * asked directly (score.json condition 'asked'), scam site, verdict scam, nonempty evidence:
    'The website is a scam. Evidence: ' + evidence.
Interface a11 (free-text final message): the reason is the message; asked directly, the message once the
verdict read from it (score.json `verdict`, written by the step that reads it) is scam.
Any other episode is not judged. Rubric: the reason_rubric of the base task's scoring/evaluation.json (persona variants
use their base task's). Pages and URLs: scamworld.scoring.visited.visited(run dir).
The verdict goes to score.json `judge_v5`: judge.V5_FIELDS plus prompt_sha12, model, backend and source. An episode whose
block has this prompt_sha12 and backend already is skipped unless force. A failed call (judge_error, or a verify call
that failed) is retried once with a fresh judge, unless its billing is unknown (cost_known false: not sent again), and is
never written.
With --write the episode's final outcome (scoring/outcome.final_outcome: outcome, outcome_strict, outcome_source,
outcome_detail) goes into score.json beside the judge block, for every run dir given (also those the judge skips: a commit,
a benign site, an already judged episode), so a record never shows the runtime behavior_path as its only result.
behavior_path itself stays as the episode runner wrote it.
"""
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

JUDGED_PATHS = ('recognized_and_stopped', 'stopped_without_naming_problem')
ASKED_PREFIX = 'The website is a scam. Evidence: '


def asked_verdict(answers):
    """'scam' / 'legitimate' / None from an asked-directly answer (same reading as the analysis)."""
    v = str((answers or {}).get('verdict') or '').strip().lower()
    return 'scam' if v.startswith('scam') or v in ('fraud', 'fraudulent') else 'legitimate' if v.startswith('legit') else None


def final_answers(trace):
    fa = trace.get('final_answer') if isinstance(trace.get('final_answer'), dict) else {}
    return (fa.get('answers') if isinstance(fa.get('answers'), dict) else fa) or {}


def final_message(run_dir):
    """The agent's free-text final message (interface a11) from trace.json, else None."""
    from scamworld.scoring.evaluation.structured import message_reply
    try:
        fa = json.loads((Path(run_dir) / 'trace.json').read_text()).get('final_answer')
    except (OSError, ValueError):
        return None
    return fa['message'] if message_reply(fa) else None


def reason_text(run_dir, field):
    """The reason field of the agent's last answer: choices.json first (a rejected answer counts), then trace.json. A free-text
    final message (interface a11) is the reason as a whole."""
    run_dir = Path(run_dir)
    message = final_message(run_dir)
    if message is not None:
        return message
    try:
        for c in reversed(json.loads((run_dir / 'choices.json').read_text())):
            a = (c.get('choice') or {}).get('answer') if isinstance(c, dict) else None
            if isinstance(a, dict):
                ans = a.get('answers') if isinstance(a.get('answers'), dict) else a
                return str(ans.get(field) or '')
    except Exception:
        pass
    try:
        return str(final_answers(json.loads((run_dir / 'trace.json').read_text())).get(field) or '')
    except Exception:
        return ''


def base_task(task):
    """The task whose case_scoring judges this one: the base site's for a task variant on the same site (account-07.busy-parent);
    a site of its own that is a localized variant of another (invest-98 of invest-83) keeps its own rubric."""
    from scamworld.corpus import index
    row = next((t for t in index()['tasks'] if t['task'] == task), None)
    base = (row or {}).get('variant_of')
    return base if base and task.startswith(base + '.') else task


def case_scoring(task, folder=None):
    """evaluation.json `case_scoring` of a task (folder: a task outside tasks/, score.json `task_dir`)."""
    from scamworld.corpus import task_dir
    ev = json.loads(((Path(folder) if folder else task_dir(base_task(task))) / 'scoring/evaluation.json').read_text())
    return ev.get('case_scoring') or {}


def job(run_dir):
    """(source, text, rubric) for one episode, or (None, why, None) when it is not judged."""
    run_dir = Path(run_dir)
    score = json.loads((run_dir / 'score.json').read_text())
    task = score.get('case_id')
    if not task:
        return None, 'no case_id in score.json', None
    if score.get('benign'):
        return None, 'benign site', None
    cs = case_scoring(task, score.get('task_dir'))
    rubric = cs.get('reason_rubric') or {}
    if score.get('condition') == 'asked' and final_message(run_dir) is not None:
        if score.get('verdict') != 'scam':
            return None, 'asked: message verdict ' + ('is not scam' if score.get('verdict') else 'not read yet'), None
        return 'asked_message', ASKED_PREFIX + final_message(run_dir), rubric
    if score.get('condition') == 'asked':
        answers = final_answers(json.loads((run_dir / 'trace.json').read_text()))
        if asked_verdict(answers) != 'scam':
            return None, 'asked: verdict is not scam', None
        ev = answers.get('evidence')
        ev = '; '.join(map(str, ev)) if isinstance(ev, list) else str(ev or '')
        if not ev.strip():
            return None, 'asked: empty evidence', None
        return 'asked_evidence', ASKED_PREFIX + ev, rubric
    if score.get('contract') != 2 or score.get('behavior_path') not in JUDGED_PATHS:
        return None, 'behavior_path not judged: ' + str(score.get('behavior_path')), None
    text = reason_text(run_dir, cs.get('reason_field') or 'reason')
    if not text.strip():
        return None, 'empty reason', None
    return 'reason', text, rubric


def _failed(v):
    return v.get('label') == 'judge_error' or 'verify call failed' in str(v.get('downgraded') or '')


def _write_block(run_dir, block, lock):
    """Write the judge block and the outcome it settles; with block None only the outcome (False when nothing changed)."""
    from scamworld.scoring.outcome import final_outcome
    path = Path(run_dir) / 'score.json'
    with lock:
        score = json.loads(path.read_text())
        before = dict(score)
        if block is not None:
            score['judge_v5'] = block
        score.update(final_outcome(score))
        if score == before:
            return False
        tmp = path.with_name('.score.json.judge-v5.tmp')
        tmp.write_text(json.dumps(score, ensure_ascii=False, indent=1))
        os.replace(tmp, path)
    return True


def judge_runs(run_dirs, backend='cz', write=False, force=False, workers=8, env_file=None, log=print, endpoint=None):
    """Judge v5 on every judged episode of run_dirs (backend: cz by default, openrouter or endpoint);
    returns {run dir: block or {'skipped': why} or {'error': why}}."""
    from scamworld.scoring.judge import JudgeV5, PHASH_V5, V5_FIELDS
    from scamworld.scoring.visited import visited
    if env_file is None:
        from scamworld.paths import OPENWEIGHTS_ENV_FILE
        env_file = OPENWEIGHTS_ENV_FILE
    out, todo = {}, []
    for d in map(str, run_dirs):
        try:
            source, text, rubric = job(d)
        except (OSError, ValueError, KeyError) as error:
            out[d] = {'skipped': 'unreadable: ' + str(error)[:200]}
            continue
        if source is None:
            out[d] = {'skipped': text}
            continue
        prev = json.loads((Path(d) / 'score.json').read_text()).get('judge_v5') or {}
        if not force and prev.get('prompt_sha12') == PHASH_V5 and prev.get('backend') == backend:
            out[d] = {'skipped': 'already judged', **prev}
            continue
        todo.append((d, source, text, rubric))
    if backend == 'openrouter':
        workers = 1   # a configured budget ledger allows one in-flight request in all
    local, lock = threading.local(), threading.Lock()

    def judge(fresh=False):
        if fresh or not hasattr(local, 'j'):
            local.j = JudgeV5(backend=backend, env_file=env_file, **({'endpoint': endpoint} if backend == 'endpoint' else {}))
        return local.j

    def work(item):
        d, source, text, rubric = item
        pages, urls = visited(d)
        j = judge()
        v = j.classify(text, rubric, pages, urls)
        if _failed(v) and v.get('cost_known') is not False:   # a call of unknown billing is not sent again
            j = judge(fresh=True)
            v = j.classify(text, rubric, pages, urls)
        if v.get('cost_known') is False:   # only that call: the next episode on this thread gets a fresh judge
            local.__dict__.pop('j', None)
        if _failed(v):
            down = str(v.get('downgraded') or '')
            why = down if 'verify call failed' in down else v.get('why')
            return d, {'error': str(why or v.get('downgraded'))[:200]}
        block = {f: v.get(f) for f in V5_FIELDS}
        block.update(prompt_sha12=PHASH_V5, model=j.model, backend=backend, source=source)
        if write:
            _write_block(d, block, lock)
        return d, block

    log(f'judge v5 ({backend}): {len(todo)} to judge, {len(out)} skipped')
    with ThreadPoolExecutor(max(1, workers)) as ex:
        for d, block in ex.map(work, todo):
            out[d] = block
    if write:   # the outcome of every other episode (skipped, already judged, failed judge: pending_judge is written as such)
        judged = {d for d, b in out.items() if 'error' not in b and 'skipped' not in b}
        for d in map(str, run_dirs):
            if d not in judged and (Path(d) / 'score.json').exists():
                try:
                    _write_block(d, None, lock)
                except (OSError, ValueError):
                    pass
    return out
