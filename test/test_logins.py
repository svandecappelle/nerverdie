# -*- coding: utf-8 -*-
"""Login journal, account lock policy and the security admin API."""

from datetime import datetime, timedelta

import pytest

import manage
import server.web.api.middleware as middleware
from conftest import PASSWORD
from server.models.base import db
from server.models.security import LoginEvent
from server.models.user import User
from server.storage import logins
from server.storage.main import Datastore


def login(client, username='alice', password=PASSWORD, address='127.0.0.1'):
    return client.post('/api/auth/login', json={'username': username, 'password': password},
                       environ_base={'REMOTE_ADDR': address})


def fail(client, times, username='alice'):
    """Failed logins, each from its own address so that the address throttle stays out of the way."""
    return [login(client, username, 'wrong', address='10.0.0.%d' % i).status_code for i in range(times)]


def outcomes():
    return [event.outcome for event in LoginEvent.select().order_by(LoginEvent.id)]


def alice():
    return User.get(User.username == 'alice')


def test_default_policy(client):
    assert logins.get_policy() == {'max_attempts': 5, 'lock_minutes': 15}


def test_account_is_locked_after_too_many_failures(client):
    assert fail(client, 4) == [401] * 4
    assert alice().failed_logins == 4

    response = login(client, password='wrong', address='10.0.1.1')
    assert response.status_code == 423
    until = datetime.fromisoformat(response.get_json()['locked_until'])
    assert until.utcoffset() is not None
    assert timedelta(minutes=14) < until - datetime.now().astimezone() <= timedelta(minutes=15)

    # Even the right password is refused while locked.
    response = login(client)
    assert response.status_code == 423
    assert client.get('/api/metrics').status_code == 401
    assert outcomes() == ['failure'] * 5 + ['locked']


def test_attempts_spread_over_addresses_still_lock(client):
    # The address throttle never triggers here: one attempt per address.
    assert fail(client, 5)[-1] == 423


def test_success_resets_the_failures(client):
    fail(client, 4)
    assert login(client).status_code == 200
    assert alice().failed_logins == 0
    assert fail(client, 4) == [401] * 4


def test_lock_expires(client):
    fail(client, 5)
    User.update(locked_until=datetime.now() - timedelta(seconds=1)).execute()
    assert login(client).status_code == 200
    assert alice().failed_logins == 0
    assert alice().locked_until is None


def test_expired_lock_gives_all_attempts_back(client):
    fail(client, 5)
    User.update(locked_until=datetime.now() - timedelta(seconds=1)).execute()
    assert fail(client, 4) == [401] * 4


def test_lock_until_unlocked(logged_client):
    logins.set_policy(3, 0)
    logged_client.post('/api/auth/logout')
    assert fail(logged_client, 3) == [401, 401, 423]
    response = login(logged_client)
    assert response.status_code == 423
    assert response.get_json()['locked_until'] is None
    assert alice().locked_until == logins.FOREVER

    logins.unlock('alice')
    assert login(logged_client).status_code == 200


def test_no_lock_when_disabled(client):
    logins.set_policy(None, 15)
    assert fail(client, 12) == [401] * 12
    assert login(client).status_code == 200


def test_unknown_accounts_are_journaled_but_never_locked(client):
    assert fail(client, 8, username='nobody') == [401] * 8
    assert set(outcomes()) == {'failure'}
    assert LoginEvent.get().username == 'nobody'


def test_throttled_attempts_are_journaled(client):
    for index in range(5):
        login(client, username='nobody%d' % index, password='wrong')
    assert login(client).status_code == 429
    assert outcomes()[-1] == 'throttled'


def test_odd_usernames_are_journaled_safely(client):
    client.post('/api/auth/login', json={'username': ['alice'], 'password': 'x'})
    client.post('/api/auth/login', json={'username': 'x' * 1000, 'password': 'x'})
    client.post('/api/auth/login', json=['not', 'an', 'object'])
    assert [len(event.username) for event in LoginEvent.select().order_by(LoginEvent.id)] == [0, 150, 0]


def test_old_events_are_forgotten(client):
    LoginEvent.create(time=datetime.now() - timedelta(days=91), username='old', address='x', outcome='success')
    LoginEvent.create(time=datetime.now() - timedelta(days=89), username='kept', address='x', outcome='success')
    login(client)
    assert [event.username for event in LoginEvent.select().order_by(LoginEvent.id)] == ['kept', 'alice']


def test_policy_values_are_checked(client):
    for attempts, minutes in ((0, 15), (101, 15), (5, -1), (5, logins.MAX_LOCK_MINUTES + 1)):
        with pytest.raises(ValueError):
            logins.set_policy(attempts, minutes)
    logins.set_policy(10, 0)
    assert logins.get_policy() == {'max_attempts': 10, 'lock_minutes': 0}


# --- admin API ----------------------------------------------------------------

def test_security_api_requires_login(client):
    assert client.get('/api/admin/security').status_code == 401
    assert client.put('/api/admin/security', json={'max_attempts': 3, 'lock_minutes': 1}).status_code == 401
    assert client.post('/api/admin/security/unlock', json={'username': 'alice'}).status_code == 401
    assert client.get('/api/admin/security/history').status_code == 401


def test_security_status(logged_client):
    User.create(username='bob', failed_logins=2, locked_until=datetime.now() + timedelta(minutes=5))
    User.create(username='carol', failed_logins=5, locked_until=logins.FOREVER)
    User.create(username='dave', failed_logins=0, locked_until=datetime.now() - timedelta(minutes=5))
    data = logged_client.get('/api/admin/security').get_json()

    assert data['policy'] == {'max_attempts': 5, 'lock_minutes': 15}
    assert data['throttle'] == {'max_failures': 5, 'window_seconds': 300}
    assert data['limits'] == {'min_attempts': 1, 'max_attempts': 100, 'max_lock_minutes': 10080}
    accounts = {account['username']: account for account in data['accounts']}
    assert accounts['alice'] == {'username': 'alice', 'failed_logins': 0, 'locked': False, 'locked_until': None}
    assert accounts['bob']['locked'] is True and accounts['bob']['locked_until']
    assert accounts['carol'] == {'username': 'carol', 'failed_logins': 5, 'locked': True, 'locked_until': None}
    assert accounts['dave']['locked'] is False
    assert data['last_day'] == {'success': 1, 'failure': 0, 'locked': 0, 'throttled': 0}
    assert data['recent'][0]['username'] == 'alice'
    assert data['recent'][0]['outcome'] == 'success'
    assert data['recent'][0]['address'] == '127.0.0.1'


def test_security_policy_update(logged_client):
    response = logged_client.put('/api/admin/security', json={'max_attempts': 3, 'lock_minutes': 60})
    assert response.status_code == 200
    assert response.get_json()['policy'] == {'max_attempts': 3, 'lock_minutes': 60}
    response = logged_client.put('/api/admin/security', json={'max_attempts': None, 'lock_minutes': 0})
    assert response.get_json()['policy'] == {'max_attempts': None, 'lock_minutes': 0}


@pytest.mark.parametrize('payload', [
    None,
    [],
    {'max_attempts': 3},
    {'lock_minutes': 3},
    {'max_attempts': True, 'lock_minutes': 3},
    {'max_attempts': 3, 'lock_minutes': None},
    {'max_attempts': '3', 'lock_minutes': 3},
    {'max_attempts': 2.5, 'lock_minutes': 3},
    {'max_attempts': 0, 'lock_minutes': 3},
    {'max_attempts': 3, 'lock_minutes': 100000},
])
def test_security_policy_rejects_bad_values(logged_client, payload):
    response = logged_client.put('/api/admin/security', json=payload)
    assert response.status_code == 400
    assert logins.get_policy() == {'max_attempts': 5, 'lock_minutes': 15}


def test_unlock_api(logged_client):
    User.create(username='bob', failed_logins=5, locked_until=logins.FOREVER)
    response = logged_client.post('/api/admin/security/unlock', json={'username': 'bob'})
    assert response.status_code == 200
    bob = next(account for account in response.get_json()['accounts'] if account['username'] == 'bob')
    assert bob == {'username': 'bob', 'failed_logins': 0, 'locked': False, 'locked_until': None}
    assert logged_client.post('/api/admin/security/unlock', json={'username': 'nobody'}).status_code == 404
    assert logged_client.post('/api/admin/security/unlock', json={}).status_code == 400


def test_security_history(logged_client):
    LoginEvent.delete().execute()
    now = datetime.now().replace(microsecond=0)
    for minutes, outcome in ((10, 'success'), (11, 'failure'), (12, 'failure'), (13, 'locked'),
                             (14, 'throttled'), (300, 'success'), (2000, 'success')):
        LoginEvent.create(time=now - timedelta(minutes=minutes), username='alice', address='x', outcome=outcome)
    end = now.timestamp() * 1000
    data = logged_client.get('/api/admin/security/history?from=%d&to=%d' % (end - 86400000, end)).get_json()

    assert data['step'] == 1800
    assert 48 <= len(data['samples']) <= 49
    dates = [sample['date'] for sample in data['samples']]
    assert dates == sorted(dates)
    total = {key: sum(sample[key] for sample in data['samples']) for key in ('success', 'failure', 'refused')}
    # The event 2000 minutes ago is outside the last day.
    assert total == {'success': 2, 'failure': 2, 'refused': 2}
    assert sum(1 for sample in data['samples'] if sample['success'] + sample['failure'] + sample['refused']) <= 3


def test_security_history_steps():
    end = datetime(2026, 11, 25, 12, 0, 0)
    assert logins.history(end - timedelta(hours=1), end)['step'] == 300
    assert logins.history(end - timedelta(days=7), end)['step'] == 6 * 3600
    assert logins.history(end - timedelta(days=30), end)['step'] == 86400


def test_security_history_rejects_bad_ranges(logged_client):
    assert logged_client.get('/api/admin/security/history?from=2000&to=1000').status_code == 400
    assert logged_client.get('/api/admin/security/history?from=x').status_code == 400
    year = 365 * 86400000
    assert logged_client.get('/api/admin/security/history?from=0&to=%d' % year).status_code == 400


# --- maintenance --------------------------------------------------------------

def test_old_user_table_gets_the_new_columns(client):
    db.execute_sql('ALTER TABLE "user" DROP COLUMN "locked_until"')
    db.execute_sql('ALTER TABLE "user" DROP COLUMN "failed_logins"')
    Datastore()
    columns = {column.name for column in db.get_columns('user')}
    assert {'failed_logins', 'locked_until'} <= columns
    assert alice().failed_logins == 0


def test_manage_unlock_user(client, capsys):
    fail(client, 5)
    manage.main(['unlock-user', 'alice'])
    assert 'unlocked' in capsys.readouterr().out
    assert login(client).status_code == 200


def test_manage_lists_locked_users(client, capsys):
    logins.set_policy(1, 0)
    fail(client, 1)
    manage.main(['list-users'])
    assert capsys.readouterr().out.strip() == 'alice (locked until unlocked)'


def test_throttle_fixture_is_reset(client):
    # The address throttle must not leak between tests.
    assert not middleware.LOGIN_THROTTLE.is_blocked('127.0.0.1')
