# Pyl.Tech : Atelier 2 - Sources de Données & Ingestion (Phase POC)

> **Date** : Mai 2026 | **Auteurs** : Équipe Pyl.Tech

*Ce document constitue le support du deuxième atelier technique. Il est centré sur l'identification des sources de données à intégrer dans le POC, leur structure, les transformations nécessaires et la méthode de chargement.*

*Objectif : à l'issue de cet atelier, nous devons avoir une vision claire des 1 à 2 sources de données prioritaires qui alimenteront le Data Hub pour le pilote.*

---

## 1. Rappel de l'Architecture d'Ingestion

Pour mémoire, voici le flux validé lors de l'atelier 1 :

```mermaid
graph LR
    SRC["📄 Source"] -->|"Fichier CSV/JSONL"| LAND["🪣 Landing"]
    LAND -->|"Événement"| CR["⚙️ Cloud Run"]
    CR -->|"Valide"| BRZ["🥉 Bronze"]
    CR -->|"Invalide"| QUA["🪣 Quarantine"]
    BRZ -->|"Dataform"| SLV["🥈 Silver"]
    SLV -->|"Dataform"| GLD["🥇 Gold"]
    GLD --> BI["📊 Looker / BI"]
    
    style BRZ fill:#cd7f32,color:#fff
    style SLV fill:#c0c0c0,color:#0b132b
    style GLD fill:#F4BF46,color:#0b132b
```

**Rappel du principe All-or-Nothing** : Chaque fichier est validé intégralement. Si une seule ligne est invalide, le fichier complet est rejeté en quarantaine. Aucune donnée partielle n'entre dans l'entrepôt.

---

## 2. Panorama des Sources de Données

### 2.1. Cartographie des Sources Identifiées

```mermaid
mindmap
  root((Sources de Données))
    Systèmes Métier
      EnergX
        Données techniques
        Consommations
        Productions
      XForce
        Contrats
        CRM / Clients
    Référentiels
      Fichiers Excel / CSV
        Référentiels sites
        Nomenclatures
        Tarifs
    Futur
      IoT / Capteurs
      API Météo
      DB Legacy
```

### 2.2. Détail des Sources

| Source | Type | Contenu Métier | Format Attendu | Fréquence | Volume Estimé | Priorité POC |
|:-------|:-----|:---------------|:---------------|:----------|:--------------|:-------------|
| **EnergX** | Système technique | Consommations énergétiques, données de production, relevés | CSV / JSONL / API ? | Quotidien à horaire | À déterminer | 🔴 POC |
| **XForce** | CRM / Contrats | Données clients, contrats, sites, conditions commerciales | CSV / JSONL / API ? | Quotidien | À déterminer | 🔴 POC |
| **Fichiers référentiels** | Dépôt manuel | Référentiels de sites, nomenclatures, tables de correspondance | Excel / CSV | Ponctuel / Mensuel | Faible | 🟡 POC si pertinent |
| **IoT / Capteurs** | Flux temps réel | Données de capteurs terrain | API / MQTT | Continu | Élevé | 🟢 Post-POC |
| **API Météo** | API externe | Données météorologiques contextuelles | REST API JSON | Horaire | Faible | 🟢 Post-POC |
| **DB Legacy** | Base existante | Historiques, données patrimoniales | Export SQL / CSV | Migration unique | Variable | 🟢 Post-POC |

### 2.3. Arbre de Décision : Comment Charger une Source ?

```mermaid
flowchart TD
    START{"Quel type de source ?"}
    
    START -->|"Fichier plat<br/>(CSV, JSONL, Excel)"| FILE["📄 Dépôt dans GCS Landing"]
    START -->|"API REST"| API["🔌 Connecteur Personnalisé<br/>(Cloud Run / Cloud Function)"]
    START -->|"Base de données"| DB{"Base accessible<br/>depuis GCP ?"}
    
    DB -->|"Oui"| DTS["📡 BigQuery Data Transfer<br/>ou Datastream"]
    DB -->|"Non"| EXPORT["📤 Export CSV périodique<br/>→ dépôt GCS"]
    
    FILE --> VALID["✅ Validation par le<br/>service d'ingestion"]
    API --> FILE
    DTS --> BRZ["🥉 Bronze"]
    EXPORT --> FILE
    VALID --> BRZ
    
    style VALID fill:#F4BF46,color:#0b132b
    style BRZ fill:#cd7f32,color:#fff
```

**Pour le POC**, nous privilégions systématiquement la méthode la plus simple : **dépôt de fichiers plats (CSV/JSONL) dans le bucket Landing**. Même si une source dispose d'une API, un export fichier périodique est plus rapide à mettre en œuvre et suffisant pour valider l'architecture.

---

## 3. Structure des Données & Contrats de Schéma

### 3.1. Principe des Contrats de Données (Data Contracts)

Chaque source de données est décrite par un **contrat de schéma YAML** qui définit les colonnes attendues, leurs types et les règles de validation. Ce contrat est le "garde-fou" de l'ingestion.

```mermaid
sequenceDiagram
    participant F as 📄 Fichier Source
    participant S as 📋 Schéma YAML
    participant CR as ⚙️ Cloud Run
    participant BQ as 📊 BigQuery

    F->>CR: Fichier arrive dans Landing
    CR->>S: Lecture du schéma correspondant
    S-->>CR: Colonnes, types, nullabilité
    CR->>CR: Validation ligne par ligne
    
    alt Conforme au contrat
        CR->>BQ: Chargement Bronze
    else Non conforme
        CR->>CR: Rejet en Quarantine
    end
```

### 3.2. Exemple de Contrat de Schéma

Voici un exemple de contrat YAML tel qu'il existe aujourd'hui dans le dépôt :

```yaml
# schemas/bronze/example_raw_data.yaml
version: 1
description: "Example raw data schema for ingestion validation"

fields:
  - name: id
    type: int
    nullable: false
    description: "Unique identifier for the record"
  - name: name
    type: str
    nullable: false
    description: "Name of the entity"
  - name: value
    type: float
    nullable: true
    description: "Numeric value associated with the record"
  - name: record_date
    type: date
    format: "%d/%m/%Y"
    nullable: false
    description: "Date of the record (e.g., 15/01/2026)"
```

### 3.3. Types Supportés

| Type YAML | Type Python (Pydantic) | Type BigQuery | Exemple |
|:----------|:----------------------|:-------------|:--------|
| `int` | `int` | `INTEGER` | `42` |
| `float` | `float` | `FLOAT` | `3.14` |
| `str` | `str` | `STRING` | `"Paris"` |
| `bool` | `bool` | `BOOLEAN` | `true` |
| `date` | `date` | `DATE` | `2026-01-15`<br/>*(L'attribut `format: "%d/%m/%Y"` est obligatoire si la date source n'est pas au format ISO `YYYY-MM-DD`)* |
| `datetime` | `datetime` | `TIMESTAMP` | `2026-01-15T08:30:00Z` |

### 3.4. Travail à Réaliser en Atelier (par Source)

Pour chaque source prioritaire du POC, nous devons remplir la fiche suivante :

> **Fiche Source : [NOM DE LA SOURCE]**
>
> | Critère | Réponse |
> |:--------|:--------|
> | Nom de la source | |
> | Système d'origine | |
> | Format du fichier | CSV / JSONL / Excel / Autre |
> | Encodage | UTF-8 / ISO-8859-1 / Autre |
> | Séparateur (si CSV) | `;` / `,` / `\t` |
> | Ligne d'en-tête | Oui / Non |
> | Nombre de colonnes | |
> | Volume moyen par fichier | |
> | Fréquence de dépôt | |
> | Qui dépose le fichier ? | Automatisé / Manuel |
> | Échantillon disponible ? | Oui / Non |

---

## 4. Les Transformations (Bronze → Silver → Gold)

### 4.1. Vue d'Ensemble du Pipeline de Transformation

```mermaid
graph TB
    subgraph "Bronze (Données Brutes)"
        B1["energx_raw<br/><i>Tel quel depuis la source</i>"]
        B2["xforce_raw<br/><i>Tel quel depuis la source</i>"]
        B3["referentiel_sites_raw<br/><i>Tel quel depuis la source</i>"]
    end
    
    subgraph "Silver (Données Nettoyées)"
        S1["energx_clean<br/><i>Typé, dédupliqué, normalisé</i>"]
        S2["xforce_clean<br/><i>Typé, dédupliqué, normalisé</i>"]
        S3["dim_sites<br/><i>Référentiel nettoyé</i>"]
    end
    
    subgraph "Gold (Données Métier)"
        G1["fact_consommations<br/><i>Table de faits enrichie</i>"]
        G2["kpi_rendement_mensuel<br/><i>KPIs agrégés</i>"]
        G3["rapport_cockpit_rcf<br/><i>Data Mart BI</i>"]
    end
    
    B1 --> S1
    B2 --> S2
    B3 --> S3
    
    S1 --> G1
    S2 --> G1
    S3 --> G1
    G1 --> G2
    G1 --> G3
    S3 --> G3
    
    style B1 fill:#cd7f32,color:#fff
    style B2 fill:#cd7f32,color:#fff
    style B3 fill:#cd7f32,color:#fff
    style S1 fill:#c0c0c0,color:#0b132b
    style S2 fill:#c0c0c0,color:#0b132b
    style S3 fill:#c0c0c0,color:#0b132b
    style G1 fill:#F4BF46,color:#0b132b
    style G2 fill:#F4BF46,color:#0b132b
    style G3 fill:#F4BF46,color:#0b132b
```

### 4.2. Détail des Transformations par Couche

| Couche | Opérations | Outil | Exemples Concrets |
|:-------|:-----------|:------|:------------------|
| **Bronze → Silver** | Typage fort, dédoublonnage, normalisation des dates, gestion des valeurs nulles, renommage des colonnes | Dataform (SQLX) | Convertir les dates `"15/01/2026"` en `DATE`, supprimer les doublons par clé primaire, uniformiser les unités (kWh vs MWh) |
| **Silver → Gold** | Jointures inter-sources, calculs métier, agrégations, création de KPIs | Dataform (SQLX) | Joindre EnergX (consos) avec XForce (contrats) sur l'ID site, calculer le rendement énergétique, agréger par mois |

### 4.3. Quality Gates (Contrôle Qualité à Chaque Couche)

```mermaid
graph LR
    subgraph "Gate 1 : TECHNIQUE"
        QG1["Format OK ?<br/>En-tête OK ?<br/>Encodage OK ?"]
    end
    
    subgraph "Gate 2 : STRUCTURELLE"
        QG2["Types conformes ?<br/>Dédoublonnage ?<br/>Intégrité référentielle ?"]
    end
    
    subgraph "Gate 3 : MÉTIER"
        QG3["Complétude ?<br/>Cohérence métier ?<br/>KPIs plausibles ?"]
    end
    
    LAND["🪣 Landing"] --> QG1
    QG1 -->|"✅"| BRZ["🥉 Bronze"]
    QG1 -->|"❌"| QUAR["🪣 Quarantine"]
    BRZ --> QG2
    QG2 -->|"✅"| SLV["🥈 Silver"]
    QG2 -->|"❌"| ALERT1["🚨 Alerte"]
    SLV --> QG3
    QG3 -->|"✅"| GLD["🥇 Gold"]
    QG3 -->|"❌"| ALERT2["🚨 Alerte"]

    style QUAR fill:#C91432,color:#fff
    style GLD fill:#F4BF46,color:#0b132b
```

| Gate | Couche | Implémenté par | Exemples de Tests |
|:-----|:-------|:---------------|:------------------|
| **Gate 1 (Technique)** | Landing → Bronze | Service d'ingestion (Python) | Format CSV valide, colonnes conformes au schéma YAML, types corrects |
| **Gate 2 (Structurelle)** | Bronze → Silver | Dataform Assertions (SQLX) | Pas de doublons sur la clé primaire, intégrité référentielle (site_id existe dans dim_sites), complétude des champs obligatoires |
| **Gate 3 (Métier)** | Silver → Gold | Dataform Assertions (SQLX) | Rendement entre 0% et 150%, pas de consommation négative, dates dans une plage cohérente |

### 4.4. Exemple d'Assertion Dataform (SQLX)

```sql
-- definitions/assertions/assert_no_duplicate_sites.sqlx
config {
  type: "assertion",
  database: "mon-projet",
  schema: "silver"
}

-- Vérifie qu'il n'y a aucun doublon dans la dimension sites
SELECT site_id, COUNT(*) as cnt
FROM ${ref("dim_sites")}
GROUP BY site_id
HAVING cnt > 1
-- Si cette requête retourne des lignes → l'assertion échoue
```

---

## 5. Méthode de Chargement : Étapes Pratiques

### 5.1. Processus de Bout en Bout pour une Nouvelle Source

```mermaid
sequenceDiagram
    autonumber
    participant ME as 👤 Métier / Data Owner
    participant DE as 🛠️ Data Engineer
    participant GIT as 🐙 Dépôt Git
    participant GCP as ☁️ GCP

    ME->>DE: Fournit un échantillon de données
    DE->>DE: Analyse la structure (colonnes, types, qualité)
    DE->>GIT: Crée le schéma YAML dans schemas/bronze/
    GIT-->>GCP: CI/CD déploie le schéma dans le bucket Schemas
    
    DE->>GIT: Écrit les transformations SQLX (Silver, Gold)
    DE->>GIT: Écrit les assertions Dataform (Quality Gates)
    GIT-->>GCP: CI/CD déploie le code Dataform
    
    ME->>GCP: Dépose le premier fichier dans Landing
    GCP->>GCP: Ingestion automatique → Bronze
    GCP->>GCP: Dataform exécution nocturne → Silver → Gold
    
    DE->>ME: Validation des résultats dans BigQuery / Looker
```

### 5.2. Conventions de Nommage des Fichiers

Pour que le service d'ingestion identifie automatiquement le schéma à appliquer, les fichiers doivent respecter une convention :

```
landing/<nom_schema>/<nom_fichier>.<extension>
```

| Exemple de Chemin | Schéma Détecté | Fichier de Contrat |
|:------------------|:---------------|:-------------------|
| `landing/energx_consos/export_2026-05-19.csv` | `energx_consos` | `schemas/bronze/energx_consos.yaml` |
| `landing/xforce_contrats/contrats_q1.jsonl` | `xforce_contrats` | `schemas/bronze/xforce_contrats.yaml` |
| `landing/referentiel_sites/sites_v3.csv` | `referentiel_sites` | `schemas/bronze/referentiel_sites.yaml` |

### 5.3. Stratégies de Chargement (Ingestion vs Transformation)

Il est crucial de distinguer comment la donnée brute entre dans le système (Ingestion), et comment elle est gérée dans le temps (Transformation).

**1. À l'Ingestion (Landing → Bronze via Cloud Run) :**
Le service d'ingestion ne fait aucune logique métier. Il se contente d'insérer les fichiers valides.
| Mode Cloud Run | Comportement | Quand l'utiliser |
|:---------------|:-------------|:-----------------|
| **Append** | Ajoute les nouvelles lignes à la table brute existante | Données incrémentales (consos quotidiennes, relevés horaires) |
| **Replace** | Écrase et remplace intégralement la table brute | Fichiers référentiels déposés manuellement (liste des sites, tarifs) |

**2. À la Transformation (Bronze → Silver via Dataform) :**
C'est ici que l'historisation complexe est gérée.
| Stratégie Dataform | Comportement | Quand l'utiliser |
|:-------------------|:-------------|:-----------------|
| **Incremental (SCD / Delta)** | Gère l'historisation (Slowly Changing Dimensions) via un `MERGE` SQL | Contrats, données CRM qui évoluent dans le temps |
| **Table (Full Refresh)** | Recalcule toute la table métier à chaque exécution | KPIs quotidiens simples, référentiels |

---

## 6. Focus POC : Sources Prioritaires

### 6.1. Périmètre Proposé pour le Pilote

D'après le cadrage initial, le POC se concentre sur **1 dataset** permettant de produire le **rapport cockpit RCF** :

```mermaid
graph TB
    subgraph "Sources POC (à confirmer)"
        E["EnergX<br/>Données techniques<br/>(consos/prod)"]
        X["XForce<br/>Données contrats<br/>& CRM"]
        REF["Référentiels<br/>Sites & nomenclatures"]
    end
    
    subgraph "Objectif POC"
        JOIN["🔗 ~20 jointures<br/>entre sources"]
        KPI["📐 20 à 40 mesures<br/>à calculer"]
        DASH["📊 1 Rapport<br/>Cockpit RCF"]
    end
    
    E --> JOIN
    X --> JOIN
    REF --> JOIN
    JOIN --> KPI
    KPI --> DASH
    
    style DASH fill:#F4BF46,color:#0b132b
    style JOIN fill:#208AAE,color:#fff
```

### 6.2. Questions Clés pour Chaque Source

**EnergX (Données Techniques)** :
- Quel format d'export est disponible (CSV, API, base directe) ?
- Quelles sont les colonnes principales (site_id, timestamp, valeur, unité) ?
- Quelle granularité temporelle (horaire, journalière, mensuelle) ?
- Un échantillon anonymisé est-il disponible ?

**XForce (Contrats & CRM)** :
- Comment extraire les données (export CSV depuis l'UI, API, extraction SQL) ?
- Quelles entités sont nécessaires pour le cockpit RCF (contrats, clients, sites) ?
- Y a-t-il des données sensibles (noms, adresses) nécessitant une pseudonymisation ?

**Référentiels (Sites, Nomenclatures)** :
- Existe-t-il un fichier Excel de référence des sites ?
- Quel est l'identifiant unique d'un site (code interne, adresse, coordonnées GPS) ?
- Qui est le propriétaire / mainteneur de ce référentiel ?

---

## 7. Synthèse & Actions de Sortie d'Atelier

### Livrables Attendus

| # | Livrable | Responsable | Deadline |
|:-:|:---------|:------------|:---------|
| 1 | Échantillon de données EnergX (anonymisé) | Métier / IT Client | S+1 |
| 2 | Échantillon de données XForce (anonymisé) | Métier / IT Client | S+1 |
| 3 | Fichier référentiel des sites | Métier Client | S+1 |
| 4 | Schémas YAML pour chaque source | Pyl.Tech | S+2 (après réception des échantillons) |
| 5 | Transformations SQLX (Silver + Gold) | Pyl.Tech | S+3 |
| 6 | Assertions Dataform (Quality Gates) | Pyl.Tech | S+3 |

### Questions Ouvertes

- **Accès aux données** : Qui peut fournir un export des systèmes EnergX et XForce ? Faut-il une demande formelle ?
- **Sensibilité des données** : Les échantillons contiennent-ils des données personnelles (RGPD) ? Si oui, prévoir une pseudonymisation avant l'export.
- **Clé de jointure** : Quel identifiant commun relie EnergX, XForce et les référentiels de sites ? (code site, numéro de contrat, etc.)
- **Définition des KPIs** : Quels sont les 5 premiers KPIs du cockpit RCF que nous devons calculer dans la couche Gold ?

---

*Ce document est un livrable Pyl.Tech. Il sera mis à jour au fil des ateliers.*

<div style="color: #208AAE; text-align: right; font-size: 0.9em; font-weight: bold;">
© Copyright 2026 Pyl.Tech
</div>
