"""`scamworld` command line.

    scamworld tasks [--scene S] [--benign | --scam]       list the tasks (SCAMWORLD_TASKS: another task folder)
    scamworld new-task <folder> [--benign]                a runnable task of your own from the template (docs/custom-tasks.md)
    scamworld new-task <folder> --from <task> [--instruction T]    a copy of a task (e.g. a released one) to change into your own
    scamworld serve <task>                                serve a task's website on 127.0.0.1 (preview, no agent)
    scamworld run <task> [--model M] [--runs N] ...       one agent episode (python -m scamworld.episode --help)
    scamworld evaluate <run dir>... [--evaluator E]       outcome of finished episodes (docs/evaluators.md)
    scamworld exp plan|run <experiment> [...]             paper experiments (python -m scamworld.experiments --help)
    scamworld verify <task>                               scripted browser probes of a task, no model calls
    scamworld score <run dir>... [--judge cached|none|live] [--write [--out NAME]]   re-score finished episodes offline
    scamworld judge <task> <reason text> [--run DIR]      classify one stop reason (judge v5; --prompt v4 for the old judge)
    scamworld judge --runs <run dir>... [--write]         judge v5 over finished episodes -> score.json `judge_v5`
    scamworld check                                       task files against release/path-map.json
    scamworld observe <task> [--obs M]... [--click BID]... [--grep T]   what the agent would see on a page, no model
    scamworld signs <task>                                the task's warning signs and where scripted paths show them
    scamworld table <run dir>... [--rows R] [--cols C]    outcome counts of finished episodes as a table

<task> is a task id under tasks/ or the path of a task folder (one holding task.json).
"""
import argparse
import json
import sys


def _delegate(module, prog, argv):
    import importlib
    main = importlib.import_module(module).main
    sys.argv = [prog] + argv
    return main()


def cmd_tasks(a):
    from scamworld.corpus import index
    rows = [t for t in index()['tasks'] if (not a.scene or t['scene'] == a.scene)
            and (not a.benign or t['benign']) and (not a.scam or not t['benign'])]
    for t in rows:
        print(f"{t['task']:<16} {t['scene']:<10} {'benign' if t['benign'] else 'scam':<6} {t['variant_of'] or ''}")
    print(f'{len(rows)} tasks', file=sys.stderr)


def _known_folder(task):
    """(name, folder) of a task id or task folder path; exits with one line when no task.json is there."""
    from scamworld.corpus import resolve_task
    name, folder = resolve_task(task)
    if not (folder / 'task.json').is_file():
        sys.exit(f"unknown task '{task}'; list them with scamworld tasks")
    return name, folder


def _use_folder(task):
    """A task given by its folder path: point the task root at its parent folder; returns the task id."""
    import scamworld.corpus
    name, folder = _known_folder(task)
    if folder != scamworld.corpus.task_dir(name):
        scamworld.corpus.TASKS = folder.parent
    return name


def answer_fields_note(folder):
    """One line when the copied task still has the answer_fields of its old request (task.json), else ''."""
    from pathlib import Path
    try:
        fields = json.loads((Path(folder) / 'task.json').read_text(encoding='utf-8')).get('answer_fields') or []
    except (OSError, ValueError):
        return ''
    questions = [f.get('question') for f in fields if isinstance(f, dict) and f.get('question')]
    if not questions:
        return ''
    return (f'  note:         answer_fields in task.json are still those of the copied request ("{questions[0][:90]}"). The agent is '
            f'not shown them: the built-in scoring fills them from what the website recorded and from the final message, and an '
            f'evaluator of your own does not use them\n')


def cmd_new_task(a):
    from scamworld.sitekit.scaffold import copy_task, new_task
    if (a.instruction or a.instruction_file) and not a.source:
        sys.exit('--instruction and --instruction-file go with --from: they replace the request of the copied task')
    instruction = a.instruction
    if a.instruction_file:
        try:
            instruction = open(a.instruction_file, encoding='utf-8').read()
        except OSError as e:
            sys.exit(f'cannot read --instruction-file: {e}')
    if instruction is not None and not instruction.strip():
        sys.exit('the instruction is empty')
    if a.source and (a.benign or a.url):
        sys.exit('--from copies a task with its own website: --benign and --url apply to the template only')
    try:
        if a.source:
            folder = copy_task(a.folder, a.source, force=a.force, instruction=instruction)
        else:
            folder = new_task(a.folder, benign=a.benign, url=a.url, force=a.force)
    except (FileExistsError, ValueError, OSError) as e:
        sys.exit(str(e))
    request = f'  your request: {folder / "task.json"} (instruction, context.persona, context.profile)\n' if a.source else ''
    if instruction is not None:
        request = f'  your request: {folder / "task.json"} instruction set from {"--instruction-file" if a.instruction_file else "--instruction"}\n'
    note = answer_fields_note(folder) if instruction is not None else ''
    print(f'wrote {folder}\n{request}{note}  look at it:   scamworld serve {a.folder}\n  check it:     scamworld verify {a.folder}\n'
          f'  run an agent: scamworld run {a.folder} --model <id> --base-url <OpenAI-compatible URL>')


def _need_runs(runs):
    """The run folders (with score.json) under the given paths; exits with one line when there is none."""
    from scamworld import evaluators
    found = evaluators.run_dirs(runs)
    if not found:
        sys.exit(f'no run folders (score.json) found under {" ".join(map(str, runs))}')
    return found


def _check_judge_backend(backend, endpoint, option='--judge-endpoint NAME', backend_option='--backend endpoint or openrouter'):
    """Exit with one line when the judge backend cannot be used: no OpenRouter or gateway key, or an endpoint that cannot be built
    or has no key."""
    if backend == 'openrouter':
        from scamworld.episode import has_judge_key
        if not has_judge_key():
            sys.exit(NO_JUDGE)
    if backend == 'cz':
        from scamworld.agents.openrouter import gateway_key
        try:
            gateway_key()
        except ValueError:
            sys.exit(f'the gateway judge backend is not configured: use {backend_option} (docs/evaluators.md)')
    if backend != 'endpoint':
        return
    import os
    from scamworld.scoring.judge import judge_endpoint
    if not (endpoint or os.environ.get('SCAMWORLD_JUDGE_ENDPOINT')):
        sys.exit(f'the endpoint judge backend needs {option} (a name in the endpoints file) or SCAMWORLD_JUDGE_ENDPOINT')
    try:
        judge_endpoint(endpoint).key()   # the key variable must be set too
    except ValueError as e:   # includes EndpointError
        sys.exit(str(e))


def cmd_evaluate(a):
    import os
    from scamworld import evaluators
    try:
        options = json.loads(a.options) if a.options else {}
    except ValueError as e:
        sys.exit(f'--options is not valid JSON: {e}')
    if not isinstance(options, dict):
        sys.exit('--options must be a JSON object of keyword arguments')
    runs = _need_runs(a.runs)
    if a.evaluator == 'scamworld':
        _check_judge_backend(options.get('judge_backend') or os.environ.get('SCAMWORLD_JUDGE_BACKEND') or evaluators.default_backend(),
                             options.get('judge_endpoint'), option='--options \'{"judge_endpoint": "NAME"}\'',
                             backend_option='judge_backend "endpoint" or "openrouter" in --options')
    bad = 0
    for run in runs:
        try:
            out = evaluators.evaluate(run, a.evaluator, write=not a.no_write, **options)
        except Exception as e:   # one unreadable episode must not stop a tree
            bad += 1
            out = {'error': f'{type(e).__name__}: {e}'[:300]}
        print(json.dumps({'run': str(run), **out}, ensure_ascii=False, default=str), flush=True)
    return 1 if bad else 0


def cmd_serve(a):
    import threading
    from scamworld.env.runtime import LocalSiteServer
    _, folder = _known_folder(a.task)
    server = LocalSiteServer(folder / 'site')
    start = json.loads((folder / 'task.json').read_text()).get('start_path', '/index.html')
    print(server.origin + start, flush=True)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        server.close()


def cmd_verify(a):
    from scamworld.corpus import require_released
    from scamworld.sitekit.verify import verify
    task = _use_folder(a.task)
    require_released([task])   # the task bytes must be the released ones before probing them (your own tasks: skipped)
    return verify(task)


def cmd_score(a):
    from pathlib import Path
    from scamworld.scoring.rescore import compare, is_setup_failure, rescore, rescore_causes, rescored_record
    if a.out == 'score.json' or Path(a.out).name != a.out:
        sys.exit('--out is a file name other than score.json: the raw score is never overwritten')
    runs = _need_runs(a.runs)   # an episode folder, or any folder above episodes (a runs tree, one model, ...)
    kept = [run for run in runs if not is_setup_failure(run)]
    if len(kept) < len(runs):
        print(f'note: skipped {len(runs) - len(kept)} run folder(s) that failed at setup and have no trace', file=sys.stderr)
    runs = kept
    bad = 0
    for run in runs:
        try:
            recorded, result = rescore(run, judge=a.judge, reparse=True)
        except Exception as e:   # one unreadable episode must not stop a tree
            bad += 1
            print(json.dumps({'run': str(run), 'error': f'{type(e).__name__}: {e}'[:300]}), flush=True)
            continue
        diff = compare(recorded, result)
        bad += bool(diff)
        print(json.dumps({'run': str(run), 'behavior_path': result.get('behavior_path'), 'overall': result.get('overall'),
                          'same_as_recorded': not diff, **({'differs': diff} if diff else {})}, ensure_ascii=False, default=str), flush=True)
        if a.write:
            causes = rescore_causes(run, recorded, result, judge=a.judge)
            (run / a.out).write_text(json.dumps(rescored_record(recorded, result, a.judge, causes), ensure_ascii=False, indent=1))
    return 1 if bad else 0


NO_JUDGE = ('no judge is configured: set SCAMWORLD_JUDGE_ENDPOINT, or put an OPENROUTER_API_KEY in .env.openweights or .env '
            '(see docs/evaluators.md)')


def resolve_backend(backend):
    """The judge backend: the one asked for, else evaluators.default_backend(); exits with one line when none is configured."""
    if backend:
        return backend
    from scamworld.evaluators import default_backend
    backend = default_backend()
    if not backend:
        sys.exit(NO_JUDGE)
    return backend


def cmd_judge(a):
    """Classify a stop reason (or the stop reasons of finished episodes) with the LLM judge; --prompt v4 selects the older judge."""
    from scamworld.paths import OPENWEIGHTS_ENV_FILE
    if a.prompt == 'v5':
        a.backend = resolve_backend(a.backend)
        _check_judge_backend(a.backend, a.judge_endpoint)
    if a.runs:
        if a.prompt != 'v5' or a.args:
            sys.exit('--runs judges with v5 only and takes no <task> <text>')
        from scamworld.scoring.rejudge import judge_runs
        out = judge_runs([str(r) for r in _need_runs(a.runs)], backend=a.backend, write=a.write, force=a.force, workers=a.workers,
                         log=lambda m: print(m, file=sys.stderr), endpoint=a.judge_endpoint)
        for run, block in out.items():
            print(json.dumps({'run': run, **{k: block.get(k) for k in ('label', 'raw_label', 'signal_verified', 'downgraded', 'skipped', 'error') if k in block}},
                             ensure_ascii=False))
        return 1 if any('error' in b for b in out.values()) else 0
    if len(a.args) != 2:
        sys.exit('usage: scamworld judge <task> <reason text> [--run DIR]  |  scamworld judge --runs <run dir>...')
    task, text = a.args
    name, folder = _known_folder(task)
    from scamworld.corpus import task_dir
    from scamworld.scoring.rejudge import case_scoring
    rubric = case_scoring(name, None if folder.resolve() == task_dir(name).resolve() else folder).get('reason_rubric') or {}
    if a.prompt == 'v4':
        from scamworld.episode import has_judge_key
        if not has_judge_key():
            sys.exit('the v4 judge runs on OpenRouter: put an OPENROUTER_API_KEY in .env.openweights or .env (see docs/evaluators.md)')
        from scamworld.scoring.judge import LLMJudge
        verdict = LLMJudge(env_file=OPENWEIGHTS_ENV_FILE, prompt='v4').classify(text, rubric)
    else:
        from scamworld.scoring.judge import JudgeV5
        from scamworld.scoring.visited import static_site, visited
        pages, urls = visited(a.run) if a.run else (static_site(folder), [])   # no episode: the site's own text
        from scamworld.scoring.rejudge import _failed
        make = lambda: JudgeV5(backend=a.backend, env_file=OPENWEIGHTS_ENV_FILE, **({'endpoint': a.judge_endpoint} if a.backend == 'endpoint' else {}))
        verdict = make().classify(text, rubric, pages, urls)
        if _failed(verdict) and verdict.get('cost_known') is not False:
            verdict = make().classify(text, rubric, pages, urls)   # once more with a fresh judge, as --runs
    print(json.dumps({k: v for k, v in verdict.items() if k not in ('api_request', 'api_response')}, ensure_ascii=False, indent=1))


PUBLIC_MANIFEST = 'scamworld.public_manifest.v1'   # release/path-map.json of the public release: task files and sha256 only


def _manifest_problem(manifest):
    """Why the rows of a public manifest cannot be read by corpus.verify (None: they can). A path under tasks/ is
    tasks/<task>/<file>."""
    def bad_path(path):
        if not isinstance(path, str):
            return f'the path {path!r} is not text'
        parts = path[len('tasks/'):].split('/', 1) if path.startswith('tasks/') else ['task', 'file']
        if len(parts) < 2 or not all(parts):
            return f'the path {path!r} has no file part'
    rows = manifest.get('rows')
    if not isinstance(rows, list):
        return 'its "rows" list is missing or malformed'
    for row in rows:
        if not isinstance(row, dict) or 'transform' not in row:
            return f'a "rows" entry has no "transform": {repr(row)[:80]}'
        if row['transform'] != 'retired' and row.get('new'):
            if 'new_sha256' not in row:
                return f'the "rows" entry of {row["new"]!r} has no "new_sha256"'
            if bad_path(row['new']):
                return 'in a "rows" entry, ' + bad_path(row['new'])
    for key in ('a8_files', 'task_tree_files'):
        files = manifest.get(key)
        if files is not None and not isinstance(files, dict):
            return f'"{key}" is not a mapping of path to digest'
        for path in files or {}:
            if bad_path(path):
                return f'in "{key}", ' + bad_path(path)


def cmd_check(a):
    from scamworld import paths
    pm = paths.RELEASE / 'path-map.json'
    manifest = None
    if pm.is_file():
        try:
            manifest = json.loads(pm.read_text())
        except ValueError as e:
            sys.exit(f'{pm} is not valid JSON ({e}): restore the release files')
    if isinstance(manifest, dict) and manifest.get('schema') == PUBLIC_MANIFEST:
        from scamworld.corpus import index, verify
        try:
            rows = index()['tasks']
        except FileNotFoundError as e:
            sys.exit(f'no task index: {e.filename}')
        released = [t['task'] for t in rows if t.get('released', True)]   # rows with "released": false are your own tasks (scamworld new-task)
        skipped = len(rows) - len(released)
        if not released:
            print(json.dumps({'manifest': PUBLIC_MANIFEST, 'tasks': 0, 'skipped_own_tasks': skipped, 'problems': [],
                              'note': 'no released tasks in the task index: nothing to check'}, indent=1))
            return 0
        problem = _manifest_problem(manifest)
        if problem:
            sys.exit(f'{pm} is not the public manifest (schema {PUBLIC_MANIFEST}): {problem}; '
                     'restore the release files (for example from the Hugging Face dataset)')
        bad = verify(released)
        print(json.dumps({'manifest': PUBLIC_MANIFEST, 'tasks': len(released), 'skipped_own_tasks': skipped,
                          'problems': [f'{t}: {", ".join(p[:3])}' for t, p in sorted(bad.items())][:50]}, indent=1))
        return 1 if bad else 0
    try:
        from scamworld.corpus.release import check
    except ImportError:
        what = 'is not the public manifest' if pm.is_file() else 'is missing or is not the public manifest'
        sys.exit(f'{pm} {what} (schema {PUBLIC_MANIFEST}), and this tree does not include the code that checks the '
                 'full release path map: restore the release files (for example from the Hugging Face dataset)')
    out = check()
    print(json.dumps({k: (v[:50] if k == 'problems' else v) for k, v in out.items()}, indent=1))
    return 1 if out['problems'] else 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] in (['run'], ['exp']):   # pass everything through to the runner's own parser
        module = {'run': 'scamworld.episode', 'exp': 'scamworld.experiments'}[argv[0]]
        return _delegate(module, 'scamworld ' + argv[0], argv[1:])
    p = build_parser()
    a = p.parse_args(argv)
    sys.exit(a.fn(a) or 0)


def _http_url(value):
    if not value.startswith(('http://', 'https://')):
        raise argparse.ArgumentTypeError('must start with http:// or https://')
    return value


def build_parser():
    p = argparse.ArgumentParser(prog='scamworld', description=__doc__.split('\n')[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split('\n', 2)[2])
    sub = p.add_subparsers(dest='command', required=True)
    s = sub.add_parser('tasks', help='list the tasks')
    s.add_argument('--scene', help='only the tasks of this scene (e.g. shop)')
    g = s.add_mutually_exclusive_group()
    g.add_argument('--benign', action='store_true', help='only the benign tasks (legitimate controls)')
    g.add_argument('--scam', action='store_true', help='only the scam tasks')
    s.set_defaults(fn=cmd_tasks)
    s = sub.add_parser('new-task', help='a runnable task of your own: from the template, or a copy of a task (--from)')
    s.add_argument('folder', help='new task folder; its name is the task id (e.g. my-tasks/parcel-fee-01)')
    s.add_argument('--benign', action='store_true', help='a benign control (the same flow without the warning sign)')
    s.add_argument('--url', type=_http_url, help='the URL the browser shows for the site, http:// or https:// (default a .example address)')
    s.add_argument('--from', dest='source', metavar='TASK',
                   help='copy this task (an id under tasks/ or a task folder) instead of the template: its website and scoring '
                        'stay, the copy gets the new id and an index row of your own (docs/custom-tasks.md)')
    g = s.add_mutually_exclusive_group()
    g.add_argument('--instruction', metavar='TEXT', help='with --from: the request of the copy, in place of the copied one (a purchase, a question, ...). '
                   'instruction_en and instruction_locale of the copied task are dropped; answer_fields stay (the agent is not shown them; the built-in scoring fills them from the website\'s record and the final message)')
    g.add_argument('--instruction-file', metavar='FILE', help='with --from: read the request of the copy from FILE (UTF-8 text)')
    s.add_argument('--force', action='store_true', help='write into a folder that already has files, overwriting the template or copied files')
    s.set_defaults(fn=cmd_new_task)
    s = sub.add_parser('serve', help="serve a task's website on 127.0.0.1 (no agent)")
    s.add_argument('task', help='task id under tasks/, or the path of a task folder')
    s.set_defaults(fn=cmd_serve)
    s = sub.add_parser('evaluate', help='outcome of finished episodes with a built-in or your own evaluator')
    s.add_argument('runs', nargs='+', help='run folders, or folders above them')
    s.add_argument('--evaluator', default='scamworld', help='scamworld (default: rules + judge v5), rules (no LLM), module:attr or file.py:attr')
    s.add_argument('--options', help='JSON keyword arguments for an evaluator class, e.g. \'{"judge_backend": "endpoint", "judge_endpoint": "my-judge"}\'')
    s.add_argument('--no-write', action='store_true', help='print only; do not write evaluation-<name>.json')
    s.set_defaults(fn=cmd_evaluate)
    sub.add_parser('run', help='one agent episode (options: scamworld run --help)')
    sub.add_parser('exp', help='paper experiments (options: scamworld exp --help)')
    s = sub.add_parser('verify', help='scripted browser checks of a task, no model calls')
    s.add_argument('task', help='task id under tasks/, or the path of a task folder')
    s.set_defaults(fn=cmd_verify)
    s = sub.add_parser('score', help='re-score finished episodes offline')
    s.add_argument('runs', nargs='+', help='run folders (with score.json), or folders above them')
    s.add_argument('--judge', choices=['cached', 'none', 'live'], default='cached',
                   help='reason judge. cached (default) replays the in-episode judge verdict recorded in score.json '
                        '(reason_judge; a run without one, or whose judge call failed, is scored by the keyword rules), '
                        'none: keyword rules only, live: calls the v4 judge on OpenRouter again (billed)')
    s.add_argument('--write', action='store_true', help='write the re-scored score.json next to score.json (never over it)')
    s.add_argument('--out', default='rescore.json', help='file name for --write (default rescore.json)')
    s.set_defaults(fn=cmd_score)
    s = sub.add_parser('judge', help='classify a stop reason with the LLM judge')
    s.add_argument('args', nargs='*', metavar='<task> <reason text>', help='the task id and the stop reason to classify (not with --runs)')
    s.add_argument('--prompt', choices=['v5', 'v4'], default='v5', help='judge version: v5 (default; checks the named sign against the visited pages) or v4 (the older judge, text only)')
    s.add_argument('--backend', choices=['cz', 'openrouter', 'endpoint'], default=None, metavar='{openrouter,endpoint}',
                   help='judge backend (default: SCAMWORLD_JUDGE_ENDPOINT if set, else OpenRouter when a key is configured)')
    s.add_argument('--judge-endpoint', help='backend endpoint: a name in the endpoints file (or SCAMWORLD_JUDGE_ENDPOINT)')
    s.add_argument('--run', help='episode whose visited pages verify the sign (v5)')
    s.add_argument('--runs', nargs='+', help='judge the stop reasons of these finished episodes (run folders, or folders above them) instead of one text')
    s.add_argument('--write', action='store_true', help='write the verdict to score.json `judge_v5`')
    s.add_argument('--force', action='store_true', help='judge again episodes that already have this v5 verdict')
    s.add_argument('--workers', type=int, default=8, help='episodes judged in parallel with --runs (default 8; 1 on OpenRouter)')
    s.set_defaults(fn=cmd_judge)
    s = sub.add_parser('check', help='check the task files against the release manifest')
    s.set_defaults(fn=cmd_check)
    from scamworld.inspect_cmds import register
    register(sub)
    return p


if __name__ == '__main__':
    sys.exit(main())
