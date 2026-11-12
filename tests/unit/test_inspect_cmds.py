"""observe / signs / table (scamworld.inspect_cmds) and Episode.signs_seen, without a browser or a model."""
import argparse
import json
from pathlib import Path

import pytest

from scamworld import evaluators, inspect_cmds


def make_task(folder):
    (folder / 'scoring').mkdir(parents=True)
    (folder / 'task.json').write_text('{}')
    anchors = [{'id': 'a1', 'selector': '#x1', 'text_contains': 'fee'}, {'id': 'a2', 'selector': '#x2', 'text_contains': 'late'},
               {'id': 'a3', 'selector': '#x3', 'text_contains': 'never'}]
    (folder / 'scoring/evaluation.json').write_text(json.dumps({'anchors': anchors}))
    return folder


def make_run(root, name, task, model, obs, path, deceived=False):
    run = root / name
    run.mkdir(parents=True)
    (run / 'score.json').write_text(json.dumps({'case_id': task, 'model': model, 'obs_modes': obs, 'behavior_path': path, 'deceived': deceived}))
    return run


def test_signs_seen_in_anchor_order(tmp_path):
    folder = make_task(tmp_path / 'task-01')
    run = make_run(tmp_path, 'r-1', 'task-01', 'm', 'ax_tree', 'x')
    (run / 'score.json').write_text(json.dumps({'case_id': 'task-01', 'task_dir': str(folder)}))
    (run / 'trace.json').write_text(json.dumps({'steps': [
        {'observation': {'visible_text_evidence': {'a2': 'late fee'}}},
        {'observation': {}},
        {'observation': {'visible_text_evidence': {'a1': 'fee', 'other': 'x'}}}]}))
    assert evaluators.Episode(run).signs_seen() == ['a1', 'a2']


def test_signs_seen_without_evidence_keys(tmp_path):
    folder = make_task(tmp_path / 'task-01')
    run = make_run(tmp_path, 'r-1', 'task-01', 'm', 'ax_tree', 'x')
    (run / 'score.json').write_text(json.dumps({'case_id': 'task-01', 'task_dir': str(folder)}))
    (run / 'trace.json').write_text(json.dumps({'steps': [{'observation': None}, {}, {'observation': {'visible_text_evidence': None}}]}))
    assert evaluators.Episode(run).signs_seen() == []
    (run / 'trace.json').write_text('{}')
    assert evaluators.Episode(run).signs_seen() == []


def test_static_signs_name_the_view(tmp_path):
    folder = make_task(tmp_path / 'task-01')
    spec = {'flow': {'views': {'checkout': {'blocks': [{'id': 'x2'}]}}}}
    rows = inspect_cmds.static_signs(folder, spec)
    assert [r['id'] for r in rows] == ['a1', 'a2', 'a3']
    assert [r['view'] for r in rows] == [None, 'checkout', None]
    assert rows[0]['text_contains'] == 'fee'


def test_paths_to_walk_starts_with_clue_and_skips_prefixes():
    paths = {'commit': ['a', 'b', 'c'], 'clue': ['a', 'b'], 'confirm': ['a', 'b'], 'leave': ['z']}
    assert inspect_cmds._paths_to_walk(paths) == ['clue', 'commit', 'leave']


def test_table_counts_outcomes_per_cell(tmp_path):
    make_run(tmp_path, 'tag-a-1', 'task-01', 'ModelA', 'ax_tree', 'deceived_commit', deceived=True)
    make_run(tmp_path, 'tag-a-2', 'task-01', 'ModelA', 'ax_tree', 'recognized_and_stopped')
    make_run(tmp_path, 'tag-a-3', 'task-02', 'ModelA', 'screenshot', 'deceived_commit', deceived=True)
    make_run(tmp_path, 'tag-b-1', 'task-02', 'ModelB', 'screenshot', 'stopped_without_naming_problem')
    table = inspect_cmds.outcome_table([tmp_path])
    assert table['ModelA']['ax_tree'] == {'deceived': 1, 'detected': 1}
    assert table['ModelA']['screenshot'] == {'deceived': 1}
    assert table['ModelB']['screenshot'] == {'declined': 1}
    assert not list(tmp_path.glob('*/evaluation-*.json'))   # nothing written
    text = inspect_cmds.format_table(table, 'model', 'obs_modes', 'md')
    assert 'deceived 1 · detected 1' in text and text.splitlines()[1].startswith('| ---')
    assert json.loads(inspect_cmds.format_table(table, 'model', 'obs_modes', 'json'))['ModelA']['ax_tree'] == {'deceived': 1, 'detected': 1}
    assert inspect_cmds.format_table(table, 'model', 'obs_modes', 'csv').splitlines()[0] == 'model \\ obs_modes,ax_tree,screenshot'


def test_table_keys_task_and_tag(tmp_path):
    make_run(tmp_path, 'base-3', 'task-01', 'ModelA', 'ax_tree', 'deceived_commit', deceived=True)
    make_run(tmp_path, 'other-1', 'task-02', 'ModelA', 'ax_tree', 'recognized_and_stopped')
    table = inspect_cmds.outcome_table([tmp_path], rows='tag', cols='task')
    assert table == {'base': {'task-01': {'deceived': 1}}, 'other': {'task-02': {'detected': 1}}}


def test_table_custom_evaluator_and_failure(tmp_path):
    make_run(tmp_path, 'r-1', 'task-01', 'ModelA', 'ax_tree', 'x')
    make_run(tmp_path, 'r-2', 'task-01', 'ModelA', 'ax_tree', 'x')
    calls = []

    def evaluate(episode):
        calls.append(episode.run_dir.name)
        if episode.run_dir.name == 'r-2':
            raise ValueError('bad')
        return {'outcome': 'custom'}

    cell = inspect_cmds.outcome_table([tmp_path], evaluator=evaluate)['ModelA']['ax_tree']
    assert cell == {'custom': 1, 'error (ValueError)': 1}


def test_register_adds_three_commands_with_functions():
    parser = argparse.ArgumentParser()
    inspect_cmds.register(parser.add_subparsers(dest='command'))
    a = parser.parse_args(['observe', 'shop-11', '--obs', 'ax_tree', '--obs', 'screenshot,ax_controls', '--click', '1', '--click', '2',
                           '--grep', 'x', '--out', 'd', '--json'])
    assert (a.fn, a.obs, a.click, a.grep, a.out, a.json) == (inspect_cmds.cmd_observe, ['ax_tree', 'screenshot,ax_controls'], ['1', '2'], 'x', 'd', True)
    assert parser.parse_args(['signs', 't', '--json']).fn is inspect_cmds.cmd_signs
    a = parser.parse_args(['table', 'a', 'b', '--rows', 'tag', '--cols', 'task', '--evaluator', 'f.py:g', '--format', 'csv'])
    assert (a.fn, a.runs, a.rows, a.cols, a.evaluator, a.format) == (inspect_cmds.cmd_table, ['a', 'b'], 'tag', 'task', 'f.py:g', 'csv')
    assert parser.parse_args(['table', 'a']).format == 'md'


def test_describe_filters_lines_and_sizes(tmp_path):
    shot = tmp_path / 's.png'
    shot.write_bytes(b'12345')
    obs = {'url': 'http://x/', 'axtree_txt': 'one\nTwo restocking fee\nthree', 'controls': [{'bid': '1'}], 'screenshot': str(shot)}
    d = inspect_cmds._describe(obs, 'RESTOCKING', keep=False)
    fields = {f['key']: f for f in d['fields']}
    assert fields['axtree_txt']['lines'] == ['Two restocking fee'] and fields['axtree_txt']['chars'] == 28
    assert fields['controls']['lines'] == []
    assert fields['screenshot'] == {'key': 'screenshot', 'bytes': 5, 'path': None}
    assert inspect_cmds._describe(obs, None, keep=True)['fields'][-1]['path'] == str(shot)


def test_save_fields_writes_files(tmp_path):
    shot = tmp_path / 's.png'
    shot.write_bytes(b'png')
    obs = {'url': 'u', 'axtree_txt': 'tree', 'pruned_html': '<p>', 'controls': [{'bid': '1'}], 'screenshot': str(shot), 'goal': 'g'}
    inspect_cmds._save_fields(obs, tmp_path / 'out')
    names = sorted(p.name for p in (tmp_path / 'out').iterdir())
    assert names == ['axtree.txt', 'controls.json', 'meta.json', 'pruned.html', 'screenshot.png']
    assert json.loads((tmp_path / 'out/meta.json').read_text()) == {'url': 'u', 'goal': 'g'}


def test_table_evaluator_that_cannot_be_loaded_is_one_line(tmp_path, capsys):
    make_run(tmp_path, 'r-1', 'task-01', 'ModelA', 'ax_tree', 'x')
    for spec in ('nosuch.py:f', 'nosuch_module_xyz:f', 'bogus'):
        with pytest.raises(ValueError, match='cannot load evaluator'):
            inspect_cmds.outcome_table([tmp_path], evaluator=spec)
        a = argparse.Namespace(runs=[str(tmp_path)], rows='model', cols='obs_modes', evaluator=spec, format='md')
        with pytest.raises(SystemExit) as e:
            inspect_cmds.cmd_table(a)
        assert str(e.value).startswith('scamworld table: cannot load evaluator') and '\n' not in str(e.value)


def test_table_evaluator_returning_a_non_dict_gets_the_evaluate_message(tmp_path, capsys):
    make_run(tmp_path, 'r-1', 'task-01', 'ModelA', 'ax_tree', 'x')
    errors = []
    table = inspect_cmds.outcome_table([tmp_path], evaluator=lambda ep: 42, errors=errors)
    assert table['ModelA']['ax_tree'] == {'error (ValueError)': 1}
    assert 'must return a dict with an "outcome" key' in errors[0]
    a = argparse.Namespace(runs=[str(tmp_path)], rows='model', cols='obs_modes', evaluator=lambda ep: {'no': 1}, format='md')
    assert inspect_cmds.cmd_table(a) == 1   # every run failed
    assert 'evaluator failed on 1 of 1 runs' in capsys.readouterr().err


def test_table_keeps_exit_zero_when_only_some_runs_fail(tmp_path):
    make_run(tmp_path, 'r-1', 'task-01', 'ModelA', 'ax_tree', 'x')
    make_run(tmp_path, 'r-2', 'task-01', 'ModelA', 'ax_tree', 'x')
    ev = lambda ep: {'outcome': 'ok'} if ep.run_dir.name == 'r-1' else 1 / 0
    a = argparse.Namespace(runs=[str(tmp_path)], rows='model', cols='obs_modes', evaluator=ev, format='md')
    assert inspect_cmds.cmd_table(a) == 0


def test_print_observation_says_when_no_line_matches(capsys):
    obs = {'url': 'u', 'axtree_txt': 'one\ntwo'}
    r = {'obs': 'ax_tree', **inspect_cmds._describe(obs, 'zzz', keep=False)}
    inspect_cmds._print_observation(r, 'zzz')
    assert capsys.readouterr().out.count("no line matches 'zzz'") == 1
    r = {'obs': 'ax_tree', **inspect_cmds._describe(obs, 'two', keep=False)}
    inspect_cmds._print_observation(r, 'two')
    assert 'no line matches' not in capsys.readouterr().out


def test_open_env_lists_the_valid_observations(tmp_path):
    with pytest.raises(SystemExit, match='ax_controls, ax_tree, html'):
        inspect_cmds._open_env('shop-11', 'bogus', tmp_path)


def test_why_text_covers_every_rank():
    assert set(inspect_cmds.WHY_RANK) == set(inspect_cmds.WHY_TEXT)


def test_follow_path_names_the_paths_of_the_task():
    with pytest.raises(SystemExit, match='clue, commit'):
        inspect_cmds._follow_path(None, {'paths': {'commit': ['a'], 'clue': ['b']}}, 'nope')


def test_visible_now_reads_the_last_observation_record():
    record = {'url': 'http://x/p', 'visible_evidence': [{'evidence_id': 'e1'}], 'private_anchor_regions': [{'id': 'a1'}, {'id': 'e1'}]}
    env = type('E', (), {})()
    env.env = type('T', (), {'task': type('K', (), {'runtime': type('R', (), {'observations': [{'url': 'old'}, record]})()})()})()
    assert inspect_cmds._visible_now(env) == (['e1', 'a1'], 'http://x/p')
