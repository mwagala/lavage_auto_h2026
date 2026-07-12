#!/bin/sh
set -eu

exec celery -A backend.celery.celery_app:celery_app worker -l "${CELERY_LOG_LEVEL:-INFO}" --pool=solo
