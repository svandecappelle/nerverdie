#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Start the Flask API and the Angular dev server together.

    python scripts/serve.py            # API on :5000 + UI on :4200
    python scripts/serve.py --no-ui    # API only

The ports come from the Neverdie configuration (etc/neverdie.yml,
NEVERDIE_PORT, NEVERDIE_UI_PORT...). The UI (ng serve) proxies /api to the API. Ctrl+C stops
both, including their child processes (metrics collector, ng workers).
If one of them exits, the other is stopped too.
"""

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT = os.path.join(ROOT, 'client')
IS_WINDOWS = os.name == 'nt'
MIN_NODE_MAJOR = 22


def fail(message):
    sys.exit('serve: ' + message)


def python_command():
    """`uv run python` when uv is installed, else the Python of .venv (created with pip if needed)."""
    uv = shutil.which('uv')
    if uv:
        return [uv, 'run', 'python']
    try:
        import uv as _uv  # noqa: F401
        return [sys.executable, '-m', 'uv', 'run', 'python']
    except ImportError:
        pass
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from bootstrap import ensure_venv
    return [ensure_venv()]


def npm_command():
    npm = shutil.which('npm')
    if not npm:
        fail('npm not found. Install Node.js %d or later.' % MIN_NODE_MAJOR)
    return npm


def check_node():
    node = shutil.which('node')
    if not node:
        fail('node not found. Install Node.js %d or later.' % MIN_NODE_MAJOR)
    version = subprocess.run([node, '--version'], capture_output=True, text=True).stdout.strip()
    match = re.match(r'v(\d+)', version)
    if match and int(match.group(1)) < MIN_NODE_MAJOR:
        fail('Node.js %s is too old for the client, version %d or later is required.'
             % (version, MIN_NODE_MAJOR))


_JOB = None


def _kill_with_us(process):
    """Windows: put the child in a job object closed (and killed) when we exit.

    This covers the cases where this script is killed abruptly (for
    instance by make on Ctrl+C, or when the terminal is closed) and
    could not stop its children itself.
    """
    global _JOB
    if not IS_WINDOWS:
        return
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]

    if _JOB is None:
        class IoCounters(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in (
                'ReadOperationCount', 'WriteOperationCount', 'OtherOperationCount',
                'ReadTransferCount', 'WriteTransferCount', 'OtherTransferCount')]

        class BasicLimits(ctypes.Structure):
            _fields_ = [('PerProcessUserTimeLimit', ctypes.c_int64), ('PerJobUserTimeLimit', ctypes.c_int64),
                        ('LimitFlags', wintypes.DWORD), ('MinimumWorkingSetSize', ctypes.c_size_t),
                        ('MaximumWorkingSetSize', ctypes.c_size_t), ('ActiveProcessLimit', wintypes.DWORD),
                        ('Affinity', ctypes.c_size_t), ('PriorityClass', wintypes.DWORD),
                        ('SchedulingClass', wintypes.DWORD)]

        class ExtendedLimits(ctypes.Structure):
            _fields_ = [('BasicLimitInformation', BasicLimits), ('IoInfo', IoCounters),
                        ('ProcessMemoryLimit', ctypes.c_size_t), ('JobMemoryLimit', ctypes.c_size_t),
                        ('PeakProcessMemoryUsed', ctypes.c_size_t), ('PeakJobMemoryUsed', ctypes.c_size_t)]

        job = kernel32.CreateJobObjectW(None, None)
        limits = ExtendedLimits()
        limits.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not job or not kernel32.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            return  # best effort: Ctrl+C handling still stops the children
        _JOB = job  # kept open for our whole lifetime
    kernel32.AssignProcessToJobObject(_JOB, int(process._handle))


def read_settings(python):
    """Host, ports... resolved by server/settings/config.py, run with the app's Python (it needs PyYAML)."""
    result = subprocess.run(python + ['-m', 'server.settings.config'], cwd=ROOT, capture_output=True,
                            text=True, encoding='utf-8', errors='replace')
    if result.returncode != 0:
        fail((result.stderr or result.stdout).strip() or 'could not read the configuration')
    try:
        return json.loads(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        fail('unexpected configuration output: %s' % result.stdout.strip())


def local_url(host, port):
    """URL to reach a server listening on host:port from this machine (same as config.local_url)."""
    if host in ('0.0.0.0', '', '*'):  # noqa: S104 (we connect to it, not listen)
        host = '127.0.0.1'
    elif host == '::':
        host = '::1'
    if ':' in host:
        host = '[%s]' % host
    return 'http://%s:%d' % (host, port)


def start(name, command, cwd, env=None):
    """Start a process whose output is printed with a [name] prefix."""
    # Python children print UTF-8 (otherwise Windows uses the ANSI code page).
    options = {'env': dict(os.environ, PYTHONUTF8='1', PYTHONUNBUFFERED='1', **(env or {}))}
    if IS_WINDOWS:
        options['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        options['start_new_session'] = True
    process = subprocess.Popen(
        command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL, text=True, encoding='utf-8', errors='replace',
        bufsize=1, **options)
    _kill_with_us(process)

    def pump():
        for line in process.stdout:
            sys.stdout.write('[%s] %s' % (name, line))
            sys.stdout.flush()

    threading.Thread(target=pump, daemon=True).start()
    return process


def stop(process):
    """Stop a process and all of its children."""
    if process.poll() is not None:
        return
    if IS_WINDOWS:
        subprocess.run(['taskkill', '/F', '/T', '/PID', str(process.pid)], capture_output=True)
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    if wait_exit(process, timeout=10) is None:
        process.kill()


def wait_exit(process, timeout):
    """Exit code of `process`, or None if it is still running after `timeout` seconds.

    Popen.wait(timeout) is not used: on Windows, a Ctrl+C arriving right as
    its timeout expires makes CPython wait with a negative delay, which the
    system takes as (almost) infinite, so Ctrl+C hung serve.py. time.sleep()
    is interruptible and poll() does not block.
    """
    deadline = time.monotonic() + timeout
    while True:
        code = process.poll()
        if code is not None or time.monotonic() >= deadline:
            return code
        time.sleep(0.1)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Start the Neverdie API and UI')
    parser.add_argument('--no-ui', action='store_true', help='start the API only')
    args = parser.parse_args(argv)

    # Never crash the output threads on characters the console cannot show.
    sys.stdout.reconfigure(errors='replace')

    # Treat termination requests like Ctrl+C so that children are stopped.
    def interrupt(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupt)
    if IS_WINDOWS:
        signal.signal(signal.SIGBREAK, interrupt)

    python = python_command()
    processes = {}
    if not args.no_ui:
        check_node()
        npm = npm_command()
        if not os.path.isdir(os.path.join(CLIENT, 'node_modules')):
            print('[ui] installing client dependencies (npm ci)...')
            if subprocess.run([npm, 'ci'], cwd=CLIENT).returncode != 0:
                fail('npm ci failed')

    settings = read_settings(python)
    api_url = local_url(settings['host'], settings['port'])
    try:
        # start.py reads the same configuration (etc/neverdie.yml, NEVERDIE_*).
        processes['api'] = start('api', python + ['start.py'], ROOT)
        if not args.no_ui:
            processes['ui'] = start('ui', [npm, 'start', '--', '--port', str(settings['ui_port'])], CLIENT,
                                    env={'NEVERDIE_API_URL': api_url})
            print('API: %s  -  UI: http://localhost:%d  (Ctrl+C to stop)' % (api_url, settings['ui_port']))
        else:
            print('API: %s  (Ctrl+C to stop)' % api_url)

        # Wait until one of the processes exits (see wait_exit about Ctrl+C).
        while True:
            for name, process in processes.items():
                code = process.poll()
                if code is not None:
                    print('serve: %s exited with code %s, stopping.' % (name, code))
                    return code or 1
            time.sleep(0.2)
    except KeyboardInterrupt:
        print('\nserve: stopping...')
        return 0
    finally:
        for process in processes.values():
            stop(process)


if __name__ == '__main__':
    sys.exit(main())
