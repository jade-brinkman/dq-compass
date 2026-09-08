# DQ Compass : plateforme de contrôle qualité des données

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?logo=pandas&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-3F4F75?logo=plotly&logoColor=white)
![Matplotlib](https://img.shields.io/badge/Matplotlib-11557C?logo=matplotlib&logoColor=white)

## Sommaire

- [Vision du projet](#vision-du-projet)
- [Démarrage rapide](#démarrage-rapide)
- [Structure du projet](#structure-du-projet)
- [Workflow en 3 étapes](#workflow-en-3-étapes)
- [Types de contrôles disponibles](#types-de-contrôles-disponibles)
- [Comment ça marche](#comment-ça-marche)
- [Exemple de rapport généré](#exemple-de-rapport-généré)
- [Pour aller plus loin](#pour-aller-plus-loin)
- [Équipe](#équipe)

## Vision du projet

DQ Compass est une plateforme de contrôle qualité des données conçue pour s'adapter à n'importe quel métier et n'importe quel type de données. Aucune règle métier n'est codée en dur : tout est piloté par configuration.

Concrètement, l'utilisateur :

1. Uploade son fichier CSV, quel que soit son format ou sa structure
2. Définit ses propres règles de qualité via un formulaire Streamlit
3. Obtient un rapport visuel des anomalies détectées, généré automatiquement

Projet réalisé dans le cadre du Datathon MBA Big Data & IA (MBA ESG).

---

## Démarrage rapide

### Lancer l'application Streamlit (recommandé)

```bash
cd dq-compass-app-en

# Windows
run.bat

# Linux/Mac
chmod +x run.sh
./run.sh
```

L'application s'ouvre à l'adresse `http://localhost:8501`.

### Utiliser le moteur en ligne de commande

```bash
cd dq-compass-engine
python engine/engine.py --catalogue catalogue/control_catalogue.csv --data-dir data
```

### Prérequis

- Python 3.8+
- pip

### Installation

```bash
git clone <repo_url>
cd dq-compass

# Dépendances de l'application Streamlit
cd dq-compass-app-en
pip install -r requirements.txt

# Le moteur seul ne dépend que de pandas
cd ../dq-compass-engine
pip install pandas
```

Aucune configuration additionnelle n'est nécessaire : les fichiers temporaires sont créés automatiquement dans `/tmp/dq_compass/` (Linux/Mac) ou `%TEMP%\dq_compass\` (Windows).

---

## Structure du projet

```
dq-compass/
│
├── dq-compass-app-en/            Application Streamlit
│   ├── Home.py                    Page d'accueil
│   ├── pages/
│   │   ├── 1_Upload_Data.py        Étape 1 : upload du CSV
│   │   ├── 2_Define_Rules.py       Étape 2 : formulaire de règles
│   │   └── 3_Quality_Report.py     Étape 3 : rapport visuel
│   ├── engine_wrapper.py          Wrapper d'appel au moteur
│   ├── requirements.txt           Dépendances (streamlit, pandas, plotly)
│   ├── README.md                  Documentation détaillée de l'app
│   └── run.bat / run.sh           Scripts de lancement
│
├── dq-compass-engine/            Moteur de règles (backend)
│   ├── engine/
│   │   ├── engine.py               Orchestrateur générique
│   │   ├── rules.py                7 logic_types génériques
│   │   └── utils.py                Utilitaires (SHA-256, run_id...)
│   ├── catalogue/
│   │   └── control_catalogue.csv   Catalogue de règles
│   ├── data/                       Jeux de données
│   └── runs/                       Historique des exécutions (evidence packs)
│
└── README.md                      Ce fichier
```

---

## Workflow en 3 étapes

### 1. Upload Data

![Upload Data](docs/screenshots/01_upload_data.png)

- Upload de n'importe quel fichier CSV
- Détection automatique du séparateur (`,` `;` `\t` `|`)
- Détection automatique de format large (colonnes temporelles) et transformation en format long
- Aperçu des données et statistiques de complétude

La transformation automatique wide → long permet de traiter directement des jeux de données pivotés, par exemple des données BIS avec des colonnes-années.

### 2. Define Rules

![Define Rules](docs/screenshots/02_define_rules.png)

- Formulaire interactif pour créer des règles de qualité
- Instructions contextuelles selon le type de règle choisi
- 7 types de contrôles disponibles (voir tableau ci-dessous)
- Import / export des règles au format JSON

Le formulaire garde une structure normée, la même quel que soit le métier, tout en restant assez souple pour s'adapter à des cas très différents.

### 3. Quality Report

![Quality Report](docs/screenshots/03_quality_report.png)

- Génération du rapport en un clic, avec barre de progression
- KPIs visuels : taux de réussite, nombre d'échecs
- Visualisations Plotly : répartition PASS / FAIL / ERROR, résultats par dimension, résultats par sévérité
- Tableau détaillé avec filtres, liste des exceptions par règle
- Export CSV / JSON des résultats et des exceptions
- Recommandations automatiques selon les résultats obtenus

> Captures d'écran à déposer dans `docs/screenshots/` sous les trois noms ci-dessus pour qu'elles s'affichent automatiquement.

---

## Types de contrôles disponibles

| # | logic_type | Description | Exemple d'usage |
|---|---|---|---|
| 1 | `not_null` | Vérifie l'absence de valeurs manquantes sur une colonne | Email obligatoire |
| 2 | `regex` | Vérifie un format via expression régulière | Format email, téléphone, IBAN |
| 3 | `unique` | Détecte les doublons sur une colonne | ID client unique |
| 4 | `unique_composite` | Détecte les doublons sur une combinaison de colonnes | (série_id + année) unique |
| 5 | `conditional_equals` | Vérifie une cohérence conditionnelle entre colonnes | Si statut = fermé alors solde = 0 |
| 6 | `max_age_days` | Vérifie la fraîcheur d'une date | Mise à jour de moins de 30 jours |
| 7 | `reconciliation_sum` | Compare des totaux entre fichiers ou groupes | Somme des régions = total national |

Ces 7 types sont strictement génériques : aucun ne fait référence à un métier ou à un dataset particulier. Six d'entre eux (`not_null`, `regex`, `unique`, `conditional_equals`, `max_age_days`, `reconciliation_sum`) correspondent aux exigences du cahier des besoins (BF-CAT-02) ; `unique_composite` est une extension documentée pour les cas multi-colonnes.

---

## Comment ça marche

1. L'utilisateur uploade un CSV via Streamlit
2. Streamlit sauvegarde le fichier dans un dossier temporaire
3. L'utilisateur définit des règles via le formulaire
4. Streamlit génère un catalogue CSV temporaire
5. L'Engine Wrapper appelle le moteur avec le catalogue et les données
6. Le moteur charge les données (transformation automatique si format large), exécute les règles génériques et retourne un résumé (`results_summary`) ainsi que les exceptions
7. Streamlit affiche le rapport avec ses visualisations

### Contrat de sortie (reproductibilité)

`results_summary.csv` (9 colonnes fixes) :

```
rule_id, control_name, dimension, severity, status,
total_records, failed_records, kpi_value, kpi_label
```

`exceptions/{rule_id}_exceptions.csv` : identifiant de ligne, colonne(s) fautive(s), motif.

`manifest.json` : run_id, timestamp, sources (SHA-256 et nombre de lignes), copie du catalogue utilisé.

Deux exécutions sur les mêmes fichiers produisent un `results_summary.csv` identique à l'octet près.

---

## Exemple de rapport généré

```
Total règles      : 6
Réussies          : 5
Échecs            : 1
Erreurs           : 0
Taux de réussite  : 83,3 %
```

Graphiques : répartition PASS / FAIL (83 % / 17 %), résultats par dimension (complétude 100 %, réconciliation 0 %), résultats par sévérité (High 75 %, Medium 100 %).

Exemple d'exceptions (règle DQ06, réconciliation du solde par région) :

```
rule_id: DQ06
failed_records: 15
kpi_value: 2.45 (écart max en %)

client_id | region | balance | computed_total | reference_total | deviation_pct
C001      | North  | 1500    | 45678.00       | 45000.00        | 1.51
...
```

---

## Pour aller plus loin

### Ajouter un 8e logic_type

1. Ouvrir `dq-compass-engine/engine/rules.py`
2. Créer une fonction générique, sur le même modèle que les 7 existantes
3. L'ajouter au dictionnaire `LOGIC_TYPE_FUNCTIONS`
4. Mettre à jour le formulaire Streamlit pour l'inclure

Exemple : un logic_type `value_range` pour vérifier qu'une valeur reste dans un intervalle [min, max].

### Automatisation

L'application Streamlit convient à l'exploration interactive. Pour une automatisation, le moteur s'utilise directement en ligne de commande :

```bash
cd dq-compass-engine
python engine/engine.py --catalogue mon_catalogue.csv --data-dir mes_donnees/
```

### Intégration CI/CD

```yaml
# Exemple GitLab CI
quality_check:
  script:
    - cd dq-compass-engine
    - python engine/engine.py --catalogue production_rules.csv --data-dir data/
    - python check_results.py
```

---

## Équipe

Projet réalisé dans le cadre du Datathon MBA Big Data & IA.

- **Lucas** : reporting layer et application Streamlit
- **Jade** : moteur de règles (DQ Engine)
- **Irmeline** : catalogue de règles
- **Johann** : couche d'audit
