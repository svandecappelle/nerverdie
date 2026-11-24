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


def flaskrun(app, default_host="127.0.0.1", default_port="5000", default_threads="8"):
    """
    Takes a flask.Flask instance and serves it with the waitress WSGI
    server. Parses command-line flags to configure it.

    Flask's development server and its interactive debugger are
    deliberately not used: the debugger allows arbitrary code execution
    for anyone who can reach the server.
    """
    from waitress import serve

    from server.daemon import Daemon
    from server.storage.main import Datastore

    # Set up the command-line options
    parser = optparse.OptionParser()
    parser.add_option("-H", "--host",
                      help="Interface to listen on " +
                           "[default %s]" % default_host,
                      default=default_host)
    parser.add_option("-P", "--port",
                      help="Port to listen on " +
                           "[default %s]" % default_port,
                      default=default_port)
    parser.add_option("-t", "--threads",
                      help="Number of request threads " +
                           "[default %s]" % default_threads,
                      default=default_threads)

    options, _ = parser.parse_args()

    Datastore()
    daemon = Daemon()
    daemon.start()

    serve(
        app,
        host=options.host,
        port=int(options.port),
        threads=int(options.threads),
        ident='neverdie',
    )
