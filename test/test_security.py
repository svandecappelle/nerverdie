# -*- coding: utf-8 -*-
"""HTTP hardening tests: security headers, API errors, proxy handling."""

from flask import Flask, jsonify, request

from server.settings.security import configure_app


def test_security_headers_on_api(client):
    response = client.get('/api/metrics')
    headers = response.headers
    assert "default-src 'self'" in headers['Content-Security-Policy']
    assert "frame-ancestors 'none'" in headers['Content-Security-Policy']
    assert headers['X-Content-Type-Options'] == 'nosniff'
    assert headers['X-Frame-Options'] == 'DENY'
    assert headers['Referrer-Policy'] == 'no-referrer'
    assert headers['Cache-Control'] == 'no-store'


def test_security_headers_on_static(client):
    response = client.get('/some/client/route')
    assert 'Content-Security-Policy' in response.headers


def test_hsts_only_when_https_enabled(client, monkeypatch):
    monkeypatch.delenv('NEVERDIE_COOKIE_SECURE', raising=False)
    assert 'Strict-Transport-Security' not in client.get('/api/metrics').headers
    monkeypatch.setenv('NEVERDIE_COOKIE_SECURE', '1')
    assert 'max-age=' in client.get('/api/metrics').headers['Strict-Transport-Security']


def test_unknown_api_url_is_json_404(logged_client):
    response = logged_client.get('/api/does-not-exist')
    assert response.status_code == 404
    assert response.get_json() == {'error': 'Not Found'}


def test_wrong_method_on_api_is_json(client):
    response = client.put('/api/auth/login', json={})
    assert response.status_code == 405
    assert response.is_json


def test_large_body_is_rejected(client):
    response = client.post('/api/auth/login', data='x' * (65 * 1024),
                           content_type='application/json')
    assert response.status_code == 413


def _app_reporting_client_address():
    app = Flask(__name__)
    configure_app(app)

    @app.route('/ip')
    def ip():
        return jsonify({'ip': request.remote_addr, 'scheme': request.scheme})

    return app


def test_forwarded_headers_ignored_without_trusted_proxy(monkeypatch):
    monkeypatch.delenv('NEVERDIE_TRUSTED_PROXIES', raising=False)
    app = _app_reporting_client_address()
    data = app.test_client().get('/ip', headers={'X-Forwarded-For': '203.0.113.9'},
                                 environ_base={'REMOTE_ADDR': '10.0.0.1'}).get_json()
    # A client cannot spoof its address to dodge the login throttle.
    assert data['ip'] == '10.0.0.1'


def test_forwarded_headers_used_behind_trusted_proxy(monkeypatch):
    monkeypatch.setenv('NEVERDIE_TRUSTED_PROXIES', '1')
    app = _app_reporting_client_address()
    data = app.test_client().get('/ip', headers={'X-Forwarded-For': '203.0.113.9',
                                                 'X-Forwarded-Proto': 'https'},
                                 environ_base={'REMOTE_ADDR': '10.0.0.1'}).get_json()
    assert data == {'ip': '203.0.113.9', 'scheme': 'https'}
