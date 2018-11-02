# -*- coding: utf-8 -*-

from server.application import APP as app
from server.application import login_required
from server.console.history import History

from flask import jsonify


HISTORY_DEFAULT_RETURN = int(200 / 3)

@app.route('/api/history/cpu/load')
@login_required
def cpu_load_history():
    """Get cpu metrics history"""
    return jsonify(History().get(metric='cpu', tail=HISTORY_DEFAULT_RETURN))
