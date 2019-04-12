"""Static routes"""
# -*- coding: utf-8 -*-

from flask import send_from_directory

import os

from server.application import APP as app

static_file_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../client/dist')


@app.route('/', methods=['GET'])
def serve_dir_directory_index():
    return send_from_directory(static_file_dir, 'index.html')


@app.route('/<path:path>', methods=['GET'])
def serve_application(path):
    if not os.path.isfile(os.path.join(static_file_dir, path)):
        path = 'index.html'
        print(path)
    return send_from_directory(static_file_dir, path)
