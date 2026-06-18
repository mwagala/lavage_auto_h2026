from celery import Celery
from bd.config import Config


celery_app = Celery('backend',
             broker=Config.CELERY_BROKER_URL,
             backend=Config.CELERY_RESULT_BACKEND,
             include=[
                 'backend.celery.tasks.health',
                 'backend.celery.tasks.outbox',
             ])

# Optional configuration, see the application user guide.
celery_app.conf.update(
    result_expires=3600,
    timezone="America/Toronto",
    task_always_eager=Config.CELERY_TASK_ALWAYS_EAGER,
    beat_schedule={
        "process-outbox-events": {
            # Beat reste un filet de securite: les reservations declenchent
            # deja cette tache apres commit, mais Beat rattrape les evenements
            # si Redis, Celery ou le worker etaient temporairement indisponibles.
            "task": "outbox.process_pending_events",
            "schedule": Config.OUTBOX_CONSUMER_INTERVAL_SECONDS,
            "args": (10,),
        },
    },
)

if __name__ == '__main__':
    # Quand ce fichier est lance directement avec python, on demarre un worker.
    # Sans cette liste d'arguments explicite, Celery peut interpreter le chemin
    # du fichier comme une commande CLI et afficher "No such command".
    celery_app.worker_main([
        "worker",
        "--loglevel=INFO",
        "--pool=solo",
    ])
