from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Quand ce fichier est lance directement avec:
# python backend\celery\run_beat.py
# Python place backend/celery dans le chemin d'import. On ajoute donc la racine
# du projet pour que l'import backend.celery.celery_app fonctionne toujours.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.celery.celery_app import celery_app


def main():
    schedule_file = PROJECT_ROOT / "celerybeat-schedule"

    # Beat ne traite pas les taches lui-meme.
    # Son role est seulement d'envoyer les taches periodiques dans Redis.
    # Le worker Celery doit tourner dans un autre terminal pour les executer.
    celery_app.Beat(
        loglevel="INFO",
        schedule=str(schedule_file),
    ).run()


if __name__ == "__main__":
    main()
