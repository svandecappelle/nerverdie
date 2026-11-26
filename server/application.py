#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import optparse

from flask import Flask, session, jsonify, request
from werkzeug.exceptions import HTTPException

from functools import wraps

from server.settings.security import configure_app

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
APP = Flask(__name__, template_folder=tmpl_dir)

configure_app(APP)


@APP.errorhandler(HTTPException)
def api_http_error(error):
    """Return JSON errors for the API instead of HTML pages."""
    if request.path.startswith('/api/'):
        return jsonify({'error': error.name}), error.code
    return error


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({'error': 'authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def server_settings(argv=None):
    """Host, port and threads: command line first, then server.settings.config."""
    from server.settings import config

    parser = optparse.OptionParser(
        epilog="Without an option, the value comes from NEVERDIE_HOST / NEVERDIE_PORT / "
               "NEVERDIE_THREADS, then from the configuration file (NEVERDIE_CONFIG or etc/neverdie.yml).")
    parser.add_option("-H", "--host", help="Interface to listen on [default %s]" % config.SETTINGS['host'][3])
    parser.add_option("-P", "--port", help="Port to listen on [default %s]" % config.SETTINGS['port'][3])
    parser.add_option("-t", "--threads", help="Number of request threads [default %s]" % config.SETTINGS['threads'][3])
    options, _ = parser.parse_args(argv)
    try:
        return config.load({'host': options.host, 'port': options.port, 'threads': options.threads})
    except config.ConfigError as error:
        parser.error(str(error))


def flaskrun(app):
    """
    Takes a flask.Flask instance and serves it with the waitress WSGI
    server, on the address and port of `server_settings()`.

    Flask's development server and its interactive debugger are
    deliberately not used: the debugger allows arbitrary code execution
    for anyone who can reach the server.
    """
    from waitress import serve

    from server.daemon import Daemon
    from server.storage.main import Datastore

    settings = server_settings()

    Datastore()
    daemon = Daemon()
    daemon.start()

    serve(
        app,
        host=settings['host'],
        port=settings['port'],
        threads=settings['threads'],
        ident='neverdie',
    )
