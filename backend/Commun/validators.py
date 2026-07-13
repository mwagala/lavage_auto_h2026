import re
import unicodedata


NAS_PATTERN = re.compile(r"^\d{9}$")
CODE_POSTAL_PATTERN = re.compile(r"^([A-Za-z]\d[A-Za-z])\s?(\d[A-Za-z]\d)$")
PASSWORD_MIN_LENGTH = 15
PASSWORD_MAX_LENGTH = 128
WEAK_PASSWORDS = {
    "password",
    "password123",
    "passwordpassword",
    "password123password",
    "motdepasse",
    "motdepasse123",
    "motdepassemotdepasse",
    "admin",
    "admin123",
    "qwerty",
    "qwertyqwerty",
    "azerty",
    "azertyazerty",
    "123456789",
    "1234567890",
    "lavageauto",
    "lavageauto123",
    "lavageautolavageauto",
    "tehisson",
    "tehisson123",
    "tehissontehisson",
}
WEAK_PASSWORD_ROOTS = {
    "password",
    "motdepasse",
    "admin",
    "qwerty",
    "azerty",
    "lavageauto",
    "tehisson",
}


def normalize_nas(value):
    if value is None:
        return None

    nas = str(value).strip()
    if not NAS_PATTERN.fullmatch(nas):
        return None

    return nas


def normalize_code_postal(value):
    if value is None:
        return None

    code_postal = str(value).strip().upper()
    match = CODE_POSTAL_PATTERN.fullmatch(code_postal)
    if not match:
        return None

    return f"{match.group(1)} {match.group(2)}"


def validate_password(value):
    if not isinstance(value, str):
        return None, "Le mot de passe est obligatoire."

    if not value.strip():
        return None, "Le mot de passe est obligatoire."

    normalized = re.sub(r"[\s_\-.'\"`]+", "", value).lower()
    if not normalized or normalized in WEAK_PASSWORDS:
        return None, "Ce mot de passe est trop facile a deviner."

    if any(re.fullmatch(rf"{root}\d*", normalized) for root in WEAK_PASSWORD_ROOTS):
        return None, "Ce mot de passe est trop facile a deviner."

    if len(value) < PASSWORD_MIN_LENGTH:
        return None, "Le mot de passe doit contenir au moins 15 caracteres."

    if len(value) > PASSWORD_MAX_LENGTH:
        return None, "Le mot de passe ne doit pas depasser 128 caracteres."

    if any(unicodedata.category(character)[0] == "C" for character in value):
        return None, "Le mot de passe ne doit pas contenir de caracteres de controle."

    return value, None
