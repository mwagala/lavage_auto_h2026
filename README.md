# Plateforme Service Lavage Auto a Domicile

Application web pour gerer une plateforme de reservation de lavage auto a domicile.

- Backend: Flask + JWT
- Frontend: Flask/Jinja templates + CSS/JS progressif
- Base de donnees: PostgreSQL

## 1) Fonctionnalites actuelles

### Authentification
- Inscription client/prestataire
- Connexion JWT
- Changement de mot de passe
- Validation du NAS, du code postal et de la robustesse des mots de passe

### Client
- Consulter/modifier son profil
- Creer une reservation
- Voir reservations a venir, historique et 10 dernieres reservations
- Modifier/annuler certaines reservations
- Ajouter/modifier un commentaire
- Consulter ses factures et leurs details

### Prestataire
- Consulter/modifier son profil
- Gerer disponibilites (CRUD)
- Gerer services (CRUD)
- Voir reservations (toutes, a venir, passees)
- Mettre a jour le statut d'une reservation

### Public
- Pages publiques (`/`, `/connexion`, `/inscription`, `/services-page`, `/equipe`)
- Catalogue services et prestataires
- Profil public des prestataires avec services, disponibilites et commentaires

### Fondations techniques de l'etape 1
- PostgreSQL avec scripts d'initialisation et migrations de fondation
- Redis + Celery worker + Celery Beat
- Outbox transactionnelle pour `reservation.created`, `reservation.updated`, `reservation.cancelled` et `reservation.status_changed`
- Idempotence pour proteger les traitements asynchrones et la creation de reservation via `Idempotency-Key`
- Audit applicatif sur auth, mots de passe, profils et reservations
- Consumer Outbox Celery avec dispatcher initial, retries, backoff et reprise des evenements expires
- Logs JSON, `correlation_id` et en-tete `X-Correlation-ID`
- Endpoints de sante `/health` et `/health/readiness`
- Scripts PowerShell pour Flask, Redis, Celery worker et Celery Beat
- Suite `pytest` pour les fondations et tests integration PostgreSQL/Redis
- Rate limiting login/register avec backend Redis et fallback memoire limite aux environnements dev/test
- Etape 1 fondations livree: compilation, tests unitaires, integration transactionnelle reservation + audit + Outbox et revue securite finale passent; P2 securite planifies pour etape 10 / production progressive

## 2) Roadmap des fonctionnalites a ajouter

Source: [docs/roadmap-fonctionnalites-stack-actuelle.md](./docs/roadmap-fonctionnalites-stack-actuelle.md)

1. Fondations (Redis + Celery + outbox + logs) - livree
2. 2FA (TOTP + recovery codes + fallback SMS) - planification ouverte
3. Notifications asynchrones (email/SMS)
4. Paiement en ligne (Stripe + webhooks signes)
5. Facture PDF (generation + download)
6. Tracking live prestataire (SocketIO)
7. Rappels automatiques 24h / 2h
8. Entente de service (generation + signature)
9. Photos et documents cloud (S3 presigne)
10. QA + mise en production progressive

Version diagrammes (clair, HTML):
- [docs/roadmap-fonctionnalites-stack-actuelle-diagrammes.html](./docs/roadmap-fonctionnalites-stack-actuelle-diagrammes.html)

## 3) Prerequis

- Python 3.11+ (ou version compatible avec les dependances)
- PostgreSQL 14+
- Redis 7+ ou Docker pour lancer Redis localement
- pip

## 4) Installation

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r dependences.txt
```

macOS/Linux:

```bash
source .venv/bin/activate
pip install -r dependences.txt
```

## 5) Configuration

Copier `.env.example` vers `.env`, puis adapter les valeurs locales:

```powershell
Copy-Item .env.example .env
```

Important: `.env` contient des secrets locaux et ne doit pas etre pousse dans Git.

Variables importantes:

- `APP_ENV`: `development`, `test` ou `production`.
- `TESTING`: active la configuration de test Flask.
- `DEBUG`: doit rester `False` hors developpement.
- `CORS_ALLOWED_ORIGINS`: liste separee par des virgules; si vide, CORS n'est ouvert automatiquement qu'en developpement.
- `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`: connexions Redis.
- `HEALTH_CHECK_CELERY_WORKER`: ajoute un ping worker Celery a `/health/readiness` quand `True`.
- `RATE_LIMITING_ENABLED`, `RATE_LIMITING_BACKEND`, `AUTH_LOGIN_RATE_LIMIT_ATTEMPTS`, `AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS`: politique de limitation des tentatives de connexion.
- `AUTH_REGISTER_RATE_LIMIT_ATTEMPTS`, `AUTH_REGISTER_RATE_LIMIT_WINDOW_SECONDS`: politique de limitation des inscriptions.
- `OUTBOX_MAX_ATTEMPTS`, `OUTBOX_RETRY_BACKOFF_SECONDS`, `OUTBOX_MAX_RETRY_DELAY_SECONDS`: politique de reprise Outbox.
- `OUTBOX_STALE_PROCESSING_SECONDS`: age apres lequel un evenement `en_traitement` est remis en reprise.

En environnement non-dev, `SECRET_KEY` et `JWT_SECRET_KEY` doivent etre definis avec des valeurs fortes, et `DEBUG` doit etre desactive.

Pour une installation exposee, PostgreSQL et Redis doivent etre limites a un reseau prive ou a des regles pare-feu strictes. Utiliser des mots de passe forts, des sauvegardes verifiees, une rotation des secrets, et TLS quand le trafic sort de la machine ou du reseau prive.

## 6) Initialiser la base de donnees

1. Creer la base si elle n'existe pas:

```bash
createdb lavage_auto
```

2. Creer les tables dans la base PostgreSQL:

```bash
psql -d lavage_auto -f bd/init.sql
```

3. Si la base existe deja et que vous ne voulez pas reinitialiser tout le schema, appliquer seulement les tables de fondation:

```bash
psql -d lavage_auto -f bd/migrations/001_fondations_tables.sql
```

La migration `002_renommer_fondations_en_francais.sql` est conservee comme jalon historique et ne fait rien en PostgreSQL.

4. Peupler des donnees de test:

```bash
python -m bd.peuplement
```

## 7) Lancer le projet

Windows PowerShell recommande:

Demarrer Redis localement avec Docker:

```powershell
.\scripts\run_redis.ps1
```

Demarrer Flask:

```powershell
.\scripts\run_flask.ps1
```

Ce script utilise explicitement `.\.venv\Scripts\python.exe`, ce qui evite de lancer Flask avec un autre environnement Python.

Worker Celery:

```powershell
.\scripts\run_celery_worker.ps1
```

Ce script utilise explicitement `.\.venv\Scripts\celery.exe`, donc Flask et Celery partagent les memes dependances du meme environnement virtuel.

Celery Beat:

```powershell
.\scripts\run_celery_beat.ps1
```

Apres la creation d'une reservation, Flask publie maintenant la tache `outbox.process_pending_events` dans Redis juste apres le `commit`. Beat reste actif comme filet de securite: il republie la meme tache toutes les `OUTBOX_CONSUMER_INTERVAL_SECONDS` secondes pour rattraper les evenements Outbox qui seraient restes en attente.

Le consumer Outbox remet en attente les echecs temporaires avec backoff jusqu'a `OUTBOX_MAX_ATTEMPTS`. Les evenements restes trop longtemps en `en_traitement` sont liberes par le prochain passage du consumer selon `OUTBOX_STALE_PROCESSING_SECONDS`.

Alternative avec un fichier Python:

```powershell
.\.venv\Scripts\python.exe -m backend.celery.run_beat
```

Consumer Outbox manuel pour debug:

```powershell
.\.venv\Scripts\python.exe -c "from backend.celery.tasks.outbox import process_pending_outbox_events; print(process_pending_outbox_events.run(10))"
```

Avec le worker Celery lance, la meme tache peut etre envoyee au broker:

```powershell
.\.venv\Scripts\python.exe -c "from backend.celery.tasks.outbox import process_pending_outbox_events; print(process_pending_outbox_events.delay(10).get(timeout=10))"
```

Alternative apres activation manuelle du `.venv`:

```bash
python app.py
```

Application disponible par defaut sur:
- `http://127.0.0.1:5000`

Controles de sante:
- `GET /health`: verifie que Flask repond.
- `GET /health/readiness`: verifie PostgreSQL, Redis, broker Celery et backend de resultats Celery.
- Si `HEALTH_CHECK_CELERY_WORKER=True`, readiness verifie aussi qu'au moins un worker Celery repond au ping.

Chaque reponse JSON inclut un `correlation_id`, aussi expose dans l'en-tete `X-Correlation-ID`.

## 8) Comptes de test (apres peuplement)

Mot de passe commun:
- `TestPassword2026!`

Exemples:
- Client: `client1.postman@example.com`
- Prestataire: `prestataire1.postman@example.com`

## 9) Endpoints API principaux

### Auth
- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/logout`

### Client
- `GET|PUT /clients/me`
- `GET /clients/me/reservations`
- `GET /clients/me/reservations/upcoming`
- `GET /clients/me/reservations/past`
- `DELETE /clients/me/reservations/{id}`
- `POST|PUT|GET /clients/me/reservations/{id}/commentaire`
- `GET /clients/me/factures`

### Prestataire
- `GET|PUT /prestataires/me`
- `GET|POST|PUT /prestataires/me/disponibilites`
- `DELETE /prestataires/me/disponibilites/{jour}/{heure_debut}/{heure_fin}`
- `GET|POST /prestataires/me/services`
- `PUT|DELETE /prestataires/me/services/{id}`
- `PATCH /prestataires/me/reservations/{id}/statut`

### Reservations
- `POST /new_reservation`
- `GET|PUT|DELETE /reservations/{id}`
- `GET /reservations/{id}/facture`

## 10) Structure du projet

```text
backend/
  Auth/ Clients/ Prestataires/ Profile/ Reservations/ public/ Commun/ Health/ celery/
bd/
  config.py database.py init.sql peuplement.py migrations/
frontend/
  route/ templates/ static/
scripts/
  run_flask.ps1 run_celery_worker.ps1 run_celery_beat.ps1
app.py
extensions.py
```

## 11) Notes

- Le projet est en cours d'evolution (voir roadmap).
- La roadmap historique mentionne MySQL, mais ce depot implemente actuellement PostgreSQL. Les scripts, migrations et exemples locaux suivent PostgreSQL.
- Une execution locale complete necessite PostgreSQL actif et correctement configure.
- Redis doit etre actif pour les workers Celery et le traitement Outbox asynchrone.
- L'etape 1 est livree sur le perimetre fondations. Les P2 securite planifies restent obligatoires avant production exposee.
