"""`scamworld new-task <folder> --from <task>`: a copy of a released task as a task of your own (docs/custom-tasks.md)."""
import json

import pytest

from scamworld import cli

SOURCE, OTHER = 'gov-13', 'shop-11'   # a Turkish site (region TR) and an American one, both in the sample tasks
CHANGED = {'task.json', 'scoring/evaluation.json', 'source/provenance.json'}


def copy(tmp_path, source=SOURCE, name='my-gov-13', **kw):
    from scamworld.sitekit.scaffold import copy_task
    return copy_task(tmp_path / 'my-tasks' / name, source, **kw)


def files(folder):
    return sorted(p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file() and p.name not in ('.DS_Store', '.metadata_never_index'))


def test_copy_is_the_source_task_under_a_new_id(tmp_path):
    from scamworld.corpus import spec_at, spec_of, task_dir
    from scamworld.scoring.evaluation import load_contract
    folder, src = copy(tmp_path), task_dir(SOURCE)
    assert files(folder) == files(src) and 'records/a8-annotations.json' in files(folder)
    for rel in set(files(src)) - CHANGED:
        assert (folder / rel).read_bytes() == (src / rel).read_bytes(), rel
    contract = load_contract(folder)
    assert contract['task']['case_id'] == contract['evaluation']['case_id'] == 'my-gov-13'
    assert contract['task']['task_id'] == 'my-gov-13.' + json.loads((src / 'task.json').read_text())['task_id'].split('.', 1)[1]
    assert contract['task']['variant_of'] == SOURCE
    assert json.loads((folder / 'source/provenance.json').read_text())['case_id'] == 'my-gov-13'
    assert spec_at(folder)['prefix'] == spec_of(SOURCE)['prefix']   # the event names of the copied flow.js
    source_task = json.loads((src / 'task.json').read_text())
    copied_task = json.loads((folder / 'task.json').read_text())
    assert {k: v for k, v in copied_task.items() if k not in ('case_id', 'task_id', 'variant_of')} == \
        {k: v for k, v in source_task.items() if k not in ('case_id', 'task_id')}


def test_copy_keeps_the_user_the_copied_pages_show(tmp_path):
    from scamworld.agents.interface_v11 import fictional_context
    from scamworld.corpus import task_dir
    from scamworld.scoring.evaluation import load_contract
    from scamworld.scoring.evaluation.contracts import public_contract
    source = load_contract(task_dir(SOURCE))['task']
    copied = load_contract(copy(tmp_path))['task']
    assert fictional_context(copied) == fictional_context(source)
    assert fictional_context(source)['profile']['address']['country'] == 'TR'
    assert public_contract(copied) == public_contract(source)   # the agent's request: nothing about the copy
    renamed = {k: v for k, v in copied.items() if k != 'variant_of'}
    assert fictional_context(renamed)['profile']['address']['country'] == 'US'   # what a hand copy under a new id would get


def test_copies_are_own_tasks(tmp_path, monkeypatch):
    import scamworld.corpus as C
    copy(tmp_path)
    copy(tmp_path, OTHER, 'my-shop-11')
    rows = {t['task']: t for t in json.loads((tmp_path / 'my-tasks/index.json').read_text())['tasks']}
    assert sorted(rows) == ['my-gov-13', 'my-shop-11']
    assert rows['my-gov-13'] == {'task': 'my-gov-13', 'task_id': json.loads((tmp_path / 'my-tasks/my-gov-13/task.json').read_text())['task_id'],
                                 'scene': 'gov', 'benign': False, 'variant_of': SOURCE, 'contract': 2, 'in_corpus': False,
                                 'released': False}
    monkeypatch.setattr(C, 'TASKS', tmp_path / 'my-tasks')
    C.require_released(['my-gov-13', 'my-shop-11'])   # no release byte check for own tasks: nothing raised


def test_copy_of_a_copy_keeps_the_first_site(tmp_path):
    from scamworld.agents.interface_v11 import fictional_context
    from scamworld.scoring.evaluation import load_contract
    from scamworld.sitekit.scaffold import copy_task
    first = copy(tmp_path)
    second = copy_task(tmp_path / 'more' / 'my-gov-13-b', str(first))
    task = load_contract(second)['task']
    assert task['case_id'] == 'my-gov-13-b' and task['variant_of'] == SOURCE and task['task_id'].startswith('my-gov-13-b.')
    assert fictional_context(task) == fictional_context(load_contract(first)['task'])


def test_copy_refusals(tmp_path):
    from scamworld.sitekit.scaffold import copy_task
    first = copy(tmp_path)
    with pytest.raises(FileExistsError):
        copy(tmp_path)
    assert copy(tmp_path, force=True) == first
    with pytest.raises(ValueError):
        copy_task(tmp_path / 'Bad_ID', SOURCE)
    with pytest.raises(FileNotFoundError):
        copy_task(tmp_path / 'mine-01', 'no-such-task-99')
    with pytest.raises(ValueError):
        copy_task(first / 'inner-01', str(first))


def test_copy_by_id_with_another_task_folder_names_the_path(tmp_path, monkeypatch):
    import scamworld.corpus as C
    from scamworld.corpus import task_dir
    from scamworld.sitekit.scaffold import copy_task
    released = task_dir(OTHER)
    monkeypatch.setattr(C, 'TASKS', tmp_path / 'my-tasks')   # as with SCAMWORLD_TASKS=my-tasks
    with pytest.raises(FileNotFoundError) as missing:
        copy_task(tmp_path / 'my-tasks' / 'my-shop-11', OTHER)
    assert f'--from {released}' in str(missing.value)
    assert copy_task(tmp_path / 'my-tasks' / 'my-shop-11', str(released)).name == 'my-shop-11'


def test_cli_new_task_from(tmp_path, capsys):
    folder = tmp_path / 'my-tasks' / 'my-shop-11'
    with pytest.raises(SystemExit) as done:
        cli.main(['new-task', str(folder), '--from', OTHER])
    out = capsys.readouterr().out
    assert done.value.code == 0 and 'your request:' in out and 'verify' in out
    assert json.loads((folder / 'task.json').read_text())['variant_of'] == OTHER
    for extra in (['--benign'], ['--url', 'https://shop.example/']):
        with pytest.raises(SystemExit) as refused:
            cli.main(['new-task', str(tmp_path / 'other-01'), '--from', OTHER, *extra])
        assert '--from copies a task' in str(refused.value.code)
    with pytest.raises(SystemExit) as unknown:
        cli.main(['new-task', str(tmp_path / 'other-02'), '--from', 'no-such-task-99'])
    assert 'no task' in str(unknown.value.code) and not (tmp_path / 'other-02').exists()
