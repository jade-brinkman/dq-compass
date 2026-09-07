#!/usr/bin/env python3
"""
DQ Compass - Universal Data Quality Platform
Point d'entrée principal de l'application Streamlit

Permet à tout utilisateur de :
1. Uploader son fichier CSV
2. Définir ses règles de qualité via un formulaire
3. Générer un rapport de qualité visuel
"""

import streamlit as st
from pathlib import Path
import sys

# Configuration de la page
st.set_page_config(
    page_title="DQ Compass - Universal Data Quality",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialisation de la session
if "data_uploaded" not in st.session_state:
    st.session_state.data_uploaded = False
    st.session_state.uploaded_file_path = None
    st.session_state.uploaded_df = None
    st.session_state.rules = []
    st.session_state.report_generated = False
    st.session_state.last_run_results = None

# En-tête principal
st.title("🧭 DQ Compass")
st.subheader("Plateforme Universelle de Qualité des Données")

st.markdown("""
---
### Bienvenue dans DQ Compass

Cette plateforme vous permet d'évaluer la qualité de **n'importe quel jeu de données**
en définissant vos propres règles de contrôle, adaptées à votre métier.

#### Comment ça marche ?

1. **📊 Uploadez vos données** - Importez votre fichier CSV
2. **📝 Définissez vos règles** - Créez des contrôles qualité via un formulaire simple
3. **📈 Consultez le rapport** - Visualisez les résultats et les anomalies détectées

#### Types de contrôles disponibles :

- **Complétude** : Vérifier qu'une colonne n'a pas de valeurs manquantes
- **Validité** : Vérifier le format des données (regex, email, dates, etc.)
- **Unicité** : Détecter les doublons sur une ou plusieurs colonnes
- **Cohérence** : Vérifier la cohérence entre colonnes (ex: si statut=X alors montant=Y)
- **Fraîcheur** : Vérifier l'âge des données (dates récentes)
- **Réconciliation** : Comparer des totaux entre colonnes ou fichiers
- **Unicité composite** : Vérifier l'unicité sur une combinaison de colonnes

---

### État de votre session

""")

# Affichage de l'état actuel
col1, col2, col3 = st.columns(3)

with col1:
    if st.session_state.data_uploaded:
        st.success("✅ Données uploadées")
        if st.session_state.uploaded_df is not None:
            st.metric("Nombre de lignes", len(st.session_state.uploaded_df))
            st.metric("Nombre de colonnes", len(st.session_state.uploaded_df.columns))
    else:
        st.warning("⏳ En attente de données")

with col2:
    if len(st.session_state.rules) > 0:
        st.success(f"✅ {len(st.session_state.rules)} règle(s) définie(s)")
    else:
        st.info("📝 Aucune règle définie")

with col3:
    if st.session_state.report_generated:
        st.success("✅ Rapport généré")
    else:
        st.info("📈 Rapport non généré")

st.markdown("---")

# Navigation
st.markdown("""
### 🚀 Commencez maintenant

Utilisez la **barre latérale** pour naviguer entre les étapes :
- **📊 Upload Data** : Importez votre fichier CSV
- **📝 Define Rules** : Créez vos règles de qualité
- **📈 Quality Report** : Consultez le rapport détaillé
""")

# Instructions de démarrage
if not st.session_state.data_uploaded:
    st.info("👉 Cliquez sur **'📊 Upload Data'** dans la barre latérale pour commencer")
elif len(st.session_state.rules) == 0:
    st.info("👉 Cliquez sur **'📝 Define Rules'** pour créer vos premières règles de qualité")
else:
    st.info("👉 Cliquez sur **'📈 Quality Report'** pour générer et consulter votre rapport")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <small>DQ Compass - Datathon MBA Big Data & IA - Solution universelle adaptable à tout métier</small>
</div>
""", unsafe_allow_html=True)
