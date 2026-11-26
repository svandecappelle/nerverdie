#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Create or update the Neverdie virtual environment, with pip only (no uv).

    python scripts/bootstrap.py            # .venv with the app dependencies
    python scripts/bootstrap.py --dev      # plus the dev tools (pytest, ruff, pip-audit)
    python scripts/bootstrap.py --recreate # delete .venv and build it again

The environment is created with the Python running this script (3.10 or
later), then the project is installed in editable mode (`pip install -e .`).
The install is skipped while pyproject.toml is unchanged, so running it
again is fast. NEVERDIE_VENV sets another environment directory.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYPROJECT = os.path.join(ROOT, 'pyproject.toml')
MIN_PYTHON = (3, 10)
# Written in the environment once the dependencies are installed.
STAMP = 'neverdie-install.json'


def fail(message):
    sys.exit('bootstrap: ' + message)


def default_venv():
    return os.path.abspath(os.environ.get('NEVERDIE_VENV') or os.path.join(ROOT, '.venv'))


def venv_python(venv):
    if os.name == 'nt':
        return os.path.join(venv, 'Scripts', 'python.exe')
    return os.path.join(venv, 'bin', 'python')


def pyproject_hash():
    with open(PYPROJECT, 'rb') as file:
        return hashlib.sha256(file.read()).hexdigest()


def read_stamp(venv):
    try:
        with open(os.path.join(venv, STAMP), encoding='utf-8') as file:
            return json.load(file)
    except (OSError, ValueError):
        return {}


def up_to_date(venv, dev):
    """Whether the environment already has the dependencies of this pyproject.toml."""
    stamp = read_stamp(venv)
    return (os.path.isfile(venv_python(venv))
            and stamp.get('pyproject') == pyproject_hash()
            and (stamp.get('dev') or not dev))


def pip_available(python):
    return os.path.isfile(python) and subprocess.run(
        [python, '-m', 'pip', '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def run(command, step, hint=''):
    """Runs a pip step; its output (build warnings...) is shown only when it fails."""
    print('bootstrap: %s...' % step, flush=True)
    result = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding='utf-8', errors='replace')
    if result.returncode != 0:
        fail('%s failed (command: %s)\n%s%s' % (step, ' '.join(command), (result.stdout or '').strip(),
                                              '\n' + hint if hint else ''))


def create(venv):
    if sys.version_info < MIN_PYTHON:
        fail('Python %d.%d or later is required, this is %s. Run this script with a newer Python.'
             % (MIN_PYTHON + (sys.version.split()[0],)))
    print('bootstrap: creating the virtual environment in %s...' % venv, flush=True)
    existed = os.path.exists(venv)
    result = subprocess.run([sys.executable, '-m', 'venv', venv], capture_output=True, text=True)
    if result.returncode != 0 or not os.path.isfile(venv_python(venv)):
        # Do not leave a half-built environment that the next run would take as ready.
        if not existed:
            shutil.rmtree(venv, ignore_errors=True)
        output = (result.stderr or result.stdout).strip()
        hint = ''
        if 'ensurepip' in output and 'apt install' not in output:
            hint = ('\nOn Debian or Ubuntu, install the venv module first: sudo apt install python%d.%d-venv'
                    % sys.version_info[:2])
        fail('could not create the virtual environment:\n%s%s' % (output, hint))


def remove(venv):
    # Only delete a directory that is a virtual environment.
    if not os.path.isfile(os.path.join(venv, 'pyvenv.cfg')):
        fail('%s is not a virtual environment, not deleting it.' % venv)
    print('bootstrap: deleting %s...' % venv, flush=True)
    try:
        shutil.rmtree(venv)
    except OSError as error:
        fail('could not delete %s (%s). Stop Neverdie and anything else running from it, then retry.'
             % (venv, error))


def ensure_venv(venv=None, dev=False, recreate=False):
    """Creates or updates the environment; returns its Python executable."""
    venv = venv or default_venv()
    if recreate and os.path.exists(venv):
        remove(venv)
    if up_to_date(venv, dev):
        return venv_python(venv)
    python = venv_python(venv)
    if not os.path.isfile(python):
        create(venv)
    else:
        # An environment with the dev tools keeps them up to date.
        dev = dev or bool(read_stamp(venv).get('dev'))
    if not pip_available(python):
        # For instance an environment made by `uv venv`, which has no pip.
        run([python, '-m', 'ensurepip', '--upgrade'], 'adding pip to the environment',
            hint='Run again with --recreate to build a new environment.')
    # pip 25.1 or later reads the dependency groups (--group).
    run([python, '-m', 'pip', 'install', '--quiet', '--upgrade', 'pip'], 'upgrading pip')
    run([python, '-m', 'pip', 'install', '--quiet', '--editable', ROOT], 'installing the dependencies')
    if dev:
        run([python, '-m', 'pip', 'install', '--quiet', '--group', 'dev'], 'installing the dev tools')
    with open(os.path.join(venv, STAMP), 'w', encoding='utf-8') as file:
        json.dump({'pyproject': pyproject_hash(), 'dev': dev}, file)
    print('bootstrap: environment ready (%s).' % venv, flush=True)
    return python


def main(argv=None):
    parser = argparse.ArgumentParser(description='Create or update the Neverdie virtual environment')
    parser.add_argument('--dev', action='store_true', help='also install the dev tools (pytest, ruff, pip-audit)')
    parser.add_argument('--recreate', action='store_true', help='delete the environment and build it again')
    parser.add_argument('--venv', help='environment directory (default: $NEVERDIE_VENV or .venv)')
    args = parser.parse_args(argv)
    python = ensure_venv(args.venv, dev=args.dev, recreate=args.recreate)
    print('Python of the environment: %s' % python)
    return 0


if __name__ == '__main__':
    sys.exit(main())
