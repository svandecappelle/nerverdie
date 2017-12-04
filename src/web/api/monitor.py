#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json

from src.server import APP as app
from src.settings.metrics import AVAILABLE_METRICS
from src.console.metric import Metric

METRIC = Metric()

@app.route('/api/metrics')
def metrics():
    """List available metrics supported by server"""
    return json.dumps(AVAILABLE_METRICS)

@app.route('/api/cpu')
def cpu():
    """Get cpu metrics"""
    return METRIC.cpu()
