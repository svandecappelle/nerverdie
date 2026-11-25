# -*- coding: utf-8 -*-

from datetime import datetime

from flask import abort, jsonify, request

from server.application import APP as app
from server.application import login_required
from server.console.history import DEFAULT_POINTS, METRICS, History


def _moment(name):
    """Optional query parameter given in epoch milliseconds, as a local datetime."""
    value = request.args.get(name)
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(float(value) / 1000)
    except (ValueError, OverflowError, OSError):
        abort(400, description='%s must be a time in epoch milliseconds' % name)


@app.route('/api/history/<metric>')
@login_required
def metric_history(metric):
    """Stored values of a metric over a time range.

    Query parameters: `from` and `to` in epoch milliseconds (default: the
    last hour) and `points`, the number of entries wanted (default 1200).
    """
    if metric not in METRICS:
        abort(404)
    try:
        points = int(request.args.get('points', DEFAULT_POINTS))
        return jsonify(History().get(metric, _moment('from'), _moment('to'), points))
    except ValueError as error:
        abort(400, description=str(error))


@app.route('/api/history/cpu/load')
@login_required
def cpu_load_history():
    """CPU load of the last hour (kept for older clients)."""
    return metric_history('cpu')
