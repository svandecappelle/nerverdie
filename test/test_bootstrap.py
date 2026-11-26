"""scripts/bootstrap.py and scripts/run.py: virtual environment without uv."""
import json
import os
import sys

import pytest

from scripts import bootstrap, run


def fake_venv(path, stamp=None):
    """An environment with a Python executable and, optionally, an install stamp."""
    python = bootstrap.venv_python(str(path))
    os.makedirs(os.path.dirname(python))
    open(python, 'w').close()
    (path / 'pyvenv.cfg').write_text('home = /usr/bin\n')
    if stamp is not None:
        (path / bootstrap.STAMP).write_text(json.dumps(stamp))
    return python


class Result:
    def __init__(self, returncode=0, stdout='', stderr=''):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


@pytest.fixture
def commands(monkeypatch):
    """Records the commands run instead of running them; pip is there unless the test says otherwise."""
    class Calls(list):
        pass

    calls = Calls()
    results = {}

    def fake_run(command, **kwargs):
        calls.append(command)
        return results.get(tuple(command[1:4]), Result())

    monkeypatch.setattr(bootstrap.subprocess, 'run', fake_run)
    monkeypatch.setattr(bootstrap, 'pip_available', lambda python: True)
    calls.results = results  # tests set {(arg1, arg2, arg3): Result} to make a command fail
    return calls


def pip_steps(calls):
    return [call[3:] for call in calls if call[1:3] == ['-m', 'pip']]


def test_missing_environment_is_not_up_to_date(tmp_path):
    assert not bootstrap.up_to_date(str(tmp_path / 'venv'), dev=False)


def test_up_to_date_follows_pyproject_and_dev_tools(tmp_path):
    venv = tmp_path / 'venv'
    fake_venv(venv, {'pyproject': bootstrap.pyproject_hash(), 'dev': False})
    assert bootstrap.up_to_date(str(venv), dev=False)
    # The dev tools are missing.
    assert not bootstrap.up_to_date(str(venv), dev=True)

    (venv / bootstrap.STAMP).write_text(json.dumps({'pyproject': bootstrap.pyproject_hash(), 'dev': True}))
    assert bootstrap.up_to_date(str(venv), dev=True)
    assert bootstrap.up_to_date(str(venv), dev=False)

    # pyproject.toml changed since the install.
    (venv / bootstrap.STAMP).write_text(json.dumps({'pyproject': 'old', 'dev': True}))
    assert not bootstrap.up_to_date(str(venv), dev=False)

    (venv / bootstrap.STAMP).write_text('{broken')
    assert not bootstrap.up_to_date(str(venv), dev=False)


def test_an_up_to_date_environment_installs_nothing(tmp_path, commands):
    venv = tmp_path / 'venv'
    python = fake_venv(venv, {'pyproject': bootstrap.pyproject_hash(), 'dev': False})
    assert bootstrap.ensure_venv(str(venv)) == python
    assert commands == []


def test_installs_the_project_and_writes_the_stamp(tmp_path, commands):
    venv = tmp_path / 'venv'
    python = fake_venv(venv)
    assert bootstrap.ensure_venv(str(venv), dev=True) == python

    assert pip_steps(commands) == [
        ['install', '--quiet', '--upgrade', 'pip'],
        ['install', '--quiet', '--editable', bootstrap.ROOT],
        ['install', '--quiet', '--group', 'dev'],
    ]
    assert all(call[0] == python for call in commands)
    assert bootstrap.read_stamp(str(venv)) == {'pyproject': bootstrap.pyproject_hash(), 'dev': True}


def test_an_update_keeps_the_dev_tools(tmp_path, commands):
    venv = tmp_path / 'venv'
    fake_venv(venv, {'pyproject': 'old', 'dev': True})
    bootstrap.ensure_venv(str(venv), dev=False)
    assert pip_steps(commands)[-1] == ['install', '--quiet', '--group', 'dev']
    assert bootstrap.read_stamp(str(venv))['dev'] is True


def test_adds_pip_to_an_environment_without_it(tmp_path, commands, monkeypatch):
    # For instance one made by `uv venv`: it is completed, never deleted.
    venv = tmp_path / 'venv'
    fake_venv(venv)
    monkeypatch.setattr(bootstrap, 'pip_available', lambda python: False)
    bootstrap.ensure_venv(str(venv))
    assert commands[0][1:] == ['-m', 'ensurepip', '--upgrade']
    assert venv.exists()


def test_a_failed_install_stops_with_its_step_and_output(tmp_path, commands):
    venv = tmp_path / 'venv'
    fake_venv(venv)
    commands.results[('-m', 'pip', 'install')] = Result(1, 'ERROR: No matching distribution found for pip\n')
    with pytest.raises(SystemExit, match='(?s)upgrading pip failed.*No matching distribution'):
        bootstrap.ensure_venv(str(venv))
    assert bootstrap.read_stamp(str(venv)) == {}


def test_creates_the_environment_with_this_python(tmp_path, commands, monkeypatch):
    venv = tmp_path / 'venv'

    def make_venv(command, **kwargs):
        commands.append(command)
        if command[1:3] == ['-m', 'venv']:
            fake_venv(venv)
        return Result()

    monkeypatch.setattr(bootstrap.subprocess, 'run', make_venv)
    bootstrap.ensure_venv(str(venv))
    assert commands[0] == [sys.executable, '-m', 'venv', str(venv)]
    assert len(pip_steps(commands)) == 2


def test_a_failed_creation_leaves_nothing_and_explains(tmp_path, commands, monkeypatch):
    venv = tmp_path / 'venv'
    error = 'The virtual environment was not created successfully because ensurepip is not available.'

    def broken_venv(command, **kwargs):
        os.makedirs(venv / 'bin')  # what python -m venv leaves on Debian without python3-venv
        return Result(1, stdout=error)

    monkeypatch.setattr(bootstrap.subprocess, 'run', broken_venv)
    with pytest.raises(SystemExit, match='(?s)ensurepip is not available.*apt install python3'):
        bootstrap.ensure_venv(str(venv))
    assert not venv.exists()


def test_venv_directory_from_the_environment(monkeypatch, tmp_path):
    monkeypatch.setenv('NEVERDIE_VENV', str(tmp_path / 'env'))
    assert bootstrap.default_venv() == str(tmp_path / 'env')
    monkeypatch.delenv('NEVERDIE_VENV')
    assert bootstrap.default_venv() == os.path.join(bootstrap.ROOT, '.venv')


def test_recreate_only_deletes_a_virtual_environment(tmp_path):
    other = tmp_path / 'data'
    other.mkdir()
    (other / 'keep.txt').write_text('x')
    with pytest.raises(SystemExit, match='not a virtual environment'):
        bootstrap.ensure_venv(str(other), recreate=True)
    assert (other / 'keep.txt').exists()

    venv = tmp_path / 'venv'
    fake_venv(venv)
    bootstrap.remove(str(venv))
    assert not venv.exists()


def test_recreate_explains_an_environment_in_use(tmp_path, monkeypatch):
    venv = tmp_path / 'venv'
    fake_venv(venv)

    def in_use(path):
        raise PermissionError(5, 'Access is denied', str(path))

    monkeypatch.setattr(bootstrap.shutil, 'rmtree', in_use)
    with pytest.raises(SystemExit, match='Stop Neverdie and anything else running from it'):
        bootstrap.remove(str(venv))


@pytest.mark.parametrize('argv, expected', [
    ([], ('start.py', [])),
    (['-P', '8080'], ('start.py', ['-P', '8080'])),
    (['manage.py', 'create-user', 'bob'], ('manage.py', ['create-user', 'bob'])),
])
def test_run_picks_the_script(argv, expected):
    assert run.command(argv) == expected


def test_run_refuses_an_unknown_script():
    with pytest.raises(SystemExit, match='not found'):
        run.main(['nothing.py'])
