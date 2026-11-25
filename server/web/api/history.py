# -*- coding: utf-8 -*-

from server.application import APP as app
from server.application import login_required
from server.console.history import History

from flask import jsonify



@app.route('/api/history/cpu/load')
@login_required
def cpu_load_history():
    """CPU load samples of the last hour, oldest first."""
    return jsonify(History().get(metric='cpu'))
