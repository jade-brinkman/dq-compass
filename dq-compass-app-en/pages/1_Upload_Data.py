import streamlit as st
import pandas as pd
from pathlib import Path
import tempfile
import shutil
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from ui_helpers import inject_base_style, render_tag, render_navbar, ensure_session_state
from data_quality_checks import (
    run_all_checks, run_gdpr_check,
    get_severity_icon, get_severity_color
)

st.set_page_config(page_title="Upload Data", layout="wide", initial_sidebar_state="collapsed")

ensure_session_state()
inject_base_style()
render_navbar(current_page="upload")
render_tag("01", "Upload data")

st.title("Upload Your Data")

st.markdown("""
Upload a CSV file to start the quality analysis.

**Supported formats:**
- CSV (comma, semicolon, or tab separated)
- Encoding: UTF-8, Latin-1, CP1252

**Data layout:**
- Standard layout: 1 row = 1 record
- Wide (pivot) layout: the engine automatically detects time-series columns
  (4-digit years) and reshapes them into a long format
""")

st.markdown("---")

# File upload
uploaded_file = st.file_uploader(
    "Choose a CSV file",
    type=['csv'],
    help="Select your data file in CSV format"
)

if uploaded_file is not None:
    try:
        # Automatic separator detection
        st.info("Detecting file format...")

        # Read the first lines to detect the separator
        sample = uploaded_file.read(10000).decode('utf-8', errors='ignore')
        uploaded_file.seek(0)

        # Try different separators
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

        # Load the full file
        df = pd.read_csv(uploaded_file, sep=best_sep, dtype=str, keep_default_na=False)

        st.success(f"File loaded successfully. Detected separator: `{repr(best_sep)}`")

        # Metadata
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Rows", f"{len(df):,}")
        with col2:
            st.metric("Columns", len(df.columns))
        with col3:
            # Estimate memory footprint
            memory_usage = df.memory_usage(deep=True).sum() / 1024 / 1024
            st.metric("Memory size", f"{memory_usage:.2f} MB")

        st.markdown("---")

        # =====================================================
        # SECTION: Basic Quality Checks (auto-detection)
        # =====================================================
        st.subheader("Automatic Quality Assessment")
        st.markdown("*Basic checks performed automatically to detect common data issues*")

        # Run basic checks
        basic_checks = run_all_checks(df)

        # Display checks in a clean grid
        checks_with_issues = [c for c in basic_checks if c['severity'] != 'ok']
        checks_ok = [c for c in basic_checks if c['severity'] == 'ok']

        if checks_with_issues:
            st.warning(f"{len(checks_with_issues)} potential issue(s) detected")

            for check in checks_with_issues:
                icon = get_severity_icon(check['severity'])
                with st.expander(f"{icon} {check['label']} - {check['severity'].upper()}", expanded=True):
                    for issue in check['issues']:
                        st.markdown(f"- {issue}")

                    # Show details if available
                    if check['check'] == 'duplicate_rows' and check['details']['duplicate_count'] > 0:
                        st.caption(f"Duplicate rows: {check['details']['duplicate_count']:,} ({check['details']['duplicate_pct']:.1f}%)")

                    if check['check'] == 'empty_columns' and check['details']['count'] > 0:
                        st.caption(f"Empty columns: {', '.join(check['details']['empty_columns'])}")

                    if check['check'] == 'missing_values' and check['details']['high_missing_columns']:
                        cols_info = check['details']['high_missing_columns']
                        for col_info in cols_info[:5]:
                            st.caption(f"- {col_info['column']}: {col_info['missing_pct']:.1f}% missing")

                    if check['check'] == 'encoding_issues' and check['details']['problematic_columns']:
                        for prob in check['details']['problematic_columns'][:5]:
                            st.caption(f"- {prob['column']}: {prob['affected_rows']} rows affected")

        if checks_ok:
            with st.expander(f"[OK] {len(checks_ok)} check(s) passed", expanded=False):
                for check in checks_ok:
                    st.markdown(f"- {check['label']}")

        st.markdown("---")

        # =====================================================
        # SECTION: GDPR / Personal Data Detection
        # =====================================================
        st.subheader("Personal Data Detection (GDPR)")

        gdpr_check = run_gdpr_check(df)

        if gdpr_check['severity'] == 'warning':
            st.warning("**Potential personal data detected**")
            st.markdown("The following columns may contain GDPR-sensitive data. Please ensure proper handling.")

            detected = gdpr_check['details']['detected_columns']

            # Group by category
            categories = {}
            for item in detected:
                cat = item['category']
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(item)

            for cat, items in categories.items():
                cols = [item['column'] for item in items]
                detection = items[0]['detection_method']
                method_label = "column name" if detection == "column_name" else "content pattern"
                st.markdown(f"- **{cat.replace('_', ' ').title()}**: {', '.join(cols)} *(detected via {method_label})*")

            st.info("""
            **Recommendations:**
            - Verify these columns actually contain personal data
            - Ensure you have proper authorization to process this data
            - Consider anonymization or pseudonymization if appropriate
            - This detection does not block processing - it's only an alert
            """)
        else:
            st.success("No obvious personal data detected in column names or content patterns")
            st.caption("Note: This is an automated check and may not catch all personal data. Manual review is recommended.")

        st.markdown("---")

        # Data preview
        st.subheader("Data preview (first rows)")
        st.dataframe(df.head(10), use_container_width=True)

        st.markdown("---")

        # Column information
        st.subheader("Column information")

        col_info = []
        for col in df.columns:
            non_empty = (df[col].str.strip() != "").sum()
            empty = len(df) - non_empty
            col_info.append({
                "Column": col,
                "Non-empty values": non_empty,
                "Empty values": empty,
                "Completeness rate": f"{non_empty / len(df) * 100:.2f}%",
                "Unique values": df[col].nunique()
            })

        col_df = pd.DataFrame(col_info)
        st.dataframe(col_df, use_container_width=True)

        # Automatic detection of a wide (year-column) layout
        year_cols = [col for col in df.columns if str(col).strip().isdigit() and len(str(col).strip()) == 4]

        if year_cols:
            st.warning(f"""
            **Wide layout detected**: {len(year_cols)} time-series columns found ({min(year_cols)} to {max(year_cols)})

            The engine will automatically reshape this into a **long format** at run time:
            - Each row will be duplicated for every year that has a value
            - Empty values will be filtered out automatically
            - A `year` column will be created
            - A `value` column will hold the values

            **Current shape**: {len(df):,} rows x {len(df.columns)} columns
            **Estimated reshaped size**: up to ~{len(df) * len(year_cols):,} rows (after filtering empty values)
            """)

        st.markdown("---")

        # =====================================================
        # SECTION: Advanced options — restrict the analysis to a subset
        # of rows/columns of the CSV before it is validated
        # =====================================================
        with st.expander("Advanced options - choose the rows/columns to analyze", expanded=False):
            st.markdown(
                "By default the full file is used. Narrow it down if you only want to "
                "run quality checks on part of the data (e.g. skip a footer, or ignore "
                "columns that are out of scope for this analysis)."
            )

            adv_col1, adv_col2 = st.columns(2)

            with adv_col1:
                st.markdown("**Columns**")
                selected_columns = st.multiselect(
                    "Columns to include in the analysis",
                    options=list(df.columns),
                    default=list(df.columns),
                    key="adv_selected_columns",
                    help="Columns left out won't be available when you define rules below.",
                )

            with adv_col2:
                st.markdown("**Rows**")
                skip_rows = st.number_input(
                    "Skip the first N rows",
                    min_value=0, max_value=max(len(df) - 1, 0), value=0, step=1,
                    key="adv_skip_rows",
                )
                limit_rows = st.number_input(
                    "Use only the first M rows (0 = all)",
                    min_value=0, max_value=len(df), value=0, step=1,
                    key="adv_limit_rows",
                )

            preview_df = df
            if selected_columns:
                preview_df = preview_df[selected_columns]
            if skip_rows:
                preview_df = preview_df.iloc[skip_rows:]
            if limit_rows:
                preview_df = preview_df.iloc[:limit_rows]

            st.caption(
                f"With these options: {len(preview_df):,} row(s) x {len(preview_df.columns)} "
                f"column(s) will be used for the analysis."
            )

        st.markdown("---")

        # Confirmation button
        if st.button("Validate and use this data", type="primary", use_container_width=True):
            # Apply the row/column selection chosen above (defaults to the
            # full file when nothing was changed)
            columns_to_use = st.session_state.get("adv_selected_columns") or list(df.columns)
            skip_n = st.session_state.get("adv_skip_rows", 0) or 0
            limit_n = st.session_state.get("adv_limit_rows", 0) or 0

            final_df = df[columns_to_use].copy()
            if skip_n:
                final_df = final_df.iloc[skip_n:]
            if limit_n:
                final_df = final_df.iloc[:limit_n]
            final_df = final_df.reset_index(drop=True)

            # Save the file to a temporary session folder
            temp_dir = Path(tempfile.gettempdir()) / "dq_compass" / "data"
            temp_dir.mkdir(parents=True, exist_ok=True)

            # Safe filename
            safe_filename = uploaded_file.name.replace(" ", "_")
            file_path = temp_dir / safe_filename

            # Save the (possibly restricted) DataFrame
            final_df.to_csv(file_path, index=False)

            # Save to session state
            st.session_state.data_uploaded = True
            st.session_state.uploaded_file_path = str(file_path)
            st.session_state.uploaded_filename = safe_filename
            st.session_state.uploaded_df = final_df
            st.session_state.report_generated = False  # Reset the report

            # Store basic checks results for reference (computed on the full
            # upload, before any row/column restriction, so nothing is hidden
            # from the automatic checks)
            st.session_state.basic_quality_checks = basic_checks
            st.session_state.gdpr_check = gdpr_check

            st.rerun()

    except Exception as e:
        st.error(f"""
        **Error while loading the file**

        ```
        {str(e)}
        ```

        Please check that:
        - The file is a valid CSV
        - The encoding is UTF-8 or compatible
        - The file is not corrupted
        """)

else:
    st.info("No file selected. Upload a CSV file to get started.")

# Show current status if data was already uploaded, and let the user move on.
# This block does not depend on any button click state from the run above, so it
# stays correct and clickable across reruns (this is what "Continue" needs to work).
if st.session_state.data_uploaded:
    st.markdown("---")
    st.success(f"""
    **Data ready**

    File: `{st.session_state.uploaded_filename}`
    Rows: {len(st.session_state.uploaded_df):,}
    Columns: {len(st.session_state.uploaded_df.columns)}

    You can upload a new file above to replace the current data.
    """)

    if st.button("Continue to Define Rules", type="primary", use_container_width=True):
        st.switch_page("pages/2_Define_Rules.py")
