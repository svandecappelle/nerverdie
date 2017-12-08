"""Static routes"""
# -*- coding: utf-8 -*-
from flask import send_from_directory
from flask import render_template

from src.server import APP as app
from src.settings.metrics import SINGLE_METRICS

SINGLE_METRICS_VALUE_LOCATION = {
    'system-status': {
        'api': '',
        'value': ''
    },
    'system-uptime': {
        'api': '/api/uptime',
        'value': '',
        'formatter': 'time'
    },
    'memory-available': {
        'api': '/api/memory',
        'value': 'virtual[0]',
        'formatter': 'bytes'
    },
    'memory-used': {
        'api': '/api/memory',
        'value': 'virtual[1]',
        'formatter': 'bytes'
    },
    'disk-available': {
        'api': '',
        'value': '',
        'formatter': 'bytes'
    },
    'disk-used': {
        'api': '',
        'value': '',
        'formatter': 'bytes'
    },
    'proc-cores': {
        'api': '/api/system_info',
        'value': 'nb_cpus'
    }
}

@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory('js', path)

@app.route('/')
def index():
    single_metrics = []
    for group_name in SINGLE_METRICS:
        for key in SINGLE_METRICS.get(group_name):
            value_metric = SINGLE_METRICS_VALUE_LOCATION.get("%s-%s" % (group_name, key))
            single_metrics.append({
                'title': "%s - %s" % (group_name, key),
                'api': value_metric.get('api'),
                'value': value_metric.get('value'),
                'formatter': value_metric.get('formatter')
            })
    return render_template('index.html', single_metrics=single_metrics)

@app.route('/login')
def login():
    return render_template('login.html')
