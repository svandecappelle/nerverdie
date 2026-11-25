# -*- coding: utf-8 -*-
"""Administration API: database size limit."""

from flask import jsonify, request

from server.application import APP as app
from server.application import login_required
from server.storage import retention


def _bad_request(message):
    return jsonify(error=message), 400


@app.route('/api/admin/storage', methods=['GET'])
@login_required
def storage_status():
    """Database sizes, size limit and stored samples."""
    return jsonify(retention.storage_status())


@app.route('/api/admin/storage', methods=['PUT'])
@login_required
def storage_update():
    """Set the size limit in MB (`null` or 0: unlimited), then apply it at once."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or 'limit_mb' not in payload:
        return _bad_request('limit_mb is required')
    limit_mb = payload['limit_mb']
    # bool is an int subclass: reject it explicitly.
    if limit_mb is not None and (isinstance(limit_mb, bool) or not isinstance(limit_mb, (int, float))):
        return _bad_request('limit_mb must be a number or null')
    if limit_mb is not None and limit_mb != int(limit_mb):
        return _bad_request('limit_mb must be a whole number of MB')
    try:
        retention.set_limit_mb(int(limit_mb) if limit_mb else None)
    except ValueError as error:
        return _bad_request(str(error))
    deleted = retention.enforce_limit()
    return jsonify(dict(retention.storage_status(), deleted=deleted))


@app.route('/api/admin/storage/compact', methods=['POST'])
@login_required
def storage_compact():
    """Give the free pages of the database back to the file system."""
    retention.compact()
    return jsonify(retention.storage_status())
