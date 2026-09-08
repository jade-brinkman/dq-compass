import streamlit as st
import pandas as pd
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from ui_helpers import inject_base_style, render_tag, render_navbar, ensure_session_state
from default_rules_catalog import (
    get_all_templates, find_matching_columns, create_rule_from_template,
    get_rule_writing_tips, RULE_WRITING_TIPS
)

st.set_page_config(page_title="Define Rules", layout="wide", initial_sidebar_state="collapsed")

ensure_session_state()
inject_base_style()
render_navbar(current_page="rules")
render_tag("02", "Define rules")

st.title("Define Quality Rules")

# Check that data was uploaded
if not st.session_state.data_uploaded:
    st.warning("Please upload your data first on the **Upload Data** page.")
    st.stop()

st.markdown(f"""
Define quality rules for: **`{st.session_state.uploaded_filename}`**

**{len(st.session_state.uploaded_df):,} rows** x **{len(st.session_state.uploaded_df.columns)} columns**
""")

# Available columns
df = st.session_state.uploaded_df
available_columns = list(df.columns)

# =====================================================
# SECTION: Data Preview
# =====================================================
with st.expander("Data Preview - See your data before defining rules", expanded=True):
    st.markdown("*First 10 rows of your dataset*")
    st.dataframe(df.head(10), use_container_width=True, height=250)

    # Quick column stats
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Columns available:**")
        cols_display = ", ".join([f"`{c}`" for c in available_columns[:10]])
        if len(available_columns) > 10:
            cols_display += f" *...and {len(available_columns) - 10} more*"
        st.markdown(cols_display)

    with col2:
        st.markdown("**Column types detected:**")
        # Show sample values for first few columns
        for col in available_columns[:5]:
            sample_val = df[col].dropna().iloc[0] if len(df[col].dropna()) > 0 else "N/A"
            sample_str = str(sample_val)[:30] + "..." if len(str(sample_val)) > 30 else str(sample_val)
            st.caption(f"• `{col}`: {sample_str}")

st.markdown("---")

# =====================================================
# SECTION: Quick-add default rules
# =====================================================
st.subheader("Quick-add Default Rules")
st.markdown("*Add common quality rules with one click. Select a column and add the rule.*")

templates = get_all_templates()

# Create tabs for rule categories
tab_names = [templates[cat]["name"] for cat in templates.keys()]
tabs = st.tabs(tab_names)

for tab, (cat_key, category) in zip(tabs, templates.items()):
    with tab:
        st.markdown(f"*{category['description']}*")

        for template in category["rules"]:
            col1, col2, col3 = st.columns([1, 2, 1])

            with col1:
                st.markdown(f"**{template['control_name']}**")
                st.caption(template.get('description', ''))

            with col2:
                # Column selection
                if template.get('requires_columns', 0) > 1:
                    # Multiple column selection for composite rules
                    selected_cols = st.multiselect(
                        "Select columns",
                        options=available_columns,
                        key=f"quick_{template['template_id']}_cols",
                        max_selections=template.get('requires_columns', 2),
                        help=f"Select {template.get('requires_columns', 2)} columns for composite check"
                    )
                    selected_column = ":".join(selected_cols) if selected_cols else ""
                else:
                    # Single column selection
                    suggested = template.get('suggested_columns', [])
                    matches = find_matching_columns(available_columns, suggested)

                    # Set default to first match if found
                    default_idx = 0
                    if matches and matches[0] in available_columns:
                        default_idx = available_columns.index(matches[0]) + 1  # +1 for empty option

                    selected_column = st.selectbox(
                        "Column",
                        options=[""] + available_columns,
                        index=default_idx if default_idx < len(available_columns) + 1 else 0,
                        key=f"quick_{template['template_id']}_col",
                        help="Select the column to apply this rule to"
                    )

            with col3:
                st.markdown("")  # Spacing

                # Check if rule ID already exists
                rule_id = f"{template['template_id']}_{selected_column.replace(':', '_')}" if selected_column else template['template_id']
                rule_exists = any(r["rule_id"] == rule_id for r in st.session_state.rules)

                if st.button(
                    "Add rule" if not rule_exists else "Already added",
                    key=f"quick_add_{template['template_id']}",
                    disabled=not selected_column or rule_exists,
                    use_container_width=True
                ):
                    new_rule = create_rule_from_template(
                        template=template,
                        column=selected_column,
                        dataset_name=st.session_state.uploaded_filename,
                        rule_id_suffix=selected_column.replace(":", "_")
                    )
                    st.session_state.rules.append(new_rule)
                    st.session_state.report_generated = False
                    st.success(f"Rule '{new_rule['rule_id']}' added!")
                    st.rerun()

            st.markdown("---")

st.markdown("---")

# =====================================================
# SECTION: Currently defined rules (with individual deletion)
# =====================================================
st.subheader("Currently Defined Rules")

if len(st.session_state.rules) == 0:
    st.info("No rules defined yet. Use the quick-add templates above or create a custom rule below.")
else:
    st.markdown(f"**{len(st.session_state.rules)} rule(s) defined**")

    # Show the rules as a table with delete buttons
    for idx, rule in enumerate(st.session_state.rules):
        col1, col2, col3, col4, col5, col6, col7 = st.columns([0.5, 1.5, 2, 1.5, 1, 1, 0.8])

        with col1:
            st.markdown(f"**{idx + 1}**")

        with col2:
            st.markdown(f"`{rule['rule_id']}`")

        with col3:
            st.markdown(rule['control_name'])

        with col4:
            st.markdown(f"*{rule['logic_type']}*")

        with col5:
            st.markdown(rule['control_type'])

        with col6:
            severity_labels = {"High": "[!]", "Medium": "[~]", "Low": "[-]"}
            st.markdown(f"{severity_labels.get(rule['severity'], '')} {rule['severity']}")

        with col7:
            if st.button("X", key=f"delete_rule_{idx}", help=f"Delete rule {rule['rule_id']}"):
                st.session_state.rules.pop(idx)
                st.session_state.report_generated = False
                st.rerun()

    st.markdown("---")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Remove all rules", type="secondary"):
            st.session_state.rules = []
            st.session_state.report_generated = False
            st.rerun()

    with col2:
        # Export rules as JSON
        if st.download_button(
            label="Export rules (JSON)",
            data=json.dumps(st.session_state.rules, indent=2, ensure_ascii=False),
            file_name="dq_rules.json",
            mime="application/json"
        ):
            st.success("Rules exported.")

st.markdown("---")

# =====================================================
# SECTION: Tips and recommendations
# =====================================================
with st.expander("Tips for writing quality rules", expanded=False):
    st.markdown("**Best practices for effective quality rules**")

    tips = get_rule_writing_tips()
    for i, tip in enumerate(tips, 1):
        st.markdown(f"**{i}. {tip['title']}**")
        st.caption(tip['description'])

st.markdown("---")

# =====================================================
# SECTION: Rule creation form (custom rules)
# =====================================================
st.subheader("Create a Custom Rule")
st.markdown("*Define your own business-specific quality rules using the form below.*")

col1, col2 = st.columns(2)

with col1:
    rule_id = st.text_input(
        "Rule ID *",
        placeholder="e.g. DQ01",
        help="Unique rule identifier (e.g. DQ01, RULE_001, CHK_EMAIL)",
        key="f_rule_id"
    )

    control_name = st.text_input(
        "Rule name *",
        placeholder="e.g. Email completeness",
        help="Descriptive name for the rule",
        key="f_control_name"
    )

    control_type = st.selectbox(
        "Quality dimension *",
        ["Completeness", "Validity", "Uniqueness", "Consistency", "Freshness", "Reconciliation"],
        help="Quality control category",
        key="f_control_type"
    )

    severity = st.selectbox(
        "Severity *",
        ["High", "Medium", "Low"],
        help="Criticality level of the rule",
        key="f_severity"
    )

with col2:
    logic_type = st.selectbox(
        "Logic type *",
        [
            "not_null",
            "regex",
            "unique",
            "unique_composite",
            "conditional_equals",
            "max_age_days",
            "reconciliation_sum"
        ],
        help="Type of check to apply",
        key="f_logic_type"
    )

    # Dynamic instructions based on logic_type
    if logic_type == "not_null":
        st.info("""
        **not_null**: Checks that a column has no missing values

        - **Column**: name of the column to check
        - **Param**: leave empty
        - **Threshold**: max % of missing values tolerated (0 = none tolerated)
        """)
    elif logic_type == "regex":
        st.info("""
        **regex**: Checks that a column matches a format (regular expression)

        - **Column**: name of the column to check
        - **Param**: regular expression (e.g. `^[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}$` for email)
        - **Threshold**: max % of non-conforming values tolerated
        """)
    elif logic_type == "unique":
        st.info("""
        **unique**: Checks that a column has no duplicates

        - **Column**: name of the key column
        - **Param**: leave empty
        - **Threshold**: max % of duplicates tolerated (0 = none tolerated)
        """)
    elif logic_type == "unique_composite":
        st.info("""
        **unique_composite**: Checks uniqueness on a combination of columns

        - **Column**: columns separated by ':' (e.g. `series_id:year`)
        - **Param**: leave empty
        - **Threshold**: max % of duplicates tolerated (0 = none tolerated)
        """)
    elif logic_type == "conditional_equals":
        st.info("""
        **conditional_equals**: Checks a conditional consistency rule

        - **Column**: `condition_col:target_col` (e.g. `status:balance`)
        - **Param**: `condition_val:target_val` (e.g. `closed:0`)
        - **Threshold**: absolute numeric tolerance (e.g. 0.01)
        """)
    elif logic_type == "max_age_days":
        st.info("""
        **max_age_days**: Checks the freshness of a date

        - **Column**: name of the date column
        - **Param**: ISO reference date (`YYYY-MM-DD`) or `today`
        - **Threshold**: maximum age tolerated, in days
        """)
    elif logic_type == "reconciliation_sum":
        st.info("""
        **reconciliation_sum**: Compares totals across files

        - **Column**: `group_col:value_col` (e.g. `region:balance`)
        - **Param**: `ref_file:ref_group_col:ref_value_col`
        - **Threshold**: max % deviation tolerated per group
        """)

# Fields specific to the selected logic_type
st.markdown("#### Rule parameters")

col3, col4, col5 = st.columns(3)

with col3:
    if logic_type in ["not_null", "regex", "unique", "max_age_days"]:
        column = st.selectbox(
            "Column *",
            [""] + available_columns,
            help="Select the column to check",
            key="f_column_select"
        )
    elif logic_type in ["unique_composite", "conditional_equals", "reconciliation_sum"]:
        column = st.text_input(
            "Column(s) *",
            placeholder="e.g. col1:col2",
            help="Columns separated by ':', depending on the rule type",
            key="f_column_text"
        )
    else:
        column = st.text_input("Column *", key="f_column_text")

with col4:
    param = st.text_input(
        "Param",
        placeholder="Depends on the rule type",
        help="Parameter specific to the rule type (see instructions above)",
        key="f_param"
    )

with col5:
    threshold = st.text_input(
        "Threshold",
        placeholder="e.g. 0, 5, 1.5",
        help="Tolerance threshold (number or %)",
        key="f_threshold"
    )

description = st.text_area(
    "Description",
    placeholder="Detailed description of the rule (optional)",
    height=80,
    key="f_description"
)

col_owner, col_freq, col_kpi = st.columns(3)

with col_owner:
    owner = st.text_input(
        "Owner",
        value="Data Quality Team",
        help="Team or person responsible for the rule",
        key="f_owner"
    )

with col_freq:
    frequency = st.selectbox(
        "Frequency",
        ["Daily", "Weekly", "Monthly", "On-demand"],
        help="Recommended execution frequency",
        key="f_frequency"
    )

with col_kpi:
    kpi = st.text_input(
        "KPI",
        placeholder="e.g. Completeness rate >= 99%",
        help="Target performance indicator",
        key="f_kpi"
    )

remediation = st.text_area(
    "Remediation action",
    placeholder="What to do when this rule fails (optional)",
    height=60,
    key="f_remediation"
)

if st.button("Add this rule", type="primary", use_container_width=True):
    # Validation
    errors = []

    if not rule_id or rule_id.strip() == "":
        errors.append("Rule ID is required")
    elif any(r["rule_id"] == rule_id for r in st.session_state.rules):
        errors.append(f"ID '{rule_id}' already exists")

    if not control_name or control_name.strip() == "":
        errors.append("Rule name is required")

    if not column or column.strip() == "":
        errors.append("Column is required")

    if errors:
        for error in errors:
            st.error(error)
    else:
        # Create the rule
        new_rule = {
            "rule_id": rule_id.strip(),
            "control_name": control_name.strip(),
            "control_type": control_type,
            "description": description.strip() if description else f"{logic_type} check on {column}",
            "logic_type": logic_type,
            "dataset": st.session_state.uploaded_filename,
            "column": column.strip(),
            "param": param.strip() if param else "",
            "threshold": threshold.strip() if threshold else "",
            "severity": severity,
            "frequency": frequency,
            "owner": owner.strip(),
            "output_type": "results_summary",
            "kpi": kpi.strip() if kpi else f"{logic_type} check",
            "remediation_action": remediation.strip() if remediation else "To be defined"
        }

        st.session_state.rules.append(new_rule)
        st.session_state.report_generated = False  # Reset the report

        # Clear only the identifying fields, so the user can add the next rule
        # without retyping the dimension / logic type / owner / frequency.
        for k in ["f_rule_id", "f_control_name", "f_column_select", "f_column_text",
                  "f_param", "f_threshold", "f_description", "f_kpi", "f_remediation"]:
            st.session_state.pop(k, None)

        st.success(f"Rule '{rule_id}' added successfully.")
        st.rerun()

st.markdown("---")

# Section 3: Import rules
st.subheader("Import rules")

TEMPLATE_COLUMNS = [
    "rule_id", "control_name", "control_type", "logic_type", "column",
    "param", "threshold", "severity", "frequency", "owner", "kpi",
    "description", "remediation_action",
]

col_upload, col_template = st.columns([2, 1])

with col_upload:
    uploaded_rules = st.file_uploader(
        "Import rules from a JSON, CSV or Excel file",
        type=['json', 'csv', 'xlsx'],
        help="Load a file with previously exported rules, or a CSV/Excel filled in from the template"
    )

with col_template:
    st.markdown("&nbsp;")
    template_df = pd.DataFrame([{
        "rule_id": "DQ01",
        "control_name": "Email completeness",
        "control_type": "Completeness",
        "logic_type": "not_null",
        "column": "email",
        "param": "",
        "threshold": "0",
        "severity": "High",
        "frequency": "Daily",
        "owner": "Data Quality Team",
        "kpi": "Completeness rate >= 99%",
        "description": "Checks that the email column has no missing values",
        "remediation_action": "Contact the source system owner",
    }], columns=TEMPLATE_COLUMNS)

    st.download_button(
        "Download CSV template",
        data=template_df.to_csv(index=False).encode("utf-8"),
        file_name="dq_rules_template.csv",
        mime="text/csv",
        use_container_width=True,
        help="One example row showing the expected columns - replace it and add your own rows"
    )

if uploaded_rules is not None:
    try:
        file_name_lower = uploaded_rules.name.lower()

        if file_name_lower.endswith(".csv"):
            imported_df = pd.read_csv(uploaded_rules, dtype=str).fillna("")
            if "rule_id" not in imported_df.columns:
                st.error(f"The file must contain at least these columns: {', '.join(TEMPLATE_COLUMNS)}")
                imported_rules = []
            else:
                imported_rules = [
                    row for row in imported_df.to_dict(orient="records")
                    if str(row.get("rule_id", "")).strip() != ""
                ]
        elif file_name_lower.endswith(".xlsx"):
            imported_df = pd.read_excel(uploaded_rules, dtype=str).fillna("")
            if "rule_id" not in imported_df.columns:
                st.error(f"The file must contain at least these columns: {', '.join(TEMPLATE_COLUMNS)}")
                imported_rules = []
            else:
                imported_rules = [
                    row for row in imported_df.to_dict(orient="records")
                    if str(row.get("rule_id", "")).strip() != ""
                ]
        else:
            imported_rules = json.load(uploaded_rules)

        if isinstance(imported_rules, list) and len(imported_rules) > 0:
            st.success(f"{len(imported_rules)} rule(s) found in the file — choose which ones to keep below.")

            # Preview with a per-row checkbox: the user picks exactly which
            # rules to import, instead of an all-or-nothing import.
            existing_ids = {r["rule_id"] for r in st.session_state.rules}
            preview_rows = []
            for rule in imported_rules:
                rid = str(rule.get("rule_id", ""))
                preview_rows.append({
                    "Keep": rid not in existing_ids,  # pre-uncheck obvious ID conflicts
                    "rule_id": rid,
                    "control_name": rule.get("control_name", ""),
                    "control_type": rule.get("control_type", ""),
                    "logic_type": rule.get("logic_type", ""),
                    "column": rule.get("column", ""),
                    "severity": rule.get("severity", ""),
                    "already exists": "yes" if rid in existing_ids else "",
                })
            preview_df = pd.DataFrame(preview_rows)

            edited_preview = st.data_editor(
                preview_df,
                use_container_width=True,
                hide_index=True,
                disabled=[c for c in preview_df.columns if c != "Keep"],
                column_config={
                    "Keep": st.column_config.CheckboxColumn("Keep", help="Untick to skip this rule on import"),
                },
                key="rules_import_preview",
            )

            if st.button("Import selected rules", type="primary"):
                selected_ids = set(edited_preview.loc[edited_preview["Keep"], "rule_id"])
                to_import = [r for r in imported_rules if str(r.get("rule_id", "")) in selected_ids]

                if not to_import:
                    st.warning("No rule selected — tick at least one row above.")
                else:
                    conflicts = [r["rule_id"] for r in to_import if r["rule_id"] in existing_ids]
                    if conflicts:
                        st.warning(f"ID conflict detected: {', '.join(conflicts)}. Existing rules will be kept.")

                    added = 0
                    for rule in to_import:
                        if rule["rule_id"] not in existing_ids:
                            # Fill in any missing optional fields and set the dataset name
                            for col in TEMPLATE_COLUMNS:
                                rule.setdefault(col, "")
                            rule["dataset"] = st.session_state.uploaded_filename
                            rule.setdefault("output_type", "results_summary")
                            st.session_state.rules.append(rule)
                            added += 1

                    st.session_state.report_generated = False
                    st.success(f"{added} rule(s) imported.")
                    st.rerun()
        elif isinstance(imported_rules, list):
            st.warning("No usable rule found in this file.")
        else:
            st.error("The JSON file must contain a list of rules")

    except Exception as e:
        st.error(f"Error while importing: {str(e)}")

# Navigation
st.markdown("---")
if len(st.session_state.rules) > 0:
    st.success(f"{len(st.session_state.rules)} rule(s) defined. You can now generate the report.")
    if st.button("Continue to Quality Report", type="primary"):
        st.switch_page("pages/3_Quality_Report.py")
else:
    st.info("Create at least one rule to generate a quality report.")
