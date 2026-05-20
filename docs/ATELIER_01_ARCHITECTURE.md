# Support de Cadrage : Architecture GCP, Landing Zone & Identités

> **Date** : Mai 2026 | **Auteurs** : Équipe d'Architecture Pyl.Tech
> *Support technique pour l'Atelier 1 (Architecture & Socle).*

*Ce document de référence synthétise les choix architecturaux et les prérequis techniques liés au déploiement de la Data Platform. Il est conçu pour être autoporteur et consultable a posteriori par l'ensemble des parties prenantes (architectes, administrateurs réseau, chefs de projet).*

---

## 1. Gouvernance et Fondations Cloud

L'objectif est de déployer le socle "Secure by Design" et de préparer la gestion des identités. Cela posera des bases saines, notamment pour la sécurité du futur Agent IA.

### 1.1. Modèle d'Organisation et de Projets (Environnement POC)

GCP structure les ressources de manière hiérarchique. L'objectif de cette phase est de **prouver la valeur métier** sur un périmètre restreint (POC). 

La plateforme s'exécutera dans des Projets GCP temporaires, isolés de votre production actuelle. Si le projet se pérennise, une véritable "Landing Zone" d'entreprise sera définie avec vos équipes sécurité, et nous pourrons tout y redéployer proprement. 

Cependant, pour démontrer dès aujourd'hui les avantages d'une plateforme industrielle, nous utilisons d'emblée l'automatisation (Terraform) avec deux environnements de travail : **Dev** et **Prod**.

<table style="width: 100%; border-collapse: collapse; font-family: 'Poppins', sans-serif; font-size: 10pt; margin: 20px 0; border: 1px solid #eeeeee;">
  <tr style="background-color: #0b132b; color: #ffffff; font-weight: bold; text-align: center;">
    <th colspan="4" style="padding: 12px; border: 1px solid #eeeeee;">Organisation GCP (votre-domaine.com)</th>
  </tr>
  <tr style="text-align: center; font-weight: bold;">
    <td colspan="2" style="width: 50%; padding: 10px; background-color: #eeeeee; border: 1px solid #eeeeee; color: #0b132b;">Dossier : Non-Production (&darr;)</td>
    <td colspan="2" style="width: 50%; padding: 10px; background-color: #eeeeee; border: 1px solid #eeeeee; color: #0b132b;">Dossier : Production (&darr;)</td>
  </tr>
  <tr style="text-align: center;">
    <td colspan="2" style="padding: 10px; background-color: #F4BF46; color: #0b132b; font-weight: bold; border: 1px solid #eeeeee;">Projet GCP : idex-data-dev</td>
    <td colspan="2" style="padding: 10px; background-color: #0d2149; color: #ffffff; font-weight: bold; border: 1px solid #eeeeee;">Projet GCP : idex-data-prod</td>
  </tr>
  <tr style="vertical-align: top;">
    <td colspan="2" style="padding: 12px; background-color: #ffffff; border: 1px solid #eeeeee; color: #4f4f4f;">
      <div style="font-weight: bold; color: #0b132b; margin-bottom: 6px; text-align: center;">Ressources POC & Dev :</div>
      <ul style="margin: 0; padding-left: 20px; list-style-type: square;">
        <li><b>Cloud Storage</b> (Stockage brut)</li>
        <li><b>BigQuery</b> (Entrepôt de données)</li>
        <li><b>Cloud Run</b> (Calcul Serverless)</li>
        <li><b>Dataform</b> (Orchestration SQL)</li>
      </ul>
    </td>
    <td colspan="2" style="padding: 12px; background-color: #ffffff; border: 1px solid #eeeeee; color: #4f4f4f;">
      <div style="font-weight: bold; color: #0b132b; margin-bottom: 6px; text-align: center;">Ressources Cibles Prod :</div>
      <ul style="margin: 0; padding-left: 20px; list-style-type: square;">
        <li><b>Cloud Storage</b> (Production)</li>
        <li><b>BigQuery</b> (Production)</li>
        <li><b>Cloud Run</b> (Production)</li>
        <li><b>Dataform</b> (Production)</li>
      </ul>
    </td>
  </tr>
</table>

Votre **Organisation GCP** existe déjà et est nativement liée à votre annuaire Google Workspace. Cela va grandement faciliter la gestion des accès.

**Actions Requises :**
1. **Vérifier l'Organisation** : Connectez-vous sur `console.cloud.google.com`. Votre domaine doit apparaître en haut à gauche.
2. **Créer les 2 Projets GCP** : `idex-data-dev` et `idex-data-prod`.
3. **Activer les APIs GCP** : `bigquery.googleapis.com`, `run.googleapis.com`, `pubsub.googleapis.com`, `storage.googleapis.com`, `dataform.googleapis.com`, `secretmanager.googleapis.com`.
4. **Instance Looker** : Validation et création de l'instance de test Looker.

---

## 2. Gestion des Identités et des Accès (IAM)

Nous séparons strictement les accès humains (Groupes) des accès machines (Comptes de Service), toujours sur le principe du moindre privilège.

### 2.1. Matrice des Rôles et Autorisations (RBAC)

Le tableau ci-dessous formalise l'affectation des droits sur les ressources GCP :

| Type d'Identité | Rôle Fonctionnel | Mode d'Authentification | Périmètre d'Accès Autorisé |
|:---|:---|:---|:---|
| **Humain** | Data Engineer | SSO Google Workspace (via Groupe) | **BigQuery** (Lecture/Écriture), **Cloud Storage** |
| **Humain** | Data Analyst | SSO Google Workspace (via Groupe) | **BigQuery** (Lecture et Écriture limitées aux Data Marts) |
| **Humain** | Utilisateur Métier | SSO Google Workspace (via Groupe) | **BigQuery** (Lecture seule sur les indicateurs agrégés) |
| **Service (Machine)** | `ingestion-sa` (Cloud Run) | Compte de Service Natif GCP | **Cloud Storage** (Processing), **BigQuery** (Bronze) |
| **Service (Machine)** | `terraform-sa` (CI/CD) | Workload Identity Federation | **Toutes ressources** (Déploiement Infrastructure as Code) |
| **Service (Machine)** | `dataform-sa` | Compte de Service Natif GCP | **BigQuery** (Exécution des transformations SQLX) |

### 2.2. Administration des Utilisateurs Humains

Il faut définir comment l'équipe PylTech accèdera aux ressources. Puisque nous sommes tous sur Google Workspace, 3 options s'offrent à nous :

1. **Ajout direct de nos emails** (`@pyl.tech`) dans vos groupes Workspace IDEX (Solution recommandée et la plus simple).
2. **Whitelisting du domaine** `@pyl.tech` sur votre tenant GCP (Si l'Option 1 est bloquée par vos règles de sécurité).
3. **Création d'identités externes IDEX** pour les consultants (ex: `consultant.ext@idex.com`). C'est l'approche la plus lourde (gestion de licences).

Durant la phase de développement, les équipes de réalisation nécessitent un niveau d'accès `Owner` (Propriétaire) sur le projet `dev` afin de garantir la vélocité. Le projet `prod` appliquera quant à lui une approche stricte de "Least Privilege".

**Actions Requises :**
1. Création de trois groupes de sécurité dans l'annuaire Google Workspace :
   - `gcp-data-engineers@votre-domaine.com`
   - `gcp-data-analysts@votre-domaine.com`
   - `gcp-business-users@votre-domaine.com`
2. Affectation de l'équipe Pyl.Tech au groupe "Engineers" selon l'option d'intégration retenue.

### 2.3. Sécurité des Comptes de Service

Ces comptes applicatifs sont créés automatiquement par notre code Terraform. Ils ne partagent jamais leurs droits entre eux.

---

## 3. Sécurité des Déploiements : Workload Identity (WIF)

**Règle d'or : Aucune clé JSON statique ne sera exportée ni stockée.**

Les clés statiques sont la principale cause de failles de sécurité dans le Cloud. Pour sécuriser le pipeline CI/CD, nous utilisons **Workload Identity Federation (WIF)**. 

Ce standard permet à votre outil Git de s'authentifier auprès de GCP de manière sécurisée et éphémère, sans utiliser de mot de passe.

<table style="width: 100%; border-collapse: collapse; font-family: 'Poppins', sans-serif; font-size: 10pt; margin: 20px 0; border: 1px solid #eeeeee;">
  <thead>
    <tr style="background-color: #0b132b; color: #ffffff; font-weight: bold; text-align: left;">
      <th style="padding: 10px; border: 1px solid #eeeeee; width: 8%; text-align: center;">Étape</th>
      <th style="padding: 10px; border: 1px solid #eeeeee; width: 25%;">Émetteur</th>
      <th style="padding: 10px; border: 1px solid #eeeeee; width: 10%; text-align: center;">Flux</th>
      <th style="padding: 10px; border: 1px solid #eeeeee; width: 25%;">Destinataire</th>
      <th style="padding: 10px; border: 1px solid #eeeeee;">Description / Action de Sécurité</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="padding: 10px; border: 1px solid #eeeeee; text-align: center; font-weight: bold; background-color: #eeeeee;">1</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; font-weight: bold; color: #0b132b;">Plateforme Git (Pipeline CI/CD)</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; text-align: center; color: #208AAE; font-weight: bold;">&rarr;</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; font-weight: bold; color: #0b132b;">Workload Identity Pool (GCP)</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; color: #4f4f4f;">Présentation d'un jeton OIDC (courte durée) généré dynamiquement par le runner Git.</td>
    </tr>
    <tr style="background-color: #fdfaf2;">
      <td style="padding: 10px; border: 1px solid #eeeeee; text-align: center; font-weight: bold; background-color: #F4BF46; color: #0b132b;">2</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; font-weight: bold; color: #0b132b;">Workload Identity Pool (GCP)</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; text-align: center; color: #F4BF46; font-weight: bold;">&olarr;</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; font-weight: bold; color: #0b132b;">Workload Identity Pool (GCP)</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; color: #4f4f4f;"><b>Auto-vérification</b> : Contrôle de la signature cryptographique du jeton et validation de l'identité du dépôt source.</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #eeeeee; text-align: center; font-weight: bold; background-color: #eeeeee;">3</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; font-weight: bold; color: #0b132b;">Workload Identity Pool (GCP)</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; text-align: center; color: #208AAE; font-weight: bold;">&rarr;</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; font-weight: bold; color: #0b132b;">Ressources GCP cibles</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; color: #4f4f4f;">Émission d'un token d'accès temporaire lié au Service Account Terraform (valide 1h max).</td>
    </tr>
    <tr style="background-color: #fdfaf2;">
      <td style="padding: 10px; border: 1px solid #eeeeee; text-align: center; font-weight: bold; background-color: #F4BF46; color: #0b132b;">4</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; font-weight: bold; color: #0b132b;">Plateforme Git (Pipeline CI/CD)</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; text-align: center; color: #F4BF46; font-weight: bold;">&rarr;</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; font-weight: bold; color: #0b132b;">Ressources GCP cibles</td>
      <td style="padding: 10px; border: 1px solid #eeeeee; color: #4f4f4f;">Exécution du déploiement via <code>terraform apply</code> avec l'identité temporaire validée.</td>
    </tr>
    <tr style="background-color: #0b132b; color: #ffffff;">
      <td colspan="5" style="padding: 10px; border: 1px solid #eeeeee; text-align: center; font-style: italic;">
        💡 <b>Note de Sécurité</b> : Le token expire automatiquement après 1 heure maximum. Aucun secret persistant n'existe.
      </td>
    </tr>
  </tbody>
</table>

**Actions Requises :**
1. Validation de l'outil de versioning (GitLab, GitHub, etc.) qui hébergera le code source.
2. Configuration conjointe du `Workload Identity Pool` sur GCP pour n'approuver que les requêtes provenant spécifiquement de ce dépôt autorisé.

---

## 4. Architecture Logique de la Plateforme

L'architecture est découpée en deux flux asynchrones et découplés : l'Ingestion (Event-Driven) et la Transformation (Batch Medallion).

<table style="width: 100%; border-collapse: collapse; font-family: 'Poppins', sans-serif; font-size: 9.5pt; margin: 20px 0; border: 1px solid #eeeeee;">
  <tr style="background-color: #0b132b; color: #ffffff; font-weight: bold; text-align: center;">
    <th style="width: 45%; padding: 12px; border: 1px solid #eeeeee;">1. Ingestion Event-Driven</th>
    <th style="width: 10%; padding: 12px; border: 1px solid #eeeeee;">Flux</th>
    <th style="width: 45%; padding: 12px; border: 1px solid #eeeeee;">2. Transformation Batch & 3. Restitution</th>
  </tr>
  <tr style="vertical-align: top;">
    <!-- Column 1: Ingestion -->
    <td style="padding: 12px; border: 1px solid #eeeeee; background-color: #ffffff;">
      <table style="width: 100%; border-collapse: collapse;">
        <tr>
          <td style="padding: 8px; background-color: #eeeeee; border: 1px solid #cccccc; border-radius: 4px; text-align: center; font-weight: bold; color: #0b132b;">Fichiers Sources</td>
        </tr>
        <tr><td style="text-align: center; color: #208AAE; padding: 4px;">&darr; (Dépôt)</td></tr>
        <tr>
          <td style="padding: 8px; background-color: #eeeeee; border: 1px solid #cccccc; border-radius: 4px; text-align: center; color: #0b132b;">
            <b>Zone Landing</b><br/><small>(Cloud Storage)</small>
          </td>
        </tr>
        <tr><td style="text-align: center; color: #208AAE; padding: 4px;">&darr; (Événement Pub/Sub)</td></tr>
        <tr>
          <td style="padding: 8px; background-color: #0d2149; border: 1px solid #0d2149; border-radius: 4px; text-align: center; color: #ffffff;">
            <b>Service d'Ingestion</b><br/><small>(Cloud Run)</small>
          </td>
        </tr>
        <tr><td style="text-align: center; color: #208AAE; padding: 4px;">&darr; (Validation du Contrat)</td></tr>
        <tr>
          <td>
            <table style="width: 100%; border-collapse: collapse;">
              <tr>
                <td style="width: 48%; padding: 8px; background-color: #138636; border: 1px solid #138636; border-radius: 4px; text-align: center; color: #ffffff; font-weight: bold;">
                  Validation OK &rarr;<br/><span style="font-size: 8pt; font-weight: normal;">Zone Staging & Bronze (BigQuery)</span>
                </td>
                <td style="width: 4%;"></td>
                <td style="width: 48%; padding: 8px; background-color: #C91432; border: 1px solid #C91432; border-radius: 4px; text-align: center; color: #ffffff; font-weight: bold;">
                  Validation KO &rarr;<br/><span style="font-size: 8pt; font-weight: normal;">Zone Quarantaine (Cloud Storage)</span>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </td>
    <!-- Column 2: Transition Arrow -->
    <td style="padding: 12px; border: 1px solid #eeeeee; background-color: #fdfaf2; text-align: center; vertical-align: middle; font-weight: bold; color: #208AAE;">
      <div style="font-size: 16pt;">&rArr;</div>
      <div style="font-size: 8pt; color: #4f4f4f; margin-top: 5px;">Chargement Bronze</div>
    </td>
    <!-- Column 3: Transformation & Restitution -->
    <td style="padding: 12px; border: 1px solid #eeeeee; background-color: #ffffff;">
      <table style="width: 100%; border-collapse: collapse;">
        <tr>
          <td style="padding: 8px; background-color: #cd7f32; border: 1px solid #cd7f32; border-radius: 4px; text-align: center; color: #ffffff; font-weight: bold;">
            Couche Bronze (BigQuery)<br/><small>Données brutes historisées</small>
          </td>
        </tr>
        <tr><td style="text-align: center; color: #208AAE; padding: 4px;">&darr; (Orchestration Dataform)</td></tr>
        <tr>
          <td style="padding: 8px; background-color: #c0c0c0; border: 1px solid #999999; border-radius: 4px; text-align: center; color: #0b132b; font-weight: bold;">
            Couche Silver (BigQuery)<br/><small>Nettoyée, typée et dédupliquée</small>
          </td>
        </tr>
        <tr><td style="text-align: center; color: #208AAE; padding: 4px;">&darr; (Agrégation Métier)</td></tr>
        <tr>
          <td style="padding: 8px; background-color: #F4BF46; border: 1px solid #F4BF46; border-radius: 4px; text-align: center; color: #0b132b; font-weight: bold;">
            Couche Gold (BigQuery)<br/><small>Indicateurs agrégés (Data Marts)</small>
          </td>
        </tr>
        <tr><td style="text-align: center; color: #208AAE; padding: 4px;">&darr; (Visualisation)</td></tr>
        <tr>
          <td style="padding: 8px; background-color: #208AAE; border: 1px solid #208AAE; border-radius: 4px; text-align: center; color: #ffffff; font-weight: bold;">
            Looker (BI Platform)<br/><small>Tableaux de bord & Reporting</small>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>

### 4.1. Flux d'Ingestion ("Circuit Breaker")

Dès qu'un fichier source est déposé, l'ingestion démarre. La règle du "All-or-Nothing" s'applique :

1. La réception d'un fichier déclenche Pub/Sub.
2. Cloud Run valide strictement le fichier vis-à-vis de son contrat (Schéma YAML).
3. **Tout ou rien** : Si le fichier a une seule erreur, tout le fichier part en Quarantaine. S'il est 100% valide, il part en Bronze (BigQuery). L'entrepôt n'est jamais pollué par des données partielles.

### 4.2. Transformation (Medallion)

Dataform orchestre la transformation de la donnée brute en indicateurs métiers :
- **Bronze** : Donnée brute, historisée.
- **Silver** : Donnée nettoyée, typée, dédupliquée.
- **Gold** : Donnée agrégée (KPIs, Data Marts) pour Looker.

---

## 5. Standards d'Ingénierie (Infrastructure as Code)

L'intégralité du socle technique (Réseau, Stockage, IAM, Traitements) est provisionnée via du code Terraform.

<table style="width: 100%; border-collapse: collapse; font-family: 'Poppins', sans-serif; font-size: 10pt; margin: 20px 0; border: 1px solid #eeeeee;">
  <tr style="background-color: #0b132b; color: #ffffff; font-weight: bold; text-align: center;">
    <th colspan="3" style="padding: 10px; border: 1px solid #eeeeee;">Architecture de l'Infrastructure as Code (Terraform)</th>
  </tr>
  <tr style="vertical-align: middle; text-align: center;">
    <!-- Inputs / Config -->
    <td style="width: 30%; padding: 15px; border: 1px solid #eeeeee; background-color: #fdfaf2;">
      <div style="font-weight: bold; color: #0b132b;">1. Paramètres par Env</div>
      <div style="margin-top: 8px; padding: 10px; background-color: #ffffff; border: 1px dashed #F4BF46; border-radius: 4px;">
        <code>config.dev.yaml</code><br/>
        <code>config.prod.yaml</code>
      </div>
      <small style="display: block; margin-top: 8px; color: #4f4f4f;">Définit les variables propres à chaque environnement.</small>
    </td>
    <!-- Arrow -->
    <td style="width: 8%; padding: 10px; border: 1px solid #eeeeee; background-color: #ffffff; font-size: 14pt; color: #208AAE; font-weight: bold;">
      &rarr;
    </td>
    <!-- Main Orchestration -->
    <td style="width: 62%; padding: 15px; border: 1px solid #eeeeee; background-color: #ffffff;">
      <div style="font-weight: bold; color: #0b132b; margin-bottom: 10px;">2. Orchestration Principal (<code>main.tf</code>)</div>
      <div style="background-color: #0b132b; color: #ffffff; padding: 10px; border-radius: 4px; font-weight: bold; margin-bottom: 10px;">
        Point d'entrée : Modules Terraform instanciés
      </div>
      <div style="font-size: 12pt; color: #208AAE; font-weight: bold; margin-bottom: 8px;">&darr;</div>
      <div style="font-weight: bold; color: #0b132b; margin-bottom: 6px;">3. Modules Réutilisables de Pyl.Tech :</div>
      <table style="width: 100%; border-collapse: collapse; font-size: 9pt;">
        <tr>
          <td style="padding: 6px; border: 1px solid #eeeeee; background-color: #eeeeee; text-align: center; width: 20%; color: #0b132b; font-weight: bold;">storage</td>
          <td style="padding: 6px; border: 1px solid #eeeeee; background-color: #eeeeee; text-align: center; width: 20%; color: #0b132b; font-weight: bold;">bigquery</td>
          <td style="padding: 6px; border: 1px solid #eeeeee; background-color: #eeeeee; text-align: center; width: 20%; color: #0b132b; font-weight: bold;">ingestion</td>
          <td style="padding: 6px; border: 1px solid #eeeeee; background-color: #eeeeee; text-align: center; width: 20%; color: #0b132b; font-weight: bold;">dataform</td>
          <td style="padding: 6px; border: 1px solid #eeeeee; background-color: #eeeeee; text-align: center; width: 20%; color: #0b132b; font-weight: bold;">monitoring</td>
        </tr>
      </table>
    </td>
  </tr>
</table>

Cette approche déclarative assure :
- **L'audits de sécurité continus** : Le code est analysé (via `tfsec`) avant chaque déploiement.
- **La reproductibilité** : L'environnement peut être recréé ou dupliqué (pour de nouveaux environnements) avec une fiabilité totale.

---

## 6. Stratégie d'Observabilité et d'Alerting

L'environnement intègre une supervision proactive via la suite Google Cloud Operations (Logging et Monitoring) afin de détecter et de qualifier les anomalies techniques ou fonctionnelles.

<table style="width: 100%; border-collapse: collapse; font-family: 'Poppins', sans-serif; font-size: 10pt; margin: 20px 0; border: 1px solid #eeeeee;">
  <tr style="background-color: #0b132b; color: #ffffff; font-weight: bold; text-align: center;">
    <th style="width: 33%; padding: 10px; border: 1px solid #eeeeee;">1. Sources & Logs</th>
    <th style="width: 34%; padding: 10px; border: 1px solid #eeeeee;">2. Centralisation & Audit</th>
    <th style="width: 33%; padding: 10px; border: 1px solid #eeeeee;">3. Alerting & Alertes Critiques</th>
  </tr>
  <tr style="vertical-align: top;">
    <!-- Column 1 -->
    <td style="padding: 12px; border: 1px solid #eeeeee; background-color: #ffffff;">
      <div style="margin-bottom: 10px; padding: 8px; background-color: #eeeeee; border-left: 4px solid #0d2149; border-radius: 2px;">
        <b>Logs Cloud Run</b><br/>
        <small style="color: #4f4f4f;">Traces techniques et fonctionnelles d'ingestion.</small>
      </div>
      <div style="padding: 8px; background-color: #eeeeee; border-left: 4px solid #F4BF46; border-radius: 2px;">
        <b>Logs Dataform</b><br/>
        <small style="color: #4f4f4f;">Statuts d'exécution et rapports des transformations SQL.</small>
      </div>
    </td>
    <!-- Column 2 -->
    <td style="padding: 12px; border: 1px solid #eeeeee; background-color: #fdfaf2; text-align: center; vertical-align: middle;">
      <div style="font-weight: bold; color: #0b132b; margin-bottom: 8px;">Log Router (GCP)</div>
      <div style="font-size: 14pt; color: #208AAE; font-weight: bold; margin-bottom: 8px;">&darr;</div>
      <div style="padding: 8px; background-color: #0b132b; color: #ffffff; border-radius: 4px; font-weight: bold;">
        BigQuery<br/>
        <span style="font-size: 8.5pt; font-weight: normal;">Dataset d'Observabilité</span>
      </div>
      <small style="display: block; margin-top: 8px; color: #4f4f4f;">Centralisation pour tableaux de bord et analyses post-mortem.</small>
    </td>
    <!-- Column 3 -->
    <td style="padding: 12px; border: 1px solid #eeeeee; background-color: #ffffff;">
      <div style="margin-bottom: 10px; padding: 8px; background-color: #C91432; color: #ffffff; border-radius: 4px; font-weight: bold;">
        Rejet en Quarantaine<br/>
        <span style="font-size: 8pt; font-weight: normal;">Alerte immédiate en cas de fichier non conforme aux schémas.</span>
      </div>
      <div style="padding: 8px; background-color: #C91432; color: #ffffff; border-radius: 4px; font-weight: bold;">
        Échec de Transformation<br/>
        <span style="font-size: 8pt; font-weight: normal;">Alerte immédiate si une règle de qualité SQL (Dataform) échoue.</span>
      </div>
    </td>
  </tr>
</table>

| Catégorie d'Anomalie | Cause Fonctionnelle Typique | Action Opérationnelle Requise |
|:--------------|:-----------------|:---------------|
| **Rejet en Quarantaine** | Le format du fichier reçu diverge du contrat de données défini (ex: changement de séparateur, colonne manquante). | Investigation du fichier déposé et concertation avec le fournisseur de données. |
| **Échec Dataform** | Les règles de qualité métier (Quality Gates) n'ont pas été respectées (ex: violation d'unicité, valeur aberrante). | Analyse de la requête SQL en erreur au sein de l'interface Dataform. |

---

## 7. Synthèse et Checklist de Déploiement

### 7.1. Prérequis Bloquants

Les actions suivantes constituent le chemin critique pour l'initialisation technique du projet.

| Priorité | Action Requise | Responsabilité |
|:--------:|:-------|:------------|
| **[Critique]** | Instanciation des **2 projets GCP** (Dev, Prod). | Administrateur GCP IDEX |
| **[Critique]** | Création des **3 groupes de sécurité Workspace** (Engineers, Analysts, Business). | Administrateur Workspace IDEX |
| **[Critique]** | Validation de l'accès pour l'équipe **Alliance Decideom x PylTech** (Ajout direct des courriels, Whitelist, ou création d'identités externes). | Administrateur IAM IDEX |
| **[Critique]** | Validation du **référentiel Git** cible et de l'outil CI/CD. | Direction de Projet |
| **[Important]** | Paramétrage du **Workload Identity Federation (WIF)**. | Administrateur GCP + Architecte Pyl.Tech |
| **[Important]** | Validation et instanciation de l'environnement de test **Looker**. | Direction de Projet |

### 7.2. Sujets à Documenter (Questions Ouvertes)

**Sécurité Réseau et Conformité** :
- Quelle est la politique de sécurité de base d'IDEX concernant les accès cloud (Restrictions par adresse IP, obligation de transit par VPN, usage de VPC Service Controls) ?
- La fédération d'identités existante est-elle formellement documentée et accessible pour consultation ?

**Données et Cas d'Usage** :
- Quels sont les cas d'usage métiers prioritaires à démontrer afin de valider la valeur du pilote ?
- Quels sont les formats exacts, la volumétrie prévisionnelle et la fréquence de rafraîchissement des fichiers sources ?
- Le dépôt des fichiers sur le Cloud Storage sera-t-il effectué manuellement par les utilisateurs ou via un système de transfert automatisé ?

<div style="color: #208AAE; text-align: right; font-size: 0.9em; font-weight: bold; margin-top: 40px;">
Document Confidentiel - © Copyright 2026 Pyl.Tech
</div>
