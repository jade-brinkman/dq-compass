import streamlit as st
import pandas as pd
import json
import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from ui_helpers import inject_base_style, render_tag, render_navbar, ensure_session_state
from default_rules_catalog import (
    get_all_templates, find_matching_columns, create_rule_from_template,
    get_rule_writing_tips, RULE_WRITING_TIPS
)


# =====================================================
# VALIDATION FUNCTIONS FOR CUSTOM RULES
# =====================================================
def validate_column_exists(column: str, available_columns: list, logic_type: str) -> tuple[bool, str, str]:
    """
    Validate that column(s) exist in the dataset.
    Returns (is_valid, error_message, suggestion).
    """
    if not column or column.strip() == "":
        return False, "Column is required.", ""

    # For composite rules, columns are separated by ':'
    if logic_type in ["unique_composite", "conditional_equals", "reconciliation_sum"]:
        cols = [c.strip() for c in column.split(":")]
        missing_cols = [c for c in cols if c and c not in available_columns]

        if missing_cols:
            # Find similar column names for suggestion
            suggestions = []
            for missing in missing_cols:
                similar = find_similar_columns(missing, available_columns)
                if similar:
                    suggestions.append(f"'{missing}' → did you mean '{similar[0]}'?")

            suggestion_text = " | ".join(suggestions) if suggestions else ""
            return False, f"Column(s) not found: {', '.join(missing_cols)}", suggestion_text
    else:
        if column not in available_columns:
            similar = find_similar_columns(column, available_columns)
            suggestion = f"Did you mean '{similar[0]}'?" if similar else ""
            return False, f"Column '{column}' does not exist in the data.", suggestion

    return True, "", ""


def find_similar_columns(target: str, available: list, max_suggestions: int = 3) -> list:
    """Find similar column names using simple string matching."""
    target_lower = target.lower()
    scored = []

    for col in available:
        col_lower = col.lower()
        # Exact substring match
        if target_lower in col_lower or col_lower in target_lower:
            scored.append((col, 0))
        # Starts with same letters
        elif col_lower.startswith(target_lower[:3]) if len(target_lower) >= 3 else False:
            scored.append((col, 1))
        # Contains similar characters
        else:
            common = sum(1 for c in target_lower if c in col_lower)
            if common >= len(target_lower) * 0.5:
                scored.append((col, 2))

    scored.sort(key=lambda x: x[1])
    return [col for col, _ in scored[:max_suggestions]]


def validate_regex_param(param: str, rule_id: str) -> tuple[bool, str, str]:
    """
    Validate that a regex pattern is provided and syntactically correct.
    Returns (is_valid, error_message, suggestion).
    """
    if not param or param.strip() == "":
        return False, "Regex pattern is required for 'regex' rule type.", \
            "Example patterns: ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$ (email), ^\\d{5}$ (5 digits)"

    try:
        re.compile(param)
        return True, "", ""
    except re.error as e:
        return False, f"Invalid regex pattern: {str(e)}", \
            "Check your regex syntax. Common issues: unescaped special chars (use \\\\ for \\), unmatched parentheses."


def validate_threshold(threshold: str, logic_type: str) -> tuple[bool, str, str]:
    """
    Validate that threshold is a valid number when required.
    Returns (is_valid, error_message, suggestion).
    """
    if not threshold or threshold.strip() == "":
        # Threshold is optional for most rules (defaults to 0)
        return True, "", ""

    try:
        val = float(threshold)
        if val < 0:
            return False, "Threshold cannot be negative.", "Use a value >= 0"
        return True, "", ""
    except ValueError:
        return False, f"Threshold must be a number, got '{threshold}'.", "Example: 0, 5, 1.5"


def validate_conditional_equals_format(column: str, param: str) -> tuple[bool, str, str]:
    """
    Validate conditional_equals specific format.
    column: col_condition:col_target
    param: val_condition:val_target
    """
    errors = []
    suggestions = []

    if ":" not in column:
        errors.append("Column must be in format 'condition_col:target_col'")
        suggestions.append("Example: status:balance")
    elif len(column.split(":")) != 2:
        errors.append("Column must contain exactly 2 columns separated by ':'")
        suggestions.append("Format: condition_column:target_column")

    if not param or param.strip() == "":
        errors.append("Param is required for conditional_equals")
        suggestions.append("Format: condition_value:target_value (e.g., closed:0)")
    elif ":" not in param:
        errors.append("Param must be in format 'condition_value:target_value'")
        suggestions.append("Example: closed:0")
    elif len(param.split(":")) != 2:
        errors.append("Param must contain exactly 2 values separated by ':'")
        suggestions.append("Format: condition_value:expected_target_value")

    if errors:
        return False, " | ".join(errors), " | ".join(suggestions)
    return True, "", ""


def validate_unique_composite_format(column: str) -> tuple[bool, str, str]:
    """
    Validate unique_composite specific format.
    column: col1:col2[:col3...]
    """
    if ":" not in column:
        return False, "unique_composite requires multiple columns separated by ':'", \
            "Example: series_id:year or client_id:product:date"

    cols = [c.strip() for c in column.split(":")]
    if len(cols) < 2:
        return False, "At least 2 columns are required for unique_composite", \
            "Format: column1:column2[:column3...]"

    empty_cols = [i+1 for i, c in enumerate(cols) if not c]
    if empty_cols:
        return False, f"Empty column name at position {empty_cols}", \
            "Remove extra ':' characters"

    return True, "", ""


def validate_max_age_days_param(param: str) -> tuple[bool, str, str]:
    """
    Validate max_age_days param (reference date).
    """
    if not param or param.strip() == "":
        return False, "Reference date is required for max_age_days", \
            "Use 'today' or an ISO date (e.g., 2024-01-15)"

    param = param.strip().lower()
    if param == "today":
        return True, "", ""

    # Try to parse as ISO date
    try:
        from datetime import datetime
        datetime.fromisoformat(param.upper() if param[0].isdigit() else param)
        return True, "", ""
    except (ValueError, IndexError):
        return False, f"Invalid date format: '{param}'", \
            "Use 'today' or ISO format: YYYY-MM-DD (e.g., 2024-01-15)"


def validate_reconciliation_sum_format(column: str, param: str) -> tuple[bool, str, str]:
    """
    Validate reconciliation_sum specific format.
    column: group_col:value_col
    param: ref_file:ref_group_col:ref_value_col
    """
    errors = []
    suggestions = []

    if ":" not in column:
        errors.append("Column must be in format 'group_col:value_col'")
        suggestions.append("Example: region:amount")
    elif len(column.split(":")) != 2:
        errors.append("Column must contain exactly 2 columns (group:value)")
        suggestions.append("Format: grouping_column:value_column")

    if not param or param.strip() == "":
        errors.append("Param is required for reconciliation_sum")
        suggestions.append("Format: ref_file:ref_group_col:ref_value_col")
    elif param.count(":") != 2:
        errors.append("Param must be in format 'ref_file:ref_group_col:ref_value_col'")
        suggestions.append("Example: reference.csv:region:expected_amount")

    if errors:
        return False, " | ".join(errors), " | ".join(suggestions)
    return True, "", ""


def validate_custom_rule(rule_id: str, control_name: str, logic_type: str,
                         column: str, param: str, threshold: str,
                         available_columns: list, existing_rules: list) -> list[dict]:
    """
    Comprehensive validation of a custom rule.
    Returns a list of error dicts with 'message' and 'suggestion' keys.
    """
    errors = []

    # Basic required fields
    if not rule_id or rule_id.strip() == "":
        errors.append({"message": "Rule ID is required", "suggestion": "Example: DQ01, RULE_EMAIL, CHK_001"})
    elif any(r["rule_id"] == rule_id for r in existing_rules):
        errors.append({"message": f"Rule ID '{rule_id}' already exists", "suggestion": "Choose a unique identifier"})

    if not control_name or control_name.strip() == "":
        errors.append({"message": "Rule name is required", "suggestion": "Example: Email format validation"})

    # Column validation
    is_valid, msg, suggestion = validate_column_exists(column, available_columns, logic_type)
    if not is_valid:
        errors.append({"message": msg, "suggestion": suggestion})

    # Logic-type specific validation
    if logic_type == "regex":
        is_valid, msg, suggestion = validate_regex_param(param, rule_id or "rule")
        if not is_valid:
            errors.append({"message": msg, "suggestion": suggestion})

    elif logic_type == "conditional_equals":
        is_valid, msg, suggestion = validate_conditional_equals_format(column, param)
        if not is_valid:
            errors.append({"message": msg, "suggestion": suggestion})

    elif logic_type == "unique_composite":
        is_valid, msg, suggestion = validate_unique_composite_format(column)
        if not is_valid:
            errors.append({"message": msg, "suggestion": suggestion})

    elif logic_type == "max_age_days":
        is_valid, msg, suggestion = validate_max_age_days_param(param)
        if not is_valid:
            errors.append({"message": msg, "suggestion": suggestion})

    elif logic_type == "reconciliation_sum":
        is_valid, msg, suggestion = validate_reconciliation_sum_format(column, param)
        if not is_valid:
            errors.append({"message": msg, "suggestion": suggestion})

    # Threshold validation (for all types)
    is_valid, msg, suggestion = validate_threshold(threshold, logic_type)
    if not is_valid:
        errors.append({"message": msg, "suggestion": suggestion})

    return errors

st.set_page_config(page_title="Define Rules", layout="wide", initial_sidebar_state="collapsed")

ensure_session_state()
inject_base_style()
render_navbar(current_page="rules")
render_tag("02", "Define rules")

st.title("Define Quality Rules")

# Check that data was uploaded
if not st.session_state.data_uploaded or st.session_state.uploaded_df is None:
    st.warning("Please upload your data first on the **Upload Data** page.")
    st.stop()

# Initialize session state for success messages and form reset
if 'rule_added_message' not in st.session_state:
    st.session_state.rule_added_message = None
if 'form_key_suffix' not in st.session_state:
    st.session_state.form_key_suffix = 0

# Show success message if a rule was just added
if st.session_state.rule_added_message:
    st.success(st.session_state.rule_added_message)
    st.session_state.rule_added_message = None  # Clear after showing

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
            is_reconciliation = template.get('logic_type') == 'reconciliation_sum'
            reference_ready = st.session_state.get('reference_uploaded') and st.session_state.get('reference_df') is not None

            if is_reconciliation and not reference_ready:
                # No reference file yet: show the template but explain what's
                # missing instead of a column picker the user can't complete.
                st.markdown(f"**{template['control_name']}**")
                st.caption(template.get('description', ''))
                st.info(
                    "Upload a reference file first, on the **Upload Data** page "
                    "('Optional: reference file for reconciliation checks'), then come back here."
                )
                st.markdown("---")
                continue

            col1, col2, col3 = st.columns([1, 2, 1])

            with col1:
                st.markdown(f"**{template['control_name']}**")
                st.caption(template.get('description', ''))

            with col2:
                if is_reconciliation:
                    # Needs 2 columns from the MAIN dataset (group, value) and
                    # 2 columns from the REFERENCE dataset (ref_group, ref_value).
                    ref_columns = list(st.session_state.reference_df.columns)
                    st.caption(f"Reference file: `{st.session_state.reference_filename}`")

                    rc1, rc2 = st.columns(2)
                    with rc1:
                        main_group = st.selectbox("Group column (your data)", [""] + available_columns,
                                                   key=f"quick_{template['template_id']}_main_group")
                        ref_group = st.selectbox("Group column (reference file)", [""] + ref_columns,
                                                  key=f"quick_{template['template_id']}_ref_group")
                    with rc2:
                        main_value = st.selectbox("Value column (your data)", [""] + available_columns,
                                                   key=f"quick_{template['template_id']}_main_value")
                        ref_value = st.selectbox("Value column (reference file)", [""] + ref_columns,
                                                  key=f"quick_{template['template_id']}_ref_value")

                    selected_column = f"{main_group}:{main_value}" if main_group and main_value else ""
                    ref_param = f"{st.session_state.reference_filename}:{ref_group}:{ref_value}" if ref_group and ref_value else ""
                    fields_complete = bool(main_group and main_value and ref_group and ref_value)
                # Column selection
                elif template.get('requires_columns', 0) > 1:
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

                if is_reconciliation:
                    rule_id = f"{template['template_id']}_{main_group}_{main_value}" if fields_complete else template['template_id']
                    rule_exists = any(r["rule_id"] == rule_id for r in st.session_state.rules)
                    can_add = fields_complete and not rule_exists
                else:
                    # Check if rule ID already exists
                    rule_id = f"{template['template_id']}_{selected_column.replace(':', '_')}" if selected_column else template['template_id']
                    rule_exists = any(r["rule_id"] == rule_id for r in st.session_state.rules)
                    can_add = bool(selected_column) and not rule_exists

                # Use a form to handle the button click properly
                add_clicked = st.button(
                    "Add rule" if not rule_exists else "Already added",
                    key=f"quick_add_{template['template_id']}",
                    disabled=not can_add,
                    use_container_width=True
                )

                if add_clicked and can_add:
                    if is_reconciliation:
                        new_rule = create_rule_from_template(
                            template=template,
                            column=selected_column,
                            dataset_name=f"{st.session_state.uploaded_filename};{st.session_state.reference_filename}",
                            rule_id_suffix=f"{main_group}_{main_value}",
                            param_override=ref_param
                        )
                    else:
                        new_rule = create_rule_from_template(
                            template=template,
                            column=selected_column,
                            dataset_name=st.session_state.uploaded_filename,
                            rule_id_suffix=selected_column.replace(":", "_")
                        )
                    st.session_state.rules.append(new_rule)
                    st.session_state.report_generated = False
                    st.toast(f"Rule {new_rule['rule_id']} added!", icon="✅")

            st.markdown("---")

# =====================================================
# SECTION: Tips and recommendations (moved up, before custom rules)
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

# Form key suffix for resetting form fields after adding a rule
fk = st.session_state.form_key_suffix

col1, col2 = st.columns(2)

with col1:
    rule_id = st.text_input(
        "Rule ID *",
        placeholder="e.g. DQ01",
        help="Unique rule identifier (e.g. DQ01, RULE_001, CHK_EMAIL)",
        key=f"f_rule_id_{fk}"
    )

    control_name = st.text_input(
        "Rule name *",
        placeholder="e.g. Email completeness",
        help="Descriptive name for the rule",
        key=f"f_control_name_{fk}"
    )

    control_type = st.selectbox(
        "Quality dimension *",
        ["Completeness", "Validity", "Uniqueness", "Consistency", "Freshness", "Reconciliation"],
        help="Quality control category",
        key=f"f_control_type_{fk}"
    )

    severity = st.selectbox(
        "Severity *",
        ["High", "Medium", "Low"],
        help="Criticality level of the rule",
        key=f"f_severity_{fk}"
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
        key=f"f_logic_type_{fk}"
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
        ref_hint = (
            f"Reference file detected: `{st.session_state.reference_filename}` — it will be added "
            "to this rule's dataset automatically."
            if st.session_state.get("reference_uploaded")
            else "No reference file yet — upload one on the **Upload Data** page first "
                 "('Optional: reference file for reconciliation checks'), or this rule will ERROR at run time."
        )
        st.info(f"""
        **reconciliation_sum**: Compares totals across files

        - **Column**: `group_col:value_col` (e.g. `region:balance`)
        - **Param**: `ref_file:ref_group_col:ref_value_col`
        - **Threshold**: max % deviation tolerated per group

        {ref_hint}
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
            key=f"f_column_select_{fk}"
        )
    elif logic_type in ["unique_composite", "conditional_equals", "reconciliation_sum"]:
        column = st.text_input(
            "Column(s) *",
            placeholder="e.g. col1:col2",
            help="Columns separated by ':', depending on the rule type",
            key=f"f_column_text_{fk}"
        )
    else:
        column = st.text_input("Column *", key=f"f_column_text_{fk}")

with col4:
    # Param is required for regex, max_age_days, conditional_equals, reconciliation_sum
    param_required = logic_type in ["regex", "max_age_days", "conditional_equals", "reconciliation_sum"]
    param_label = "Param *" if param_required else "Param"
    param = st.text_input(
        param_label,
        placeholder="Depends on the rule type",
        help="Parameter specific to the rule type (see instructions above)",
        key=f"f_param_{fk}"
    )

with col5:
    threshold = st.text_input(
        "Threshold",
        placeholder="e.g. 0, 5, 1.5",
        help="Tolerance threshold (number or %)",
        key=f"f_threshold_{fk}"
    )

description = st.text_area(
    "Description",
    placeholder="Detailed description of the rule (optional)",
    height=80,
    key=f"f_description_{fk}"
)

col_owner, col_freq, col_kpi = st.columns(3)

with col_owner:
    owner = st.text_input(
        "Owner",
        value="Data Quality Team",
        help="Team or person responsible for the rule",
        key=f"f_owner_{fk}"
    )

with col_freq:
    frequency = st.selectbox(
        "Frequency",
        ["Daily", "Weekly", "Monthly", "On-demand"],
        help="Recommended execution frequency",
        key=f"f_frequency_{fk}"
    )

with col_kpi:
    kpi = st.text_input(
        "KPI",
        placeholder="e.g. Completeness rate >= 99%",
        help="Target performance indicator",
        key=f"f_kpi_{fk}"
    )

remediation = st.text_area(
    "Remediation action",
    placeholder="What to do when this rule fails (optional)",
    height=60,
    key=f"f_remediation_{fk}"
)

if st.button("Add this rule", type="primary", use_container_width=True):
    # Comprehensive validation
    validation_errors = validate_custom_rule(
        rule_id=rule_id,
        control_name=control_name,
        logic_type=logic_type,
        column=column,
        param=param,
        threshold=threshold,
        available_columns=available_columns,
        existing_rules=st.session_state.rules
    )

    if validation_errors:
        st.error("**Validation failed** - Please fix the following issues:")
        for err in validation_errors:
            st.markdown(f"❌ **{err['message']}**")
            if err.get('suggestion'):
                st.caption(f"   💡 {err['suggestion']}")
    else:
        # Reconciliation rules need both the main file and the reference
        # file listed in `dataset` (';'-separated) so the engine loads both.
        rule_dataset = st.session_state.uploaded_filename
        if logic_type == "reconciliation_sum" and st.session_state.get("reference_uploaded"):
            rule_dataset = f"{st.session_state.uploaded_filename};{st.session_state.reference_filename}"

        # Create the rule
        new_rule = {
            "rule_id": rule_id.strip(),
            "control_name": control_name.strip(),
            "control_type": control_type,
            "description": description.strip() if description else f"{logic_type} check on {column}",
            "logic_type": logic_type,
            "dataset": rule_dataset,
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

        # Show success toast
        st.toast(f"Rule {rule_id} added!", icon="✅")
        st.success(f"Rule **{rule_id}** added successfully! You can add another rule or continue to the report.")

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
                            # Reconciliation rules need the reference file listed
                            # too (';'-separated) - overwriting with only the
                            # main filename here silently broke every imported
                            # reconciliation_sum rule.
                            if rule.get("logic_type") == "reconciliation_sum" and st.session_state.get("reference_uploaded"):
                                rule["dataset"] = f"{st.session_state.uploaded_filename};{st.session_state.reference_filename}"
                            else:
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

# =====================================================
# SECTION: Currently defined rules (at the end, in expander)
# =====================================================
st.markdown("---")

rules_count = len(st.session_state.rules)
expander_title = f"Currently Defined Rules ({rules_count})" if rules_count > 0 else "Currently Defined Rules"

with st.expander(expander_title, expanded=rules_count > 0):
    if rules_count == 0:
        st.info("No rules defined yet. Use the quick-add templates above or create a custom rule.")
    else:
        # Create a DataFrame for display
        rules_data = []
        for idx, rule in enumerate(st.session_state.rules):
            rules_data.append({
                "#": idx + 1,
                "Rule ID": rule['rule_id'],
                "Name": rule['control_name'],
                "Type": rule['logic_type'],
                "Dimension": rule['control_type'],
                "Severity": rule['severity'],
                "Column": rule.get('column', '')[:30] + ('...' if len(rule.get('column', '')) > 30 else '')
            })

        rules_df = pd.DataFrame(rules_data)
        st.dataframe(rules_df, use_container_width=True, hide_index=True)

        st.markdown("---")

        # Delete individual rules
        st.markdown("**Delete a rule:**")
        rule_options = [f"{r['rule_id']} - {r['control_name']}" for r in st.session_state.rules]

        col_del1, col_del2 = st.columns([3, 1])
        with col_del1:
            rule_to_delete = st.selectbox(
                "Select rule to delete",
                options=[""] + rule_options,
                key="rule_to_delete",
                label_visibility="collapsed"
            )
        with col_del2:
            if st.button("Delete", disabled=not rule_to_delete, use_container_width=True):
                if rule_to_delete:
                    idx = rule_options.index(rule_to_delete)
                    st.session_state.rules.pop(idx)
                    st.session_state.report_generated = False
                    st.rerun()

        st.markdown("---")

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Remove all rules", type="secondary", use_container_width=True):
                st.session_state.rules = []
                st.session_state.report_generated = False
                st.rerun()

        with col2:
            st.download_button(
                label="Export rules (JSON)",
                data=json.dumps(st.session_state.rules, indent=2, ensure_ascii=False),
                file_name="dq_rules.json",
                mime="application/json",
                use_container_width=True
            )

# Navigation
st.markdown("---")
if len(st.session_state.rules) > 0:
    st.success(f"{len(st.session_state.rules)} rule(s) defined. You can now generate the report.")
    if st.button("Continue to Quality Report", type="primary", use_container_width=True):
        st.switch_page("pages/3_Quality_Report.py")
else:
    st.info("Create at least one rule to generate a quality report.")
