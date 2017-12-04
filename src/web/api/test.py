#!/usr/bin/env python
# -*- coding: utf-8 -*-
from src.server import APP as app

@app.route('/')
def hello_world():
    """Say hello"""
    return 'Hello, World!'
