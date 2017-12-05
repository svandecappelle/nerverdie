#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json

from src.server import APP as app
from src.settings.metrics import AVAILABLE_METRICS
from src.console.metric import Metric

from flask import jsonify

metrics = Metric()

@app.route('/api/metrics')
def metrics():
    """List available metrics supported by server"""
    return jsonify(AVAILABLE_METRICS)

@app.route('/api/cpu')
def cpu():
    """Get cpu metrics"""
    return jsonify(Metric().cpu())

@app.route('/api/memory')
def memory():
    """Get memory metrics"""
    return jsonify(Metric().memory())

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

