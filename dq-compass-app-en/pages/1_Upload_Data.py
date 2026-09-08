import streamlit as st
import pandas as pd
from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from ui_helpers import inject_base_style, render_tag, render_navbar, ensure_session_state
from data_quality_checks import (
    run_all_checks, run_gdpr_check,
    get_severity_icon, get_severity_color
)


def deduplicate_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    """
    Rename duplicate columns by appending _1, _2, etc.
    Returns the modified DataFrame and a list of renamed columns.
    """
    cols = df.columns.tolist()
    seen = {}
    new_cols = []
    renamed = []

    for col in cols:
        if col in seen:
            seen[col] += 1
            new_name = f"{col}_{seen[col]}"
            renamed.append((col, new_name))
            new_cols.append(new_name)
        else:
            seen[col] = 0
            new_cols.append(col)

    df.columns = new_cols
    return df, renamed


@st.cache_data(show_spinner=False)
def compute_quality_checks(_df_hash: str, df: pd.DataFrame) -> tuple[list, dict]:
    """Cache quality checks based on DataFrame hash."""
    basic_checks = run_all_checks(df)
    gdpr_check = run_gdpr_check(df)
    return basic_checks, gdpr_check


@st.cache_data(show_spinner=False)
def compute_column_stats(_df_hash: str, df: pd.DataFrame) -> pd.DataFrame:
    """Cache column statistics computation."""
    col_info = []
    total_rows = len(df)
    for col in df.columns:
        non_empty = (df[col].astype(str).str.strip() != "").sum()
        col_info.append({
            "Column": col,
            "Non-empty": non_empty,
            "Empty": total_rows - non_empty,
            "Completeness": f"{non_empty / total_rows * 100:.1f}%",
            "Unique": df[col].nunique()
        })
    return pd.DataFrame(col_info)


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

        # Handle duplicate column names
        renamed_cols = []
        if df.columns.duplicated().any():
            df, renamed_cols = deduplicate_columns(df)

        st.success(f"File loaded successfully. Detected separator: `{repr(best_sep)}`")

        if renamed_cols:
            st.warning(f"**{len(renamed_cols)} duplicate column(s) detected and renamed:**")
            for old_name, new_name in renamed_cols[:10]:
                st.caption(f"  • `{old_name}` → `{new_name}`")
            if len(renamed_cols) > 10:
                st.caption(f"  • ...and {len(renamed_cols) - 10} more")

        # Metadata - fast estimation
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Rows", f"{len(df):,}")
        with col2:
            st.metric("Columns", len(df.columns))
        with col3:
            # Fast memory estimate (avoid deep=True which is slow)
            mem_estimate = len(df) * len(df.columns) * 50 / 1024 / 1024  # rough estimate
            st.metric("Est. memory", f"~{mem_estimate:.1f} MB")

        st.markdown("---")

        # Data preview (fast - no computation)
        st.subheader("Data preview (first rows)")
        st.dataframe(df.head(10), use_container_width=True)

        # Create a hash for caching based on shape and first/last values
        df_hash = f"{len(df)}_{len(df.columns)}_{uploaded_file.name}"

        # =====================================================
        # SECTION: Quality Checks (in expander - computed on demand)
        # =====================================================
        with st.expander("Quality Assessment (automatic checks)", expanded=False):
            with st.spinner("Running quality checks..."):
                basic_checks, gdpr_check = compute_quality_checks(df_hash, df)

            # Display basic checks
            st.markdown("##### Data Quality Checks")
            checks_with_issues = [c for c in basic_checks if c['severity'] != 'ok']
            checks_ok = [c for c in basic_checks if c['severity'] == 'ok']

            if checks_with_issues:
                st.warning(f"{len(checks_with_issues)} potential issue(s) detected")

                for check in checks_with_issues:
                    icon = get_severity_icon(check['severity'])
                    color = get_severity_color(check['severity'])

                    # Display check header with colored box (no nested expander)
                    st.markdown(
                        f"<div style='background-color: {color}20; border-left: 4px solid {color}; "
                        f"padding: 10px; margin: 10px 0; border-radius: 4px;'>"
                        f"<strong>{icon} {check['label']} - {check['severity'].upper()}</strong></div>",
                        unsafe_allow_html=True
                    )

                    for issue in check['issues']:
                        st.markdown(f"  - {issue}")

                    if check['check'] == 'duplicate_rows' and check['details']['duplicate_count'] > 0:
                        st.caption(f"  Duplicate rows: {check['details']['duplicate_count']:,} ({check['details']['duplicate_pct']:.1f}%)")

                    if check['check'] == 'empty_columns' and check['details']['count'] > 0:
                        st.caption(f"  Empty columns: {', '.join(check['details']['empty_columns'][:10])}")

                    if check['check'] == 'missing_values' and check['details']['high_missing_columns']:
                        for col_info in check['details']['high_missing_columns'][:5]:
                            st.caption(f"  - {col_info['column']}: {col_info['missing_pct']:.1f}% missing")

                    if check['check'] == 'encoding_issues' and check['details']['problematic_columns']:
                        for prob in check['details']['problematic_columns'][:5]:
                            st.caption(f"  - {prob['column']}: {prob['affected_rows']} rows affected")

            if checks_ok:
                st.success(f"{len(checks_ok)} check(s) passed")

            # GDPR section
            st.markdown("##### Personal Data Detection (GDPR)")

            if gdpr_check['severity'] == 'warning':
                st.warning("**Potential personal data detected**")
                detected = gdpr_check['details']['detected_columns']

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
                    st.markdown(f"- **{cat.replace('_', ' ').title()}**: {', '.join(cols)} *(via {method_label})*")
            else:
                st.success("No obvious personal data detected")

        # Store checks in a variable for later use (when validating)
        # Compute only if not already done
        if 'current_basic_checks' not in st.session_state or st.session_state.get('current_file_hash') != df_hash:
            st.session_state.current_basic_checks, st.session_state.current_gdpr_check = compute_quality_checks(df_hash, df)
            st.session_state.current_file_hash = df_hash

        st.markdown("---")

        # Column information (in expander)
        with st.expander("Column information", expanded=False):
            col_df = compute_column_stats(df_hash, df)
            st.dataframe(col_df, use_container_width=True)

        # Automatic detection of a wide (year-column) layout
        year_cols = [col for col in df.columns if str(col).strip().isdigit() and len(str(col).strip()) == 4]

        if year_cols:
            st.warning(f"""
            **Wide layout detected**: {len(year_cols)} time-series columns found ({min(year_cols)} to {max(year_cols)})

            The engine will automatically reshape this into a **long format** at run time:
            - Each row will be duplicated for every year that has a value
            - A `year` column and a `value` column will be created

            **Current shape**: {len(df):,} rows x {len(df.columns)} columns
            **Estimated reshaped size**: up to ~{len(df) * len(year_cols):,} rows
            """)

        st.markdown("---")

        # =====================================================
        # SECTION: Advanced options
        # =====================================================
        with st.expander("Advanced options - choose the rows/columns to analyze", expanded=False):
            st.markdown(
                "By default the full file is used. Narrow it down if you only want to "
                "run quality checks on part of the data."
            )

            adv_col1, adv_col2 = st.columns(2)

            with adv_col1:
                st.markdown("**Columns**")
                selected_columns = st.multiselect(
                    "Columns to include in the analysis",
                    options=list(df.columns),
                    default=list(df.columns),
                    key="adv_selected_columns",
                    help="Columns left out won't be available when you define rules.",
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
            with st.spinner("Preparing data..."):
                # Apply the row/column selection
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

                # Save the DataFrame
                final_df.to_csv(file_path, index=False)

                # Save to session state
                st.session_state.data_uploaded = True
                st.session_state.uploaded_file_path = str(file_path)
                st.session_state.uploaded_filename = safe_filename
                st.session_state.uploaded_df = final_df
                st.session_state.report_generated = False

                # Store basic checks results
                st.session_state.basic_quality_checks = st.session_state.get('current_basic_checks', [])
                st.session_state.gdpr_check = st.session_state.get('current_gdpr_check', {})

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

# Show current status if data was already uploaded
if st.session_state.data_uploaded:
    st.markdown("---")
    st.success(f"""
    **Data ready**

    File: `{st.session_state.uploaded_filename}`
    Rows: {len(st.session_state.uploaded_df):,}
    Columns: {len(st.session_state.uploaded_df.columns)}

    You can upload a new file above to replace the current data.
    """)

    st.markdown("---")

    # =====================================================
    # SECTION: Optional reference file (reconciliation only)
    # =====================================================
    with st.expander("Optional: reference file for reconciliation checks", expanded=False):
        st.markdown(
            "Only needed if you plan to add a **Reconciliation** rule (e.g. DQ06-style: "
            "compare totals in your data above against a source-of-truth file). "
            "Every other rule type ignores this file — skip it otherwise."
        )

        reference_file = st.file_uploader(
            "Choose the reference/source-of-truth CSV file",
            type=['csv'],
            key="reference_file_uploader",
            help="A file with one row per group (e.g. region, category) and a total/value column to compare against."
        )

        if reference_file is not None:
            try:
                ref_sample = reference_file.read(10000).decode('utf-8', errors='ignore')
                reference_file.seek(0)

                ref_best_sep = ','
                ref_max_cols = 0
                for sep in [',', ';', '\t', '|']:
                    try:
                        test_df = pd.read_csv(pd.io.common.StringIO(ref_sample), sep=sep, nrows=5)
                        if len(test_df.columns) > ref_max_cols:
                            ref_max_cols = len(test_df.columns)
                            ref_best_sep = sep
                    except Exception:
                        continue

                ref_df = pd.read_csv(reference_file, sep=ref_best_sep, dtype=str, keep_default_na=False)
                if ref_df.columns.duplicated().any():
                    ref_df, _ = deduplicate_columns(ref_df)

                st.dataframe(ref_df.head(5), use_container_width=True)
                st.caption(f"{len(ref_df):,} row(s) x {len(ref_df.columns)} column(s)")

                # Reference file must live in the same folder as the main data
                # file so the engine's data_dir scan finds both (see
                # `dataset` = "main.csv;reference.csv" on the reconciliation rule).
                temp_dir = Path(tempfile.gettempdir()) / "dq_compass" / "data"
                temp_dir.mkdir(parents=True, exist_ok=True)
                ref_safe_filename = reference_file.name.replace(" ", "_")
                if ref_safe_filename == st.session_state.uploaded_filename:
                    st.error(
                        "The reference file must have a different name from the main data file "
                        f"(`{st.session_state.uploaded_filename}`) so the engine can tell them apart."
                    )
                else:
                    ref_file_path = temp_dir / ref_safe_filename
                    ref_df.to_csv(ref_file_path, index=False)

                    st.session_state.reference_uploaded = True
                    st.session_state.reference_file_path = str(ref_file_path)
                    st.session_state.reference_filename = ref_safe_filename
                    st.session_state.reference_df = ref_df

                    st.success(f"Reference file ready: `{ref_safe_filename}`. You can now use a Reconciliation rule on the Define Rules page.")
            except Exception as e:
                st.error(f"Error while loading the reference file: {str(e)}")

        elif st.session_state.get("reference_uploaded"):
            st.info(f"Reference file already set: `{st.session_state.reference_filename}` "
                    f"({len(st.session_state.reference_df):,} rows). Upload a new one above to replace it.")

    st.markdown("---")

    if st.button("Continue to Define Rules", type="primary", use_container_width=True):
        st.switch_page("pages/2_Define_Rules.py")
