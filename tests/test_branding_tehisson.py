import re
from pathlib import Path

import pytest

from backend.Health import routes as health_routes


PUBLIC_ROUTES = [
    "/",
    "/services-page",
    "/equipe",
    "/connexion",
    "/inscription",
    "/prestataires/1/profil",
]

CONNECTED_ROUTES = [
    "/clients/dashboard",
    "/client/profil",
    "/client/reservations/new",
    "/client/reservations/123/edit",
    "/client/reservations/123/commentaire/edit",
    "/prestataires/dashboard",
    "/prestataires/profil",
]

OFFICIAL_COLORS = {
    "#b3fdd1",
    "#9cffb6",
    "#111111",
    "#e5feef",
    "#81fcb3",
    "#cfffdc",
}


def _html(response):
    return response.get_data(as_text=True)


def _assert_lavageauto_only_in_weak_password_context(html):
    normalized = html.lower()
    for match in re.finditer("lavageauto", normalized):
        context = normalized[max(0, match.start() - 500): match.end() + 500]
        assert "weakpassword" in context


def _contrast_ratio(hex_a, hex_b):
    def channel(value):
        value = int(value, 16) / 255
        if value <= 0.03928:
            return value / 12.92
        return ((value + 0.055) / 1.055) ** 2.4

    def luminance(hex_color):
        color = hex_color.lstrip("#")
        red = channel(color[0:2])
        green = channel(color[2:4])
        blue = channel(color[4:6])
        return 0.2126 * red + 0.7152 * green + 0.0722 * blue

    lum_a = luminance(hex_a)
    lum_b = luminance(hex_b)
    lighter = max(lum_a, lum_b)
    darker = min(lum_a, lum_b)
    return (lighter + 0.05) / (darker + 0.05)


def test_tehisson_logo_asset_is_served_by_static_route(client, app):
    logo = Path(app.static_folder) / "images" / "tehisson-logo.png"

    assert logo.is_file()
    assert logo.stat().st_size > 0

    response = client.get("/static/images/tehisson-logo.png")

    assert response.status_code == 200
    assert response.content_type == "image/png"


@pytest.mark.parametrize("route", PUBLIC_ROUTES)
def test_public_and_auth_pages_render_tehisson_branding(client, route):
    response = client.get(route)
    html = _html(response)

    assert response.status_code == 200
    assert "TEHISSON" in html
    assert "SERVICES PROFESSIONNELS AUX PARTICULIERS" in html.upper()
    assert "/static/images/tehisson-logo.png" in html
    assert 'aria-label="TEHISSON - Accueil"' in html
    assert "LavageAuto" not in html
    _assert_lavageauto_only_in_weak_password_context(html)


@pytest.mark.parametrize("route", CONNECTED_ROUTES)
def test_connected_pages_render_tehisson_branding(client, route):
    response = client.get(route)
    html = _html(response)

    assert response.status_code == 200
    assert "TEHISSON" in html
    assert "LavageAuto" not in html
    _assert_lavageauto_only_in_weak_password_context(html)


def test_registration_and_connected_password_validations_block_brand_passwords(client):
    pages = [
        client.get("/inscription"),
        client.get("/clients/dashboard"),
        client.get("/prestataires/dashboard"),
    ]

    for response in pages:
        html = _html(response).lower()
        assert response.status_code == 200
        assert "tehisson" in html
        assert "weakpassword" in html
        assert "lavageauto" in html


def test_brand_css_uses_official_palette_and_focus_states(app):
    public_css = Path(app.static_folder) / "css" / "public.css"
    connected_css = Path(app.static_folder) / "css" / "client.css"
    public_text = public_css.read_text(encoding="utf-8").lower()
    connected_text = connected_css.read_text(encoding="utf-8").lower()
    combined_css = public_text + "\n" + connected_text

    for color in OFFICIAL_COLORS:
        assert color in combined_css

    assert ":focus" in combined_css
    assert "border-color" in combined_css
    assert "btn-primary" in combined_css
    assert "btn-secondary" in combined_css
    assert "alert-error" in combined_css or "auth-message-error" in combined_css
    assert _contrast_ratio("#111111", "#9cffb6") >= 4.5
    assert _contrast_ratio("#111111", "#e5feef") >= 4.5


def test_public_catalog_api_contracts_survive_branding_changes(client, monkeypatch):
    from backend.public import routes as catalogue_routes

    monkeypatch.setattr(
        catalogue_routes,
        "list_services_public",
        lambda: ([{"id": 1, "nom": "Lavage premium"}], None),
    )
    monkeypatch.setattr(
        catalogue_routes,
        "list_prestataires_public",
        lambda: ([{"id": 7, "nom": "Diallo"}], None),
    )

    services_response = client.get("/services")
    prestataires_response = client.get("/prestataires")

    assert services_response.status_code == 200
    assert services_response.get_json()["success"] is True
    assert services_response.get_json()["data"] == [{"id": 1, "nom": "Lavage premium"}]

    assert prestataires_response.status_code == 200
    assert prestataires_response.get_json()["success"] is True
    assert prestataires_response.get_json()["data"] == [{"id": 7, "nom": "Diallo"}]


def test_health_api_contract_survives_branding_changes(client, monkeypatch):
    monkeypatch.setattr(
        health_routes,
        "_check_database",
        lambda: health_routes._ok({"result": 1}),
    )
    monkeypatch.setattr(
        health_routes,
        "_check_redis_url",
        lambda url: health_routes._ok({"url": url}),
    )

    health_response = client.get("/health")
    readiness_response = client.get("/health/readiness")

    assert health_response.status_code == 200
    assert health_response.get_json()["success"] is True
    assert health_response.get_json()["data"]["service"] == "lavage-auto"

    assert readiness_response.status_code == 200
    assert readiness_response.get_json()["success"] is True
    assert readiness_response.get_json()["data"]["status"] == "ok"
