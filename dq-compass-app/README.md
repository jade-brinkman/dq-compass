# DQ Compass - Universal Data Quality Platform

## 🎯 Vision

**DQ Compass** est une plateforme universelle de contrôle qualité des données, conçue pour s'adapter à **n'importe quel métier** et **n'importe quel type de données**.

Contrairement aux solutions spécifiques à un domaine, DQ Compass permet à tout utilisateur de :
1. Uploader son fichier CSV (n'importe quel format, n'importe quelle structure)
2. Définir ses propres règles de qualité via un formulaire simple
3. Générer automatiquement un rapport visuel avec les anomalies détectées

## 🚀 Démarrage rapide

### Installation

```bash
# Naviguer vers le dossier de l'application
cd dq-compass-app

# Installer les dépendances
pip install -r requirements.txt
```

### Lancer l'application

```bash
streamlit run app.py
```

L'application s'ouvre automatiquement dans votre navigateur à l'adresse : `http://localhost:8501`

## 📋 Guide d'utilisation

### Étape 1 : Upload Data (📊)

1. Cliquez sur **"📊 Upload Data"** dans la barre latérale
2. Sélectionnez votre fichier CSV
3. L'application détecte automatiquement :
   - Le séparateur (`,` `;` `\t` `|`)
   - Les colonnes temporelles (format large → transformation automatique en format long)
   - Les métadonnées (nombre de lignes, colonnes, complétude)
4. Validez les données

**Formats supportés :**
- Format classique : 1 ligne = 1 enregistrement
- Format large/pivot : colonnes temporelles (années) → transformation automatique en format long

### Étape 2 : Define Rules (📝)

1. Cliquez sur **"📝 Define Rules"** dans la barre latérale
2. Créez vos règles de qualité via le formulaire :
   - **ID** : Identifiant unique (ex: `DQ01`)
   - **Nom** : Nom descriptif (ex: `Complétude email`)
   - **Dimension** : Complétude, Validité, Unicité, Cohérence, Fraîcheur, Réconciliation
   - **Type de logique** : Choisissez parmi 7 types disponibles (voir ci-dessous)
   - **Colonne(s)** : Colonne(s) à contrôler
   - **Paramètre** : Selon le type de règle (regex, valeur de référence, etc.)
   - **Seuil** : Tolérance (% ou valeur absolue)
3. Ajoutez autant de règles que nécessaire
4. Exportez/importez vos règles en JSON pour les réutiliser

**Types de contrôles disponibles :**

| Type | Description | Exemple d'usage |
|------|-------------|-----------------|
| `not_null` | Vérifie qu'une colonne n'a pas de valeurs manquantes | Email obligatoire |
| `regex` | Vérifie le format via une expression régulière | Format email, téléphone, code postal |
| `unique` | Détecte les doublons sur une colonne | ID client unique |
| `unique_composite` | Détecte les doublons sur plusieurs colonnes | (série_id + année) unique |
| `conditional_equals` | Cohérence conditionnelle entre colonnes | Si statut=fermé alors solde=0 |
| `max_age_days` | Vérifie la fraîcheur d'une date | Données mises à jour dans les 30 derniers jours |
| `reconciliation_sum` | Compare des totaux entre fichiers/groupes | Somme des régions = Total national |

### Étape 3 : Quality Report (📈)

1. Cliquez sur **"📈 Quality Report"** dans la barre latérale
2. Cliquez sur **"Générer le rapport"**
3. Consultez :
   - **Vue d'ensemble** : Métriques globales (taux de réussite, nombre d'échecs)
   - **Visualisations** : Graphiques interactifs (statuts, dimensions, sévérités)
   - **Résultats détaillés** : Tableau filtrable de toutes les règles
   - **Exceptions** : Liste des enregistrements en échec pour chaque règle
   - **Recommandations** : Actions à entreprendre

4. Téléchargez :
   - Le rapport de synthèse (CSV)
   - Le rapport complet (JSON)
   - Les exceptions par règle (CSV)

## 🏗️ Architecture

```
dq-compass/
├── dq-compass-engine/          # Moteur de règles (backend)
│   ├── engine/
│   │   ├── engine.py           # Orchestrateur
│   │   ├── rules.py            # 7 logic_types génériques
│   │   └── utils.py            # Utilitaires
│   └── ...
│
├── dq-compass-app/             # Interface Streamlit (frontend)
│   ├── app.py                  # Page d'accueil
│   ├── pages/
│   │   ├── 1_📊_Upload_Data.py
│   │   ├── 2_📝_Define_Rules.py
│   │   └── 3_📈_Quality_Report.py
│   ├── engine_wrapper.py       # Wrapper pour appeler le moteur
│   ├── requirements.txt
│   └── README.md (ce fichier)
```

## 🎨 Captures d'écran

### Page d'accueil
- Vue d'ensemble de l'état de la session
- Navigation claire entre les 3 étapes

### Upload Data
- Détection automatique du format
- Aperçu des données
- Statistiques de complétude par colonne

### Define Rules
- Formulaire intuitif avec instructions contextuelles
- Liste des règles actives
- Import/export JSON

### Quality Report
- Métriques visuelles (KPIs)
- Graphiques interactifs (Plotly)
- Tableau détaillé avec filtres
- Exceptions téléchargeables

## 🔧 Cas d'usage

### Exemple 1 : Banque (données clients)
- **Complétude** : Email obligatoire
- **Validité** : Format email valide
- **Unicité** : ID client unique
- **Cohérence** : Si compte fermé → solde = 0
- **Fraîcheur** : MAJ < 30 jours
- **Réconciliation** : Somme soldes par région = Total référence

### Exemple 2 : E-commerce (commandes)
- **Complétude** : Adresse de livraison obligatoire
- **Validité** : Code postal à 5 chiffres
- **Unicité** : Numéro de commande unique
- **Cohérence** : Si statut=livré → date de livraison non nulle
- **Fraîcheur** : Commandes < 90 jours

### Exemple 3 : Statistiques BIS (dérivés OTC)
- **Complétude** : Colonnes de classification renseignées
- **Validité** : Format de la série (14 segments séparés par `:`)
- **Unicité** : (série_id + année) unique
- **Réconciliation** : Somme des composantes = Total (DER_INSTR=A)

### Exemple 4 : RH (employés)
- **Complétude** : Nom, prénom, département obligatoires
- **Validité** : Email professionnel (@entreprise.com)
- **Unicité** : Matricule employé unique
- **Cohérence** : Si CDI → date de fin nulle

## 🌟 Avantages

### Universalité
- **Aucun code spécifique à un métier** : tout est piloté par configuration
- S'adapte à n'importe quelle structure de données
- Transformation automatique format large ↔ format long

### Simplicité
- Interface 100% no-code
- Formulaire guidé avec instructions contextuelles
- Pas besoin de connaître Python ou SQL

### Traçabilité
- Chaque exécution génère un run_id unique
- Logs détaillés
- Export complet (JSON) pour audit

### Reproductibilité
- Export/import des règles en JSON
- Mêmes règles = mêmes résultats
- Versionnable dans Git

### Visualisation
- Graphiques interactifs (Plotly)
- KPIs visuels
- Filtres dynamiques

## 🛠️ Développement

### Ajouter un nouveau logic_type

Si les 7 types existants ne suffisent pas, vous pouvez en ajouter un 8ème :

1. Ouvrir `dq-compass-engine/engine/rules.py`
2. Créer une fonction générique (même patron que les 7 existantes)
3. L'ajouter au dictionnaire `LOGIC_TYPE_FUNCTIONS`
4. Documenter le contrat (colonne, param, threshold) dans les docstrings

**Exemple : règle "entre min et max"**
```python
def value_range(df: pd.DataFrame, rule: dict, datasets: dict) -> dict:
    """
    Vérifie qu'une colonne numérique est dans un intervalle [min, max]

    column : colonne numérique
    param : "min:max" (ex: "0:100")
    threshold : % max de valeurs hors intervalle tolérées
    """
    # ... implémentation générique ...
```

### Contribuer

1. Fork le projet
2. Créez votre branche (`git checkout -b feature/AmazingFeature`)
3. Committez vos changements (`git commit -m 'Add some AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrez une Pull Request

## 📜 Licence

Ce projet a été développé dans le cadre du **Datathon MBA Big Data & IA**.

## 👥 Équipe

- **Lucas** : Reporting Layer
- **Jade** : DQ Engine
- **Irmeline** : Catalogue
- **Johann** : Audit Layer

## 📞 Support

Pour toute question ou problème :
1. Consultez ce README
2. Vérifiez les logs dans le dossier temporaire (`/tmp/dq_compass/runs/`)
3. Ouvrez une issue sur GitHub

---

**DQ Compass** - La qualité des données, universelle et accessible à tous 🧭
