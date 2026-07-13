from backend.Commun.validators import validate_password


def test_validate_password_rejects_tehisson_brand_passwords():
    for password in [
        "tehisson",
        "tehisson123",
        "tehissontehisson",
        "tehisson20262026",
        "tehisson-2026-2026",
    ]:
        normalized_password, error = validate_password(password)

        assert normalized_password is None
        assert error


def test_validate_password_marks_long_tehisson_variants_as_weak():
    assert validate_password("tehisson20262026") == (
        None,
        "Ce mot de passe est trop facile a deviner.",
    )


def test_validate_password_accepts_strong_non_brand_password():
    password = "Voiture!Securisee#2026"

    assert validate_password(password) == (password, None)
