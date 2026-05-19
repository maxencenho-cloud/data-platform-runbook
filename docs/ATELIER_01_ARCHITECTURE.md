# Pyl.Tech : Atelier de Lancement - Data Platform (Phase POC)

> **Date** : Mai 2026 | **Auteurs** : Équipe Pyl.Tech
> *Support de cadrage technique pour l'atelier 1 (Architecture & Socle).*

*Ce document est conçu pour être déroulé pas à pas. Il vous guidera dans la compréhension de l'architecture cible et l'exécution des prérequis techniques.*

---

## 1. Gouvernance & Fondations GCP

L'objectif du POC est de valider la valeur technique sur un périmètre restreint, tout en respectant dès le premier jour les standards de sécurité (isolation, IAM, CI/CD).

### 1.1. L'Organisation et les Projets (Landing Zone)

GCP structure les ressources de manière hiérarchique. Le POC s'exécutera dans un conteneur (Projet) totalement isolé de votre production actuelle ou future.

```mermaid
graph TD
    A["🏢 Organisation<br/>(votre-domaine.com)"] --> B["📁 Dossier : Production"]
    A --> C["📁 Dossier : Non-Production"]
    
    C --> D["📦 Projet GCP : POC Data Platform"]
    B --> E["📦 Projet GCP : Prod (futur)"]
    
    D --> F["🪣 Cloud Storage (Buckets)"]
    D --> G["📊 BigQuery (Datasets)"]
    D --> H["⚙️ Cloud Run (Services)"]
    D --> I["🔄 Dataform (Repos)"]
    
    style A fill:#0b132b,stroke:#0b132b,color:#fff
    style D fill:#F4BF46,stroke:#F4BF46,color:#0b132b
    style E fill:#eeeeee,stroke:#ccc,color:#999
```

L'avantage majeur de votre environnement est que votre **Organisation GCP est déjà créée et liée à votre annuaire Google Workspace**. 

**Todo :**
1. **Vérifier l'Organisation** : Connectez-vous sur `console.cloud.google.com` (en tant qu'admin). Votre domaine doit apparaître en haut à gauche.
2. **Créer le Projet POC** : Créez un projet nommé par exemple `idex-poc-data` dans un dossier "Non-Production".
3. **Activer les APIs** sur ce projet : `bigquery.googleapis.com`, `run.googleapis.com`, `pubsub.googleapis.com`, `storage.googleapis.com`, `dataform.googleapis.com`, `secretmanager.googleapis.com`.

---

## 2. Gestion des Identités et Accès (IAM)

Nous appliquons une séparation stricte entre les accès humains (Groupes) et les accès machines (Comptes de Service), basée sur le principe du moindre privilège.

### 2.1. Cartographie des Accès (RBAC)

```mermaid
flowchart TB
    subgraph "Identités Humaines (via Groupes)"
        U1["👤 Data Engineer"]
        U2["👤 Data Analyst"]
        U3["👤 Métier / Sponsor"]
    end
    
    subgraph "Identités de Service (Service Accounts)"
        SA1["🤖 ingestion-sa<br/>Cloud Run"]
        SA3["🤖 terraform-sa<br/>CI/CD Déploiement"]
        SA4["🤖 dataform-sa<br/>Dataform natif"]
    end
    
    subgraph "Ressources GCP"
        GCS["🪣 Cloud Storage"]
        BQ["📊 BigQuery"]
    end
    
    U1 -->|via Groupe| BQ
    U2 -->|via Groupe| BQ
    U3 -->|via Groupe, lecture seule| BQ
    SA1 --> GCS
    SA1 --> BQ
    SA3 -->|WIF, pas de clé| GCS
    SA3 -->|WIF, pas de clé| BQ
    SA4 -->|Exécute les requêtes| BQ
    
    style SA1 fill:#208AAE,stroke:#0b132b,color:#fff
    style SA3 fill:#5BC0BE,stroke:#0b132b,color:#0b132b
    style SA4 fill:#208AAE,stroke:#0b132b,color:#fff
```

### 2.2. Les Groupes Humains (Action Requise)

Les groupes créés dans votre console d'administration Workspace sont nativement reconnus par GCP. **Aucun droit nominatif ne sera distribué**.

**Todo :**
1. Allez sur `admin.google.com` > Annuaire > Groupes.
2. Créez les 3 groupes ci-dessous.
3. Ajoutez l'équipe Pyl.Tech au groupe Engineers.

| Groupe Workspace | Périmètre d'Accès GCP |
|:-----------------|:----------------------|
| `gcp-data-engineers@votre-domaine.com` | **Admin/Écriture** : Maintenance infra, ingestion, datasets Bronze/Silver/Gold. |
| `gcp-data-analysts@votre-domaine.com` | **Lecture/Analyse** : Requêtage Dataform, accès complet Gold, lecture Bronze/Silver. |
| `gcp-business-users@votre-domaine.com` | **Lecture Seule** : Consultation restreinte au dataset Gold (Data Marts/BI). |

### 2.3. Les Comptes de Service (Gérés par le code)

Ces comptes machines sont créés automatiquement par notre code Terraform. Ils ne partagent jamais leurs droits :
- `ingestion-sa` : Écrit dans Cloud Storage (Processing/Quarantine) et BigQuery (Bronze).
- `terraform-sa` : Déploie l'infrastructure (CI/CD).
- `dataform-sa` : Exécute les transformations SQLX dans BigQuery.

---

## 3. Sécurité CI/CD : Approche Zero Trust (WIF)

**Règle d'or : Aucune clé JSON statique de compte de service ne sera exportée ni stockée.**

Pour éviter toute fuite de credentials (par ex. un développeur qui "commit" une clé sur Git), nous utilisons **Workload Identity Federation (WIF)** :

```mermaid
sequenceDiagram
    autonumber
    participant Git as 🐙 Plateforme Git (Pipeline)
    participant WIF as 🔐 Workload Identity (GCP)
    participant GCP as ☁️ Ressources GCP

    Git->>WIF: Présente un jeton OIDC (courte durée)
    WIF->>WIF: Vérifie l'identité du dépôt cryptographiquement
    WIF->>GCP: Émet un token d'accès temporaire (Terraform SA)
    Git->>GCP: terraform apply (avec token temporaire)
    Note over Git,GCP: Le token expire après 1h. Aucun secret stocké.
```

**Todo :**
1. Identifier votre outil Git (GitHub, GitLab...).
2. Pyl.Tech paramétrera avec vous le Workload Identity Pool sur GCP pour approuver spécifiquement ce dépôt.

---

## 4. Architecture Globale de la Plateforme

L'architecture est découpée en deux flux asynchrones et découplés : l'ingestion (Event-Driven) et la transformation (Batch Medallion).

```mermaid
graph TB
    subgraph "1. Ingestion Event-Driven"
        SRC["📄 Fichier Source"] --> LAND["🪣 Landing"]
        LAND -->|"Événement GCS"| PS["📬 Pub/Sub"]
        PS -->|"Push"| CR["⚙️ Cloud Run<br/>(Python)"]
        CR -->|"Validation OK"| STG["🪣 Staging"]
        STG -->|"BQ Load Job"| BRZ["🥉 Bronze"]
        CR -->|"Validation KO"| QUA["🪣 Quarantine"]
    end
    
    subgraph "2. Transformation Batch"
        GIT["🐙 GitHub"] -->|"Git Sync"| DF["🔄 Dataform"]
        DF -->|"Nettoyage SQL"| SLV["🥈 Silver"]
        DF -->|"Agrégation SQL"| GLD["🥇 Gold"]
        BRZ -.->|"Source"| DF
    end
    
    subgraph "3. Consommation"
        GLD --> VIZ["📊 Looker / BI"]
    end
    
    style BRZ fill:#cd7f32,color:#fff
    style SLV fill:#c0c0c0,color:#0b132b
    style GLD fill:#F4BF46,color:#0b132b
```

### 4.1. Flux d'Ingestion : La règle du "All-or-Nothing"

Dès qu'un fichier source (CSV/JSONL) est déposé sur Cloud Storage :
1. **Événement Pub/Sub** : Déclenche immédiatement le service d'ingestion (Cloud Run).
2. **Validation stricte (YAML)** : Vérification du typage et des règles métier.
3. **Poison Pill Handling** : Si une seule ligne est invalide, le fichier entier est rejeté en **Quarantaine**. S'il est 100% valide, il est chargé de manière atomique dans la table **Bronze** (BigQuery). L'entrepôt n'est jamais pollué par des données partielles.

### 4.2. Flux de Transformation (Dataform)

Dataform orchestre nativement la transformation de la donnée brute en indicateurs métier, via du code SQLX synchronisé avec votre dépôt Git.

```mermaid
graph LR
    B["🥉 BRONZE<br/>Donnée Brute"] -->|"SQLX (Nettoyage,<br/>Typage, Dédup)"| S["🥈 SILVER<br/>Clean Data"]
    S -->|"SQLX (Agrégation,<br/>Jointures métier)"| G["🥇 GOLD<br/>KPIs / Data Marts"]
    
    style B fill:#cd7f32,color:#fff
    style S fill:#c0c0c0,color:#0b132b
    style G fill:#F4BF46,color:#0b132b
```

---

## 5. Pratiques d'Ingénierie (GitOps & Terraform)

L'intégralité du socle (Réseau, Stockage, IAM, Compute) est définie en code Terraform.

```mermaid
graph TD
    subgraph "Code Terraform (modules)"
        M1["📦 storage"]
        M2["📦 bigquery"]
        M3["📦 ingestion"]
        M4["📦 dataform"]
        M5["📦 monitoring"]
    end
    
    subgraph "Configuration"
        DEV["📄 config.poc.yaml"]
    end
    
    DEV --> MAIN["🏗️ main.tf"]
    MAIN --> M1 & M2 & M3 & M4 & M5
    
    style MAIN fill:#7B42BC,color:#fff
```

- **Reproductibilité** : L'environnement peut être recréé à l'identique en quelques minutes.
- **Mises en production** : Les déploiements (Infra, Code Python, SQL Dataform) sont 100% automatisés via votre outil CI/CD (validation via `terraform plan` systématique).

---

## 6. Observabilité et Alerting

Même en phase POC, une supervision proactive est configurée pour remonter les anomalies :

```mermaid
graph TB
    subgraph "Sources"
        CR_LOG["⚙️ Cloud Run Logs"]
        DF_LOG["🔄 Dataform Logs"]
    end
    
    subgraph "Centralisation"
        SINK["📤 Log Router Sink"]
        OBS["📊 BQ: observability_logs"]
    end
    
    subgraph "Alertes Automatiques"
        A1["🚨 Quarantine Spike"]
        A2["🚨 Dataform Error"]
    end
    
    CR_LOG & DF_LOG --> SINK --> OBS
    CR_LOG --> A1
    DF_LOG --> A2
    
    style A1 fill:#C91432,color:#fff
    style A2 fill:#C91432,color:#fff
```

| Type d'Alerte | Cause Principale | Action requise |
|:--------------|:-----------------|:---------------|
| **Quarantine Spike** | Un fichier source a échoué à la validation YAML. | Vérifier le format du fichier déposé. |
| **Dataform Error** | Échec d'un test qualité (doublon, valeur nulle inattendue). | Analyser la requête SQL en erreur. |

---

## 7. Synthèse et Discussion d'Atelier

### 7.1. Checklist des Actions Client

Ces actions sont les prérequis bloquants pour démarrer l'implémentation technique du POC.

| Priorité | Action | Responsable |
|:--------:|:-------|:------------|
| 🔴 | Créer le **projet GCP POC** (dossier Non-Prod). | Admin GCP Client |
| 🔴 | Créer les **3 groupes IAM Workspace** (Engineers, Analysts, Business). | Admin Workspace |
| 🔴 | Valider le **dépôt Git** et l'outil CI/CD (GitHub, GitLab...). | Chef de Projet |
| 🟡 | Configurer le **Workload Identity (WIF)**. | Admin GCP + Pyl.Tech |
| 🟡 | Donner lesaccès Git/Workspace à l'équipe Pyl.Tech. | Chef de Projet |

### 7.2. Questions Ouvertes

**Données & Use Cases** :
- Quels sont les cas d'usage métiers prioritaires à démontrer dans le POC ?
- Quels sont les formats (CSV, JSONL, Excel ?), volumes et fréquences des fichiers sources ?
- Les fichiers sources seront-ils déposés manuellement ou via un système automatisé (SFTP, API) ?

<div style="color: #208AAE; text-align: right; font-size: 0.9em; font-weight: bold; margin-top: 40px;">
© Copyright 2026 Pyl.Tech
</div>
