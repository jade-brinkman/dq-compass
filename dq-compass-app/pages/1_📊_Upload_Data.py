import streamlit as st
import pandas as pd
from pathlib import Path
import tempfile
import shutil

st.set_page_config(page_title="Upload Data", page_icon="📊", layout="wide")

st.title("📊 Upload Your Data")

st.markdown("""
Uploadez votre fichier CSV pour commencer l'analyse de qualité.

**Formats supportés :**
- CSV (avec séparateur virgule, point-virgule, ou tabulation)
- Encodage : UTF-8, Latin-1, CP1252

**Format des données :**
- Format classique : 1 ligne = 1 enregistrement
- Format large (pivot) : Le moteur détectera automatiquement les colonnes temporelles
  (années à 4 chiffres) et transformera en format long
""")

st.markdown("---")

# Upload du fichier
uploaded_file = st.file_uploader(
    "Choisissez un fichier CSV",
    type=['csv'],
    help="Sélectionnez votre fichier de données au format CSV"
)

if uploaded_file is not None:
    try:
        # Détection automatique du séparateur
        st.info("🔍 Détection du format du fichier...")

        # Lire les premières lignes pour détecter le séparateur
        sample = uploaded_file.read(10000).decode('utf-8', errors='ignore')
        uploaded_file.seek(0)

        # Tester différents séparateurs
        separators = [',', ';', '\t', '|']
        best_sep = ','
        max_cols = 0

        for sep in separators:
            try:
                test_df = pd.read_csv(
                    pd.io.common.StringIO(sample),
                    sep=sep,
                    nrows=5
                )
                if len(test_df.columns) > max_cols:
                    max_cols = len(test_df.columns)
                    best_sep = sep
            except:
                continue

        # Chargement du fichier complet
        df = pd.read_csv(uploaded_file, sep=best_sep, dtype=str, keep_default_na=False)

        st.success(f"✅ Fichier chargé avec succès ! Séparateur détecté : `{repr(best_sep)}`")

        # Affichage des métadonnées
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Nombre de lignes", f"{len(df):,}")
        with col2:
            st.metric("Nombre de colonnes", len(df.columns))
        with col3:
            # Estimer la taille mémoire
            memory_usage = df.memory_usage(deep=True).sum() / 1024 / 1024
            st.metric("Taille en mémoire", f"{memory_usage:.2f} MB")

        st.markdown("---")

        # Aperçu des données
        st.subheader("📋 Aperçu des données (premières lignes)")
        st.dataframe(df.head(10), use_container_width=True)

        st.markdown("---")

        # Informations sur les colonnes
        st.subheader("📊 Informations sur les colonnes")

        col_info = []
        for col in df.columns:
            non_empty = (df[col].str.strip() != "").sum()
            empty = len(df) - non_empty
            col_info.append({
                "Colonne": col,
                "Valeurs non vides": non_empty,
                "Valeurs vides": empty,
                "Taux de complétude": f"{non_empty / len(df) * 100:.2f}%",
                "Valeurs uniques": df[col].nunique()
            })

        col_df = pd.DataFrame(col_info)
        st.dataframe(col_df, use_container_width=True)

        # Détection automatique de format large (colonnes-année)
        year_cols = [col for col in df.columns if str(col).strip().isdigit() and len(str(col).strip()) == 4]

        if year_cols:
            st.warning(f"""
            ⚠️ **Format large détecté** : {len(year_cols)} colonnes temporelles trouvées ({min(year_cols)} à {max(year_cols)})

            Le moteur transformera automatiquement ce format en **format long** lors de l'exécution :
            - Chaque ligne sera dupliquée pour chaque année contenant une valeur
            - Les valeurs vides seront automatiquement filtrées
            - Une colonne `year` sera créée
            - Une colonne `value` contiendra les valeurs

            **Format actuel** : {len(df):,} lignes × {len(df.columns)} colonnes
            **Format transformé estimé** : ~{len(df) * len(year_cols):,} lignes max (après filtrage des valeurs vides)
            """)

        st.markdown("---")

        # Bouton de confirmation
        if st.button("✅ Valider et utiliser ces données", type="primary", use_container_width=True):
            # Sauvegarder le fichier dans un dossier temporaire de la session
            temp_dir = Path(tempfile.gettempdir()) / "dq_compass" / "data"
            temp_dir.mkdir(parents=True, exist_ok=True)

            # Nom de fichier sécurisé
            safe_filename = uploaded_file.name.replace(" ", "_")
            file_path = temp_dir / safe_filename

            # Sauvegarder le DataFrame
            df.to_csv(file_path, index=False)

            # Sauvegarder dans la session
            st.session_state.data_uploaded = True
            st.session_state.uploaded_file_path = str(file_path)
            st.session_state.uploaded_filename = safe_filename
            st.session_state.uploaded_df = df
            st.session_state.report_generated = False  # Reset le rapport

            st.success(f"""
            ✅ **Données sauvegardées !**

            Fichier : `{safe_filename}`
            Emplacement : `{file_path}`

            👉 Passez à l'étape suivante : **📝 Define Rules**
            """)

            st.balloons()

    except Exception as e:
        st.error(f"""
        ❌ **Erreur lors du chargement du fichier**

        ```
        {str(e)}
        ```

        Veuillez vérifier que :
        - Le fichier est un CSV valide
        - L'encodage est UTF-8 ou compatible
        - Le fichier n'est pas corrompu
        """)

else:
    st.info("📁 Aucun fichier sélectionné. Uploadez un fichier CSV pour commencer.")

# Affichage de l'état actuel si des données sont déjà uploadées
if st.session_state.data_uploaded and uploaded_file is None:
    st.success(f"""
    ✅ **Données déjà chargées**

    Fichier : `{st.session_state.uploaded_filename}`
    Nombre de lignes : {len(st.session_state.uploaded_df):,}
    Nombre de colonnes : {len(st.session_state.uploaded_df.columns)}

    Vous pouvez uploader un nouveau fichier ci-dessus pour remplacer les données actuelles.
    """)
