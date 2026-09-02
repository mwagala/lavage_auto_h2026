#!/bin/sh
set -eu

run_bootstrap() {
    BOOTSTRAP_TIMEOUT_SECONDS="${RENDER_WEB_BOOTSTRAP_TIMEOUT_SECONDS:-15}" python -m scripts.bootstrap
}

case "${RENDER_WEB_BOOTSTRAP_REQUIRED:-False}" in
    True|true|1|yes|on)
        if run_bootstrap; then
            echo "Bootstrap termine avant demarrage web."
        else
            echo "Bootstrap echoue et RENDER_WEB_BOOTSTRAP_REQUIRED=True; arret du service web." >&2
            exit 1
        fi
        ;;
    *)
        (
            if run_bootstrap; then
                echo "Bootstrap termine en arriere-plan."
            else
                echo "Bootstrap non concluant; service web maintenu en mode degrade." >&2
            fi
        ) &
        echo "Demarrage web sans attendre la fin du bootstrap."
        ;;
esac

exec gunicorn -b "0.0.0.0:${PORT:-5000}" app:app
