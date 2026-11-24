# Nerverdie
Python monitor servers

## Development install
### The prefered way is to run with pipenv
if pipenv is not installed you should: 
```
python -m pip install pipenv --user
```

Then use pipenv to create virtual environment:
```
pipenv --python 3.5
pipenv install
pipenv shell
```

* Run app:
  * In web service: ```python start.py```
  * In console management: ```python console.py```

### Users and security
There are no default credentials. Create an account before logging in:
```
python manage.py create-user <username>
```
(`set-password`, `delete-user` and `list-users` are also available.)

Environment variables:
* `NEVERDIE_SECRET_KEY`: session signing key. If unset, a random key is generated once in `instance/secret_key` (git-ignored).
* `NEVERDIE_COOKIE_SECURE=1`: send the session cookie over HTTPS only. Set it as soon as the app is served behind TLS.
* `NEVERDIE_DB`: SQLite database path (default `db.sqlite`).

After 5 failed logins from one address within 5 minutes, further attempts are refused (HTTP 429).

### With virtualenv
another way is to use virtualenv

* install virtualenv
* run ```virtualenv .```
* run ```source bin/activate```
* Run app:
  * In web service: ```python start.py```
  * In console management: ```python console.py```
