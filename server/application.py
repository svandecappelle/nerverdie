#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import optparse

from flask import Flask, session, jsonify

from functools import wraps

from server.settings.security import configure_app

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
APP = Flask(__name__, template_folder=tmpl_dir)

configure_app(APP)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({'error': 'authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def flaskrun(app, default_host="127.0.0.1", default_port="5000"):
    """
    Takes a flask.Flask instance and runs it. Parses
    command-line flags to configure the app.

    The interactive debugger is deliberately not exposed: it allows
    arbitrary code execution for anyone who can reach the server.
    """
    from server.daemon import Daemon
    from server.storage.main import Datastore

    # Set up the command-line options
    parser = optparse.OptionParser()
    parser.add_option("-H", "--host",
                      help="Hostname of the Flask app " +
                           "[default %s]" % default_host,
                      default=default_host)
    parser.add_option("-P", "--port",
                      help="Port for the Flask app " +
                           "[default %s]" % default_port,
                      default=default_port)

    options, _ = parser.parse_args()

    Datastore()
    daemon = Daemon()
    daemon.start()

    app.run(
        debug=False,
        host=options.host,
        port=int(options.port)
    )
