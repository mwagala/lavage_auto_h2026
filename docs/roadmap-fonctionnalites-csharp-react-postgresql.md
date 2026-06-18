# Roadmap Fonctionnalites - Version C# / React / PostgreSQL

## 1) Stack cible recommandee

- Backend: ASP.NET Core 8 Web API (C#)
- Frontend: React + TypeScript (Vite)
- Base de donnees: PostgreSQL 16 + PostGIS
- Realtime: SignalR
- Jobs: Hangfire + Redis
- Auth: ASP.NET Identity + JWT + Refresh tokens + 2FA
- Notifications: SendGrid (email), Twilio (SMS)
- Paiement: Stripe (Payment Intents + Webhooks)
- PDF: QuestPDF
- Stockage cloud: S3 (ou Azure Blob)
- Signature: DocuSign (ou signature interne)

## 2) Pourquoi PostgreSQL/PostGIS

- Transactions robustes pour reservations/factures/paiements.
- Tres bon modele relationnel pour ce domaine.
- PostGIS adapte au suivi GPS live prestataire.
- JSONB utile pour metadata/documents/evenements.

## 3) Diagramme d'architecture global (C#)

```mermaid
flowchart LR
    subgraph U[Utilisateurs]
        C[Client]
        P[Prestataire]
        A[Admin]
    end

    subgraph FE[Frontend]
        R[React SPA]
    end

    subgraph BE[Backend .NET]
        API[ASP.NET Core API]
        HUB[SignalR Hub]
        JOBS[Hangfire Jobs]
        OUTBOX[Outbox Worker]
    end

    subgraph DATA[Data]
        PG[(PostgreSQL + PostGIS)]
        REDIS[(Redis)]
        S3[(S3/Blob)]
    end

    subgraph EXT[Externe]
        STRIPE[Stripe]
        SENDGRID[SendGrid]
        TWILIO[Twilio]
        DOCUSIGN[DocuSign]
    end

    C --> R
    P --> R
    A --> R
    R --> API
    R <--> HUB

    API --> PG
    API --> REDIS
    JOBS --> REDIS
    OUTBOX --> PG
    API --> S3

    API --> STRIPE
    API --> SENDGRID
    API --> TWILIO
    API --> DOCUSIGN
```

## 4) Diagramme d'architecture backend uniquement (C#)

```mermaid
flowchart TB
    subgraph API[ASP.NET Core Backend]
        GW[Controllers]
        AUTH[Auth + 2FA]
        RES[Reservations]
        BILL[Facturation/PDF]
        PAY[Paiements]
        NOTIF[Notifications]
        TRACK[Tracking]
        MEDIA[Media/Documents]
        AGREE[Ententes]
        HUB[SignalR]
        JOBS[Hangfire]
        OUTBOX[Outbox]
    end

    subgraph STORE[Stockage]
        PG[(PostgreSQL + PostGIS)]
        REDIS[(Redis)]
        CLOUD[(S3/Blob)]
    end

    subgraph PROVIDERS[Providers]
        STRIPE[Stripe]
        SENDGRID[SendGrid]
        TWILIO[Twilio]
        DOCUSIGN[DocuSign]
    end

    GW --> AUTH
    GW --> RES
    GW --> BILL
    GW --> PAY
    GW --> NOTIF
    GW --> TRACK
    GW --> MEDIA
    GW --> AGREE
    GW <--> HUB

    AUTH --> PG
    RES --> PG
    BILL --> PG
    PAY --> PG
    NOTIF --> PG
    TRACK --> PG
    MEDIA --> PG
    AGREE --> PG
    OUTBOX --> PG

    HUB --> REDIS
    JOBS --> REDIS

    MEDIA --> CLOUD
    BILL --> CLOUD
    AGREE --> CLOUD

    PAY --> STRIPE
    NOTIF --> SENDGRID
    NOTIF --> TWILIO
    AGREE --> DOCUSIGN
```

## 5) Diagramme d'architecture front-end uniquement (React)

```mermaid
flowchart TB
    subgraph UI[React SPA]
        APP[App Shell]
        ROUTER[React Router]
        AUTHP[AuthProvider]
        GUARD[Route Guards RBAC]
        STATE[Redux Toolkit / React Query]
        FORMS[React Hook Form + Zod]
        MAP[Tracking Map View]
        CENTER[Notification Center]
        FILES[Upload Media/Documents]
        BILLVIEW[PDF Facture Viewer]
        SIGN[Entente Signature UI]
        WS[SignalR Client]
    end

    subgraph PAGES[Pages]
        LOGIN[Login + 2FA]
        CD[Client Dashboard]
        PD[Prestataire Dashboard]
        AD[Admin Console]
        RESV[Reservations]
        FACT[Factures]
    end

    subgraph API[Backend]
        REST[REST API]
        HUB[SignalR Hub]
        PRE[Pre-signed Upload URLs]
    end

    APP --> ROUTER
    ROUTER --> LOGIN
    ROUTER --> CD
    ROUTER --> PD
    ROUTER --> AD
    ROUTER --> RESV
    ROUTER --> FACT

    AUTHP --> GUARD
    GUARD --> ROUTER
    STATE --> REST
    FORMS --> LOGIN
    FORMS --> RESV
    WS <--> HUB
    MAP <--> WS
    CENTER <--> WS
    FILES --> PRE
    FILES --> REST
    BILLVIEW --> REST
    SIGN --> REST
```

## 6) Diagramme de classes (domaine principal)

```mermaid
classDiagram
    class User {
      +Guid Id
      +string Nom
      +string Prenoms
      +string Courriel
      +bool EstActif
    }
    class Client
    class Prestataire {
      +string NAS
      +decimal NoteMoyenne
      +bool DoitChangerMotDePasse
    }
    class Administrateur

    class Reservation {
      +Guid Id
      +DateOnly DateService
      +TimeOnly HeureDebut
      +TimeOnly HeureFin
      +string Statut
    }
    class ReservationService {
      +Guid ReservationId
      +Guid ServiceId
      +decimal PrixApplique
      +decimal DureePrevue
      +int Quantite
    }
    class ServiceOffert {
      +Guid Id
      +Guid PrestataireId
      +string Nom
      +decimal Prix
      +decimal Duree
    }
    class Facture {
      +Guid Id
      +Guid ReservationId
      +decimal SousTotal
      +decimal Total
      +string PdfUrl
    }
    class PaymentTransaction {
      +Guid Id
      +Guid ReservationId
      +decimal Montant
      +string Statut
    }
    class NotificationEvent
    class NotificationDelivery
    class ProviderLocationPoint
    class ServiceAgreement
    class ServiceMedia
    class TwoFactorMethod

    User <|-- Client
    User <|-- Prestataire
    User <|-- Administrateur

    Client "1" --> "0..*" Reservation : cree
    Prestataire "1" --> "0..*" Reservation : execute
    Prestataire "1" --> "0..*" ServiceOffert : propose
    Reservation "1" --> "1..*" ReservationService
    ServiceOffert "1" --> "0..*" ReservationService
    Reservation "1" --> "0..1" Facture
    Reservation "1" --> "0..*" PaymentTransaction
    Reservation "1" --> "0..*" NotificationEvent
    NotificationEvent "1" --> "0..*" NotificationDelivery
    Prestataire "1" --> "0..*" ProviderLocationPoint
    Reservation "1" --> "0..1" ServiceAgreement
    Reservation "1" --> "0..*" ServiceMedia
    User "1" --> "0..*" TwoFactorMethod
```

## 7) Plan d'implementation par phases

1. **Fondations**: architecture modulaire, migrations, observabilite, Redis/Hangfire/SignalR.
2. **Auth + 2FA**: TOTP, OTP SMS fallback, recovery codes, audit securite.
3. **Evenements + notifications**: outbox, templates, envois email/SMS, retries.
4. **Paiement en ligne**: Stripe + webhooks signes + rapprochement transactionnel.
5. **Facture PDF**: generation QuestPDF + endpoint download + archivage.
6. **Tracking live**: publication position prestataire, diffusion SignalR, statut trajet.
7. **Rappels 24h/2h**: jobs planifies, liens securises annuler/deplacer.
8. **Entente de service**: generation, signature, blocage demarrage si non signee.
9. **Photos/docs cloud**: pre-signed uploads, metadata, permissions et retention.
10. **QA + rollout**: tests end-to-end, feature flags, deploiement progressif.

## 8) Tables a ajouter (minimum)

- `two_factor_methods`
- `two_factor_recovery_codes`
- `notification_preferences`
- `notification_events`
- `notification_deliveries`
- `payment_transactions`
- `payment_webhook_logs`
- `provider_locations`
- `service_reminders`
- `service_agreements`
- `service_agreement_signatures`
- `service_media`
- `service_documents`
- `audit_logs`

