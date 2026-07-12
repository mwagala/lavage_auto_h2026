#!/bin/sh
set -eu

exec celery -A backend.celery.celery_app:celery_app beat -l "${CELERY_LOG_LEVEL:-INFO}" --schedule "${CELERY_BEAT_SCHEDULE_PATH:-/tmp/celerybeat-schedule}"
