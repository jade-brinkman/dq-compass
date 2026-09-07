import streamlit as st
import pandas as pd
import json

st.set_page_config(page_title="Define Rules", page_icon="📝", layout="wide")

st.title("📝 Define Quality Rules")

# Vérifier que des données ont été uploadées
if not st.session_state.data_uploaded:
    st.warning("⚠️ Veuillez d'abord uploader vos données dans la page **📊 Upload Data**")
    st.stop()

st.markdown(f"""
Définissez vos règles de qualité pour le fichier : **`{st.session_state.uploaded_filename}`**

**{len(st.session_state.uploaded_df):,} lignes** × **{len(st.session_state.uploaded_df.columns)} colonnes**
""")

# Récupérer les colonnes disponibles
df = st.session_state.uploaded_df
available_columns = list(df.columns)

st.markdown("---")

# Section 1 : Liste des règles existantes
st.subheader("📋 Règles actuellement définies")

if len(st.session_state.rules) == 0:
    st.info("Aucune règle définie pour le moment. Utilisez le formulaire ci-dessous pour créer votre première règle.")
else:
    # Afficher les règles sous forme de tableau
    rules_display = []
    for idx, rule in enumerate(st.session_state.rules):
        rules_display.append({
            "#": idx + 1,
            "ID": rule["rule_id"],
            "Nom": rule["control_name"],
            "Type": rule["logic_type"],
            "Dimension": rule["control_type"],
            "Colonne(s)": rule["column"],
            "Sévérité": rule["severity"]
        })

    st.dataframe(pd.DataFrame(rules_display), use_container_width=True)

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🗑️ Supprimer toutes les règles", type="secondary"):
            st.session_state.rules = []
            st.session_state.report_generated = False
            st.rerun()

    with col2:
        # Export des règles en JSON
        if st.download_button(
            label="💾 Exporter les règles (JSON)",
            data=json.dumps(st.session_state.rules, indent=2, ensure_ascii=False),
            file_name="dq_rules.json",
            mime="application/json"
        ):
            st.success("Règles exportées !")

st.markdown("---")

# Section 2 : Formulaire de création de règle
st.subheader("➕ Créer une nouvelle règle")

with st.form("rule_form", clear_on_submit=True):
    col1, col2 = st.columns(2)

    with col1:
        rule_id = st.text_input(
            "ID de la règle *",
            placeholder="Ex: DQ01",
            help="Identifiant unique de la règle (ex: DQ01, RULE_001, CHK_EMAIL)"
        )

        control_name = st.text_input(
            "Nom de la règle *",
            placeholder="Ex: Complétude email",
            help="Nom descriptif de la règle"
        )

        control_type = st.selectbox(
            "Dimension qualité *",
            ["Complétude", "Validité", "Unicité", "Cohérence", "Fraîcheur", "Réconciliation"],
            help="Catégorie de contrôle qualité"
        )

        severity = st.selectbox(
            "Sévérité *",
            ["High", "Medium", "Low"],
            help="Niveau de criticité de la règle"
        )

    with col2:
        logic_type = st.selectbox(
            "Type de logique *",
            [
                "not_null",
                "regex",
                "unique",
                "unique_composite",
                "conditional_equals",
                "max_age_days",
                "reconciliation_sum"
            ],
            help="Type de contrôle à appliquer"
        )

        # Instructions dynamiques selon le logic_type
        if logic_type == "not_null":
            st.info("""
            **not_null** : Vérifie qu'une colonne n'a pas de valeurs manquantes

            - **Colonne** : Nom de la colonne à vérifier
            - **Paramètre** : Laisser vide
            - **Seuil** : % max de valeurs manquantes tolérées (0 = zéro toléré)
            """)
        elif logic_type == "regex":
            st.info("""
            **regex** : Vérifie qu'une colonne respecte un format (expression régulière)

            - **Colonne** : Nom de la colonne à vérifier
            - **Paramètre** : Expression régulière (ex: `^[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}$` pour email)
            - **Seuil** : % max de non-conformes tolérés
            """)
        elif logic_type == "unique":
            st.info("""
            **unique** : Vérifie qu'une colonne n'a pas de doublons

            - **Colonne** : Nom de la colonne clé
            - **Paramètre** : Laisser vide
            - **Seuil** : % max de doublons tolérés (0 = zéro toléré)
            """)
        elif logic_type == "unique_composite":
            st.info("""
            **unique_composite** : Vérifie l'unicité sur une combinaison de colonnes

            - **Colonne** : Colonnes séparées par ':' (ex: `series_id:year`)
            - **Paramètre** : Laisser vide
            - **Seuil** : % max de doublons tolérés (0 = zéro toléré)
            """)
        elif logic_type == "conditional_equals":
            st.info("""
            **conditional_equals** : Vérifie une cohérence conditionnelle

            - **Colonne** : `col_condition:col_cible` (ex: `status:balance`)
            - **Paramètre** : `val_condition:val_cible` (ex: `closed:0`)
            - **Seuil** : Tolérance numérique absolue (ex: 0.01)
            """)
        elif logic_type == "max_age_days":
            st.info("""
            **max_age_days** : Vérifie la fraîcheur d'une date

            - **Colonne** : Nom de la colonne date
            - **Paramètre** : Date de référence ISO (`AAAA-MM-JJ`) ou `today`
            - **Seuil** : Âge maximum en jours toléré
            """)
        elif logic_type == "reconciliation_sum":
            st.info("""
            **reconciliation_sum** : Compare des totaux entre fichiers

            - **Colonne** : `col_groupe:col_valeur` (ex: `region:balance`)
            - **Paramètre** : `fichier_ref:col_groupe_ref:col_valeur_ref`
            - **Seuil** : % max d'écart toléré par groupe
            """)

    # Champs spécifiques selon le logic_type
    st.markdown("#### Paramètres de la règle")

    col3, col4, col5 = st.columns(3)

    with col3:
        if logic_type in ["not_null", "regex", "unique", "max_age_days"]:
            column = st.selectbox(
                "Colonne *",
                [""] + available_columns,
                help="Sélectionnez la colonne à contrôler"
            )
        elif logic_type in ["unique_composite", "conditional_equals", "reconciliation_sum"]:
            column = st.text_input(
                "Colonne(s) *",
                placeholder="Ex: col1:col2",
                help="Colonnes séparées par ':' selon le type de règle"
            )
        else:
            column = st.text_input("Colonne *")

    with col4:
        param = st.text_input(
            "Paramètre",
            placeholder="Selon le type de règle",
            help="Paramètre spécifique au type de règle (voir instructions)"
        )

    with col5:
        threshold = st.text_input(
            "Seuil",
            placeholder="Ex: 0, 5, 1.5",
            help="Seuil de tolérance (nombre ou %)"
        )

    description = st.text_area(
        "Description",
        placeholder="Description détaillée de la règle (optionnel)",
        height=80
    )

    col_owner, col_freq, col_kpi = st.columns(3)

    with col_owner:
        owner = st.text_input(
            "Responsable",
            value="Data Quality Team",
            help="Équipe ou personne responsable"
        )

    with col_freq:
        frequency = st.selectbox(
            "Fréquence",
            ["Daily", "Weekly", "Monthly", "On-demand"],
            help="Fréquence d'exécution recommandée"
        )

    with col_kpi:
        kpi = st.text_input(
            "KPI",
            placeholder="Ex: Taux de complétude >= 99%",
            help="Indicateur de performance cible"
        )

    remediation = st.text_area(
        "Action de remédiation",
        placeholder="Que faire en cas d'échec ? (optionnel)",
        height=60
    )

    submitted = st.form_submit_button("✅ Ajouter cette règle", type="primary", use_container_width=True)

    if submitted:
        # Validation
        errors = []

        if not rule_id or rule_id.strip() == "":
            errors.append("L'ID de la règle est obligatoire")
        elif any(r["rule_id"] == rule_id for r in st.session_state.rules):
            errors.append(f"L'ID '{rule_id}' existe déjà")

        if not control_name or control_name.strip() == "":
            errors.append("Le nom de la règle est obligatoire")

        if not column or column.strip() == "":
            errors.append("La colonne est obligatoire")

        if errors:
            for error in errors:
                st.error(f"❌ {error}")
        else:
            # Créer la règle
            new_rule = {
                "rule_id": rule_id.strip(),
                "control_name": control_name.strip(),
                "control_type": control_type,
                "description": description.strip() if description else f"Contrôle {logic_type} sur {column}",
                "logic_type": logic_type,
                "dataset": st.session_state.uploaded_filename,
                "column": column.strip(),
                "param": param.strip() if param else "",
                "threshold": threshold.strip() if threshold else "",
                "severity": severity,
                "frequency": frequency,
                "owner": owner.strip(),
                "output_type": "results_summary",
                "kpi": kpi.strip() if kpi else f"Contrôle {logic_type}",
                "remediation_action": remediation.strip() if remediation else "À définir"
            }

            st.session_state.rules.append(new_rule)
            st.session_state.report_generated = False  # Reset le rapport
            st.success(f"✅ Règle **{rule_id}** ajoutée avec succès !")
            st.rerun()

st.markdown("---")

# Section 3 : Import de règles
st.subheader("📥 Importer des règles")

uploaded_rules = st.file_uploader(
    "Importer des règles depuis un fichier JSON",
    type=['json'],
    help="Chargez un fichier JSON contenant des règles exportées précédemment"
)

if uploaded_rules is not None:
    try:
        imported_rules = json.load(uploaded_rules)

        if isinstance(imported_rules, list):
            st.success(f"✅ {len(imported_rules)} règle(s) trouvée(s) dans le fichier")

            if st.button("💾 Importer ces règles", type="primary"):
                # Vérifier les conflits d'ID
                conflicts = []
                for rule in imported_rules:
                    if any(r["rule_id"] == rule["rule_id"] for r in st.session_state.rules):
                        conflicts.append(rule["rule_id"])

                if conflicts:
                    st.warning(f"⚠️ Conflit d'ID détecté : {', '.join(conflicts)}. Les règles existantes seront conservées.")

                # Ajouter les règles non conflictuelles
                for rule in imported_rules:
                    if not any(r["rule_id"] == rule["rule_id"] for r in st.session_state.rules):
                        # Adapter le nom du dataset
                        rule["dataset"] = st.session_state.uploaded_filename
                        st.session_state.rules.append(rule)

                st.session_state.report_generated = False
                st.success("✅ Règles importées !")
                st.rerun()
        else:
            st.error("❌ Le fichier JSON doit contenir une liste de règles")

    except Exception as e:
        st.error(f"❌ Erreur lors de l'import : {str(e)}")

# Navigation
st.markdown("---")
if len(st.session_state.rules) > 0:
    st.success(f"✅ {len(st.session_state.rules)} règle(s) définie(s). Vous pouvez maintenant générer le rapport !")
    st.info("👉 Passez à l'étape suivante : **📈 Quality Report**")
else:
    st.info("Créez au moins une règle pour pouvoir générer un rapport de qualité.")
