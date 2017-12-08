"""Static routes"""
# -*- coding: utf-8 -*-


from flask import json, jsonify
from flask import send_from_directory
from flask import render_template

from src.server import APP as app
from src.settings.metrics import SINGLE_METRICS

SINGLE_METRICS_VALUE_LOCATION = {
    'system-status': {
        'api': '/api/system_info',
        'value': '',
        'formatter': 'boolean',
        'formatter_opts': {
            'true': 'Up',
            'false': 'Down'
        }
    },
    'system-uptime': {
        'screen': {
            'size': 2,
        },
        'api': '/api/uptime',
        'value': '',
        'formatter': 'time',
        'formatter_opts': "d [days], h [hrs], m [mins], s [sec]"
    },
    'memory-total': {
        'screen': {
            'size': 2,
        },
        'api': '/api/memory',
        'value': 'virtual[0]',
        'formatter': 'bytes'
    },
    'memory-available': {
        'screen': {
            'size': 2,
        },
        'api': '/api/memory',
        'value': 'virtual[1]',
        'formatter': 'bytes'
    },
    'disk-available': {
        'screen': {
            'size': 2,
        },
        'api': '/api/partitions',
        'value': 'usage[0]',
        'formatter': 'bytes'
    },
    'disk-used': {
        'screen': {
            'size': 2,
        },
        'api': '/api/partitions',
        'value': 'usage[1]',
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
            ret_metric = {
                'title': "%s - %s" % (group_name, key)
            }
            ret_metric.update(value_metric)
            single_metrics.append(ret_metric)
    return render_template('index.html', single_metrics=single_metrics)

@app.route('/login')
def login():
    return render_template('login.html')
