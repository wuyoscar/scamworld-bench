"""`new-task --from --instruction`. No model, no browser."""
import json

import pytest

from scamworld import cli
from scamworld.sitekit.scaffold import copy_task

TEXT = 'Do not buy anything. Tell me in one sentence what this site offers.'


def test_copy_with_instruction_replaces_the_request(tmp_path):
    folder = copy_task(tmp_path / 'my-gov-13', 'gov-13', instruction=f'  {TEXT}\n')
    task = json.loads((folder / 'task.json').read_text(encoding='utf-8'))
    assert task['instruction'] == TEXT and task['variant_of'] == 'gov-13'
    assert 'instruction_en' not in task and 'instruction_locale' not in task
    assert task['answer_fields']


def test_copy_without_instruction_keeps_the_request(tmp_path):
    folder = copy_task(tmp_path / 'my-gov-13', 'gov-13')
    assert 'instruction_en' in json.loads((folder / 'task.json').read_text(encoding='utf-8'))


def test_copy_with_empty_instruction_is_refused(tmp_path):
    with pytest.raises(ValueError):
        copy_task(tmp_path / 'my-gov-13', 'gov-13', instruction=' ')


def test_cli_instruction_file_and_exclusion(tmp_path, capsys):
    f = tmp_path / 'ask.txt'
    f.write_text(TEXT + '\n', encoding='utf-8')
    p = cli.build_parser()
    a = p.parse_args(['new-task', str(tmp_path / 'my-shop-11'), '--from', 'shop-11', '--instruction-file', str(f)])
    assert cli.cmd_new_task(a) is None
    assert json.loads((tmp_path / 'my-shop-11' / 'task.json').read_text(encoding='utf-8'))['instruction'] == TEXT
    with pytest.raises(SystemExit):
        p.parse_args(['new-task', 'x', '--from', 'shop-11', '--instruction', 'a', '--instruction-file', str(f)])


def test_cli_instruction_needs_from(tmp_path):
    a = cli.build_parser().parse_args(['new-task', str(tmp_path / 'x'), '--instruction', 'hi'])
    with pytest.raises(SystemExit, match='--from'):
        cli.cmd_new_task(a)
