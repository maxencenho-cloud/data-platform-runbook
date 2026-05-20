# Support de Cadrage : Sources de Données & Pipeline d'Ingestion

> **Date** : Mai 2026 | **Auteurs** : Équipe d'Architecture Pyl.Tech
> *Support technique pour l'Atelier 2 (Données & Ingestion).*

*Ce document se concentre sur l'identification des sources de données, leur structure, et la méthode de chargement. Il servira de référence aux équipes techniques tout au long du projet.*

*Objectif : Configurer les pipelines d'ingestion à partir des fichiers fournis par IDEX, et définir les règles de rejet (le "Circuit Breaker").*

---

## 1. Architecture d'Ingestion : Rappel du Modèle Validé

Pour mémoire, voici le flux technique validé lors de l'Atelier 1 :

```text
📥 Système Source (EnergX / XForce)
└── 📦 Landing GCS (Dépôt du fichier)
    └── ⚡ Ingestion Cloud Run (Validation par Contrats YAML)
        ├── Si Conforme (100%) ➔ 📊 Bronze (BigQuery) ➔ ⚙️ Silver (BigQuery) ➔ 🏆 Gold (BigQuery) ➔ 📊 Looker (BI)
        └── Si Non Conforme ➔ 🔴 Quarantaine (GCS) (Rejet global du fichier)
```

**Rappel du principe "All-or-Nothing" (Circuit Breaker)** : Chaque fichier est validé de bout en bout. Si une seule anomalie de structure ou de type est détectée, le fichier entier part en Quarantaine. Aucune donnée partielle ou corrompue n'entre dans l'entrepôt.

---

## 2. Cartographie des Sources de Données

Pour ce POC, nous nous concentrons sur les deux systèmes métiers centraux :

```text
🗂️ Sources de Données IDEX
├── 📊 EnergX (Système Technique)
│   ├── 🛠️ Données techniques : Spécifications et statuts des équipements.
│   ├── 📈 Consommations : Historiques et relevés d'énergie consommée.
│   └── 🔋 Productions : Mesures de l'énergie produite par les centrales.
└── 📝 XForce (CRM / Référentiel Contrats)
    ├── 🤝 Contrats : Tarifs, conditions d'engagement et renouvellements.
    └── 👥 CRM Clients : Fiches d'identité clients, comptes et interlocuteurs.
```

### 2.1. Spécifications des Sources

Les données seront extraites sous forme de fichiers plats (pas d'API prévue pour le moment).

| Source d'Origine | Nature du Système | Contenu Métier Principal | Format d'Extraction | Fréquence de Mise à Jour | Priorité Projet |
|:-------|:-----|:---------------|:---------------|:----------|:-------------|
| **EnergX** | Système technique | Consommations énergétiques, données de production, relevés compteurs | **CSV / XML / JSON** | Quotidien à horaire | **[Obligatoire]** |
| **XForce** | CRM / Référentiel Contrats | Données clients, contrats, périmètres géographiques, conditions | **CSV / XML / JSON** | Quotidien | **[Obligatoire]** |

---

## 3. Standardisation via Contrats de Données (Data Contracts)

Pour protéger la plateforme, chaque flux de données respecte un **Contrat de Données** (un fichier YAML). Il définit les colonnes, les types et les règles de validation. C'est notre garde-fou à l'ingestion.

### 3.1. Séquence de Validation

| Étape | Source / Acteur | Flux | Cible / Acteur | Action de Validation |
| :---: | :--- | :---: | :--- | :--- |
| **1** | Fichier d'Extraction | `→` | Service d'Ingestion | Réception du fichier brut dans l'espace de stockage temporaire (Landing Zone). |
| **2** | Service d'Ingestion | `→` | Contrat de Données (YAML) | Requête d'analyse pour charger les schémas de validation officiels. |
| **3** | Contrat de Données (YAML) | `←` | Service d'Ingestion | Retour des règles : noms des colonnes, types stricts, nullabilité et clés. |
| **4** | Service d'Ingestion | `↺` | Service d'Ingestion | **Validation Circuit Breaker** : Analyse ligne par ligne du fichier. |
| **5A** | Service d'Ingestion | `→` | Entrepôt BigQuery | **Cas 100% conforme** : Chargement immédiat et atomique dans la **Couche Bronze**. |
| **5B** | Service d'Ingestion | `→` | Zone de Quarantaine | **Cas non conforme** : Rejet global immédiat du fichier vers la **Quarantaine (Cloud Storage)**. |

### 3.2. Types de Données Supportés

Le service d'ingestion traduit les types du contrat vers BigQuery selon cette correspondance :

| Déclaration dans le Contrat (YAML) | Traduction Technique (BigQuery) | Exemple Concret |
|:----------|:-------------|:--------|
| `int` | `INTEGER` | `42` |
| `float` | `FLOAT` | `3.14159` |
| `str` | `STRING` | `"Réseau de Chaleur Urbain"` |
| `bool` | `BOOLEAN` | `true` ou `false` |
| `date` | `DATE` | `2026-01-15` *(Le format doit être précisé si différent de la norme ISO)* |
| `datetime` | `TIMESTAMP` | `2026-01-15T08:30:00Z` |

### 3.3. Fiche de Spécification Source (À remplir en atelier)

Pour chaque source, nous devons remplir cette fiche avec les experts métiers :

> **Fiche de Spécification : [NOM DU SYSTÈME SOURCE]**
>
> | Critère d'Analyse | Valeur / Réponse |
> |:--------|:--------|
> | Nom usuel de la source | |
> | Application ou Système d'origine | |
> | Format de l'extraction | CSV / XML / JSON |
> | Encodage du fichier | UTF-8 / ISO-8859-1 |
> | Caractère séparateur (si format CSV) | Point-virgule (`;`) / Virgule (`,`) |
> | Présence d'une ligne d'en-tête | Oui / Non |
> | Volumétrie moyenne par fichier | |
> | Modalité de dépôt sur le Cloud | Processus automatisé / Transfert manuel |

### 3.4. Prérequis Techniques (Point Bloquant Critique)

Ces éléments doivent absolument être fournis par IDEX pour que nous puissions démarrer les développements :

1. **Espace de Réception (Point de dépôt)** : Création et validation des espaces de stockage (Buckets Cloud Storage) de l'environnement GCP pour réceptionner les fichiers.
2. **Échantillons Représentatifs (Samples)** : Fourniture impérative d'un jeu de fichiers d'extractions représentatif (CSV, XML ou JSON) couvrant les systèmes EnergX et XForce. Ceci est obligatoire en l'absence de connectivité directe par API.
3. **Dictionnaire de Données** : Fourniture de la documentation métier des données afin de paramétrer les règles de rejet du Circuit Breaker (définition des champs strictement obligatoires, formatage des dates, identification des clés uniques).

---

## 4. Stratégie de Transformation (De la donnée brute à l'indicateur)

Nous utilisons le modèle "Medallion", orchestré par Dataform. La donnée traverse trois couches pour gagner en qualité et en valeur métier.

### 4.1. Opérations par Couche de Données

| Couche de Destination | Objectif du Traitement | Typologie d'Exemples Concrets |
|:-------|:-----------|:------------------|
| **Couche Bronze → Silver** | Nettoyage, standardisation technique, dédoublonnage, harmonisation des nomenclatures. | Conversion des dates locales en formats standards, suppression des enregistrements dupliqués via la clé primaire, normalisation des unités de mesure (conversion kW vers MW). |
| **Couche Silver → Gold** | Modélisation métier, jointures inter-systèmes, création d'indicateurs (KPIs). | Réconciliation des consommations EnergX avec les contrats XForce via l'identifiant du site, calcul du rendement énergétique global, agrégation des données par période fiscale. |

### 4.2. Grilles de Qualité (Quality Gates)

Chaque transition de couche est sécurisée par des tests automatisés appelés "Quality Gates" ou assertions. Si un test échoue, une alerte est déclenchée pour garantir la fiabilité des tableaux de bord finaux.

1. **Gate Technique (Avant l'entrée en Bronze)** : Validation du format du fichier, de son encodage et du respect strict du contrat de données. Géré par le service Python.
2. **Gate Structurelle (Passage Silver)** : Vérification de l'intégrité des données (absence de doublons, respect des intégrités référentielles, absence de valeurs nulles sur les champs critiques). Géré par Dataform.
3. **Gate Métier (Passage Gold)** : Validation de la vraisemblance fonctionnelle (ex: les rendements énergétiques doivent être logiquement compris entre 0% et 100%, aucune consommation ne peut être négative). Géré par Dataform.

---

## 5. Synthèse des Actions de Sortie d'Atelier

### 5.1. Livrables et Responsabilités

| Numéro | Description du Livrable | Entité Responsable | Échéance |
|:-:|:---------|:------------|:---------|
| 1 | Échantillon de données EnergX (strictement anonymisé) | Métier / IT IDEX | Semaine + 1 |
| 2 | Échantillon de données XForce (strictement anonymisé) | Métier / IT IDEX | Semaine + 1 |
| 3 | Documentation ou dictionnaire des données | Métier IDEX | Semaine + 1 |
| 4 | Contrats de Données (Schémas YAML) pour chaque source | Architecte Pyl.Tech | Semaine + 2 |
| 5 | Code des transformations SQLX (Silver et Gold) | Data Engineer Pyl.Tech | Semaine + 3 |

### 5.2. Sujets à Documenter (Questions Ouvertes)

- **Gouvernance des Exports** : Quelles entités ou processus sont en charge de générer et déposer les extractions des systèmes EnergX et XForce ?
- **Conformité RGPD** : Les échantillons ou les données finales comportent-ils des Informations Personnellement Identifiables (PII) ? Dans l'affirmative, une stratégie de pseudonymisation doit être définie préalablement à l'export.
- **Réconciliation Métier** : Quel est l'identifiant pivot (Clé primaire) permettant de joindre de manière déterministe les relevés d'EnergX avec les contrats de XForce (ex: Code Site, Numéro de Compteur, Référence Contrat) ?
- **Pilotage de la Valeur** : Quels sont les 3 à 5 indicateurs de performance (KPIs) prioritaires qui doivent être restitués dans la couche Gold pour démontrer le succès du projet ?

---

*Ce document de conception est un livrable officiel Pyl.Tech. Il est sujet à des révisions itératives à mesure de l'avancement des phases de spécification.*

<div style="color: #208AAE; text-align: right; font-size: 0.9em; font-weight: bold; margin-top: 40px;">
Document Confidentiel - © Copyright 2026 Pyl.Tech
</div>
