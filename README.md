# 🧭 DQ Compass - Universal Data Quality Platform

## 🎯 Vision du Projet

**DQ Compass** est une plateforme universelle de contrôle qualité des données qui s'adapte à **n'importe quel métier** et **n'importe quel type de données**.

Contrairement aux solutions spécifiques à un domaine, DQ Compass permet à tout utilisateur de :
1. ✅ Uploader son fichier CSV (n'importe quel format, n'importe quelle structure)
2. ✅ Définir ses propres règles de qualité via un formulaire Streamlit simple
3. ✅ Générer automatiquement un rapport visuel avec les anomalies détectées

**Principe clé** : Aucune règle métier n'est codée en dur. Tout est piloté par configuration.

---

## 🚀 Démarrage Rapide

### Option 1 : Lancer l'application Streamlit (Recommandé)

```bash
# Se placer dans le dossier de l'application
cd dq-compass-app-en

# Windows
run.bat

# Linux/Mac
chmod +x run.sh
./run.sh
```

L'application s'ouvre automatiquement à `http://localhost:8501`

### Option 2 : Utiliser le moteur en ligne de commande

```bash
cd dq-compass-engine
python engine/engine.py --catalogue catalogue/control_catalogue.csv --data-dir data
```

---

## 📂 Structure du Projet

```
dq-compass/
│
├── dq-compass-app-en/             ✨ NOUVELLE APPLICATION STREAMLIT
│   ├── Home.py                 # Page d'accueil
│   ├── pages/
│   │   ├── 1_Upload_Data.py      # Étape 1 : Upload CSV
│   │   ├── 2_Define_Rules.py     # Étape 2 : Formulaire de règles
│   │   └── 3_Quality_Report.py   # Étape 3 : Rapport visuel
│   ├── engine_wrapper.py       # Wrapper pour appeler le moteur
│   ├── requirements.txt        # Dépendances (streamlit, pandas, plotly)
│   ├── README.md              # Documentation détaillée de l'app
│   ├── run.bat / run.sh       # Scripts de lancement
│   └── ...
│
├── dq-compass-engine/          🔧 MOTEUR DE RÈGLES (Backend)
│   ├── engine/
│   │   ├── engine.py           # Orchestrateur générique
│   │   ├── rules.py            # 7 logic_types génériques
│   │   └── utils.py            # Utilitaires (SHA-256, run_id, etc.)
│   ├── catalogue/
│   │   └── control_catalogue.csv   # Catalogue de règles (format CSV)
│   ├── data/                   # Dossier de données
│   ├── runs/                   # Historique des exécutions
│   └── README.md              # Documentation du moteur
│
└── README.md                   📘 CE FICHIER (vue d'ensemble)
```

---

## 🎨 Interface Streamlit : Workflow en 3 Étapes

### Étape 1 : Upload Data

![Upload Data](https://img.shields.io/badge/Statut-Terminé-brightgreen)

- Upload de n'importe quel fichier CSV
- Détection automatique du séparateur (`,` `;` `\t` `|`)
- Détection automatique de format large (colonnes temporelles) → transformation en format long
- Aperçu des données + statistiques de complétude
- Validation et sauvegarde en session

**Innovation** : Transformation automatique wide→long pour les datasets pivotés (ex: données BIS avec colonnes-années)

### Étape 2 : Define Rules

![Define Rules](https://img.shields.io/badge/Statut-Terminé-brightgreen)

- Formulaire interactif pour créer des règles de qualité
- Instructions contextuelles selon le type de règle choisi
- 7 types de contrôles disponibles (voir ci-dessous)
- Import/export des règles en JSON (réutilisabilité)
- Liste des règles actives avec possibilité de suppression

**Innovation** : Formulaire normé mais flexible, adapté à n'importe quel métier

### Étape 3 : Quality Report

![Quality Report](https://img.shields.io/badge/Statut-Terminé-brightgreen)

- Génération du rapport en un clic
- Barre de progression en temps réel
- **Vue d'ensemble** : KPIs visuels (taux de réussite, nombre d'échecs)
- **Visualisations interactives** (Plotly) :
  - Camembert des statuts (PASS/FAIL/ERROR)
  - Barres par dimension qualité
  - Barres par sévérité
- **Tableau détaillé** avec filtres dynamiques
- **Exceptions** : Liste des enregistrements en échec par règle
- **Téléchargements** : CSV, JSON, exceptions par règle
- **Recommandations** automatiques selon les résultats

**Innovation** : Reporting visuel riche et interactif, sans aucun codage

---

## 📊 Types de Contrôles Disponibles (7 Logic Types)

| # | Logic Type | Description | Exemple d'usage |
|---|------------|-------------|-----------------|
| 1 | `not_null` | Vérifie qu'une colonne n'a pas de valeurs manquantes | Email obligatoire |
| 2 | `regex` | Vérifie le format via une expression régulière | Format email, téléphone, IBAN |
| 3 | `unique` | Détecte les doublons sur une colonne | ID client unique |
| 4 | `unique_composite` | Détecte les doublons sur plusieurs colonnes | (série_id + année) unique |
| 5 | `conditional_equals` | Cohérence conditionnelle entre colonnes | Si statut=fermé alors solde=0 |
| 6 | `max_age_days` | Vérifie la fraîcheur d'une date | MAJ < 30 jours |
| 7 | `reconciliation_sum` | Compare des totaux entre fichiers/groupes | Somme régions = Total national |

**Tous les logic_types sont 100% génériques** : aucune référence à un métier ou à un dataset spécifique.

---

## 🌟 Cas d'Usage Réels

### 🏦 Cas 1 : Banque (Données Clients)

**Dataset** : `clients.csv` (521 lignes)

**Règles définies** :
- ✅ Complétude email (`not_null`)
- ✅ Validité format email (`regex`)
- ✅ Unicité client_id (`unique`)
- ✅ Cohérence compte clos (`conditional_equals`) : Si status=closed → balance=0
- ✅ Fraîcheur dernière MAJ (`max_age_days`) : < 30 jours
- ✅ Réconciliation soldes par région (`reconciliation_sum`)

**Résultat** : 6 règles, taux de réussite 83%, 1 échec (réconciliation), rapport visuel complet

---

### 📈 Cas 2 : Statistiques BIS (Dérivés OTC)

**Dataset** : `WS_DER_OTC_TOV_csv_col.csv` (77 992 lignes × 73 colonnes → transformé en format long)

**Règles définies** :
- ✅ Complétude TITLE_TS (`not_null`) : Colonne vide à 100% → détection
- ✅ Unicité (série + année) (`unique_composite`) : Pas de doublons
- ✅ Complétude codes instrument (`not_null`) : DER_INSTR obligatoire
- ✅ Validité format Series (`regex`) : 14 segments séparés par `:`
- ✅ Réconciliation composantes/total (`reconciliation_sum`) : DER_INSTR=A vs autres

**Résultat** : Transformation automatique wide→long, détection des incohérences, rapport exploitable

---

### 🛒 Cas 3 : E-commerce (Commandes)

**Dataset** : `orders.csv`

**Règles définies** :
- ✅ Complétude adresse de livraison (`not_null`)
- ✅ Validité code postal (`regex`) : 5 chiffres
- ✅ Unicité numéro de commande (`unique`)
- ✅ Cohérence livraison (`conditional_equals`) : Si statut=livré → date_livraison non nulle
- ✅ Fraîcheur commandes (`max_age_days`) : < 90 jours

---

### 👥 Cas 4 : RH (Employés)

**Dataset** : `employees.csv`

**Règles définies** :
- ✅ Complétude nom, prénom, département (`not_null`)
- ✅ Validité email professionnel (`regex`) : @entreprise.com
- ✅ Unicité matricule (`unique`)
- ✅ Cohérence contrat (`conditional_equals`) : Si CDI → date_fin nulle

---

## 🏗️ Architecture Technique

### Principe de Séparation

```
┌─────────────────────────────────────────────────────────┐
│  FRONTEND : Streamlit (dq-compass-app-en/)                 │
│  - Interface no-code                                     │
│  - Formulaire de règles                                  │
│  - Visualisations (Plotly)                              │
└────────────────┬────────────────────────────────────────┘
                 │
                 │ appelle via engine_wrapper.py
                 ▼
┌─────────────────────────────────────────────────────────┐
│  BACKEND : Moteur DQ (dq-compass-engine/)               │
│  - Chargement données (avec transformation wide→long)   │
│  - Exécution des 7 logic_types génériques              │
│  - Génération des résultats + exceptions                │
└─────────────────────────────────────────────────────────┘
```

### Flux de Données

1. **Utilisateur** uploade un CSV via Streamlit
2. **Streamlit** sauvegarde le fichier dans un dossier temporaire
3. **Utilisateur** définit des règles via le formulaire
4. **Streamlit** génère un catalogue CSV temporaire
5. **Engine Wrapper** appelle le moteur avec le catalogue + données
6. **Moteur** :
   - Charge les données (transformation automatique si format large)
   - Exécute les règles génériques
   - Retourne results_summary + exceptions
7. **Streamlit** affiche le rapport avec visualisations

### Contrat de Sortie (Reproductibilité)

**results_summary.csv** (9 colonnes fixes) :
```
rule_id, control_name, dimension, severity, status,
total_records, failed_records, kpi_value, kpi_label
```

**exceptions/{rule_id}_exceptions.csv** :
- Identifiant de ligne + colonne(s) fautive(s) + reason

**manifest.json** :
- run_id, timestamp, sources (SHA-256 + nb lignes), copie du catalogue

---

## 🔧 Installation et Configuration

### Prérequis

- Python 3.8+
- pip

### Installation

```bash
# Cloner le repo
git clone <repo_url>
cd dq-compass

# Installer les dépendances de l'app Streamlit
cd dq-compass-app-en
pip install -r requirements.txt

# (Optionnel) Installer les dépendances du moteur seul
cd ../dq-compass-engine
pip install pandas  # Le moteur n'a besoin que de pandas
```

### Configuration

Aucune configuration nécessaire ! L'application est prête à l'emploi.

Les fichiers temporaires sont créés automatiquement dans `/tmp/dq_compass/` (Linux/Mac) ou `%TEMP%\dq_compass\` (Windows).

---

## 📊 Exemple de Rapport Généré

### Vue d'ensemble
```
Total Règles     : 6
✅ Réussies      : 5
❌ Échecs        : 1
⚠️ Erreurs       : 0
Taux de réussite : 83.3%
```

### Graphiques
- Camembert : 83% PASS, 17% FAIL
- Barres par dimension : Complétude 100%, Réconciliation 0%
- Barres par sévérité : High 75%, Medium 100%

### Exceptions (exemple : DQ06)
```
rule_id: DQ06
control_name: Réconciliation solde par région
failed_records: 15
kpi_value: 2.45 (écart max en %)

Exceptions détaillées :
client_id | region | balance | computed_total | reference_total | deviation_pct
C001      | North  | 1500    | 45678.00      | 45000.00       | 1.51
...
```

---

## 🎓 Pour Aller Plus Loin

### Ajouter un 8ème Logic Type

Si les 7 types existants ne suffisent pas, vous pouvez en ajouter un nouveau :

1. Ouvrir `dq-compass-engine/engine/rules.py`
2. Créer une fonction générique (même patron que les 7 existantes)
3. L'ajouter au dictionnaire `LOGIC_TYPE_FUNCTIONS`
4. Mettre à jour le formulaire Streamlit pour l'inclure

**Exemple** : `value_range` pour vérifier qu'une valeur est dans un intervalle [min, max]

### Automatisation

L'application Streamlit est idéale pour l'exploration interactive, mais pour une automatisation :

```bash
# Générer un catalogue JSON depuis Streamlit (export)
# Puis l'utiliser en ligne de commande :
cd dq-compass-engine
python engine/engine.py --catalogue mon_catalogue.csv --data-dir mes_donnees/
```

### Intégration CI/CD

Le moteur peut être intégré dans un pipeline CI/CD :

```yaml
# Exemple GitLab CI
quality_check:
  script:
    - cd dq-compass-engine
    - python engine/engine.py --catalogue production_rules.csv --data-dir data/
    - python check_results.py  # Script custom pour vérifier les résultats
```

---

## 🤝 Contribution

Ce projet est ouvert aux contributions ! N'hésitez pas à :

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/AmazingFeature`)
3. Committer vos changements (`git commit -m 'Add AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

---

## 📜 Licence

Développé dans le cadre du **Datathon MBA Big Data & IA**.

---

## 👥 Équipe

- **Lucas** : Reporting Layer + Streamlit
- **Jade** : DQ Engine
- **Irmeline** : Catalogue de règles
- **Johann** : Audit Layer

---

## 📞 Support

- 📖 Documentation : Consultez les README dans chaque dossier
- 🐛 Issues : Ouvrez une issue sur GitHub
- 💬 Questions : Contactez l'équipe

---

**DQ Compass** - La qualité des données, universelle et accessible à tous 🧭

*Toute organisation, tout métier, toute donnée.*
