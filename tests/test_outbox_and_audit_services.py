import json

from backend.Commun.journaux import audit_service
from backend.Commun.outbox_events import outbox_dispatcher, outbox_service


class DummyConnection:
    def __init__(self):
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def test_creer_evenement_outbox_requires_all_fields():
    result, error = outbox_service.creer_evenement_outbox(
        "",
        "reservation",
        "1",
        {"id": 1},
        cle_idempotence="k",
    )

    assert result is None
    assert error == "Le type_evenement est obligatoire"


def test_creer_evenement_outbox_uses_external_connection_without_commit(monkeypatch):
    connection = DummyConnection()
    captured = {}

    def fake_insert_new_event(payload, connection=None):
        captured["payload"] = payload
        captured["connection"] = connection
        return 123

    monkeypatch.setattr(outbox_service, "insert_new_event", fake_insert_new_event)

    result, error = outbox_service.creer_evenement_outbox(
        "reservation.created",
        "reservation",
        "10",
        {"reservation_id": 10},
        cle_idempotence="reservation.created:10",
        connection=connection,
    )

    assert error is None
    assert result["id"] == 123
    assert result["statut"] == "en_attente"
    assert json.loads(result["donnees_json"]) == {"reservation_id": 10}
    assert captured["connection"] is connection
    assert connection.committed is False
    assert connection.rolled_back is False
    assert connection.closed is False


def test_creer_evenement_outbox_rolls_back_local_connection_on_invalid_json(monkeypatch):
    connection = DummyConnection()
    monkeypatch.setattr(outbox_service, "get_connection", lambda: connection)

    result, error = outbox_service.creer_evenement_outbox(
        "reservation.created",
        "reservation",
        "10",
        "{invalid-json",
        cle_idempotence="reservation.created:10",
    )

    assert result is None
    assert "Expecting property name" in error
    assert connection.rolled_back is True
    assert connection.closed is True


def test_dispatcher_handles_reservation_created():
    result = outbox_dispatcher.dispatch_evenement_outbox(
        {
            "id": 1,
            "type_evenement": "reservation.created",
            "type_ressource": "reservation",
            "ressource_id": "10",
        }
    )

    assert result == {"type_evenement": "reservation.created", "traite": True}


def test_dispatcher_accepts_unknown_event_temporarily():
    result = outbox_dispatcher.dispatch_evenement_outbox(
        {"id": 2, "type_evenement": "unknown.event"}
    )

    assert result == {"type_evenement": "unknown.event", "traite": True}


def test_enregistrer_journal_audit_validates_role_and_result():
    result, error = audit_service.enregistrer_journal_audit(
        "reservation.created",
        "reservation",
        role_acteur="intrus",
    )

    assert result is None
    assert error == "Le role_acteur est invalide"

    result, error = audit_service.enregistrer_journal_audit(
        "reservation.created",
        "reservation",
        resultat="partiel",
    )

    assert result is None
    assert error == "Le resultat est invalide"


def test_enregistrer_journal_audit_uses_external_connection_without_commit(monkeypatch):
    connection = DummyConnection()
    captured = {}

    def fake_insert_new_audit_log(payload, connection=None):
        captured["payload"] = payload
        captured["connection"] = connection
        return 77

    monkeypatch.setattr(audit_service, "insert_new_audit_log", fake_insert_new_audit_log)

    result, error = audit_service.enregistrer_journal_audit(
        action="reservation.created",
        type_ressource="reservation",
        ressource_id="10",
        resultat="succes",
        acteur_id=5,
        role_acteur="client",
        adresse_ip="127.0.0.1",
        correlation_id="corr-1",
        details={"safe": True},
        connection=connection,
    )

    assert error is None
    assert result["id"] == 77
    assert result["role_acteur"] == "client"
    assert json.loads(result["details_json"]) == {"safe": True}
    assert captured["connection"] is connection
    assert captured["payload"].correlation_id == "corr-1"
    assert connection.committed is False
    assert connection.rolled_back is False
    assert connection.closed is False

