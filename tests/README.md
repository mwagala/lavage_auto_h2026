# Test suite

Run unit tests with:

```powershell
python -m pytest
```

Most tests mock PostgreSQL, Redis and Celery-facing boundaries. Integration tests that need real services are marked with `@pytest.mark.integration` and skipped by default.

Integration tests are present but skipped by default. They cover PostgreSQL foundation tables, Redis ping, and the full reservation creation transaction with `Reservations`, `Factures`, `Cles_Idempotence`, `Evenements_Outbox`, `Journaux_Audit`, and the Outbox consumer. To run them, start the PostgreSQL and Redis services configured in `.env`, then run:

```powershell
$env:RUN_INTEGRATION_TESTS='1'
python -m pytest -m integration
```

Rate limiting tests are present in `tests/test_rate_limiting_security.py`; they cover login/register thresholds, generic responses, `Retry-After`, memory fallback for dev/test, reset after window expiration, and fail-closed behavior outside non-production.
