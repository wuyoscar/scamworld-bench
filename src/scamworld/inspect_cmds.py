"""Commands that show what a task gives the agent and what it scores, without a model.

    scamworld observe TASK [--obs MODES]... [--click BID]... [--goto URL] [--grep TEXT] [--out DIR] [--json]
    scamworld signs TASK [--json]
    scamworld table RUNS... [--rows model] [--cols obs_modes] [--evaluator rules] [--format md]

`observe` opens a task and prints the observation the tested agent would receive under each observation setting.
`signs` lists the warning signs a task scores on and where a scripted walk of the task finds them.
`table` counts the outcomes of finished episodes per cell of a table.
`register(subparsers)` adds the three commands to the `scamworld` command line; `python -m scamworld.inspect_cmds` runs them alone.
"""
import argparse
import json
import logging
import shutil
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

DEFAULT_OBS = 'screenshot,ax_controls'   # the observation setting of `scamworld run` and ScamWorldEnv
TEXT_LINES = 8                           # lines shown per text field without --grep
LINE_CHARS = 160                         # characters shown per line
OBS_FILES = {'axtree_txt': 'axtree.txt', 'pruned_html': 'pruned.html', 'controls': 'controls.json'}   # --out file names


# ------------------------------------------------------------------------------------------------------------ observe
def _open_env(task, obs, out_dir, **options):
    from scamworld.gym import ScamWorldEnv
    logging.getLogger('browsergym.core.env').setLevel(logging.ERROR)   # its notes about overridden viewport and timeout are not about your task
    try:
        return ScamWorldEnv(task, out_dir=out_dir, obs_modes=obs, **options)
    except (FileNotFoundError, ValueError) as e:
        hint = '; observations: screenshot, som, ax_controls, ax_tree, html, joined with commas (e.g. screenshot,ax_controls)' if 'Bad modality' in str(e) else ''
        sys.exit(str(e) + hint)


def _follow_path(env, spec, name):
    """Carry out the steps of the spec's path NAME (or NAME:N for its first N steps), as `scamworld signs` walks them."""
    name, _, count = name.partition(':')
    paths = spec.get('paths') or {}
    if name not in paths:
        sys.exit(f'--path {name}: this task has the paths {", ".join(sorted(paths)) or "(none)"}')
    steps = paths[name][:int(count)] if count.isdigit() else paths[name]
    for number, step in enumerate(steps, 1):
        if env.done or not _do_step(env, step):
            sys.exit(f'--path {name}: step {number} ({step}) could not be carried out')


def _walk(env, clicks, goto, path=None):
    """Follow --path, carry out the --click bids in order, then the --goto address (a site-relative address is joined to the
    current page); exits with one line when an action is rejected."""
    from urllib.parse import urljoin
    if path:
        _follow_path(env, env.spec, path)
    actions = [{'action': 'click', 'bid': bid} for bid in clicks]
    for action in actions + ([{'action': 'goto', 'url': urljoin(env.obs['url'], goto)}] if goto else []):
        obs, _, terminated, truncated, info = env.step(action)
        if info.get('rejected'):
            sys.exit(f'{action} was rejected: {info.get("error")}')
        if terminated or truncated:
            break
    return env.obs


def _text_of(value):
    """A field as text: strings as they are, controls and other structures as JSON, one list entry per line."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return '\n'.join(json.dumps(v, ensure_ascii=False) for v in value)
    return json.dumps(value, ensure_ascii=False, indent=1)


def _shown_lines(text, grep):
    lines = text.splitlines()
    if grep:
        return [ln[:LINE_CHARS * 2] for ln in lines if grep.casefold() in ln.casefold()]
    return [ln[:LINE_CHARS] for ln in lines[:TEXT_LINES]]


def _describe(obs, grep, keep):
    """One observation as {'url', 'fields': [{'key', 'chars', 'lines' | 'path'}]}."""
    fields = []
    for key, value in obs.items():
        if key == 'screenshot':
            size = Path(value).stat().st_size if Path(value).is_file() else 0
            fields.append({'key': key, 'bytes': size, 'path': value if keep else None})
            continue
        text = _text_of(value)
        fields.append({'key': key, 'chars': len(text), 'lines': _shown_lines(text, grep)})
    return {'url': obs.get('url'), 'fields': fields}


def _save_fields(obs, folder):
    folder.mkdir(parents=True, exist_ok=True)
    meta = {}
    for key, value in obs.items():
        if key == 'screenshot':
            shutil.copyfile(value, folder / 'screenshot.png')
        elif key in OBS_FILES:
            (folder / OBS_FILES[key]).write_text(_text_of(value) if key != 'controls' else json.dumps(value, ensure_ascii=False, indent=1))
        else:
            meta[key] = value
    (folder / 'meta.json').write_text(json.dumps(meta, ensure_ascii=False, indent=1))


def observe(task, obs_settings=None, clicks=(), goto=None, grep=None, out=None, path=None):
    """The observation of `task` under each setting, after the optional walk: [{'obs', 'url', 'fields'}]. With `out`, the
    full fields are saved in out/<setting>/ and screenshot paths point there. `path` is a scripted path of the task, NAME or
    NAME:N for its first N steps, followed before the clicks."""
    results = []
    for setting in obs_settings or [DEFAULT_OBS]:
        work = Path(tempfile.mkdtemp(prefix='scamworld-observe-'))
        env = _open_env(task, setting, work)
        try:
            env.reset()
            obs = _walk(env, clicks, goto, path)
            folder = Path(out) / setting.replace(',', '+') if out else None
            if folder:
                _save_fields(obs, folder)
                obs = {**obs, **({'screenshot': str(folder / 'screenshot.png')} if obs.get('screenshot') else {})}
            results.append({'obs': setting, **_describe(obs, grep, keep=bool(folder))})
        finally:
            env.close()
            shutil.rmtree(work, ignore_errors=True)
    return results


def _print_observation(r, grep):
    print(f'== {r["obs"]}\npage: {r["url"]}')
    for f in r['fields']:
        if 'bytes' in f:
            print(f'  screenshot  {f["bytes"]} bytes' + (f'  {f["path"]}' if f['path'] else '  (--out DIR keeps it)'))
            continue
        print(f'  {f["key"]}  {f["chars"]} chars' + (f'  {len(f["lines"])} lines match {grep!r}' if grep and f['lines'] else ''))
        for line in f['lines']:
            print(f'    {line}')
    if grep and not any(f.get('lines') for f in r['fields']):
        print(f'  no line matches {grep!r}')


def cmd_observe(a):
    results = observe(a.task, a.obs, a.click, a.goto, a.grep, a.out, a.path)
    if a.json:
        print(json.dumps(results, ensure_ascii=False, indent=1))
    else:
        for r in results:
            _print_observation(r, a.grep)
    return 0


# ------------------------------------------------------------------------------------------------------------ signs
def _view_of(selector, spec):
    """The task view (page or dialog) whose block the selector names, or None."""
    block = (selector or '').lstrip('#')
    for name, view in ((spec.get('flow') or {}).get('views') or {}).items():
        if any(b.get('id') == block for b in view.get('blocks') or []):
            return name
    return None


def static_signs(folder, spec):
    """The anchors of the task's scoring/evaluation.json: id, phrase, selector and the view that defines the selector."""
    anchors = json.loads((Path(folder) / 'scoring/evaluation.json').read_text()).get('anchors') or []
    return [{'id': a['id'], 'text_contains': a.get('text_contains'), 'selector': a.get('selector'),
             'view': _view_of(a.get('selector'), spec)} for a in anchors]


def _site_event(env):
    actions = env.env.task.runtime.actions
    return any(e.get('source') == 'site_instrumentation' and e.get('event_id') for e in (actions[-1].get('events', []) if actions else []))


def _bids(env, selector):
    """The bids of the visible elements the selector matches, in page order."""
    from scamworld.corpus.neutral_names import to_served
    loc = env.env.page.locator(to_served(selector))
    return [b for i in range(loc.count()) if loc.nth(i).is_visible() and (b := loc.nth(i).get_attribute('bid'))]


def _click_step(env, selector, expect_event):
    """Click the first match; for a go: step whose click records no site event, try the next match (as `scamworld verify`)."""
    for bid in _bids(env, selector):
        _, _, _, _, info = env.step({'action': 'click', 'bid': bid})
        if not info.get('rejected') and (not expect_event or _site_event(env) or env.done):
            return True
    return False


def _fill_step(env, selector, text):
    bids = _bids(env, selector)
    return bool(bids) and not env.step({'action': 'fill', 'bid': bids[0], 'text': text})[4].get('rejected')


def _do_step(env, step):
    """One step of a spec path ('do:go:product', 'click:<selector>', 'fill:<id>=<kind>', 'compose:<id>=<JSON text>'); True when done."""
    if step.startswith('do:'):
        return _click_step(env, f'[data-sw-do="{step[3:]}"]', step.startswith('do:go:'))
    if step.startswith('click:'):
        return _click_step(env, step[6:], False)
    if step.startswith('fill:'):
        from scamworld.scoring.evaluation.contracts import fixture_value
        iid, kind = step[5:].split('=')
        return _fill_step(env, '#' + iid, fixture_value(kind))
    if step.startswith('compose:'):
        iid, encoded = step[8:].split('=', 1)
        return _fill_step(env, '#' + iid, json.loads(encoded))
    return False


def _visible_now(env):
    """(ids of the anchors on screen after the last step, page address), read from the last observation record.
    (Exporting the whole trace instead copies every earlier observation each time and slows a long walk down.)"""
    record = env.env.task.runtime.observations[-1]
    ids = [e['evidence_id'] for e in record.get('visible_evidence') or []] + [a['id'] for a in record.get('private_anchor_regions') or []]
    return list(dict.fromkeys(ids)), record.get('url')


def _page_key(env):
    record = env.env.task.runtime.observations[-1]
    return record.get('url'), (record.get('state') or {}).get('state_id')


WHY_RANK = ('text', 'hidden', 'off screen', 'covered', 'other')   # how far an element on the page is from counting; later is closer
# The checks of the scorer's anchor test (env/environment.py PRIVATE_ANCHORS_JS): innerText with the phrase (case matters, so CSS
# upper-casing counts), painted, fully inside the viewport, and the element is what sits at five points of it.
WHY_JS = """([selector, phrase]) => { try {
  const squash = s => s.normalize('NFKC').replace(/\\s+/g, '');
  const els = Array.from(document.querySelectorAll(selector));
  if (!els.length) return 'missing';
  let best = 'text';
  const rank = ['text', 'hidden', 'off screen', 'covered', 'other'];
  const up = w => { if (rank.indexOf(w) > rank.indexOf(best)) best = w; };
  for (const el of els) {
    const text = (el.innerText || '').replace(/\\s+/g, ' ').trim();
    if (!text || (phrase && !(text.includes(phrase) || (squash(phrase) && squash(text).includes(squash(phrase)))))) continue;
    const r = el.getBoundingClientRect();
    let painted = true;
    for (let p = el; p; p = p.parentElement) { const s = getComputedStyle(p); if (s.display === 'none' || s.visibility === 'hidden' || Number(s.opacity) === 0) painted = false; }
    if (!painted || !(r.width > 0 && r.height > 0)) { up('hidden'); continue; }
    if (!(r.left >= 0 && r.top >= 0 && r.right <= innerWidth && r.bottom <= innerHeight)) { up('off screen'); continue; }
    const hit = [[.5, .5], [.05, .05], [.95, .05], [.05, .95], [.95, .95]].every(([x, y]) => {
      const h = document.elementFromPoint(r.x + r.width * x, r.y + r.height * y); return h && (h === el || el.contains(h) || h.contains(el)); });
    up(hit ? 'other' : 'covered');
  }
  return best; } catch (e) { return 'missing'; } }"""
WHY_TEXT = {'text': 'its text, as shown (capital letters included), does not contain the phrase',
            'hidden': 'it is hidden or has no size', 'off screen': 'it is never fully inside the window',
            'covered': 'another element covers it',
            'other': "it looks fully on screen, yet the scorer did not count it; check the anchor's states and that its text is part of the visible text"}
SCROLL_STEP, SCROLL_MAX = 700, 8   # pixels per scroll and number of scrolls after each path step
WALK_SECONDS = 180                 # time limit of the whole walk of `scamworld signs`


def _scroll_through(env, look, out_of_time=lambda: False):
    """Scroll down the page in steps, calling look() at each position, then back to the top."""
    moved = 0
    for _ in range(SCROLL_MAX):
        if out_of_time():
            break
        before = env.env.page.evaluate('window.scrollY')
        if env.done or env.step({'action': 'scroll', 'dy': SCROLL_STEP})[4].get('rejected'):
            break
        after = env.env.page.evaluate('window.scrollY')
        if after == before:
            break
        moved += after - before
        look()
    if moved and not env.done:
        env.step({'action': 'scroll', 'dy': -moved})


def _paths_to_walk(paths):
    """The spec's path names to walk: 'clue' first, then the others; a path that only repeats the start of another is left out."""
    names = sorted(paths, key=lambda n: (n != 'clue', n))
    walk = []
    for name in names:
        steps = paths[name]
        if not any(paths[w][:len(steps)] == steps for w in walk):
            walk.append(name)
    return walk


def walk_signs(task, anchors, seconds=WALK_SECONDS):
    """Walk the task's scripted paths in the browser and note for each anchor id where it was first on screen
    ({'path', 'step', 'action', 'url', 'scrolled'}; step 0 is the start page; each step is also looked at while scrolling down
    the page) and, separately, where its element was closest to counting without being on screen as the scorer needs it (the
    same dict plus 'why': one of WHY_TEXT). The walk stops after `seconds`.
    Returns (on screen, on the page only, problems), each a dict by anchor id except the list of problems."""
    from scamworld.corpus.neutral_names import to_served
    shown, present, problems = {}, {}, []
    deadline = time.monotonic() + seconds
    out_of_time = lambda: time.monotonic() > deadline
    work = Path(tempfile.mkdtemp(prefix='scamworld-signs-'))
    env = _open_env(task, DEFAULT_OBS, work, max_steps=1000)

    scanned = set()   # (page address, task state) whose page was already scrolled through; a step that leaves them is not scrolled again

    def scan(path, number, action):
        note(path, number, action)
        key = _page_key(env)
        if key not in scanned:
            scanned.add(key)
            _scroll_through(env, lambda: note(path, number, action, True), out_of_time)

    def note(path, number, action, scrolled=False):
        ids, url = _visible_now(env)
        where = {'path': path, 'step': number, 'action': action, 'url': url, 'scrolled': scrolled}
        for a in anchors:
            if a['id'] in ids:
                shown.setdefault(a['id'], where)
            elif a.get('selector'):
                why = env.env.page.evaluate(WHY_JS, [to_served(a['selector']), a.get('text_contains')])
                if why in WHY_RANK and (a['id'] not in present or WHY_RANK.index(why) > WHY_RANK.index(present[a['id']]['why'])):
                    present[a['id']] = {**where, 'why': why}

    try:
        paths = env.spec.get('paths') or {}
        for name in _paths_to_walk(paths):
            if out_of_time():
                break
            env.reset()
            scan(name, 0, 'start')
            for number, step in enumerate(paths[name], 1):
                if out_of_time():
                    break
                if env.done or not _do_step(env, step):
                    problems.append(f'path {name!r}: step {number} ({step}) could not be carried out')
                    break
                scan(name, number, step)
        if out_of_time():
            problems.append(f'the walk stopped after {seconds} s: later steps and paths were not looked at')
    finally:
        env.close()
        shutil.rmtree(work, ignore_errors=True)
    return shown, {k: v for k, v in present.items() if k not in shown}, problems


def _where(w):
    return f'{w["url"]}  path {w["path"]}, step {w["step"]} ({w["action"]})' + (', after scrolling' if w['scrolled'] else '')


def cmd_signs(a):
    from scamworld.corpus import spec_at
    from scamworld.cli import _known_folder
    name, folder = _known_folder(a.task)
    spec = spec_at(folder)
    signs = static_signs(folder, spec)
    benign = bool(spec.get('benign'))
    problems = []
    print(f'walking the scripted paths of {name} (up to {WALK_SECONDS} s)...', file=sys.stderr)
    try:
        shown, present, problems = walk_signs(a.task, signs)
    except Exception as e:   # the static part is still worth printing
        shown, present, problems = {}, {}, [f'the walk failed: {type(e).__name__}: {str(e)[:200]}']
    rows = [{**s, 'seen': shown.get(s['id']), 'on_page_only': present.get(s['id'])} for s in signs]
    if a.json:
        print(json.dumps({'task': name, 'signs': rows, 'notes': problems}, ensure_ascii=False, indent=1))
        return 0
    print(f'{name}: {len(rows)} {"checked statements" if benign else "warning signs"} (hidden scoring information, for whoever writes the task)')
    for r in rows:
        where = (_where(r['seen']) if r['seen'] else
                 f'on the page, but not counted - {WHY_TEXT[r["on_page_only"]["why"]]}: {_where(r["on_page_only"])}' if r['on_page_only']
                 else 'not reached on any scripted path')
        print(f'  {r["id"]}\n    phrase:   {r["text_contains"]!r}\n    selector: {r["selector"]}'
              + (f'  (view {r["view"]})' if r['view'] else '') + f'\n    shown:    {where}')
    for p in problems:
        print(f'note: {p}', file=sys.stderr)
    return 0


# ------------------------------------------------------------------------------------------------------------ table
KEYS = ('model', 'obs_modes', 'task', 'tag')


def run_key(run, score, key):
    """The value of a table row/column key for one run folder."""
    import re
    if key == 'tag':
        return re.sub(r'-\d+$', '', Path(run).name)
    if key == 'task':
        return score.get('case_id') or '?'
    return str(score.get(key) or '?')


def outcome_of(run, evaluator, errors=None):
    """The outcome word the evaluator gives for one run folder; 'error (ClassName)' when it fails (its message is added to `errors`)."""
    from scamworld import evaluators
    try:
        fn = evaluator.evaluate if hasattr(evaluator, 'evaluate') else evaluator
        result = fn(evaluators.Episode(Path(run)))
        if not isinstance(result, dict) or 'outcome' not in result:
            raise ValueError('an evaluator must return a dict with an "outcome" key')
        outcome = result['outcome']
    except Exception as e:
        if errors is not None:
            errors.append(f'{Path(run).name}: {type(e).__name__}: {str(e)[:200]}')
        return f'error ({type(e).__name__})'
    return str(outcome) if outcome else 'none'


def outcome_table(runs, rows='model', cols='obs_modes', evaluator='rules', errors=None):
    """{row value: {column value: Counter of outcomes}} for the run folders under `runs`; no file is written. An evaluator
    that cannot be loaded raises ValueError (one line); the messages of failed runs are added to the list `errors`."""
    from scamworld import evaluators
    try:
        ev = evaluators.load(evaluator)
    except Exception as e:
        raise ValueError(f'cannot load evaluator {evaluator!r}: {type(e).__name__}: {str(e)[:200]}') from e
    table = {}
    for run in evaluators.run_dirs(runs):
        score = json.loads((run / 'score.json').read_text())
        cell = table.setdefault(run_key(run, score, rows), {}).setdefault(run_key(run, score, cols), Counter())
        cell[outcome_of(run, ev, errors)] += 1
    return table


def _cell(counter):
    return ' · '.join(f'{k} {v}' for k, v in sorted(counter.items()))


def format_table(table, rows, cols, fmt):
    columns = sorted({c for r in table.values() for c in r})
    if fmt == 'json':
        return json.dumps({r: {c: dict(table[r][c]) for c in columns if c in table[r]} for r in sorted(table)}, ensure_ascii=False, indent=1)
    grid = [[r] + [_cell(table[r].get(c, Counter())) for c in columns] for r in sorted(table)]
    head = [f'{rows} \\ {cols}'] + columns
    if fmt == 'csv':
        import csv
        import io
        buf = io.StringIO()
        csv.writer(buf, lineterminator='\n').writerows([head] + grid)
        return buf.getvalue().rstrip('\n')
    line = lambda cells: '| ' + ' | '.join(cells) + ' |'
    return '\n'.join([line(head), line(['---'] * len(head))] + [line(row) for row in grid])


def cmd_table(a):
    from scamworld.cli import _need_runs
    runs = _need_runs(a.runs)
    errors = []
    try:
        table = outcome_table(runs, a.rows, a.cols, a.evaluator, errors)
    except ValueError as e:
        sys.exit(f'scamworld table: {e}')
    print(format_table(table, a.rows, a.cols, a.format))
    if errors:
        print(f'note: the evaluator failed on {len(errors)} of {len(runs)} runs (shown as "error (...)"); first: {errors[0]}', file=sys.stderr)
    return 1 if len(errors) == len(runs) else 0


# ------------------------------------------------------------------------------------------------------------ wiring
def register(subparsers):
    """Add observe, signs and table to the `scamworld` subparsers."""
    s = subparsers.add_parser('observe', help='what the agent receives for a page, under each observation setting (no model)')
    s.add_argument('task', help='task id under tasks/, or the path of a task folder')
    s.add_argument('--obs', action='append', metavar='MODES',
                   help=f'observation setting as in scamworld run --obs, e.g. ax_tree or screenshot,ax_controls; repeat for more '
                        f'than one (default {DEFAULT_OBS})')
    s.add_argument('--path', metavar='NAME[:N]', help="first follow a scripted path of the task (the names are in scoring/spec.json, e.g. clue), or its first N steps; "
                   "`scamworld signs` shows where each path step leads")
    s.add_argument('--click', action='append', default=[], metavar='BID',
                   help='click this element id (the number in [ ] in ax_tree, "bid" in ax_controls; find it with a first observe and --grep) before '
                        'observing; repeat to click in order')
    s.add_argument('--goto', metavar='URL', help='open this address (after --path and any --click); it skips the earlier steps of the visit, '
                   'so the cart and other state are empty; a site-relative address like checkout.html is joined to the current page')
    s.add_argument('--grep', metavar='TEXT', help='show the lines that contain TEXT (any case) instead of the first lines of each field')
    s.add_argument('--out', metavar='DIR', help='save the full fields in DIR/<setting>/ (axtree.txt, pruned.html, controls.json, screenshot.png, meta.json)')
    s.add_argument('--json', action='store_true', help='print JSON instead of text')
    s.set_defaults(fn=cmd_observe)
    s = subparsers.add_parser('signs', help="a task's warning signs and where they are shown (the task's hidden scoring information)")
    s.add_argument('task', help='task id under tasks/, or the path of a task folder')
    s.add_argument('--json', action='store_true', help='print JSON instead of text')
    s.description = ('Lists the warning signs the task scores on: id, phrase, and the page or dialog and step of the task\'s scripted '
                     'path where the phrase is on screen. This is the hidden scoring information of the task: it is for whoever '
                     'writes the task, not for the agent under test.')
    s.set_defaults(fn=cmd_signs)
    s = subparsers.add_parser('table', help='count the outcomes of finished episodes per row and column')
    s.add_argument('runs', nargs='+', help='run folders, or folders above them')
    s.add_argument('--rows', choices=KEYS, default='model', help='what the rows are (default model; tag is the run folder name without its -N suffix)')
    s.add_argument('--cols', choices=KEYS, default='obs_modes', help='what the columns are (default obs_modes)')
    s.add_argument('--evaluator', default='rules', help='rules (default, no LLM), scamworld (judge v5), or module:attr / file.py:attr; nothing is written')
    s.add_argument('--format', choices=['md', 'csv', 'json'], default='md', help='output format (default md)')
    s.set_defaults(fn=cmd_table)


def main(argv=None):
    p = argparse.ArgumentParser(prog='python -m scamworld.inspect_cmds', description=__doc__.split('\n')[0])
    register(p.add_subparsers(dest='command', required=True))
    a = p.parse_args(argv)
    sys.exit(a.fn(a) or 0)


if __name__ == '__main__':
    main()
