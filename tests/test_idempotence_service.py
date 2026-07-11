import json

import pytest

from backend.Commun.idempotence import idempotence_service as service


def test_reserver_cle_idempotence_requires_key():
    result, error = service.reserver_cle_idempotence("", "reservation")

    assert result is None
    assert error == "La cle_idempotence est obligatoire"


def test_reserver_cle_idempotence_creates_new_key(monkeypatch):
    captured = {}

    def fake_book_new_key(payload, connection=None):
        captured["payload"] = payload
        captured["connection"] = connection
        return {
            "cle_creee": True,
            "cle": {"id": 10, "statut": "reservee"},
            "message": None,
        }

    monkeypatch.setattr(service, "book_new_key", fake_book_new_key)

    result, error = service.reserver_cle_idempotence(
        "reservation.created:1",
        "reservation",
        ressource_id="1",
        empreinte_requete="hash",
        duree_expiration_heures=2,
        connection="conn",
    )

    assert error is None
    assert result["decision"] == "nouvelle_action"
    assert result["cle_creee"] is True
    assert captured["connection"] == "conn"
    assert captured["payload"].cle_idempotence == "reservation.created:1"
    assert captured["payload"].expire_a is not None


@pytest.mark.parametrize(
    ("statut", "decision"),
    [
        ("reservee", "action_deja_vue"),
        ("en_traitement", "action_en_cours"),
        ("traitee", "action_deja_traitee"),
        ("echouee", "action_deja_vue"),
        ("inattendu", "action_deja_vue"),
    ],
)
def test_reserver_cle_idempotence_maps_existing_status(monkeypatch, statut, decision):
    monkeypatch.setattr(
        service,
        "book_new_key",
        lambda payload, connection=None: {
            "cle_creee": False,
            "cle": {"id": 11, "statut": statut},
            "message": "La cle existe deja",
        },
    )

    result, error = service.reserver_cle_idempotence("key", "reservation")

    assert error is None
    assert result["decision"] == decision
    assert result["message"] == "La cle existe deja"


def test_trouver_cle_idempotence_requires_key():
    result, error = service.trouver_cle_idempotence("")

    assert result is None
    assert error == "La cle_idempotence est obligatoire"


def test_marquer_cle_traitee_serializes_response(monkeypatch):
    captured = {}

    def fake_update_key_status_to_completed(cle_id, reponse_json, connection=None):
        captured["cle_id"] = cle_id
        captured["reponse_json"] = reponse_json
        captured["connection"] = connection

    monkeypatch.setattr(
        service,
        "update_key_status_to_completed",
        fake_update_key_status_to_completed,
    )

    result, error = service.marquer_cle_traitee(
        42,
        {"processed": True},
        connection="conn",
    )

    assert error is None
    assert result == {"id": 42, "statut": "traitee"}
    assert json.loads(captured["reponse_json"]) == {"processed": True}
    assert captured["connection"] == "conn"

