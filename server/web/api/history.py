# -*- coding: utf-8 -*-

import ast
import json

from datetime import date

from server.application import APP as app
from server.application import login_required
from server.settings.metrics import AVAILABLE_METRICS
from server.console.metric import Metric

from flask import jsonify


from server.storage.main import Datastore



HISTORY_DEFAULT_RETURN = int(20 / 3)

@app.route('/api/history/cpu/load')
@login_required
def cpu_load_history():
    """Get cpu metrics history"""
    today = date.today()
    today_formatted = 'cpu_'+today.isoformat()
    
    storage = Datastore()
    history = []
    with storage.iterator(start = today_formatted) as it:
        for key, value in it:
            history.append(str(value))

    print('end')
    print(len(history))
    return jsonify(history[-HISTORY_DEFAULT_RETURN:])# cpu[-HISTORY_DEFAULT_RETURN:])
