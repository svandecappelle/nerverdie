"""Static routes"""
# -*- coding: utf-8 -*-

import os

from flask import abort, send_from_directory
from werkzeug.security import safe_join

from server.application import APP as app

static_file_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../client/dist')


@app.route('/', methods=['GET'])
def serve_dir_directory_index():
    return send_from_directory(static_file_dir, 'index.html')


@app.route('/<path:path>', methods=['GET'])
def serve_application(path):
    # Unknown API URLs are errors, not client-side routes.
    if path == 'api' or path.startswith('api/'):
        abort(404)
    # safe_join returns None for paths escaping static_file_dir, so the
    # existence check cannot be used to probe files elsewhere on disk.
    full_path = safe_join(static_file_dir, path)
    if full_path is None or not os.path.isfile(full_path):
        path = 'index.html'
    return send_from_directory(static_file_dir, path)
