"""
data_quality_checks.py — Basic automatic quality checks run right after upload,
before the user defines any rule (Upload Data page).

Purpose (from the team's working session): as soon as a file is uploaded, the
app should flag common, generic data issues on its own ("type attention à
avoir en tête") and separately flag potential personal/GDPR-sensitive data.

These checks are 100% generic (column-name/content pattern based) — they never
reference a specific business dataset or rule_id, in line with the same
"no hard-coded business logic" principle as the DQ Engine itself.

Each check in `run_all_checks()` returns a dict:
    {
        "check": str,            # stable machine id, e.g. "duplicate_rows"
        "label": str,            # human-readable title
        "severity": str,         # "ok" | "warning" | "critical"
        "issues": list[str],     # human-readable bullet points
        "details": dict,         # structured data for the UI to drill into
    }
"""

import re

import pandas as pd

# ---------------------------------------------------------------------------
# GDPR / personal-data detection helpers
# ---------------------------------------------------------------------------

GDPR_COLUMN_HINTS = {
    "identity": ["name", "nom", "prenom", "prénom", "firstname", "lastname", "surname"],
    "email": ["email", "mail", "e-mail", "courriel"],
    "phone": ["phone", "tel", "tél", "telephone", "téléphone", "mobile", "gsm"],
    "address": ["address", "adresse", "street", "rue", "postal", "zipcode", "cp"],
    "national_id": ["ssn", "nir", "national_id", "passport", "passeport", "siren", "siret",
                     "iban", "national_insurance"],
    "birth": ["birth", "naissance", "dob", "date_of_birth"],
    "ip": ["ip_address", "ip_addr", "adresse_ip"],
}

EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_PATTERN = re.compile(r"^(\+?\d[\d .-]{7,}\d)$")
IBAN_PATTERN = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{10,30}$")
FR_NIR_PATTERN = re.compile(r"^[12]\d{2}(0[1-9]|1[0-2])\d{2}\d{3}\d{3}\d{2}$")
# Plain calendar dates (YYYY-MM-DD, DD/MM/YYYY...) are excluded from the phone
# check below — they'd otherwise false-positive-match PHONE_PATTERN (digits +
# separators), and a date column is not personal data by itself.
DATE_LIKE_PATTERN = re.compile(r"^\d{4}[-/]\d{2}[-/]\d{2}([ T]\d{2}:\d{2}(:\d{2})?)?$|^\d{2}[-/]\d{2}[-/]\d{4}$")


def _sample_values(series: pd.Series, n: int = 100):
    """Get a sample of non-empty values for pattern detection.
    Uses random sampling for better representativeness on large datasets."""
    values = series.dropna().astype(str)
    values = values[values.str.strip() != ""]
    if len(values) <= n:
        return values
    # Random sample for better representativeness
    return values.sample(n=n, random_state=42)


def run_gdpr_check(df: pd.DataFrame) -> dict:
    """
    Best-effort, generic detection of columns that may hold personal data:
    - by column name (against GDPR_COLUMN_HINTS)
    - by content pattern (email / phone / IBAN / French NIR format)

    This is purely advisory: it never blocks processing, it only surfaces a
    warning so a human can confirm/anonymise before sharing results further.
    """
    detected = []

    for col in df.columns:
        col_lower = str(col).strip().lower()

        # 1) column-name based detection
        matched_category = None
        for category, hints in GDPR_COLUMN_HINTS.items():
            if any(hint in col_lower for hint in hints):
                matched_category = category
                break

        if matched_category:
            detected.append({
                "column": col,
                "category": matched_category,
                "detection_method": "column_name",
            })
            continue

        # 2) content-pattern based detection (only if name didn't already match)
        sample = _sample_values(df[col])
        if len(sample) == 0:
            continue

        # A column that's mostly plain calendar dates is not personal data by
        # itself and would otherwise false-positive-match PHONE_PATTERN.
        date_rate = sample.apply(lambda v: bool(DATE_LIKE_PATTERN.match(v.strip()))).mean()
        if date_rate >= 0.6:
            continue

        for category, pattern in (
            ("email", EMAIL_PATTERN),
            ("national_id", IBAN_PATTERN),
            ("national_id", FR_NIR_PATTERN),
            ("phone", PHONE_PATTERN),
        ):
            hit_rate = sample.apply(lambda v: bool(pattern.match(v.strip()))).mean()
            if hit_rate >= 0.6:
                detected.append({
                    "column": col,
                    "category": category,
                    "detection_method": "content_pattern",
                })
                break

    severity = "warning" if detected else "ok"
    return {
        "check": "gdpr_personal_data",
        "label": "Personal data detection (GDPR)",
        "severity": severity,
        "details": {"detected_columns": detected},
    }


# ---------------------------------------------------------------------------
# Basic quality checks (run automatically on upload)
# ---------------------------------------------------------------------------

def _check_duplicate_rows(df: pd.DataFrame) -> dict:
    # For large datasets, use a faster hash-based approach
    if len(df) > 10000:
        # Sample-based estimation for very large datasets
        sample_size = min(5000, len(df))
        sample = df.sample(n=sample_size, random_state=42)
        sample_dup_count = int(sample.duplicated(keep=False).sum())
        dup_pct = (sample_dup_count / sample_size * 100)
        dup_count = int(len(df) * dup_pct / 100)  # Estimated
    else:
        dup_mask = df.duplicated(keep=False)
        dup_count = int(dup_mask.sum())
        dup_pct = (dup_count / len(df) * 100) if len(df) else 0.0

    severity = "ok"
    issues = []
    if dup_count > 0:
        severity = "critical" if dup_pct >= 5 else "warning"
        estimate_note = " (estimated)" if len(df) > 10000 else ""
        issues.append(f"{dup_count:,} fully duplicated row(s) found{estimate_note} ({dup_pct:.1f}% of the file).")

    return {
        "check": "duplicate_rows",
        "label": "Duplicate rows",
        "severity": severity,
        "issues": issues,
        "details": {"duplicate_count": dup_count, "duplicate_pct": dup_pct},
    }


def _check_empty_columns(df: pd.DataFrame) -> dict:
    empty_cols = [c for c in df.columns if (df[c].astype(str).str.strip() == "").all()]

    severity = "warning" if empty_cols else "ok"
    issues = [f"{len(empty_cols)} column(s) are entirely empty."] if empty_cols else []

    return {
        "check": "empty_columns",
        "label": "Empty columns",
        "severity": severity,
        "issues": issues,
        "details": {"count": len(empty_cols), "empty_columns": empty_cols},
    }


def _check_missing_values(df: pd.DataFrame, threshold_pct: float = 20.0) -> dict:
    high_missing_columns = []
    total_rows = len(df)

    if total_rows == 0:
        return {
            "check": "missing_values",
            "label": "High missing-value rate",
            "severity": "ok",
            "issues": [],
            "details": {"high_missing_columns": []},
        }

    # Vectorized approach - much faster than iterating
    # Convert all columns to string and check for empty/whitespace
    empty_counts = df.apply(lambda col: (col.astype(str).str.strip() == "").sum())

    for col in df.columns:
        missing_pct = (empty_counts[col] / total_rows) * 100
        if missing_pct >= threshold_pct:
            high_missing_columns.append({"column": col, "missing_pct": round(missing_pct, 1)})

    high_missing_columns.sort(key=lambda c: c["missing_pct"], reverse=True)

    severity = "ok"
    issues = []
    if high_missing_columns:
        severity = "critical" if any(c["missing_pct"] >= 50 for c in high_missing_columns) else "warning"
        issues.append(
            f"{len(high_missing_columns)} column(s) have {threshold_pct:.0f}%+ missing values."
        )

    return {
        "check": "missing_values",
        "label": "High missing-value rate",
        "severity": severity,
        "issues": issues,
        "details": {"high_missing_columns": high_missing_columns},
    }


def _check_encoding_issues(df: pd.DataFrame) -> dict:
    """Flags typical mojibake artefacts left by a wrong encoding guess (e.g. CP1252
    read as UTF-8: 'Ã©' instead of 'é', 'â€™' instead of an apostrophe, or the
    literal replacement character '<EFBFBD>')."""
    suspicious_markers = ["Ã©", "Ã¨", "Ã ", "â€™", "â€œ", "â€", "�"]
    problematic_columns = []

    for col in df.select_dtypes(include="object").columns if hasattr(df, "select_dtypes") else df.columns:
        sample = _sample_values(df[col], n=200)
        if len(sample) == 0:
            continue
        affected = sample.apply(lambda v: any(marker in v for marker in suspicious_markers))
        affected_rows = int(affected.sum())
        if affected_rows > 0:
            problematic_columns.append({"column": col, "affected_rows": affected_rows})

    severity = "warning" if problematic_columns else "ok"
    issues = [f"{len(problematic_columns)} column(s) show signs of an encoding mismatch."] if problematic_columns else []

    return {
        "check": "encoding_issues",
        "label": "Encoding issues",
        "severity": severity,
        "issues": issues,
        "details": {"problematic_columns": problematic_columns},
    }


def _check_constant_columns(df: pd.DataFrame) -> dict:
    constant_cols = [
        c for c in df.columns
        if df[c].nunique(dropna=False) <= 1 and not (df[c].astype(str).str.strip() == "").all()
    ]

    severity = "warning" if constant_cols else "ok"
    issues = [f"{len(constant_cols)} column(s) hold a single constant value across all rows."] if constant_cols else []

    return {
        "check": "constant_columns",
        "label": "Constant columns",
        "severity": severity,
        "issues": issues,
        "details": {"count": len(constant_cols), "constant_columns": constant_cols},
    }


def _check_whitespace_issues(df: pd.DataFrame) -> dict:
    affected_columns = []

    # For large datasets, only sample
    if len(df) > 5000:
        sample_df = df.sample(n=5000, random_state=42)
    else:
        sample_df = df

    for col in sample_df.columns:
        sample = sample_df[col].dropna().astype(str)
        if len(sample) == 0:
            continue
        has_padding = (sample != sample.str.strip()) & (sample.str.strip() != "")
        count = int(has_padding.sum())
        if count > 0:
            # Extrapolate count for full dataset
            if len(df) > 5000:
                count = int(count * len(df) / 5000)
            affected_columns.append({"column": col, "affected_rows": count})

    severity = "warning" if affected_columns else "ok"
    issues = [f"{len(affected_columns)} column(s) contain values with leading/trailing spaces."] if affected_columns else []

    return {
        "check": "whitespace_issues",
        "label": "Leading/trailing whitespace",
        "severity": severity,
        "issues": issues,
        "details": {"affected_columns": affected_columns},
    }


def run_all_checks(df: pd.DataFrame) -> list:
    """Runs every basic check and returns the list of results (order matters
    for display: issues first is handled by the caller, not here)."""
    return [
        _check_duplicate_rows(df),
        _check_empty_columns(df),
        _check_missing_values(df),
        _check_encoding_issues(df),
        _check_constant_columns(df),
        _check_whitespace_issues(df),
    ]


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

_ICONS = {"ok": "[OK]", "warning": "[!]", "critical": "[X]"}
_COLORS = {"ok": "#00CC96", "warning": "#FFA15A", "critical": "#E2001A"}


def get_severity_icon(severity: str) -> str:
    return _ICONS.get(severity, "[?]")


def get_severity_color(severity: str) -> str:
    return _COLORS.get(severity, "#5C5C5C")
