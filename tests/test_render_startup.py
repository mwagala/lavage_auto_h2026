from pathlib import Path


def test_render_web_starts_gunicorn_when_bootstrap_is_not_required():
    script = Path("scripts/render_web.sh").read_text(encoding="utf-8")

    assert "python -m scripts.bootstrap" in script
    assert "RENDER_WEB_BOOTSTRAP_REQUIRED" in script
    assert "RENDER_WEB_BOOTSTRAP_TIMEOUT_SECONDS" in script
    assert "True|true|1|yes|on" in script
    assert ") &" in script
    assert "Demarrage web sans attendre la fin du bootstrap." in script
    assert "Bootstrap non concluant; service web maintenu en mode degrade." in script
    assert "exec gunicorn" in script
