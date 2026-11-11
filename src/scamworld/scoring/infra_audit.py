"""Output audit: episodes whose stop says the model or provider refused, but whose recorded error is infrastructure
(for example rate-limit 429s recorded as provider_refused).

A second line of defence behind the transport's own retry rules (agents/direct.py): it reads score.json (stop) and the
error rows of choices.json, never changes a byte, and lists every episode that should be re-run.

  infra      HTTP 408 / 429 / 5xx, RESOURCE_EXHAUSTED, rate limit, timeouts, connection errors: re-run
  billing    HTTP 402, prepayment credits, insufficient_quota, billing: re-run once the account is funded
  refusal    a refusal of the content itself (prompt blocked, safety block, refusal stop): kept as the model's outcome

    uv run python -m scamworld.scoring.infra_audit results/runs [--exp r8-main] [--model google:gemini-3.8-flash] [--json out.json]
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

SUSPECT_STOPS = ('provider_refused', 'protocol_error', 'refused', 'agent_error_or_budget')
BILLING = re.compile(r'(?i)\b402\b|prepayment credits|insufficient_quota|credit balance|billing details|payment required')
INFRA = re.compile(r'(?i)\b(?:408|429|5\d\d)\b|resource_exhausted|rate[ -]?limit|reduce the rate|exceeded your current quota|'
                   r'quota|timed? ?out|timeout|connection (?:reset|refused|aborted|error)|urlerror|remotedisconnected|'
                   r'service unavailable|bad gateway|gateway time|overloaded|temporarily unavailable')
REFUSAL = re.compile(r'(?i)prompt blocked|blocked by|safety|content (?:filter|policy)|recitation|declined the request|refus')


def classify(error):
    """'infra' / 'billing' / 'refusal' / None for one recorded error row ({http_status, message, error_type, origin, body})."""
    if not error:
        return None
    status = error.get('http_status')
    text = ' '.join(str(error.get(k) or '') for k in ('error_type', 'message', 'vendor_error_type'))
    if status == 402 or (status == 429 and 'insufficient_quota' in text.lower()):
        return 'billing'
    if isinstance(status, int) and (status in (408, 429) or status >= 500):   # Google's "current quota ... billing details" is a 429
        return 'infra'
    if BILLING.search(text):
        return 'billing'
    if INFRA.search(text):
        return 'infra'
    if REFUSAL.search(text):
        return 'refusal'
    return None


def audit_episode(run_dir):
    """None, or {stop, kind, step, error} for an episode whose stop is a refusal or protocol stop. kind is the class of the
    last error row (the one that ended it); 'infra' and 'billing' are suspect."""
    run_dir = Path(run_dir)
    try:
        score = json.loads((run_dir / 'score.json').read_text())
    except (OSError, ValueError):
        return None
    if score.get('stop') not in SUSPECT_STOPS:
        return None
    try:
        rows = [r for r in json.loads((run_dir / 'choices.json').read_text()) if r.get('error')]
    except (OSError, ValueError):
        rows = []
    last = rows[-1] if rows else {'step_id': None, 'error': {'message': str(score.get('error') or '')}}
    error = last['error']
    return {'stop': score.get('stop'), 'kind': classify(error), 'step': last.get('step_id'),
            'error': (f"HTTP {error['http_status']}: " if error.get('http_status') else '') + str(error.get('message') or '')[:200]}


def audit(runs, exp=None, model=None):
    """Rows {exp, model, config, task, run, stop, kind, step, error} under runs/<exp>/<model>/<config>/<task>/r<k>
    (attempt folders in _attempts are not scanned), and counts by kind."""
    rows = []
    for score in sorted(Path(runs).glob(f"{exp or 'r8-*'}/{model or '*'}/*/*/r*/score.json")):
        found = audit_episode(score.parent)
        if found:
            e, m, c, t, r = score.parts[-6:-1]
            rows.append({'exp': e, 'model': m, 'config': c, 'task': t, 'run': r, **found,
                         'suggest': 'rerun' if found['kind'] in ('infra', 'billing') else 'keep'})
    return rows, Counter(r['kind'] or 'unclassified' for r in rows)


def suspect(rows):
    return [r for r in rows if r['kind'] in ('infra', 'billing')]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('runs', type=Path); ap.add_argument('--exp'); ap.add_argument('--model'); ap.add_argument('--json', type=Path)
    a = ap.parse_args(argv)
    rows, counts = audit(a.runs, a.exp, a.model)
    bad = suspect(rows)
    if a.json:
        a.json.write_text(json.dumps({'counts': counts, 'suspect_infra': len(bad), 'rows': rows}, indent=1, ensure_ascii=False))
    for r in bad:
        print('\t'.join(str(r[k]) for k in ('model', 'exp', 'config', 'task', 'step', 'kind', 'error')))
    print(json.dumps({'refused_or_protocol_stops': len(rows), 'by_kind': dict(counts), 'suspect_infra': len(bad)}), file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
