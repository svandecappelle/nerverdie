# -*- coding: utf-8 -*-
"""Login journal and account lock policy.

Every login attempt is journaled (kept EVENT_RETENTION). After
`max_attempts` failed logins in a row, an account is locked for
`lock_minutes` (0: until an administrator unlocks it); a successful login
resets the count. While locked, logins are refused even with the right
password.

This comes on top of the per-address throttle of the login route, which
stops one address after a few failures but not attempts spread over many
addresses.
"""

import calendar
import logging
from datetime import datetime, timedelta

from peewee import fn

from server.console.history import _format, _from_epoch, json_date
from server.models.base import db
from server.models.security import LoginEvent
from server.models.setting import Setting
from server.models.user import User

LOGGER = logging.getLogger(__name__)

MAX_ATTEMPTS_SETTING = 'login_max_attempts'
LOCK_MINUTES_SETTING = 'login_lock_minutes'
DEFAULT_MAX_ATTEMPTS = 5
DEFAULT_LOCK_MINUTES = 15
MIN_ATTEMPTS, MAX_ATTEMPTS = 1, 100
MAX_LOCK_MINUTES = 7 * 24 * 60
# Lock without end: until an administrator unlocks the account.
FOREVER = datetime(9999, 12, 31)

OUTCOMES = ('success', 'failure', 'locked', 'throttled')
EVENT_RETENTION = timedelta(days=90)
MAX_USERNAME = 150

# Bucket sizes of the connection history (seconds), and how many buckets at most.
HISTORY_STEPS = (60, 300, 900, 1800, 3600, 3 * 3600, 6 * 3600, 12 * 3600, 86400, 7 * 86400)
DEFAULT_BUCKETS = 48
MAX_SPAN = EVENT_RETENTION


def _now():
    return datetime.now().replace(microsecond=0)


def clean_username(username):
    """The attempted username as journaled: a string of reasonable length."""
    return username[:MAX_USERNAME] if isinstance(username, str) else ''


# --- policy -----------------------------------------------------------------

def get_policy():
    """{'max_attempts': int or None (no lock), 'lock_minutes': int (0: until unlocked)}."""
    attempts = Setting.read(MAX_ATTEMPTS_SETTING, str(DEFAULT_MAX_ATTEMPTS))
    minutes = Setting.read(LOCK_MINUTES_SETTING, str(DEFAULT_LOCK_MINUTES))
    return {
        'max_attempts': int(attempts) if attempts else None,
        'lock_minutes': int(minutes) if minutes else 0,
    }


def set_policy(max_attempts, lock_minutes):
    """Set the lock policy. Raises ValueError when a value is out of range."""
    if max_attempts is not None and not MIN_ATTEMPTS <= max_attempts <= MAX_ATTEMPTS:
        raise ValueError('max_attempts must be between %d and %d' % (MIN_ATTEMPTS, MAX_ATTEMPTS))
    if not 0 <= lock_minutes <= MAX_LOCK_MINUTES:
        raise ValueError('lock_minutes must be between 0 and %d' % MAX_LOCK_MINUTES)
    with db.atomic():
        Setting.write(MAX_ATTEMPTS_SETTING, '' if max_attempts is None else str(max_attempts))
        Setting.write(LOCK_MINUTES_SETTING, str(lock_minutes))


# --- lock state ---------------------------------------------------------------

def _clear(user_id):
    User.update(failed_logins=0, locked_until=None).where(User.id == user_id).execute()


def locked_until(username):
    """End of the lock of an account (FOREVER: until unlocked), or None when it is not locked.

    An expired lock is cleared, so that the account gets all its attempts back.
    """
    user = User.get_or_none(User.username == clean_username(username))
    if user is None or user.locked_until is None:
        return None
    if user.locked_until > datetime.now():
        return user.locked_until
    _clear(user.id)
    return None


def register_failure(username):
    """Count a failed login. Returns the end of the lock when it locks the account, else None."""
    user = User.get_or_none(User.username == clean_username(username))
    if user is None:
        return None
    User.update(failed_logins=User.failed_logins + 1).where(User.id == user.id).execute()
    failures = User.get_by_id(user.id).failed_logins
    policy = get_policy()
    if policy['max_attempts'] is None or failures < policy['max_attempts']:
        return None
    minutes = policy['lock_minutes']
    until = _now() + timedelta(minutes=minutes) if minutes else FOREVER
    User.update(locked_until=until).where(User.id == user.id).execute()
    LOGGER.warning("Account %s locked after %d failed logins (%s)", user.username, failures,
                   'until unlocked' if until == FOREVER else 'until %s' % _format(until))
    return until


def register_success(user):
    if user.failed_logins or user.locked_until:
        _clear(user.id)


def unlock(username):
    """Unlock an account and reset its failed logins. Returns False for an unknown user."""
    user = User.get_or_none(User.username == clean_username(username))
    if user is None:
        return False
    _clear(user.id)
    LOGGER.info("Account %s unlocked", user.username)
    return True


def describe_lock(until):
    """JSON value of a lock end: a date, or None for a lock without end."""
    return None if until is None or until == FOREVER else json_date(until)


def accounts():
    """Every account with its failed logins and lock."""
    now = datetime.now()
    result = []
    for user in User.select().order_by(User.username):
        locked = user.locked_until is not None and user.locked_until > now
        result.append({
            'username': user.username,
            'failed_logins': user.failed_logins or 0,
            'locked': locked,
            'locked_until': describe_lock(user.locked_until) if locked else None,
        })
    return result


# --- journal ------------------------------------------------------------------

def record(username, address, outcome):
    """Journal a login attempt, and forget the attempts older than EVENT_RETENTION."""
    now = _now()
    with db.atomic():
        LoginEvent.create(time=now, username=clean_username(username),
                          address=(address or 'unknown')[:64], outcome=outcome)
        LoginEvent.delete().where(LoginEvent.time < now - EVENT_RETENTION).execute()


def recent(limit=20):
    """The last login attempts, newest first."""
    query = LoginEvent.select().order_by(LoginEvent.time.desc(), LoginEvent.id.desc()).limit(limit)
    return [{'time': json_date(event.time),'username': event.username,
             'address': event.address, 'outcome': event.outcome} for event in query]


def totals(since):
    """Number of attempts of each outcome since a moment."""
    counts = dict.fromkeys(OUTCOMES, 0)
    query = (LoginEvent.select(LoginEvent.outcome, fn.COUNT(LoginEvent.id).alias('count'))
             .where(LoginEvent.time >= since).group_by(LoginEvent.outcome))
    for row in query:
        counts[row.outcome] = row.count
    return counts


def _epoch(moment):
    """Like SQLite strftime('%s'): the local time read as UTC."""
    return calendar.timegm(moment.timetuple())


def history(start=None, end=None, buckets=DEFAULT_BUCKETS):
    """Login attempts counted by time bucket between `start` and `end` (local datetimes).

    Returns {'step': seconds, 'from': date, 'to': date, 'samples': [
        {'date': bucket start, 'success': n, 'failure': n, 'refused': n}, ...]}
    with every bucket of the range, empty ones included; `refused` counts
    the attempts refused without checking the password (account locked or
    address throttled).
    """
    end = end or datetime.now()
    start = start or end - timedelta(days=1)
    if start >= end:
        raise ValueError('the start of the range must be before its end')
    if end - start > MAX_SPAN:
        raise ValueError('the range cannot exceed %d days' % MAX_SPAN.days)
    buckets = min(max(int(buckets), 6), 500)
    span = (end - start).total_seconds()
    step = next((s for s in HISTORY_STEPS if span / s <= buckets), HISTORY_STEPS[-1])

    first = _epoch(start) // step * step
    samples = {}
    moment = first
    while moment <= _epoch(end):
        samples[moment] = {'date': json_date(_from_epoch(moment)),'success': 0, 'failure': 0, 'refused': 0}
        moment += step

    # Only internal constants are formatted in; the range is a parameter.
    query = (  # noqa: S608
        'SELECT (CAST(strftime(\'%%s\', "time") AS INTEGER) / %(step)d) * %(step)d AS bucket, '
        '"outcome", COUNT(*) FROM "%(table)s" WHERE "time" >= ? AND "time" <= ? '
        'GROUP BY bucket, "outcome"'
    ) % {'step': step, 'table': LoginEvent._meta.table_name}
    for bucket, outcome, count in db.execute_sql(query, [_format(start), _format(end)]):
        sample = samples.get(bucket)
        if sample is not None:
            key = outcome if outcome in ('success', 'failure') else 'refused'
            sample[key] += count
    return {'step': step, 'from': json_date(start), 'to': json_date(end), 'samples': list(samples.values())}
