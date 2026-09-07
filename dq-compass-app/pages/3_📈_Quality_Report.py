import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

# Ajouter le wrapper du moteur
sys.path.insert(0, str(Path(__file__).parent.parent))
from engine_wrapper import DQEngineWrapper

st.set_page_config(page_title="Quality Report", page_icon="📈", layout="wide")

st.title("📈 Data Quality Report")

# Vérifications préliminaires
if not st.session_state.data_uploaded:
    st.warning("⚠️ Veuillez d'abord uploader vos données dans la page **📊 Upload Data**")
    st.stop()

if len(st.session_state.rules) == 0:
    st.warning("⚠️ Veuillez définir au moins une règle dans la page **📝 Define Rules**")
    st.stop()

st.markdown(f"""
Rapport de qualité pour : **`{st.session_state.uploaded_filename}`**

**{len(st.session_state.rules)} règle(s)** définies
""")

st.markdown("---")

# Bouton de génération/régénération du rapport
col1, col2 = st.columns([3, 1])

with col1:
    if not st.session_state.report_generated:
        st.info("👉 Cliquez sur **'Générer le rapport'** pour exécuter les contrôles qualité")
    else:
        st.success("✅ Rapport généré. Vous pouvez le régénérer à tout moment.")

with col2:
    if st.button("🔄 Générer le rapport", type="primary", use_container_width=True):
        st.session_state.report_generated = False  # Reset pour forcer la régénération
        st.session_state.last_run_results = None

# Génération du rapport
if not st.session_state.report_generated or st.session_state.last_run_results is None:
    with st.spinner("⏳ Exécution des contrôles qualité en cours..."):
        # Créer une barre de progression
        progress_bar = st.progress(0)
        status_text = st.empty()

        def update_progress(current, total, message):
            progress = int(current / total * 100)
            progress_bar.progress(progress)
            status_text.text(f"{message} ({current}/{total})")

        # Exécuter le moteur
        engine = DQEngineWrapper(
            data_file_path=st.session_state.uploaded_file_path,
            rules=st.session_state.rules
        )

        results = engine.run(progress_callback=update_progress)

        progress_bar.empty()
        status_text.empty()

        if results['status'] == 'success':
            st.session_state.last_run_results = results
            st.session_state.report_generated = True
            st.success(f"✅ {results['message']}")
            st.rerun()
        else:
            st.error(f"❌ {results['message']}")
            st.stop()

# Afficher le rapport
if st.session_state.report_generated and st.session_state.last_run_results:
    results = st.session_state.last_run_results
    summary_df = results['summary']
    exceptions = results['exceptions']

    # Section 1 : Métriques globales
    st.subheader("📊 Vue d'ensemble")

    # Calculer les statistiques
    total_rules = len(summary_df)
    passed = len(summary_df[summary_df['status'] == 'PASS'])
    failed = len(summary_df[summary_df['status'] == 'FAIL'])
    errors = len(summary_df[summary_df['status'] == 'ERROR'])
    pass_rate = (passed / total_rules * 100) if total_rules > 0 else 0

    # Afficher les métriques en colonnes
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Règles", total_rules)

    with col2:
        st.metric("✅ Réussies", passed, delta=None, delta_color="off")

    with col3:
        st.metric("❌ Échecs", failed, delta=None, delta_color="off")

    with col4:
        st.metric("⚠️ Erreurs", errors, delta=None, delta_color="off")

    with col5:
        st.metric("Taux de réussite", f"{pass_rate:.1f}%", delta=None, delta_color="off")

    st.markdown("---")

    # Section 2 : Visualisations
    st.subheader("📉 Visualisations")

    col1, col2 = st.columns(2)

    with col1:
        # Graphique en camembert : répartition PASS/FAIL/ERROR
        status_counts = summary_df['status'].value_counts()

        fig_pie = go.Figure(data=[go.Pie(
            labels=status_counts.index,
            values=status_counts.values,
            marker=dict(colors=['#00CC96', '#EF553B', '#FFA15A']),
            hole=0.4
        )])

        fig_pie.update_layout(
            title="Répartition des statuts",
            height=400
        )

        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        # Graphique en barres : par dimension
        dim_status = summary_df.groupby(['dimension', 'status']).size().reset_index(name='count')

        fig_bar = px.bar(
            dim_status,
            x='dimension',
            y='count',
            color='status',
            title="Résultats par dimension qualité",
            color_discrete_map={'PASS': '#00CC96', 'FAIL': '#EF553B', 'ERROR': '#FFA15A'},
            height=400
        )

        st.plotly_chart(fig_bar, use_container_width=True)

    # Section 3 : Détails par sévérité
    st.markdown("---")
    st.subheader("⚖️ Analyse par sévérité")

    severity_status = summary_df.groupby(['severity', 'status']).size().reset_index(name='count')

    fig_severity = px.bar(
        severity_status,
        x='severity',
        y='count',
        color='status',
        title="Résultats par niveau de sévérité",
        color_discrete_map={'PASS': '#00CC96', 'FAIL': '#EF553B', 'ERROR': '#FFA15A'},
        height=350,
        category_orders={'severity': ['High', 'Medium', 'Low']}
    )

    st.plotly_chart(fig_severity, use_container_width=True)

    st.markdown("---")

    # Section 4 : Tableau détaillé des résultats
    st.subheader("📋 Résultats détaillés")

    # Filtres
    col1, col2, col3 = st.columns(3)

    with col1:
        status_filter = st.multiselect(
            "Filtrer par statut",
            options=['PASS', 'FAIL', 'ERROR'],
            default=['PASS', 'FAIL', 'ERROR']
        )

    with col2:
        dimension_filter = st.multiselect(
            "Filtrer par dimension",
            options=summary_df['dimension'].unique().tolist(),
            default=summary_df['dimension'].unique().tolist()
        )

    with col3:
        severity_filter = st.multiselect(
            "Filtrer par sévérité",
            options=['High', 'Medium', 'Low'],
            default=['High', 'Medium', 'Low']
        )

    # Appliquer les filtres
    filtered_df = summary_df[
        (summary_df['status'].isin(status_filter)) &
        (summary_df['dimension'].isin(dimension_filter)) &
        (summary_df['severity'].isin(severity_filter))
    ]

    # Formater le DataFrame pour l'affichage
    display_df = filtered_df.copy()

    # Ajouter des emojis pour le statut
    status_emoji = {'PASS': '✅', 'FAIL': '❌', 'ERROR': '⚠️'}
    display_df['statut'] = display_df['status'].apply(lambda x: f"{status_emoji.get(x, '')} {x}")

    # Réorganiser les colonnes
    display_cols = ['statut', 'rule_id', 'control_name', 'dimension', 'severity',
                    'total_records', 'failed_records', 'kpi_value', 'kpi_label']

    display_df = display_df[display_cols]

    # Renommer pour l'affichage
    display_df.columns = ['Statut', 'ID Règle', 'Nom', 'Dimension', 'Sévérité',
                          'Total', 'Échecs', 'KPI Valeur', 'KPI']

    st.dataframe(
        display_df,
        use_container_width=True,
        height=400
    )

    # Export des résultats
    col1, col2 = st.columns(2)

    with col1:
        csv_summary = summary_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="💾 Télécharger le résumé (CSV)",
            data=csv_summary,
            file_name=f"dq_report_summary_{results['run_id']}.csv",
            mime="text/csv"
        )

    with col2:
        # Export JSON complet
        import json
        json_export = {
            'run_id': results['run_id'],
            'timestamp': results['timestamp'],
            'filename': st.session_state.uploaded_filename,
            'summary': summary_df.to_dict(orient='records'),
            'statistics': {
                'total_rules': total_rules,
                'passed': int(passed),
                'failed': int(failed),
                'errors': int(errors),
                'pass_rate': float(pass_rate)
            }
        }

        st.download_button(
            label="💾 Télécharger le rapport complet (JSON)",
            data=json.dumps(json_export, indent=2, ensure_ascii=False),
            file_name=f"dq_report_full_{results['run_id']}.json",
            mime="application/json"
        )

    st.markdown("---")

    # Section 5 : Exceptions (règles en échec)
    failed_rules = summary_df[summary_df['status'] == 'FAIL']

    if len(failed_rules) > 0:
        st.subheader("🔍 Exceptions détaillées (règles en échec)")

        st.warning(f"⚠️ {len(failed_rules)} règle(s) en échec avec des exceptions détectées")

        for _, rule in failed_rules.iterrows():
            rule_id = rule['rule_id']

            if rule_id in exceptions and len(exceptions[rule_id]) > 0:
                with st.expander(f"❌ {rule_id} - {rule['control_name']} ({len(exceptions[rule_id])} exception(s))"):
                    st.markdown(f"""
                    **Dimension** : {rule['dimension']}
                    **Sévérité** : {rule['severity']}
                    **KPI** : {rule['kpi_label']} = {rule['kpi_value']}
                    **Total enregistrements** : {rule['total_records']}
                    **Enregistrements en échec** : {rule['failed_records']}
                    """)

                    exc_df = exceptions[rule_id]

                    # Limiter l'affichage aux 100 premières exceptions
                    if len(exc_df) > 100:
                        st.info(f"ℹ️ Affichage des 100 premières exceptions sur {len(exc_df)}")
                        st.dataframe(exc_df.head(100), use_container_width=True)
                    else:
                        st.dataframe(exc_df, use_container_width=True)

                    # Bouton de téléchargement des exceptions
                    csv_exc = exc_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label=f"💾 Télécharger les exceptions {rule_id} (CSV)",
                        data=csv_exc,
                        file_name=f"exceptions_{rule_id}_{results['run_id']}.csv",
                        mime="text/csv",
                        key=f"download_{rule_id}"
                    )
    else:
        st.success("✅ Aucune règle en échec ! Toutes les règles ont réussi.")

    st.markdown("---")

    # Section 6 : Recommandations
    st.subheader("💡 Recommandations")

    if failed > 0:
        st.warning(f"""
        **{failed} règle(s) en échec détectée(s)**

        Actions recommandées :
        1. Consultez les exceptions détaillées ci-dessus pour identifier les enregistrements problématiques
        2. Vérifiez les règles avec sévérité **High** en priorité
        3. Corrigez les données à la source ou ajustez les seuils de tolérance si nécessaire
        4. Régénérez le rapport après correction pour vérifier l'amélioration
        """)

    if errors > 0:
        st.error(f"""
        **{errors} erreur(s) de configuration détectée(s)**

        Actions recommandées :
        1. Vérifiez la configuration des règles en erreur
        2. Assurez-vous que les colonnes référencées existent dans les données
        3. Vérifiez la syntaxe des paramètres (regex, formats, etc.)
        4. Modifiez les règles dans la page **📝 Define Rules** et régénérez le rapport
        """)

    if passed == total_rules and total_rules > 0:
        st.success("""
        🎉 **Excellent !** Toutes les règles de qualité sont respectées.

        Votre jeu de données est conforme à tous les contrôles définis.
        Pensez à :
        - Documenter ce niveau de qualité comme référence
        - Automatiser ces contrôles pour surveiller la qualité dans le temps
        - Partager ces règles avec votre équipe
        """)

    st.markdown("---")

    # Informations de run
    with st.expander("ℹ️ Informations d'exécution"):
        st.markdown(f"""
        **Run ID** : `{results['run_id']}`
        **Timestamp** : `{results['timestamp']}`
        **Fichier** : `{st.session_state.uploaded_filename}`
        **Nombre de règles** : {total_rules}
        **Log file** : `{results.get('log_file', 'N/A')}`
        """)
