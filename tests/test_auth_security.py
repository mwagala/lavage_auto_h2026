from backend.Auth import service as auth_service


def test_login_inactive_account_uses_generic_public_error(monkeypatch):
    monkeypatch.setattr(
        auth_service,
        "_get_login_candidates",
        lambda email: [
            (
                "client",
                {
                    "id": 1,
                    "mot_passe_hash": "hash",
                    "est_actif": False,
                },
            )
        ],
    )
    monkeypatch.setattr(auth_service, "check_password_hash", lambda stored, value: True)
    monkeypatch.setattr(auth_service, "_enregistrer_audit_auth", lambda *args, **kwargs: None)

    result, error = auth_service.login_user(
        {"courriel": "client@example.com", "mot_de_passe": "secret"}
    )

    assert result is None
    assert error == "Identifiants invalides."

