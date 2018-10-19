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
def cpu():
    """Get cpu metrics"""
    return jsonify(Metric().cpu())

@app.route('/api/cpu/load')
def cpu_load():
    """Get cpu metrics"""
    return jsonify(Metric().cpu_load())

@app.route('/api/memory')
def memory():
    """Get memory metrics"""
    return jsonify(Metric().memory())

@app.route('/api/memory/load')
def memory_loads():
    """Get cpu metrics"""
    return jsonify(Metric().memory_loads())

@app.route('/api/partitions')
def disk():
    """Get disk metrics"""
    return jsonify(Metric().disk())

@app.route('/api/system_info')
def system_info():
    """Get system info metrics"""
    return jsonify(Metric().system_info())

@app.route('/api/uptime')
def uptime():
    """Get uptime metrics"""
    return jsonify(Metric().uptime())

@app.route('/api/sensors')
def sensors():
    """Get sensors metrics"""
    return jsonify(Metric().sensors())

@app.route('/api/network')
def network():
    """Get sensors metrics"""
    return jsonify(Metric().network())