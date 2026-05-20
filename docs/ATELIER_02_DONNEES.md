# Support de Cadrage : Sources de Données & Pipeline d'Ingestion

> **Date** : Mai 2026 | **Auteurs** : Équipe d'Architecture Pyl.Tech
> *Support technique pour l'Atelier 2 (Données & Ingestion).*

*Ce document se concentre sur l'identification des sources de données, leur structure, et la méthode de chargement. Il servira de référence aux équipes techniques tout au long du projet.*

*Objectif : Configurer les pipelines d'ingestion à partir des fichiers fournis par IDEX, et définir les règles de rejet (le "Circuit Breaker").*

---

## 1. Architecture d'Ingestion : Rappel du Modèle Validé

Pour mémoire, voici le flux technique validé lors de l'Atelier 1 :

<table style="width: 100%; border-collapse: collapse; font-family: 'Poppins', sans-serif; font-size: 9.5pt; margin: 20px 0; border: 1px solid #eeeeee; text-align: center;">
  <tr style="background-color: #0b132b; color: #ffffff; font-weight: bold;">
    <th colspan="7" style="padding: 10px; border: 1px solid #eeeeee;">Flux de Données de Bout en Bout</th>
  </tr>
  <tr style="vertical-align: middle;">
    <!-- Step 1 -->
    <td style="width: 22%; padding: 12px; border: 1px solid #eeeeee; background-color: #ffffff;">
      <div style="font-weight: bold; color: #0b132b;">Système Source</div>
      <div style="font-size: 8pt; color: #4f4f4f; margin-top: 4px;">EnergX / XForce<br/>(CSV / XML / JSON)</div>
    </td>
    <!-- Arrow -->
    <td style="width: 4%; padding: 4px; border: 1px solid #eeeeee; background-color: #fdfaf2; color: #208AAE; font-weight: bold; font-size: 12pt;">
      &rarr;
    </td>
    <!-- Step 2 -->
    <td style="width: 22%; padding: 12px; border: 1px solid #eeeeee; background-color: #ffffff;">
      <div style="font-weight: bold; color: #0b132b;">Zone Landing</div>
      <div style="font-size: 8pt; color: #4f4f4f; margin-top: 4px;">Cloud Storage<br/>(Dépôt initial)</div>
    </td>
    <!-- Arrow -->
    <td style="width: 4%; padding: 4px; border: 1px solid #eeeeee; background-color: #fdfaf2; color: #208AAE; font-weight: bold; font-size: 12pt;">
      &rarr;
    </td>
    <!-- Step 3 (Validation) -->
    <td style="width: 26%; padding: 12px; border: 1px solid #eeeeee; background-color: #ffffff;">
      <div style="font-weight: bold; color: #0b132b;">Ingestion Cloud Run</div>
      <div style="font-size: 8pt; color: #4f4f4f; margin-top: 4px; font-style: italic;">Validation par Data Contracts</div>
      
      <!-- Rejection split -->
      <table style="width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 8pt;">
        <tr>
          <td style="background-color: #138636; color: #ffffff; padding: 4px; border-radius: 2px; width: 48%; font-weight: bold;">Valide &darr;</td>
          <td style="width: 4%;"></td>
          <td style="background-color: #C91432; color: #ffffff; padding: 4px; border-radius: 2px; width: 48%; font-weight: bold;">Erreur &rarr;</td>
        </tr>
        <tr>
          <td></td>
          <td></td>
          <td style="padding: 2px; background-color: #eeeeee; color: #C91432; font-weight: bold;">Quarantaine</td>
        </tr>
      </table>
    </td>
    <!-- Arrow -->
    <td style="width: 4%; padding: 4px; border: 1px solid #eeeeee; background-color: #fdfaf2; color: #208AAE; font-weight: bold; font-size: 12pt;">
      &rarr;
    </td>
    <!-- Step 4 (Medallion & Looker) -->
    <td style="width: 18%; padding: 12px; border: 1px solid #eeeeee; background-color: #ffffff;">
      <table style="width: 100%; border-collapse: collapse; font-size: 8.5pt; text-align: left;">
        <tr>
          <td style="background-color: #cd7f32; color: #ffffff; padding: 4px; font-weight: bold; text-align: center; border-radius: 2px;">Bronze (Brute)</td>
        </tr>
        <tr><td style="text-align: center; color: #208AAE; padding: 1px;">&darr;</td></tr>
        <tr>
          <td style="background-color: #c0c0c0; color: #0b132b; padding: 4px; font-weight: bold; text-align: center; border-radius: 2px;">Silver (Propre)</td>
        </tr>
        <tr><td style="text-align: center; color: #208AAE; padding: 1px;">&darr;</td></tr>
        <tr>
          <td style="background-color: #F4BF46; color: #0b132b; padding: 4px; font-weight: bold; text-align: center; border-radius: 2px;">Gold (KPIs)</td>
        </tr>
        <tr><td style="text-align: center; color: #208AAE; padding: 1px;">&darr;</td></tr>
        <tr>
          <td style="background-color: #208AAE; color: #ffffff; padding: 4px; font-weight: bold; text-align: center; border-radius: 2px;">Looker (BI)</td>
        </tr>
      </table>
    </td>
  </tr>
</table>

**Rappel du principe "All-or-Nothing" (Circuit Breaker)** : Chaque fichier est validé de bout en bout. Si une seule anomalie de structure ou de type est détectée, le fichier entier part en Quarantaine. Aucune donnée partielle ou corrompue n'entre dans l'entrepôt.

---

## 2. Cartographie des Sources de Données

Pour ce POC, nous nous concentrons sur les deux systèmes métiers centraux :

<table style="width: 100%; border-collapse: collapse; font-family: 'Poppins', sans-serif; font-size: 10pt; margin: 20px 0; border: 1px solid #eeeeee;">
  <tr style="background-color: #0b132b; color: #ffffff; font-weight: bold; text-align: center;">
    <th colspan="2" style="padding: 10px; border: 1px solid #eeeeee;">Cartographie des Sources de Données IDEX</th>
  </tr>
  <tr style="vertical-align: top;">
    <!-- System 1: EnergX -->
    <td style="width: 50%; padding: 15px; border: 1px solid #eeeeee; background-color: #ffffff;">
      <div style="padding: 8px; background-color: #F4BF46; color: #0b132b; font-weight: bold; text-align: center; border-radius: 4px; margin-bottom: 10px;">
        EnergX (Système Technique)
      </div>
      <div style="color: #4f4f4f;">
        <ul style="margin: 0; padding-left: 20px; list-style-type: square;">
          <li style="margin-bottom: 6px;"><b>Données techniques</b> : Spécifications et statuts des équipements.</li>
          <li style="margin-bottom: 6px;"><b>Consommations</b> : Historiques et relevés d'énergie consommée.</li>
          <li style="margin-bottom: 6px;"><b>Productions</b> : Mesures de l'énergie produite par les centrales.</li>
        </ul>
      </div>
    </td>
    <!-- System 2: XForce -->
    <td style="width: 50%; padding: 15px; border: 1px solid #eeeeee; background-color: #ffffff;">
      <div style="padding: 8px; background-color: #0d2149; color: #ffffff; font-weight: bold; text-align: center; border-radius: 4px; margin-bottom: 10px;">
        XForce (CRM / Référentiel Contrats)
      </div>
      <div style="color: #4f4f4f;">
        <ul style="margin: 0; padding-left: 20px; list-style-type: square;">
          <li style="margin-bottom: 6px;"><b>Contrats</b> : Tarifs, conditions d'engagement et renouvellements.</li>
          <li style="margin-bottom: 6px;"><b>CRM Clients</b> : Fiches d'identité clients, comptes et interlocuteurs.</li>
        </ul>
      </div>
    </td>
  </tr>
</table>

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

<table style="width: 100%; border-collapse: collapse; font-family: 'Poppins', sans-serif; font-size: 10pt; margin: 20px 0; border: 1px solid #eeeeee;">
  <thead>
    <tr style="background-color: #0b132b; color: #ffffff; font-weight: bold; text-align: left;">
      <th style="padding: 10px; border: 1px solid #eeeeee; width: 8%; text-align: center;">Étape</th>
      <th style="padding: 10px; border: 1px solid #eeeeee; width: 25%;">Source / Acteur</th>
      <th style="padding: 10px; border: 1px solid #eeeeee; width: 10%; text-align: center;">Flux</th>
      <th style="padding: 10px; border: 1px solid #eeeeee; width: 25%;">Cible / Acteur</th>
      <th style="padding: 10px; border: 1px solid #eeeeee;">Action de Validation</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="padding: 10px; border: 1px solid #eeeeee; text-align: center; font-weight: bold; background-color: #eeeeee;">1</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; font-weight: bold; color: #0b132b;">Fichier d'Extraction</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; text-align: center; color: #208AAE; font-weight: bold;">&rarr;</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; font-weight: bold; color: #0b132b;">Service d'Ingestion</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; color: #4f4f4f;">Réception du fichier brut dans l'espace de stockage temporaire (Landing Zone).</td>
    </tr>
    <tr style="background-color: #fdfaf2;">
      <td style="padding: 10px; border: 1px solid #eeeeee; text-align: center; font-weight: bold; background-color: #F4BF46; color: #0b132b;">2</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; font-weight: bold; color: #0b132b;">Service d'Ingestion</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; text-align: center; color: #F4BF46; font-weight: bold;">&rarr;</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; font-weight: bold; color: #0b132b;">Contrat de Données (YAML)</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; color: #4f4f4f;">Requête d'analyse pour charger les schémas de validation officiels.</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #eeeeee; text-align: center; font-weight: bold; background-color: #eeeeee;">3</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; font-weight: bold; color: #0b132b;">Contrat de Données (YAML)</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; text-align: center; color: #208AAE; font-weight: bold;">&larr;</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; font-weight: bold; color: #0b132b;">Service d'Ingestion</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; color: #4f4f4f;">Retour des règles : noms des colonnes, types stricts, nullabilité et clés.</td>
    </tr>
    <tr style="background-color: #fdfaf2;">
      <td style="padding: 10px; border: 1px solid #eeeeee; text-align: center; font-weight: bold; background-color: #F4BF46; color: #0b132b;">4</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; font-weight: bold; color: #0b132b;">Service d'Ingestion</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; text-align: center; color: #F4BF46; font-weight: bold;">&olarr;</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; font-weight: bold; color: #0b132b;">Service d'Ingestion</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; color: #4f4f4f;"><b>Validation Circuit Breaker</b> : Analyse ligne par ligne du fichier.</td>
    </tr>
    <!-- Scenario A -->
    <tr style="background-color: #edf7ed;">
      <td style="padding: 10px; border: 1px solid #eeeeee; text-align: center; font-weight: bold; background-color: #138636; color: #ffffff;">5A</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; font-weight: bold; color: #138636;">Service d'Ingestion</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; text-align: center; color: #138636; font-weight: bold;">&rarr;</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; font-weight: bold; color: #0b132b;">Entrepôt BigQuery</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; color: #138636;"><b>Cas 100% conforme</b> : Chargement immédiat et atomique dans la <b>Couche Bronze</b>.</td>
    </tr>
    <!-- Scenario B -->
    <tr style="background-color: #fdf2f2;">
      <td style="padding: 10px; border: 1px solid #eeeeee; text-align: center; font-weight: bold; background-color: #C91432; color: #ffffff;">5B</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; font-weight: bold; color: #C91432;">Service d'Ingestion</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; text-align: center; color: #C91432; font-weight: bold;">&rarr;</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; font-weight: bold; color: #0b132b;">Zone de Quarantaine</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; color: #C91432;"><b>Cas non conforme</b> : Rejet global immédiat du fichier vers la <b>Quarantaine (Cloud Storage)</b>.</td>
    </tr>
  </tbody>
</table>

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
