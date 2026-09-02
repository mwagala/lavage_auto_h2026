#!/bin/sh
set -eu

if python -m scripts.bootstrap; then
    echo "Bootstrap termine avant demarrage web."
else
    case "${RENDER_WEB_BOOTSTRAP_REQUIRED:-False}" in
        True|true|1|yes|on)
            echo "Bootstrap echoue et RENDER_WEB_BOOTSTRAP_REQUIRED=True; arret du service web." >&2
            exit 1
            ;;
        *)
            echo "Bootstrap non concluant; demarrage web en mode degrade." >&2
            ;;
    esac
fi

exec gunicorn -b "0.0.0.0:${PORT:-5000}" app:app
