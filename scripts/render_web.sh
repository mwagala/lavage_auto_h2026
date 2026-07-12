#!/bin/sh
set -eu

python -m scripts.bootstrap

exec gunicorn -b "0.0.0.0:${PORT:-5000}" app:app
