"""Text of the pages an agent actually visited in one recorded episode (judge v5 input; the same text the published
judge v5 labels were made from).

From <run dir>/trace.json: per step, the observation's URL, page title (first accessibility control = the RootWebArea name)
and text (visible_text_regions + public_accessibility_text), lines already shown earlier in the episode removed. Capped at
~30k tokens (CHAR_CAP): the first step and the last steps are kept whole, middle steps are dropped first (the commit /
confirm view the agent stops on is the last observation).
    visited(run_dir) -> (text, urls)
"""
import json, re
from pathlib import Path

CHAR_CAP = 60000          # ~30k tokens for mixed Latin/CJK text


def _lines(o):
    out = []
    for r in o.get('visible_text_regions') or []:
        out.append(r.get('text') or '')
    for r in o.get('public_accessibility_text') or []:
        out.append(r.get('text') if isinstance(r, dict) else str(r))
    return [' '.join(str(t).split()) for t in out if t and len(str(t).strip()) > 1]


def visited(run_dir):
    p = Path(run_dir) / 'trace.json'
    if not p.exists(): return '', []
    steps = [s for s in json.load(open(p)).get('steps') or [] if isinstance(s.get('observation'), dict)]
    seen, blocks, urls = set(), [], []
    for i, s in enumerate(steps):
        o = s['observation']
        url = o.get('public_url') or o.get('url') or ''
        if url: urls.append(url)
        ctl = o.get('public_accessibility_controls') or []
        title = (ctl[0].get('name') or ctl[0].get('text') or '') if ctl and isinstance(ctl[0], dict) else ''
        new = []
        for t in _lines(o):
            if t not in seen: seen.add(t); new.append(t)
        blocks.append('[step %d] %s%s\n%s' % (i, url, (' | ' + title) if title else '', '\n'.join(new)))
    keep = list(range(len(blocks)))
    while sum(len(blocks[i]) for i in keep) > CHAR_CAP and len(keep) > 2:
        keep.pop(1)                               # drop the earliest middle step
    if sum(len(blocks[i]) for i in keep) > CHAR_CAP:   # still too long: trim each kept block, keep its tail for the last
        per = CHAR_CAP // len(keep)
        out = [blocks[i][:per] if i != keep[-1] else blocks[i][:200] + '\n...\n' + blocks[i][-(per - 200):] for i in keep]
    else:
        out = [blocks[i] for i in keep]
    if len(keep) < len(blocks): out.insert(1, '[... %d middle steps omitted ...]' % (len(blocks) - len(keep)))
    return '\n\n'.join(out), urls


def visited_union(run_dirs):
    """Synthetic rubric-test sentences have no episode: use the union of the task's recorded episodes (all backbones),
    each line once, capped like visited()."""
    seen, out, urls = set(), [], []
    for d in run_dirs:
        t, u = visited(d)
        urls += [x for x in u if x not in urls]
        for line in t.split('\n'):
            if line.startswith('[step') or line.startswith('[...'): continue
            if line and line not in seen: seen.add(line); out.append(line)
    txt = '\n'.join(out)
    return (txt[:CHAR_CAP] + '\n[... truncated ...]' if len(txt) > CHAR_CAP else txt), urls


def static_site(task_dir):
    """Fallback for a reason with no recorded episode (rubric-test sentences): visible text of the task's site/**/*.html
    plus its scoring/spec.json clue_texts. Not a visit, so marked as such."""
    import glob
    task_dir = Path(task_dir)
    out, seen = ['[static site text: no recorded episode for this task]'], set()
    for f in sorted(glob.glob(str(task_dir / 'site/**/*.html'), recursive=True)):
        h = open(f, errors='ignore').read()
        h = re.sub(r'<(script|style|template)\b.*?</\1>', '\n', h, flags=re.S | re.I)
        for line in re.sub(r'<[^>]+>', '\n', h).split('\n'):
            line = ' '.join(line.split())
            if len(line) > 1 and line not in seen: seen.add(line); out.append(line)
    spec = task_dir / 'scoring/spec.json'
    if spec.exists():
        out += [t for t in json.load(open(spec)).get('clue_texts') or [] if t]
    txt = '\n'.join(out)
    return txt[:CHAR_CAP]
