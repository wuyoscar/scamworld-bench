"""`scamworld run --instruction / --instruction-file / --evaluate` and the run_dir key of the printed line.
    uv run pytest tests/unit/test_run_custom.py -q
"""
import json

import pytest

from scamworld import episode


def parse(*argv):
    return episode.build_parser().parse_args(['shop-11', *argv])


def stub_run_one(monkeypatch, calls, folder_files=None):
    def run_one(cid, out, *a, **k):
        calls.append({'cid': cid, 'out': out, **k})
        out.mkdir(parents=True, exist_ok=True)
        (out / 'score.json').write_text(json.dumps({'case_id': cid}))
        (out / 'trace.json').write_text(json.dumps({'case_id': cid, 'steps': []}))
        return {'behavior_path': 'x', 'overall': 1, 'stop': 'terminated'}
    monkeypatch.setattr(episode, 'run_one', run_one)


def test_parser_accepts_the_new_options_and_keeps_defaults():
    a = parse()
    assert a.instruction is None and a.instruction_file is None and a.evaluate is None
    a = parse('--instruction', 'Tell me what it sells.', '--evaluate', 'rules')
    assert a.instruction == 'Tell me what it sells.' and a.evaluate == 'rules'


def test_instruction_and_instruction_file_exclude_each_other(tmp_path, capsys):
    f = tmp_path / 'ask.txt'
    f.write_text('x')
    with pytest.raises(SystemExit):
        parse('--instruction', 'a', '--instruction-file', str(f))
    assert 'not allowed with' in capsys.readouterr().err


def test_instruction_file_is_read(tmp_path, monkeypatch):
    f = tmp_path / 'ask.txt'
    f.write_text('  What does this shop sell?\n')
    calls = []
    stub_run_one(monkeypatch, calls)
    code = episode.main(['shop-11', '--judge', 'off', '--instruction-file', str(f), '--out', str(tmp_path / 'run')])
    assert code == 0 and calls[0]['instruction'] == 'What does this shop sell?'


def test_missing_or_empty_instruction_file_stops_with_a_message(tmp_path):
    with pytest.raises(SystemExit) as e:
        episode.main(['shop-11', '--instruction-file', str(tmp_path / 'none.txt')])
    assert 'cannot read --instruction-file' in str(e.value)
    with pytest.raises(SystemExit) as e:
        episode.main(['shop-11', '--instruction', '  '])
    assert 'empty' in str(e.value)


def test_without_instruction_run_one_gets_no_instruction_argument(tmp_path, monkeypatch):
    calls = []
    stub_run_one(monkeypatch, calls)
    episode.main(['shop-11', '--judge', 'off', '--out', str(tmp_path / 'run')])
    assert 'instruction' not in calls[0]


def test_printed_line_ends_with_run_dir_and_note_names_the_rule_score(tmp_path, monkeypatch, capsys):
    calls = []
    stub_run_one(monkeypatch, calls)
    episode.main(['shop-11', '--judge', 'off', '--instruction', 'Just look.', '--out', str(tmp_path / 'run')])
    out = capsys.readouterr()
    line = json.loads(out.out.strip().splitlines()[-1])
    assert list(line)[-1] == 'run_dir' and line['run_dir'] == str(tmp_path / 'run')
    assert 'written for the task' in out.err and '--evaluate' in out.err


def test_evaluate_prints_the_evaluate_line_and_writes_the_file(tmp_path, monkeypatch, capsys):
    calls = []
    stub_run_one(monkeypatch, calls)
    seen = []

    def evaluate(run_dir, evaluator, write=True, **options):
        seen.append((run_dir, evaluator))
        return {'evaluator': 'rules', 'task': 'shop-11', 'outcome': 'ok'}
    from scamworld import evaluators
    monkeypatch.setattr(evaluators, 'evaluate', evaluate)
    episode.main(['shop-11', '--judge', 'off', '--instruction', 'Just look.', '--evaluate', 'rules', '--out', str(tmp_path / 'run')])
    out = capsys.readouterr()
    lines = [json.loads(x) for x in out.out.strip().splitlines()]
    assert seen == [(tmp_path / 'run', 'rules')]
    assert lines[1] == {'run': str(tmp_path / 'run'), 'evaluator': 'rules', 'task': 'shop-11', 'outcome': 'ok'}
    assert 'written for the task' not in out.err


def test_evaluate_a_real_run_folder_writes_evaluation_file(tmp_path, monkeypatch, capsys):
    stub_run_one(monkeypatch, [])
    episode.main(['shop-11', '--judge', 'off', '--evaluate', 'rules', '--out', str(tmp_path / 'run')])
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 2 and json.loads(lines[1])['run'] == str(tmp_path / 'run')
    assert (tmp_path / 'run' / 'evaluation-rules.json').is_file() or 'error' in json.loads(lines[1])


class StopAtReset(Exception):
    pass


def capture_task_kwargs(monkeypatch, tmp_path):
    """Replace the browser environment by one that records the task arguments and stops before any browser starts."""
    seen = {}

    class Env:
        def __init__(self, task, task_kwargs=None, **k):
            seen.update(task_kwargs)

        def reset(self, seed=None):
            raise StopAtReset()

        def close(self):
            pass
    import scamworld.env
    monkeypatch.setattr(scamworld.env, 'FormalBrowserEnv', Env)
    return seen


def run_setup(monkeypatch, tmp_path, case, **k):
    seen = capture_task_kwargs(monkeypatch, tmp_path)
    with pytest.raises(episode.EpisodeSetupError):
        episode.run_one(case, tmp_path / 'run', 3, judge=False, base_url='http://localhost:9/v1', model='m', **k)
    return seen


def test_override_reaches_the_task_of_a_released_id(monkeypatch, tmp_path):
    seen = run_setup(monkeypatch, tmp_path, 'shop-11', instruction='Tell me what it sells.')
    assert seen['goal'] == 'Tell me what it sells.' and 'task_path' not in seen


def test_override_reaches_the_task_of_a_task_folder(monkeypatch, tmp_path):
    from scamworld.paths import TASKS
    import shutil
    folder = tmp_path / 'mine'
    shutil.copytree(TASKS / 'shop-11', folder)
    seen = run_setup(monkeypatch, tmp_path, str(folder), instruction='Tell me what it sells.')
    assert seen['goal'] == 'Tell me what it sells.' and seen['case_dir'] == str(folder.resolve())


def test_hidden_task_path_still_refuses_an_override(monkeypatch, tmp_path):
    capture_task_kwargs(monkeypatch, tmp_path)
    with pytest.raises(episode.EpisodeSetupError, match='unreviewed instruction'):
        episode.run_one('shop-11', tmp_path / 'run', 3, judge=False, instruction='x', task_path=tmp_path)


@pytest.mark.parametrize('spec', ['bogus', 'nosuch_file.py:f', 'nosuch_module_xyz:f'])
def test_bad_evaluator_stops_before_any_episode(tmp_path, monkeypatch, spec):
    calls = []
    stub_run_one(monkeypatch, calls)
    with pytest.raises(SystemExit) as e:
        episode.main(['shop-11', '--judge', 'off', '--evaluate', spec, '--out', str(tmp_path / 'run')])
    assert 'cannot use --evaluate' in str(e.value) and spec in str(e.value) and '\n' not in str(e.value)
    assert calls == []


def test_evaluator_spelled_as_in_evaluate_is_read_as_evaluate(tmp_path, monkeypatch, capsys):
    calls = []
    stub_run_one(monkeypatch, calls)
    seen = []
    from scamworld import evaluators
    monkeypatch.setattr(evaluators, 'evaluate', lambda run_dir, evaluator, write=True, **o: seen.append(evaluator) or {'outcome': 'ok'})
    episode.main(['shop-11', '--judge', 'off', '--evaluator', 'rules', '--out', str(tmp_path / 'run')])
    assert seen == ['rules'] and calls[0]['evaluator'] == 'v1'
    assert len(capsys.readouterr().out.strip().splitlines()) == 2


def test_two_different_evaluators_are_refused(tmp_path, monkeypatch):
    calls = []
    stub_run_one(monkeypatch, calls)
    with pytest.raises(SystemExit, match='give one'):
        episode.main(['shop-11', '--judge', 'off', '--evaluate', 'rules', '--evaluator', 'scamworld', '--out', str(tmp_path / 'run')])
    assert calls == []
