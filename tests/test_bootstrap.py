from scripts import bootstrap


def test_bootstrap_applies_schema_when_public_catalog_is_missing(monkeypatch):
    calls = []

    monkeypatch.setenv("BOOTSTRAP_APPLY_SCHEMA", "true")
    monkeypatch.setattr(bootstrap, "_wait_for", lambda *args: None)
    monkeypatch.setattr(bootstrap, "_missing_schema_columns", lambda: [("services", "prix")])
    monkeypatch.setattr(bootstrap, "_apply_schema", lambda: calls.append("schema"))
    monkeypatch.setattr(bootstrap, "_seed_if_needed", lambda: calls.append("seed"))

    bootstrap.main()

    assert calls == ["schema", "seed"]


def test_bootstrap_fails_when_schema_is_missing_and_apply_is_disabled(monkeypatch):
    monkeypatch.setenv("BOOTSTRAP_APPLY_SCHEMA", "false")
    monkeypatch.setattr(bootstrap, "_wait_for", lambda *args: None)
    monkeypatch.setattr(bootstrap, "_missing_schema_columns", lambda: [("services", "prix")])

    try:
        bootstrap.main()
    except RuntimeError as exc:
        assert "BOOTSTRAP_APPLY_SCHEMA=false" in str(exc)
    else:
        raise AssertionError("bootstrap.main() should fail when schema apply is disabled")
