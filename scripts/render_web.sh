#!/bin/sh
set -eu

exec gunicorn -b "0.0.0.0:${PORT:-5000}" app:app
