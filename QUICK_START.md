# 🚀 Quick Start - DQ Compass Universal

## Installation (1 minute)

```bash
# Se placer dans le dossier de l'application
cd dq-compass-app-en

# Installer les dépendances
pip install -r requirements.txt
```

## Lancer l'application (10 secondes)

### Windows
```bash
run.bat
```

### Linux / Mac
```bash
chmod +x run.sh
./run.sh
```

### Méthode alternative (toutes plateformes)
```bash
streamlit run app.py
```

L'application s'ouvre automatiquement à : **http://localhost:8501**

---

## Premier Test (5 minutes)

### Étape 1 : Upload Data 📊

1. Cliquez sur **"Upload Data"** dans la barre de navigation en haut de page
2. Uploadez le fichier d'exemple : `../dq-compass-engine/data/clients.csv`
3. Vérifiez l'aperçu des données
4. Cliquez sur **"Valider et utiliser ces données"**

### Étape 2 : Define Rules 📝

1. Cliquez sur **"Define Rules"** dans la barre de navigation en haut de page
2. Créez votre première règle :
   - **ID** : `TEST01`
   - **Nom** : `Test Complétude Email`
   - **Dimension** : `Complétude`
   - **Type de logique** : `not_null`
   - **Colonne** : `email`
   - **Seuil** : `0`
   - **Sévérité** : `High`
3. Cliquez sur **"Ajouter cette règle"**
4. Créez une 2ème règle (optionnel) :
   - **ID** : `TEST02`
   - **Nom** : `Test Unicité Client`
   - **Type de logique** : `unique`
   - **Colonne** : `client_id`

### Étape 3 : Quality Report 📈

1. Cliquez sur **"Quality Report"** dans la barre de navigation en haut de page
2. Cliquez sur **"Générer le rapport"**
3. Attendez quelques secondes
4. Consultez :
   - Les KPIs en haut
   - Les graphiques (camembert, barres)
   - Le tableau détaillé
   - Les exceptions (si des règles échouent)
5. Téléchargez les résultats (CSV, JSON)

---

## ✅ C'est Fait !

Vous avez créé votre premier rapport de qualité en **5 minutes** sans écrire une seule ligne de code !

---

## 🎯 Prochaines Étapes

### Testez avec vos propres données
1. Uploadez votre fichier CSV
2. Créez des règles adaptées à votre métier
3. Générez votre rapport personnalisé

### Explorez les 7 types de règles
- `not_null` : Complétude
- `regex` : Validité (format)
- `unique` : Unicité
- `unique_composite` : Unicité sur plusieurs colonnes
- `conditional_equals` : Cohérence conditionnelle
- `max_age_days` : Fraîcheur
- `reconciliation_sum` : Réconciliation

### Réutilisez vos règles
1. Exportez vos règles en JSON (bouton dans Define Rules)
2. Réimportez-les dans une autre session
3. Partagez-les avec votre équipe

---

## 🐛 Problèmes Courants

### L'application ne démarre pas
```bash
# Vérifier que streamlit est installé
pip install streamlit

# Vérifier la version de Python (3.8+ requis)
python --version
```

### Erreur "ModuleNotFoundError: No module named 'pandas'"
```bash
pip install pandas plotly
```

### Le fichier ne s'uploade pas
- Vérifiez que c'est un fichier CSV
- Vérifiez l'encodage (UTF-8 recommandé)
- Essayez avec un séparateur différent (`,` `;` `\t`)

---

## 📚 Documentation Complète

- [README Principal](README.md) - Vue d'ensemble du projet
- [README Application](dq-compass-app-en/README.md) - Documentation détaillée de l'app
- [CHANGEMENTS](CHANGEMENTS.md) - Récapitulatif des modifications

---

**Besoin d'aide ?** Consultez la documentation ou contactez l'équipe !

🧭 **DQ Compass Universal** - La qualité des données, simple et accessible
