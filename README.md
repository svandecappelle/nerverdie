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

### With virtualenv
another way is to use virtualenv

* install virtualenv
* run ```virtualenv .```
* run ```source bin/activate```
* Run app:
  * In web service: ```python start.py```
  * In console management: ```python console.py```
