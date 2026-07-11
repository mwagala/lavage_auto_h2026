from backend.Reservations import service as reservation_service


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


def _future_reservation():
    return {
        "id": 10,
        "client_id": 7,
        "prestataire_id": 3,
        "statut": "Assignee",
        "date": "2099-01-20",
        "heure_debut": "09:00:00",
    }


def test_update_reservation_writes_outbox_and_audit_in_transaction(monkeypatch):
    connection = DummyConnection()
    calls = []
    reservation = _future_reservation()

    monkeypatch.setattr(reservation_service, "get_connection", lambda: connection)
    monkeypatch.setattr(reservation_service, "get_reservation_by_id", lambda rid: reservation)
    monkeypatch.setattr(
        reservation_service,
        "_build_service_lines",
        lambda prestataire_id, services_payload: (
            [{"service_id": 5, "prix_applique": 20.0, "duree_prevue": 1.0, "quantite": 1}],
            3600,
            None,
        ),
    )
    monkeypatch.setattr(
        reservation_service,
        "count_active_client_reservations_same_day",
        lambda *args, **kwargs: 0,
    )
    monkeypatch.setattr(reservation_service, "has_prestataire_conflict", lambda *args: False)
    monkeypatch.setattr(
        reservation_service,
        "update_reservation_header",
        lambda **kwargs: calls.append(("update_header", kwargs["connection"])),
    )
    monkeypatch.setattr(
        reservation_service,
        "delete_reservation_services",
        lambda reservation_id, connection=None: calls.append(("delete_services", connection)),
    )
    monkeypatch.setattr(
        reservation_service,
        "insert_reservation_service",
        lambda **kwargs: calls.append(("insert_service", kwargs["connection"])),
    )
    monkeypatch.setattr(
        reservation_service,
        "_create_reservation_outbox_event",
        lambda **kwargs: calls.append((kwargs["event_type"], kwargs["connection"]))
        or ({"id": 1}, None),
    )
    monkeypatch.setattr(
        reservation_service,
        "_record_reservation_audit",
        lambda **kwargs: calls.append((kwargs["action"], kwargs["connection"]))
        or ({"id": 2}, None),
    )
    monkeypatch.setattr(
        reservation_service,
        "_declencher_consumer_outbox_apres_commit",
        lambda: calls.append(("trigger_outbox", None)),
    )
    monkeypatch.setattr(
        reservation_service,
        "_build_reservation_response",
        lambda rid: {"id": rid, "statut": "Assignee"},
    )

    result, error = reservation_service.update_reservation_any(
        actor_id=7,
        actor_role="client",
        reservation_id=10,
        payload={
            "prestataire_id": 3,
            "date": "2099-01-21",
            "heure_debut": "10:00",
            "services": [{"service_id": 5, "quantite": 1}],
        },
        audit_context={"correlation_id": "corr-update"},
    )

    assert error is None
    assert result == {"id": 10, "statut": "Assignee"}
    assert ("reservation.updated", connection) in calls
    assert ("reservation.updated", connection) in calls
    assert ("trigger_outbox", None) in calls
    assert connection.committed is True
    assert connection.rolled_back is False
    assert connection.closed is True


def test_update_reservation_rolls_back_when_required_audit_fails(monkeypatch):
    connection = DummyConnection()
    reservation = _future_reservation()

    monkeypatch.setattr(reservation_service, "get_connection", lambda: connection)
    monkeypatch.setattr(reservation_service, "get_reservation_by_id", lambda rid: reservation)
    monkeypatch.setattr(
        reservation_service,
        "_build_service_lines",
        lambda prestataire_id, services_payload: (
            [{"service_id": 5, "prix_applique": 20.0, "duree_prevue": 1.0, "quantite": 1}],
            3600,
            None,
        ),
    )
    monkeypatch.setattr(
        reservation_service,
        "count_active_client_reservations_same_day",
        lambda *args, **kwargs: 0,
    )
    monkeypatch.setattr(reservation_service, "has_prestataire_conflict", lambda *args: False)
    monkeypatch.setattr(reservation_service, "update_reservation_header", lambda **kwargs: None)
    monkeypatch.setattr(
        reservation_service,
        "delete_reservation_services",
        lambda reservation_id, connection=None: None,
    )
    monkeypatch.setattr(reservation_service, "insert_reservation_service", lambda **kwargs: None)
    monkeypatch.setattr(
        reservation_service,
        "_create_reservation_outbox_event",
        lambda **kwargs: ({"id": 1}, None),
    )
    monkeypatch.setattr(
        reservation_service,
        "_record_reservation_audit",
        lambda **kwargs: (None, "audit down"),
    )

    result, error = reservation_service.update_reservation_any(
        actor_id=7,
        actor_role="client",
        reservation_id=10,
        payload={
            "prestataire_id": 3,
            "date": "2099-01-21",
            "heure_debut": "10:00",
            "services": [{"service_id": 5, "quantite": 1}],
        },
        audit_context={"correlation_id": "corr-update"},
    )

    assert result is None
    assert error == reservation_service.AUDIT_RESERVATION_REQUIRED_ERROR
    assert connection.committed is False
    assert connection.rolled_back is True
    assert connection.closed is True


def test_status_change_writes_outbox_and_audit_in_transaction(monkeypatch):
    connection = DummyConnection()
    calls = []
    reservation = _future_reservation()

    monkeypatch.setattr(reservation_service, "get_connection", lambda: connection)
    monkeypatch.setattr(reservation_service, "get_reservation_by_id", lambda rid: reservation)
    monkeypatch.setattr(
        reservation_service,
        "update_reservation_status",
        lambda reservation_id, statut, connection=None: calls.append(("status", statut, connection)),
    )
    monkeypatch.setattr(
        reservation_service,
        "_create_reservation_outbox_event",
        lambda **kwargs: calls.append((kwargs["event_type"], kwargs["connection"]))
        or ({"id": 3}, None),
    )
    monkeypatch.setattr(
        reservation_service,
        "_record_reservation_audit",
        lambda **kwargs: calls.append((kwargs["action"], kwargs["connection"]))
        or ({"id": 4}, None),
    )
    monkeypatch.setattr(
        reservation_service,
        "_declencher_consumer_outbox_apres_commit",
        lambda: calls.append(("trigger_outbox", None)),
    )
    monkeypatch.setattr(
        reservation_service,
        "_build_reservation_response",
        lambda rid: {"id": rid, "statut": "En cours"},
    )

    result, error = reservation_service.update_reservation_status_prestataire(
        prestataire_id=3,
        reservation_id=10,
        payload={"statut": "En cours"},
        audit_context={"correlation_id": "corr-status"},
    )

    assert error is None
    assert result == {"id": 10, "statut": "En cours"}
    assert ("status", "En cours", connection) in calls
    assert ("reservation.status_changed", connection) in calls
    assert ("trigger_outbox", None) in calls
    assert connection.committed is True
    assert connection.rolled_back is False


def test_cancel_reservation_writes_outbox_and_audit_in_transaction(monkeypatch):
    connection = DummyConnection()
    calls = []
    reservation = _future_reservation()

    monkeypatch.setattr(reservation_service, "get_connection", lambda: connection)
    monkeypatch.setattr(reservation_service, "get_reservation_by_id", lambda rid: reservation)
    monkeypatch.setattr(
        reservation_service,
        "cancel_reservation",
        lambda reservation_id, connection=None: calls.append(("cancel", reservation_id, connection)),
    )
    monkeypatch.setattr(
        reservation_service,
        "_create_reservation_outbox_event",
        lambda **kwargs: calls.append((kwargs["event_type"], kwargs["connection"]))
        or ({"id": 5}, None),
    )
    monkeypatch.setattr(
        reservation_service,
        "_record_reservation_audit",
        lambda **kwargs: calls.append((kwargs["action"], kwargs["connection"]))
        or ({"id": 6}, None),
    )
    monkeypatch.setattr(
        reservation_service,
        "_declencher_consumer_outbox_apres_commit",
        lambda: calls.append(("trigger_outbox", None)),
    )
    monkeypatch.setattr(
        reservation_service,
        "_build_reservation_response",
        lambda rid: {"id": rid, "statut": "annulee"},
    )

    result, error = reservation_service.cancel_reservation_any(
        actor_id=7,
        actor_role="client",
        reservation_id=10,
        audit_context={"correlation_id": "corr-cancel"},
    )

    assert error is None
    assert result == {"id": 10, "statut": "annulee"}
    assert ("cancel", 10, connection) in calls
    assert ("reservation.cancelled", connection) in calls
    assert ("trigger_outbox", None) in calls
    assert connection.committed is True
    assert connection.rolled_back is False


def test_create_reservation_idempotency_replays_same_key_same_payload(monkeypatch):
    payload = {
        "prestataire_id": 3,
        "date": "2099-01-21",
        "heure_debut": "10:00",
        "services": [{"service_id": 5, "quantite": 1}],
    }
    fingerprint = reservation_service._build_payload_fingerprint(7, payload)

    monkeypatch.setattr(
        reservation_service,
        "trouver_cle_idempotence",
        lambda key: (
            {
                "cle_idempotence": key,
                "empreinte_requete": fingerprint,
                "statut": "traitee",
                "ressource_id": "44",
                "reponse_json": {"reservation_id": 44},
            },
            None,
        ),
    )
    monkeypatch.setattr(
        reservation_service,
        "_build_reservation_response",
        lambda rid: {"id": rid, "statut": "Assignee"},
    )

    result, error = reservation_service.create_reservation_client(
        client_id=7,
        payload=payload,
        idempotency_key="client-click-1",
    )

    assert error is None
    assert result == {"id": 44, "statut": "Assignee"}


def test_create_reservation_idempotency_rejects_same_key_different_payload(monkeypatch):
    payload = {
        "prestataire_id": 3,
        "date": "2099-01-21",
        "heure_debut": "10:00",
        "services": [{"service_id": 5, "quantite": 1}],
    }

    monkeypatch.setattr(
        reservation_service,
        "trouver_cle_idempotence",
        lambda key: (
            {
                "cle_idempotence": key,
                "empreinte_requete": "different-fingerprint",
                "statut": "traitee",
                "ressource_id": "44",
                "reponse_json": {"reservation_id": 44},
            },
            None,
        ),
    )

    result, error = reservation_service.create_reservation_client(
        client_id=7,
        payload=payload,
        idempotency_key="client-click-1",
    )

    assert result is None
    assert error == "La cle d'idempotence existe deja avec une requete differente"

