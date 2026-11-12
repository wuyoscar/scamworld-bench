"""docs/api.md against the code: every documented name exists, every documented signature matches, every offline example runs.

Three checks, no browser and no model call:
1. each backticked dotted name that starts with `scamworld.` can be imported and read;
2. each `<!-- signature: NAME -->` comment above a code block is followed by a call form whose parameter names, order
   and defaults equal inspect.signature (a class: its constructor; a method: without self);
3. each python block under `<!-- offline example -->` runs in a fresh temporary folder with SCAMWORLD_TASKS unset.
"""
import ast
import importlib
import inspect
import re
import sys
from pathlib import Path

import pytest

DOC = Path(__file__).resolve().parents[2] / 'docs' / 'api.md'
TEXT = DOC.read_text(encoding='utf-8')

REQUIRED = [
    'scamworld.gym.ScamWorldEnv', 'scamworld.gym.ScamWorldEnv.reset', 'scamworld.gym.ScamWorldEnv.step',
    'scamworld.gym.ScamWorldEnv.save', 'scamworld.gym.ScamWorldEnv.evaluate', 'scamworld.gym.run_episode',
    'scamworld.gym.Agent.reset', 'scamworld.gym.Agent.act', 'scamworld.evaluators.load',
    'scamworld.evaluators.evaluate', 'scamworld.evaluators.run_dirs', 'scamworld.evaluators.ScamWorldEvaluator',
    'scamworld.evaluators.Episode', 'scamworld.corpus.index', 'scamworld.corpus.task_dir',
    'scamworld.corpus.resolve_task', 'scamworld.corpus.spec_at', 'scamworld.sitekit.scaffold.new_task',
    'scamworld.sitekit.scaffold.copy_task',
]


def resolve(name):
    """Import the longest importable module prefix of a dotted name and getattr the rest."""
    parts = name.split('.')
    for i in range(len(parts), 0, -1):
        try:
            obj = importlib.import_module('.'.join(parts[:i]))
        except ImportError:
            continue
        for attr in parts[i:]:
            obj = getattr(obj, attr)
        return obj
    raise ImportError(name)


def documented_names():
    names = set()
    for span in re.findall(r'`([^`\n]+)`', TEXT):
        m = re.match(r'scamworld(?:\.[A-Za-z_]\w*)+', span)
        if m:
            names.add(m.group(0))
    return sorted(names)


SRC = Path(__file__).resolve().parents[2] / 'src' / 'scamworld'


def test_every_listed_function_or_class_has_a_signature_block():
    stability = TEXT.split('\n## Stability', 1)[1]
    documented = {n for n, _ in signature_blocks()}
    missing = []
    for m in re.finditer(r'`(scamworld(?:\.\w+)+)`: ([^\n]*(?:\n  [^\n]*)*)', stability):
        module, names = m.group(1), re.findall(r'`(\w+)`', m.group(2))
        for n in names:
            try:
                obj = getattr(importlib.import_module(module), n)
            except (ImportError, AttributeError):
                continue
            if (inspect.isfunction(obj) or inspect.isclass(obj)) and f'{module}.{n}' not in documented \
                    and not (inspect.isclass(obj) and issubclass(obj, BaseException)) and n not in ('RuleEvaluator', 'Agent'):
                missing.append(f'{module}.{n}')
    assert not missing, 'public callables without a signature block: ' + ', '.join(missing)


def test_documented_variables_exist_in_the_source():
    source = '\n'.join(p.read_text(encoding='utf-8') for p in SRC.rglob('*.py'))
    missing = sorted({v for v in re.findall(r'`(SCAMWORLD_[A-Z_]+)`', TEXT) if v not in source})
    assert not missing, 'variables the source never reads: ' + ', '.join(missing)


def test_documented_cli_flags_exist():
    from scamworld import cli
    source = (SRC / 'cli.py').read_text(encoding='utf-8') + (SRC / 'episode.py').read_text(encoding='utf-8') \
        + (SRC / 'experiments.py').read_text(encoding='utf-8') + (SRC / 'inspect_cmds.py').read_text(encoding='utf-8')
    missing = sorted({f for f in re.findall(r'`(--[a-z][a-z-]+)', TEXT) if f"'{f}'" not in source})
    assert not missing, 'flags that no parser defines: ' + ', '.join(missing)


def test_documented_outcomes_and_episode_attributes():
    outcome_source = (SRC / 'scoring' / 'outcome.py').read_text(encoding='utf-8')
    table = TEXT.split('### Outcomes', 1)[1].split('`detected` and `declined`', 1)[0]
    outcomes = re.findall(r'^\| `(\w+)` \|', table, re.M)
    assert outcomes and not [o for o in outcomes if o != 'None' and f"'{o}'" not in outcome_source]
    from scamworld.evaluators import Episode
    block = TEXT.split('### `Episode`', 1)[1].split('### Evaluators', 1)[0]
    names = [n for row in re.findall(r'^\| ((?:`\w+`(?:, )?)+) \|', block, re.M) for n in re.findall(r'\w+', row)]
    assert not [n for n in names if n not in ('attribute',) and not (hasattr(Episode, n) or n in getattr(Episode, '__dataclass_fields__', {}) or n in Episode.__init__.__code__.co_varnames)], names


def test_defaults_and_links():
    from scamworld import experiments
    args = experiments.build_parser().parse_args(['plan', 'custom'])
    assert str(experiments.STEP_CAP) in TEXT and f'default {args.jobs}' in TEXT and f'default {args.budget}' in TEXT
    docs = DOC.parent
    broken = [m for m in re.findall(r'\]\((?!http)([\w./-]+\.md)', TEXT) if not (docs / m).exists()]
    assert not broken, broken


def test_doc_exists_and_has_the_sections():
    assert TEXT.startswith('# API reference\n')
    h2 = re.findall(r'^## (.+)$', TEXT, re.M)
    assert [h.split(':')[0].strip().lower() for h in h2] == [
        'tasks', 'environment', 'agents', 'evaluation', 'experiments', 'command line to python', 'stability']


def test_documented_names_exist():
    missing = []
    for name in documented_names():
        try:
            resolve(name)
        except Exception as e:
            missing.append(f'{name} ({type(e).__name__}: {e})')
    assert not missing, 'documented names that do not exist:\n  ' + '\n  '.join(missing)


def parse_call(line):
    """'f(a, b=1, *args, **kw)' -> list of (name, default or inspect.Parameter.empty, kind)."""
    call = ast.parse(line.strip(), mode='eval').body
    assert isinstance(call, ast.Call), line
    out = []
    for a in call.args:
        if isinstance(a, ast.Starred):
            out.append((a.value.id, inspect.Parameter.empty, inspect.Parameter.VAR_POSITIONAL))
        else:
            assert isinstance(a, ast.Name), f'positional parameter must be a bare name: {line}'
            out.append((a.id, inspect.Parameter.empty, None))
    for k in call.keywords:
        if k.arg is None:
            out.append((k.value.id, inspect.Parameter.empty, inspect.Parameter.VAR_KEYWORD))
        else:
            out.append((k.arg, ast.literal_eval(k.value), None))
    return out


def actual(obj):
    sig = inspect.signature(obj)
    params = list(sig.parameters.values())
    if params and params[0].name == 'self':
        params = params[1:]
    return [(p.name, p.default, p.kind if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD) else None) for p in params]


def signature_blocks():
    return re.findall(r'<!-- signature: (\S+) -->\s*\n```[a-z]*\n(.*?)\n', TEXT)


def test_signatures_match_the_code():
    blocks = signature_blocks()
    problems = []
    for name, first in blocks:
        try:
            want, have = parse_call(first), actual(resolve(name))
        except Exception as e:
            problems.append(f'{name}: cannot compare ({type(e).__name__}: {e})')
            continue
        if want != have:
            problems.append(f'{name}\n    doc:  {first.strip()}\n    code: {have}')
    assert not problems, 'signature mismatches:\n  ' + '\n  '.join(problems)
    documented = {n for n, _ in blocks}
    assert not [r for r in REQUIRED if r not in documented], \
        'no signature block for: ' + ', '.join(r for r in REQUIRED if r not in documented)


def offline_examples():
    return re.findall(r'<!-- offline example -->\s*\n```python\n(.*?)\n```', TEXT, re.S)


def test_there_are_offline_examples():
    assert len(offline_examples()) >= 6


@pytest.mark.parametrize('index', range(len(offline_examples())))
def test_offline_example_runs(index, tmp_path, monkeypatch):
    code = offline_examples()[index]
    monkeypatch.delenv('SCAMWORLD_TASKS', raising=False)
    monkeypatch.chdir(tmp_path)
    experiments = sys.modules.get('scamworld.experiments')
    saved = dict(experiments.EXPERIMENTS) if experiments else None
    try:
        exec(compile(code, f'api.md example {index}', 'exec'), {'__name__': '__example__'})
    finally:
        experiments = sys.modules.get('scamworld.experiments')
        if experiments and saved is not None:
            experiments.EXPERIMENTS.clear()
            experiments.EXPERIMENTS.update(saved)
        elif experiments:
            for k in [k for k in experiments.EXPERIMENTS if k.startswith('my-')]:
                del experiments.EXPERIMENTS[k]
