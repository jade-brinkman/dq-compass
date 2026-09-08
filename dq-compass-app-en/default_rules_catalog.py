"""
default_rules_catalog.py — Built-in starter catalog for the "Define Rules" page.

Per the team's working session: the Define Rules page must show, from the
very start, a set of basic/common quality-rule templates the user can add
in one click ("Quick-add Default Rules"), on top of the free-form custom
rule form that already lets any business define its own rules. Each
business still owns its own controls — these templates are generic
starting points across the 6 DQ dimensions, not a fixed pattern every
dataset must follow.

Every template maps 1:1 to a `logic_type` already supported by the DQ
Engine (engine/rules.py) — adding a template here never requires touching
the engine.
"""

TEMPLATES = {
    "completeness": {
        "name": "Completeness",
        "description": "Make sure a field that must always be filled in actually is.",
        "rules": [
            {
                "template_id": "TPL_NOTNULL",
                "control_name": "Mandatory field (no missing values)",
                "description": "The selected column must never be null or empty.",
                "control_type": "Completeness",
                "logic_type": "not_null",
                "severity": "High",
                "suggested_columns": ["email", "id", "client_id", "name", "code", "reference"],
                "requires_columns": 1,
                "default_param": "",
                "default_threshold": "0",
                "kpi_template": "Completeness rate >= 99%",
                "remediation_action": "Contact the source system owner to complete the missing value.",
            },
            {
                "template_id": "TPL_LOWMISSING",
                "control_name": "Low missing-value tolerance (< 1%)",
                "description": "Tolerates a small share of missing values (useful for optional-but-important fields).",
                "control_type": "Completeness",
                "logic_type": "not_null",
                "severity": "Medium",
                "suggested_columns": ["phone", "comment", "secondary_email"],
                "requires_columns": 1,
                "default_param": "",
                "default_threshold": "1",
                "kpi_template": "Completeness rate >= 99%",
                "remediation_action": "Review the source process feeding this field.",
            },
        ],
    },
    "validity": {
        "name": "Validity",
        "description": "Check that values respect an expected format.",
        "rules": [
            {
                "template_id": "TPL_EMAIL",
                "control_name": "Email format",
                "description": "Value must match a standard email address format.",
                "control_type": "Validity",
                "logic_type": "regex",
                "severity": "Medium",
                "suggested_columns": ["email", "mail", "e_mail", "courriel"],
                "requires_columns": 1,
                "default_param": r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$",
                "default_threshold": "0",
                "kpi_template": "Format compliance rate",
                "remediation_action": "Correct or re-collect the malformed email address.",
            },
            {
                "template_id": "TPL_PHONE_FR",
                "control_name": "Phone number format (FR)",
                "description": "Value must match a French phone number format.",
                "control_type": "Validity",
                "logic_type": "regex",
                "severity": "Low",
                "suggested_columns": ["phone", "tel", "telephone", "mobile"],
                "requires_columns": 1,
                "default_param": r"^(\+33|0)[1-9](\s?\d{2}){4}$",
                "default_threshold": "5",
                "kpi_template": "Format compliance rate",
                "remediation_action": "Correct or re-collect the malformed phone number.",
            },
            {
                "template_id": "TPL_POSTAL_FR",
                "control_name": "Postal code format (FR, 5 digits)",
                "description": "Value must be a 5-digit French postal code.",
                "control_type": "Validity",
                "logic_type": "regex",
                "severity": "Low",
                "suggested_columns": ["postal_code", "zipcode", "code_postal", "cp"],
                "requires_columns": 1,
                "default_param": r"^\d{5}$",
                "default_threshold": "0",
                "kpi_template": "Format compliance rate",
                "remediation_action": "Correct the postal code at the source.",
            },
            {
                "template_id": "TPL_DATE_ISO",
                "control_name": "ISO date format (YYYY-MM-DD)",
                "description": "Value must be a valid ISO 8601 date.",
                "control_type": "Validity",
                "logic_type": "regex",
                "severity": "Medium",
                "suggested_columns": ["date", "signup_date", "created_at", "updated_at"],
                "requires_columns": 1,
                "default_param": r"^\d{4}-\d{2}-\d{2}$",
                "default_threshold": "0",
                "kpi_template": "Format compliance rate",
                "remediation_action": "Fix the date format at the source system.",
            },
        ],
    },
    "uniqueness": {
        "name": "Uniqueness",
        "description": "Detect duplicate records or keys.",
        "rules": [
            {
                "template_id": "TPL_UNIQUE_ID",
                "control_name": "Unique identifier",
                "description": "The selected column must contain no duplicate values.",
                "control_type": "Uniqueness",
                "logic_type": "unique",
                "severity": "High",
                "suggested_columns": ["id", "client_id", "code", "reference", "matricule"],
                "requires_columns": 1,
                "default_param": "",
                "default_threshold": "0",
                "kpi_template": "Duplication rate = 0%",
                "remediation_action": "De-duplicate the records and investigate the source of the duplicate.",
            },
            {
                "template_id": "TPL_UNIQUE_COMPOSITE",
                "control_name": "Unique combination (composite key)",
                "description": "The combination of the selected columns must be unique (e.g. series + period).",
                "control_type": "Uniqueness",
                "logic_type": "unique_composite",
                "severity": "High",
                "suggested_columns": [],
                "requires_columns": 2,
                "default_param": "",
                "default_threshold": "0",
                "kpi_template": "Duplication rate = 0%",
                "remediation_action": "De-duplicate the records and investigate the source of the duplicate.",
            },
        ],
    },
    "consistency": {
        "name": "Consistency",
        "description": "Validate a relationship between two fields.",
        "rules": [
            {
                "template_id": "TPL_CLOSED_ZERO_BALANCE",
                "control_name": "Closed status implies zero balance",
                "description": (
                    "Starter template: if the first selected column equals 'closed', the second "
                    "selected column must equal 0. Add it, then duplicate it via the custom rule "
                    "form below to adapt the condition/target values to your own business case."
                ),
                "control_type": "Consistency",
                "logic_type": "conditional_equals",
                "severity": "High",
                "suggested_columns": [],
                "requires_columns": 2,
                "default_param": "closed:0",
                "default_threshold": "0.01",
                "kpi_template": "Number of inconsistent records",
                "remediation_action": "Investigate and correct the inconsistent record.",
            },
        ],
    },
    "freshness": {
        "name": "Freshness",
        "description": "Verify data freshness against an expected threshold.",
        "rules": [
            {
                "template_id": "TPL_FRESH_30D",
                "control_name": "Updated within the last 30 days",
                "description": "The selected date column must not be older than 30 days.",
                "control_type": "Freshness",
                "logic_type": "max_age_days",
                "severity": "Medium",
                "suggested_columns": ["last_update_ts", "updated_at", "last_modified"],
                "requires_columns": 1,
                "default_param": "today",
                "default_threshold": "30",
                "kpi_template": "Number of SLA breaches",
                "remediation_action": "Trigger a refresh of the record at the source.",
            },
            {
                "template_id": "TPL_FRESH_90D",
                "control_name": "Updated within the last 90 days",
                "description": "The selected date column must not be older than 90 days.",
                "control_type": "Freshness",
                "logic_type": "max_age_days",
                "severity": "Low",
                "suggested_columns": ["last_update_ts", "order_date", "created_at"],
                "requires_columns": 1,
                "default_param": "today",
                "default_threshold": "90",
                "kpi_template": "Number of SLA breaches",
                "remediation_action": "Trigger a refresh of the record at the source.",
            },
        ],
    },
    "reconciliation": {
        "name": "Reconciliation",
        "description": (
            "Compare totals across two files (e.g. detail vs. source-of-truth totals). "
            "This always needs a second reference file and specific group/value columns, "
            "so there is no one-click template here — use the custom rule form below with "
            "logic_type 'reconciliation_sum'."
        ),
        "rules": [],
    },
}


def get_all_templates() -> dict:
    return TEMPLATES


def find_matching_columns(available_columns, suggested_columns) -> list:
    """Case/substring-insensitive match between a template's suggested column
    names and the columns actually present in the uploaded dataset. Returns
    matches in the same order as `suggested_columns` (most likely first)."""
    if not suggested_columns:
        return []
    available_lower = {str(c).lower(): c for c in available_columns}
    matches = []
    for hint in suggested_columns:
        hint_lower = hint.lower()
        # exact match first
        if hint_lower in available_lower and available_lower[hint_lower] not in matches:
            matches.append(available_lower[hint_lower])
            continue
        # then substring match
        for col_lower, original in available_lower.items():
            if hint_lower in col_lower and original not in matches:
                matches.append(original)
    return matches


def create_rule_from_template(template: dict, column: str, dataset_name: str, rule_id_suffix: str) -> dict:
    """Builds a full rule dict (same schema as the custom rule form) from a
    quick-add template and the column(s) the user picked."""
    rule_id = f"{template['template_id']}_{rule_id_suffix}"

    return {
        "rule_id": rule_id,
        "control_name": template["control_name"],
        "control_type": template["control_type"],
        "description": template.get("description", ""),
        "logic_type": template["logic_type"],
        "dataset": dataset_name,
        "column": column,
        "param": template.get("default_param", ""),
        "threshold": template.get("default_threshold", ""),
        "severity": template.get("severity", "Medium"),
        "frequency": "Daily",
        "owner": "Data Quality Team",
        "output_type": "results_summary",
        "kpi": template.get("kpi_template", f"{template['logic_type']} check"),
        "remediation_action": template.get("remediation_action", "To be defined"),
    }


RULE_WRITING_TIPS = [
    {
        "title": "One rule, one clear question",
        "description": (
            "A good rule answers a single yes/no question ('is this field always filled in?'). "
            "If you need 'and', split it into two rules — it keeps exceptions readable."
        ),
    },
    {
        "title": "Set a numeric threshold, not a vague qualifier",
        "description": (
            "Prefer '0% missing tolerated' or '< 5% duplicates' over 'mostly complete'. "
            "A rule the engine can evaluate must have a number to compare against."
        ),
    },
    {
        "title": "Pick severity by business impact, not by gut feeling",
        "description": (
            "High = blocks trust in the dataset (e.g. duplicate client IDs). "
            "Medium = degrades quality but is workable. Low = cosmetic/monitoring only."
        ),
    },
    {
        "title": "Reuse a generic logic_type before asking for a new one",
        "description": (
            "not_null / regex / unique / unique_composite / conditional_equals / max_age_days / "
            "reconciliation_sum cover most business checks. Reusing them means zero engine code change."
        ),
    },
    {
        "title": "Write the remediation action as an instruction",
        "description": (
            "'Contact the source system owner to complete the missing value' is actionable. "
            "'Data issue' is not — whoever reads the report should know what to do next."
        ),
    },
    {
        "title": "Give rules a consistent, ordered ID",
        "description": (
            "DQ01, DQ02... (or a prefix per domain, e.g. RH01, BIS01) makes the results_summary.csv "
            "and the scorecard easy to scan and to reference during an audit."
        ),
    },
]


def get_rule_writing_tips() -> list:
    return RULE_WRITING_TIPS
