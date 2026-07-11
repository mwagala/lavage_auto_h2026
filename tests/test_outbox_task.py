import pytest

celery = pytest.importorskip("celery")

from backend.celery.tasks import outbox as outbox_task


def test_process_pending_outbox_events_processes_claimed_batch(monkeypatch):
    events = [
        {"id": 1, "cle_idempotence": "k1"},
        {"id": 2, "cle_idempotence": "k2"},
    ]

    monkeypatch.setattr(outbox_task, "claim_pending_events", lambda limit=10: events)
    monkeypatch.setattr(
        outbox_task,
        "release_stale_processing_events",
        lambda **kwargs: [{"id": 99}],
    )
    monkeypatch.setattr(
        outbox_task,
        "_traiter_evenement_outbox",
        lambda event: {"event_id": event["id"], "statut": "traite"},
    )

    result = outbox_task.process_pending_outbox_events.run(limit=2)

    assert result == {
        "nombre_evenements_repris": 1,
        "nombre_evenements": 2,
        "resultats": [
            {"event_id": 1, "statut": "traite"},
            {"event_id": 2, "statut": "traite"},
        ],
    }


def test_traiter_evenement_outbox_fails_when_key_is_missing(monkeypatch):
    monkeypatch.setattr(
        outbox_task,
        "update_event_status_after_failure",
        lambda **kwargs: {
            **kwargs["event"],
            "statut": "en_attente",
            "tentatives": 1,
            "disponible_a": "later",
        },
    )

    result = outbox_task._traiter_evenement_outbox({"id": 5, "tentatives": 0})

    assert result["statut"] == "reprogramme"
    assert "cle_idempotence" in result["erreur"]
    assert result["tentatives"] == 1


def test_traiter_evenement_outbox_marks_already_processed_event_completed(monkeypatch):
    completed = []
    monkeypatch.setattr(
        outbox_task,
        "trouver_cle_idempotence",
        lambda cle: ({"id": 9, "statut": "traitee"}, None),
    )
    monkeypatch.setattr(
        outbox_task,
        "update_event_status_to_completed",
        lambda event_id: completed.append(event_id),
    )

    result = outbox_task._traiter_evenement_outbox(
        {"id": 6, "cle_idempotence": "reservation.created:6"}
    )

    assert result == {"event_id": 6, "statut": "deja_traite"}
    assert completed == [6]


def test_traiter_evenement_outbox_success_path(monkeypatch):
    calls = []
    monkeypatch.setattr(
        outbox_task,
        "trouver_cle_idempotence",
        lambda cle: ({"id": 10, "statut": "reservee"}, None),
    )
    monkeypatch.setattr(
        outbox_task,
        "marquer_cle_en_traitement",
        lambda cle_id: calls.append(("processing", cle_id)),
    )
    monkeypatch.setattr(
        outbox_task,
        "dispatch_evenement_outbox",
        lambda event: {"type_evenement": event["type_evenement"], "traite": True},
    )
    monkeypatch.setattr(
        outbox_task,
        "marquer_cle_traitee",
        lambda cle_id, response: calls.append(("completed_key", cle_id, response)),
    )
    monkeypatch.setattr(
        outbox_task,
        "update_event_status_to_completed",
        lambda event_id: calls.append(("completed_event", event_id)),
    )

    result = outbox_task._traiter_evenement_outbox(
        {
            "id": 7,
            "cle_idempotence": "reservation.created:7",
            "type_evenement": "reservation.created",
        }
    )

    assert result == {"event_id": 7, "statut": "traite"}
    assert calls[0] == ("processing", 10)
    assert calls[-1] == ("completed_event", 7)


def test_traiter_evenement_outbox_failure_path(monkeypatch):
    calls = []
    monkeypatch.setattr(
        outbox_task,
        "trouver_cle_idempotence",
        lambda cle: ({"id": 11, "statut": "reservee"}, None),
    )
    monkeypatch.setattr(
        outbox_task,
        "marquer_cle_en_traitement",
        lambda cle_id: calls.append(("processing", cle_id)),
    )
    monkeypatch.setattr(
        outbox_task,
        "dispatch_evenement_outbox",
        lambda event: (_ for _ in ()).throw(RuntimeError("dispatch failed")),
    )
    monkeypatch.setattr(
        outbox_task,
        "marquer_cle_echouee",
        lambda cle_id: calls.append(("failed_key", cle_id)),
    )
    monkeypatch.setattr(
        outbox_task,
        "update_event_status_after_failure",
        lambda **kwargs: calls.append(
            ("failed_event", kwargs["event"]["id"], kwargs["error_message"])
        )
        or {
            **kwargs["event"],
            "statut": "echoue",
            "tentatives": kwargs["event"].get("tentatives", 0) + 1,
            "disponible_a": None,
        },
    )

    result = outbox_task._traiter_evenement_outbox(
        {
            "id": 8,
            "cle_idempotence": "reservation.created:8",
            "type_evenement": "reservation.created",
            "tentatives": 4,
        }
    )

    assert result == {
        "event_id": 8,
        "statut": "echoue",
        "erreur": "dispatch failed",
        "tentatives": 5,
        "prochaine_tentative": None,
    }
    assert ("failed_key", 11) in calls
    assert ("failed_event", 8, "dispatch failed") in calls
