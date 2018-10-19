# -*- coding: utf-8 -*-
import json
from server.application import APP as app

from server.application import login_required
import werkzeug.exceptions as ex

from server.settings.metrics import AVAILABLE_METRICS
from server.console.metric import Metric

from flask import jsonify, flash, redirect, render_template, request, session, abort, g, url_for


class AuthenticationError(ex.HTTPException):
    code = 400
    description = '<p>Invalid credentials</p>'


@app.errorhandler(AuthenticationError)
def invalid_credentials(e):
    return e.description, e.code


@app.route('/api/auth', methods=['GET'])
@login_required
def get_user_logged():
    return jsonify({'token': 'token', 'duration': 600, 'user': { 'uid': 'uid'}})


@app.route('/api/auth/login', methods=['GET', 'POST'])
def autentication():
    if request.method == 'POST':
        if request.json['password'] == 'password' and request.json['username'] == 'admin':
            session['logged_in'] = True
            # session['user'] = 
        else:
            raise AuthenticationError
    return jsonify({'token': 'token', 'duration': 600, 'user': { 'uid': 'uid'}})
    '''user = User.verify_auth_token(username_or_token)
    if not user:
        # try to authenticate with username/password
        user = User.query.filter_by(username=username_or_token).first()
        if not user or not user.verify_password(password):
            return False
    g.user = user
    return True'''


@app.route('/api/auth/logout', methods=['GET', 'POST'])
def logout():
    session['logged_in'] = False
    return jsonify({ 'message': 'ok'})


@app.route('/api/resource')
def get_resource():
    return jsonify({'data': 'Hello, %s!' % g.user.username})
