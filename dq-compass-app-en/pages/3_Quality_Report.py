import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys
import json
import tempfile
import io
import zipfile

# Add the engine wrapper's path
sys.path.insert(0, str(Path(__file__).parent.parent))
from engine_wrapper import DQEngineWrapper
from ui_helpers import inject_base_style, render_tag, render_navbar, ensure_session_state
from pdf_report import generate_pdf_report

# ---------------------------------------------------------------------------
# BF-REP-01 — traffic-light scorecard color per rule:
#   green  : failed_records == 0
#   red    : severity High and failing, OR failure rate >= 5%
#   orange : failing, severity Medium/Low, failure rate < 5%
# (An ERROR status — a configuration issue, not a data failure — is always
# shown red: it still needs immediate attention, and BNF-04 caps the report
# at 3 colors.)
# ---------------------------------------------------------------------------
def _traffic_light(row) -> tuple:
    status = row.get("status")
    if status == "ERROR":
        return "red", "#EF553B"

    failed = row.get("failed_records")
    total = row.get("total_records")
    try:
        failed = int(failed)
    except (TypeError, ValueError):
        failed = 0
    try:
        total = int(total)
    except (TypeError, ValueError):
        total = 0

    if failed == 0:
        return "green", "#00CC96"

    if row.get("severity") == "High":
        return "red", "#EF553B"

    fail_rate = (failed / total * 100) if total else 100.0
    if fail_rate < 5:
        return "orange", "#FFA15A"
    return "red", "#EF553B"

st.set_page_config(page_title="Quality Report", layout="wide", initial_sidebar_state="collapsed")

ensure_session_state()
inject_base_style()
render_navbar(current_page="report")
render_tag("03", "Quality report")

st.title("Data Quality Report")

# Preliminary checks
if not st.session_state.data_uploaded:
    st.warning("Please upload your data first on the **Upload Data** page.")
    st.stop()

if len(st.session_state.rules) == 0:
    st.warning("Please define at least one rule on the **Define Rules** page.")
    st.stop()

st.markdown(f"""
Quality report for: **`{st.session_state.uploaded_filename}`**

**{len(st.session_state.rules)} rule(s)** defined
""")

st.markdown("---")

# Report generation button
col1, col2 = st.columns([3, 1])

with col1:
    if not st.session_state.report_generated:
        st.info("Click **Generate report** to run the quality checks.")
    else:
        st.success("Report generated. You can regenerate it at any time.")

with col2:
    if st.button("Generate report", type="primary", use_container_width=True):
        st.session_state.report_generated = False  # Force regeneration
        st.session_state.last_run_results = None

# Report generation
if not st.session_state.report_generated or st.session_state.last_run_results is None:
    with st.spinner("Running quality checks..."):
        # Progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()

        def update_progress(current, total, message):
            progress = int(current / total * 100)
            progress_bar.progress(progress)
            status_text.text(f"{message} ({current}/{total})")

        # Run the engine
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
            st.success(results['message'])
            st.rerun()
        else:
            st.error(results['message'])
            st.stop()

# Display the report
if st.session_state.report_generated and st.session_state.last_run_results:
    results = st.session_state.last_run_results
    summary_df = results['summary']
    exceptions = results['exceptions']

    # Section 1: Overview metrics
    st.subheader("Overview")

    # Compute statistics
    total_rules = len(summary_df)
    passed = len(summary_df[summary_df['status'] == 'PASS'])
    failed = len(summary_df[summary_df['status'] == 'FAIL'])
    errors = len(summary_df[summary_df['status'] == 'ERROR'])
    pass_rate = (passed / total_rules * 100) if total_rules > 0 else 0

    # Metric columns
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total rules", total_rules)

    with col2:
        st.metric("Passed", passed, delta=None, delta_color="off")

    with col3:
        st.metric("Failed", failed, delta=None, delta_color="off")

    with col4:
        st.metric("Errors", errors, delta=None, delta_color="off")

    with col5:
        st.metric("Pass rate", f"{pass_rate:.1f}%", delta=None, delta_color="off")

    st.markdown("---")

    # =====================================================
    # Section 1bis: Scorecard (BF-REP-01) — traffic lights, one screen,
    # at most 3 colors (BNF-04)
    # =====================================================
    st.subheader("Scorecard")
    st.caption(
        "Green = no failure - Orange = failing, Medium/Low severity, under 5% failure rate - "
        "Red = High severity failure, or failure rate at/above 5%"
    )

    badge_html = ["<div style='display:flex;flex-wrap:wrap;gap:8px;'>"]
    for _, row in summary_df.iterrows():
        _, hex_color = _traffic_light(row)
        badge_html.append(
            f"<div style='display:flex;align-items:center;gap:6px;border:1px solid {hex_color};"
            f"border-radius:8px;padding:4px 10px;font-size:0.85rem;'>"
            f"<span style='width:10px;height:10px;border-radius:50%;background:{hex_color};"
            f"display:inline-block;'></span>"
            f"<strong>{row['rule_id']}</strong><span style='opacity:0.7;'>· {row['dimension']}</span>"
            f"</div>"
        )
    badge_html.append("</div>")
    st.markdown("".join(badge_html), unsafe_allow_html=True)

    st.markdown("---")

    # Section 2: Charts
    st.subheader("Charts")

    col1, col2 = st.columns(2)

    with col1:
        # Pie chart: PASS/FAIL/ERROR breakdown
        status_counts = summary_df['status'].value_counts()

        fig_pie = go.Figure(data=[go.Pie(
            labels=status_counts.index,
            values=status_counts.values,
            marker=dict(colors=['#00CC96', '#EF553B', '#FFA15A']),
            hole=0.4
        )])

        fig_pie.update_layout(
            title="Status breakdown",
            height=400
        )

        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        # Bar chart: by dimension
        dim_status = summary_df.groupby(['dimension', 'status']).size().reset_index(name='count')

        fig_bar = px.bar(
            dim_status,
            x='dimension',
            y='count',
            color='status',
            title="Results by quality dimension",
            color_discrete_map={'PASS': '#00CC96', 'FAIL': '#EF553B', 'ERROR': '#FFA15A'},
            height=400
        )

        st.plotly_chart(fig_bar, use_container_width=True)

    # Section 3: Breakdown by severity
    st.markdown("---")
    st.subheader("Breakdown by severity")

    severity_status = summary_df.groupby(['severity', 'status']).size().reset_index(name='count')

    fig_severity = px.bar(
        severity_status,
        x='severity',
        y='count',
        color='status',
        title="Results by severity level",
        color_discrete_map={'PASS': '#00CC96', 'FAIL': '#EF553B', 'ERROR': '#FFA15A'},
        height=350,
        category_orders={'severity': ['High', 'Medium', 'Low']}
    )

    st.plotly_chart(fig_severity, use_container_width=True)

    st.markdown("---")

    # Section 4: Detailed results table
    st.subheader("Detailed results")

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        status_filter = st.multiselect(
            "Filter by status",
            options=['PASS', 'FAIL', 'ERROR'],
            default=['PASS', 'FAIL', 'ERROR']
        )

    with col2:
        dimension_filter = st.multiselect(
            "Filter by dimension",
            options=summary_df['dimension'].unique().tolist(),
            default=summary_df['dimension'].unique().tolist()
        )

    with col3:
        severity_filter = st.multiselect(
            "Filter by severity",
            options=['High', 'Medium', 'Low'],
            default=['High', 'Medium', 'Low']
        )

    # Apply filters
    filtered_df = summary_df[
        (summary_df['status'].isin(status_filter)) &
        (summary_df['dimension'].isin(dimension_filter)) &
        (summary_df['severity'].isin(severity_filter))
    ]

    # Format the DataFrame for display
    display_df = filtered_df.copy()

    # Reorder columns
    display_cols = ['status', 'rule_id', 'control_name', 'dimension', 'severity',
                    'total_records', 'failed_records', 'kpi_value', 'kpi_label']

    display_df = display_df[display_cols]

    # Rename for display
    display_df.columns = ['Status', 'Rule ID', 'Name', 'Dimension', 'Severity',
                          'Total', 'Failed', 'KPI value', 'KPI']

    st.dataframe(
        display_df,
        use_container_width=True,
        height=400
    )

    # =====================================================
    # Section 4bis: Control coverage (BF-REP-03) — which rule checks which
    # dataset/column
    # =====================================================
    st.markdown("---")
    st.subheader("Control coverage")
    st.caption("Which rule is active, and which dataset/column it controls.")

    coverage_rows = [{
        "Rule ID": r.get("rule_id", ""),
        "Control name": r.get("control_name", ""),
        "Dimension": r.get("control_type", ""),
        "Dataset(s)": r.get("dataset", ""),
        "Column(s)": r.get("column", ""),
    } for r in st.session_state.rules]
    st.dataframe(pd.DataFrame(coverage_rows), use_container_width=True, height=250)

    # =====================================================
    # SECTION: Export options (CSV, JSON, PDF, evidence pack)
    # =====================================================
    st.markdown("---")
    st.subheader("Export Report")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        csv_summary = summary_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download summary (CSV)",
            data=csv_summary,
            file_name=f"dq_report_summary_{results['run_id']}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col2:
        # Full JSON export
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
            label="Download full report (JSON)",
            data=json.dumps(json_export, indent=2, ensure_ascii=False),
            file_name=f"dq_report_full_{results['run_id']}.json",
            mime="application/json",
            use_container_width=True
        )

    with col3:
        # PDF export
        try:
            pdf_bytes = generate_pdf_report(
                results=results,
                filename=st.session_state.uploaded_filename,
                total_rules=total_rules,
                passed=passed,
                failed=failed,
                errors=errors,
                pass_rate=pass_rate
            )

            st.download_button(
                label="Download report (PDF)",
                data=pdf_bytes,
                file_name=f"dq_report_{results['run_id']}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"PDF generation error: {str(e)}")
            st.caption("Make sure reportlab is installed: pip install reportlab")

    with col4:
        # Evidence pack (BF-AUD-01/02): the full runs/<run_id>/ folder written
        # by the engine — manifest.json, results_summary.csv, exceptions/,
        # engine.log — zipped for a one-click, audit-ready download.
        run_dir = results.get("run_dir")
        if run_dir and Path(run_dir).exists():
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for file_path in Path(run_dir).rglob("*"):
                    if file_path.is_file():
                        zf.write(file_path, arcname=file_path.relative_to(Path(run_dir).parent))
            zip_buffer.seek(0)

            st.download_button(
                label="Download evidence pack (ZIP)",
                data=zip_buffer,
                file_name=f"dq_evidence_pack_{results['run_id']}.zip",
                mime="application/zip",
                use_container_width=True,
                help="manifest.json + results_summary.csv + exceptions/ + engine.log — audit trail for this run",
            )
        else:
            st.caption("Evidence pack unavailable for this run.")

    st.markdown("---")

    # =====================================================
    # SECTION: Validation Loop - Re-import corrected CSV
    # =====================================================
    st.subheader("Validation Loop")
    st.markdown("""
    After fixing the data issues identified in this report, you can re-import the corrected CSV
    to verify that the errors have been resolved. The same rules will be applied automatically.
    """)

    with st.expander("Re-import corrected CSV", expanded=False):
        st.markdown("""
        **How it works:**
        1. Export the data with exceptions (use the CSV export above)
        2. Fix the identified issues in your source system or spreadsheet
        3. Upload the corrected CSV here
        4. The same rules will be re-executed to validate corrections
        """)

        corrected_file = st.file_uploader(
            "Upload corrected CSV",
            type=['csv'],
            key="corrected_csv_uploader",
            help="Upload the corrected version of your data file"
        )

        if corrected_file is not None:
            try:
                # Read the corrected file
                corrected_df = pd.read_csv(corrected_file, dtype=str, keep_default_na=False)

                st.success(f"Corrected file loaded: {len(corrected_df):,} rows x {len(corrected_df.columns)} columns")

                # Show comparison
                original_df = st.session_state.uploaded_df

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Original rows", len(original_df))
                with col2:
                    st.metric("Corrected rows", len(corrected_df))

                # Check column compatibility
                original_cols = set(original_df.columns)
                corrected_cols = set(corrected_df.columns)

                if original_cols != corrected_cols:
                    missing = original_cols - corrected_cols
                    extra = corrected_cols - original_cols
                    if missing:
                        st.warning(f"Missing columns in corrected file: {', '.join(missing)}")
                    if extra:
                        st.info(f"New columns in corrected file: {', '.join(extra)}")

                if st.button("Validate corrected data", type="primary", use_container_width=True):
                    # Save the corrected file
                    temp_dir = Path(tempfile.gettempdir()) / "dq_compass" / "data"
                    temp_dir.mkdir(parents=True, exist_ok=True)

                    corrected_filename = f"corrected_{st.session_state.uploaded_filename}"
                    corrected_path = temp_dir / corrected_filename

                    corrected_df.to_csv(corrected_path, index=False)

                    # Update session state
                    st.session_state.uploaded_file_path = str(corrected_path)
                    st.session_state.uploaded_filename = corrected_filename
                    st.session_state.uploaded_df = corrected_df
                    st.session_state.report_generated = False
                    st.session_state.last_run_results = None

                    # Update dataset reference in rules
                    for rule in st.session_state.rules:
                        rule['dataset'] = corrected_filename

                    st.success("Corrected data loaded. Regenerating report...")
                    st.rerun()

            except Exception as e:
                st.error(f"Error loading corrected file: {str(e)}")

    st.markdown("---")

    # Section 5: Exceptions (failed rules)
    failed_rules = summary_df[summary_df['status'] == 'FAIL']

    if len(failed_rules) > 0:
        st.subheader("Exception details (failed rules)")

        st.warning(f"{len(failed_rules)} rule(s) failed with detected exceptions")

        for _, rule in failed_rules.iterrows():
            rule_id = rule['rule_id']

            if rule_id in exceptions and len(exceptions[rule_id]) > 0:
                with st.expander(f"{rule_id} - {rule['control_name']} ({len(exceptions[rule_id])} exception(s))"):
                    st.markdown(f"""
                    **Dimension**: {rule['dimension']}
                    **Severity**: {rule['severity']}
                    **KPI**: {rule['kpi_label']} = {rule['kpi_value']}
                    **Total records**: {rule['total_records']}
                    **Failed records**: {rule['failed_records']}
                    """)

                    exc_df = exceptions[rule_id]

                    # Cap display at the first 100 exceptions
                    if len(exc_df) > 100:
                        st.info(f"Showing the first 100 exceptions out of {len(exc_df)}")
                        st.dataframe(exc_df.head(100), use_container_width=True)
                    else:
                        st.dataframe(exc_df, use_container_width=True)

                    # Download button for the exceptions
                    csv_exc = exc_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label=f"Download {rule_id} exceptions (CSV)",
                        data=csv_exc,
                        file_name=f"exceptions_{rule_id}_{results['run_id']}.csv",
                        mime="text/csv",
                        key=f"download_{rule_id}"
                    )
    else:
        st.success("No failed rules. Every rule passed.")

    st.markdown("---")

    # Section 6: Recommendations
    st.subheader("Recommendations")

    if failed > 0:
        st.warning(f"""
        **{failed} rule(s) failed**

        Recommended actions:
        1. Review the exception details above to identify the problematic records
        2. Address **High** severity rules first
        3. Fix the data at the source, or adjust the tolerance thresholds if needed
        4. Use the **Validation Loop** above to re-import corrected data and verify improvements
        """)

    if errors > 0:
        st.error(f"""
        **{errors} configuration error(s) detected**

        Recommended actions:
        1. Review the configuration of the rules in error
        2. Make sure the referenced columns exist in the data
        3. Check the parameter syntax (regex, formats, etc.)
        4. Update the rules on the **Define Rules** page and regenerate the report
        """)

    if passed == total_rules and total_rules > 0:
        st.success("""
        **All quality rules passed.**

        Your dataset conforms to every control that was defined.
        Consider:
        - Documenting this quality level as a baseline
        - Automating these checks to monitor quality over time
        - Sharing these rules with your team
        """)

    st.markdown("---")

    # Run information
    with st.expander("Run details"):
        st.markdown(f"""
        **Run ID**: `{results['run_id']}`
        **Timestamp**: `{results['timestamp']}`
        **File**: `{st.session_state.uploaded_filename}`
        **Number of rules**: {total_rules}
        **Log file**: `{results.get('log_file', 'N/A')}`
        """)
