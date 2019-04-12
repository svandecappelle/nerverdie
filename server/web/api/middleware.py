# -*- coding: utf-8 -*-
from server.application import APP as app

from server.application import login_required
import werkzeug.exceptions as ex

from flask import jsonify, request, session, g


class AuthenticationError(ex.HTTPException):
    code = 400
    description = '<p>Invalid credentials</p>'


@app.errorhandler(AuthenticationError)
def invalid_credentials(e):
    return e.description, e.code


@app.route('/api/auth', methods=['GET'])
@login_required
def get_user_logged():
    return jsonify({'token': 'token', 'duration': 600, 'user': {'uid': 'uid'}, 'connected': True})


@app.route('/api/auth/login', methods=['GET', 'POST'])
def autentication():
    # Yet in dev
    if request.method == 'POST':
        if request.json['password'] == 'password' and request.json['username'] == 'admin':
            session['logged_in'] = True
            # session['user'] =
        elif request.json['token'] == 'fl?8dnh432fmfokf1!sfz54fxgk84x:wx':
            session['logged_in'] = True
        else:
            raise AuthenticationError
    return jsonify({'token': 'token', 'duration': 600, 'user': {'uid': 'uid'}, 'connected': True})


@app.route('/api/auth/logout', methods=['GET', 'POST'])
def logout():
    session['logged_in'] = False
    return jsonify({'message': 'ok'})


@app.route('/api/resource')
def get_resource():
    return jsonify({'data': 'Hello, %s!' % g.user.username})
