#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run Neverdie from its virtual environment, creating or updating it first.

    python scripts/run.py                       # web service (start.py)
    python scripts/run.py -P 8080               # start.py options
    python scripts/run.py manage.py create-user bob
    python scripts/run.py console.py

The first run creates .venv and installs the dependencies (see
bootstrap.py); later runs start right away while pyproject.toml is unchanged.
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bootstrap import ROOT, ensure_venv  # noqa: E402

DEFAULT_SCRIPT = 'start.py'


def command(argv):
    """Script to run and its arguments: start.py unless the first argument is a .py file."""
    if argv and argv[0].endswith('.py'):
        return argv[0], argv[1:]
    return DEFAULT_SCRIPT, argv


def main(argv=None):
    script, args = command(sys.argv[1:] if argv is None else argv)
    path = os.path.join(ROOT, script)
    if not os.path.isfile(path):
        sys.exit('run: %s not found' % path)
    python = ensure_venv()
    full = [python, path] + args
    env = dict(os.environ, PYTHONUTF8='1')
    if os.name != 'nt':
        os.chdir(ROOT)
        os.execve(python, full, env)  # the app takes over this process (signals, exit code)
    # Windows has no real exec: wait for the app, which gets Ctrl+C from the console too.
    process = subprocess.Popen(full, cwd=ROOT, env=env)
    while True:
        try:
            return process.wait()
        except KeyboardInterrupt:
            continue


if __name__ == '__main__':
    sys.exit(main())
