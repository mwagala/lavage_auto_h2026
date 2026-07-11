"""Routes factures historiques.

Ce module est conserve comme jalon legacy mais n'est pas enregistre dans
`app.py`. Les endpoints factures actifs sont exposes via les routes clients et
reservations.
"""

from flask import Blueprint


factures_legacy_bp = Blueprint("factures_legacy", __name__)
