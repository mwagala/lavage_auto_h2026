# Roadmap Fonctionnalites - Version Stack Actuelle (Flask/Jinja/MySQL)

## Stack conservee

- Backend: Flask + Flask-JWT-Extended
- Frontend: Flask + Jinja templates existants + CSS/JS progressif
- DB: MySQL
- Async: Celery + Redis
- Realtime: Flask-SocketIO
- Email: SendGrid
- SMS: Twilio
- Paiement: Stripe
- PDF: WeasyPrint
- Stockage cloud: S3

## Plan etapes par etapes

1. **Fondations**
   - Ajouter Redis + Celery + workers.
   - Introduire table outbox + consumer.
   - Ajouter idempotence applicative pour outbox, webhooks, notifications et jobs planifies.
   - Ajouter journal d'audit pour 2FA, paiements, signatures, medias et changements de reservation.
   - Standardiser logs et erreurs.

2. **2FA**
   - TOTP + recovery codes.
   - Fallback OTP SMS.
   - Login en 2 etapes.

3. **Notifications**
   - Evenements: confirmation reservation, annulation, modification, en route, en cours, termine.
   - Envoi email/SMS asynchrone.
   - Livraison idempotente pour eviter les doublons email/SMS.

4. **Paiement en ligne**
   - Stripe Payment Intent.
   - Webhooks signes.
   - Rapprochement reservation/facture/transaction.
   - Traitement idempotent des webhooks et audit des transitions de paiement.

5. **Facture PDF**
   - Generation facture detaillee.
   - Endpoint download PDF.

6. **Tracking live**
   - Publication position prestataire.
   - Diffusion live vers client (SocketIO).

7. **Rappels 24h / 2h**
   - Jobs planifies.
   - Lien securise annuler/deplacer.
   - Historique idempotent des rappels pour eviter les envois multiples.

8. **Entente de service**
   - Generation + signature.
   - Blocage demarrage si non signee.
   - Audit de signature et conservation de la version signee.

9. **Photos et documents cloud**
   - Upload pre-signe S3.
   - Association media/documents a la reservation.
   - Validation securite: type MIME, taille, scan antivirus, chiffrement et retention.

10. **QA et mise en prod**
   - Tests API + E2E + webhooks + realtime.
   - Feature flags et deploiement progressif.
   - Verification des flags, audit, idempotence et controles de sante avant activation.

## Version diagrammes (HTML)

- [Roadmap stack actuelle avec diagrammes (clair)](./roadmap-fonctionnalites-stack-actuelle-diagrammes.html)
