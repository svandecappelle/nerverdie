"""Static routes"""
# -*- coding: utf-8 -*-


from flask import json, jsonify
from flask import send_from_directory
from flask import render_template
from flask import send_file

import os

from server.application import APP as app
from server.settings.metrics import SINGLE_METRICS

static_file_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../client/dist')

@app.route('/', methods=['GET'])
def serve_dir_directory_index():
    return send_from_directory(static_file_dir, 'index.html')

@app.route('/<path:path>')
def serve_application(path, methods=['GET']):
    if not os.path.isfile(os.path.join(static_file_dir, path)):
        path = os.path.join(path, 'index.html')
    return send_from_directory(static_file_dir, path)