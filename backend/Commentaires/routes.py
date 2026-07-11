"""Routes commentaires historiques.

Ce module est conserve comme jalon legacy mais n'est pas enregistre dans
`app.py`. Les routes commentaires actives vivent dans `backend.Clients.routes`
et `backend.Prestataires.routes`.
"""

from flask import Blueprint


commentaires_legacy_bp = Blueprint("commentaires_legacy", __name__)
