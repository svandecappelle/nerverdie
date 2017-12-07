"""Static routes"""
# -*- coding: utf-8 -*-
from flask import send_from_directory
from flask import render_template

from src.server import APP as app

@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory('js', path)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')
