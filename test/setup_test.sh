#!/usr/bin/env bash

set -e

THIS_PATH=$(dirname "$0")
BASE_PATH=$(dirname "$THIS_PATH")

cd $BASE_PATH

pip install --upgrade pip

# install prog AND tests requirements :
pip install -e .
pip install --upgrade -r test/requirements.txt