# -*- coding: utf-8 -*-

import json

from server.application import APP as app
from server.application import login_required
from server.settings.metrics import AVAILABLE_METRICS
from server.console.metric import Metric

from flask import jsonify

@app.route('/api/metrics')
@login_required
def metrics():
    """List available metrics supported by server"""
    return jsonify(AVAILABLE_METRICS)

@app.route('/api/cpu')
@login_required
def cpu():
    """Get cpu metrics"""
    return jsonify(Metric().cpu())

@app.route('/api/cpu/load')
@login_required
def cpu_load():
    """Get cpu metrics"""
    return jsonify(Metric().cpu_load())

@app.route('/api/memory')
@login_required
def memory():
    """Get memory metrics"""
    return jsonify(Metric().memory())

@app.route('/api/memory/load')
@login_required
def memory_loads():
    """Get cpu metrics"""
    return jsonify(Metric().memory_loads())

@app.route('/api/partitions')
@login_required
def disk():
    """Get disk metrics"""
    return jsonify(Metric().disk())

@app.route('/api/system_info')
@login_required
def system_info():
    """Get system info metrics"""
    return jsonify(Metric().system_info())

@app.route('/api/uptime')
@login_required
def uptime():
    """Get uptime metrics"""
    return jsonify(Metric().uptime())

@app.route('/api/sensors')
@login_required
def sensors():
    """Get sensors metrics"""
    return jsonify(Metric().sensors())

@app.route('/api/network')
@login_required
def network():
    """Get sensors metrics"""
    return jsonify(Metric().network())
