"""
rules.py — Les 6 fonctions génériques de logic_type (BF-ENG-03).

Contrat catalogue <-> moteur (à partager avec Irmeline) :

  logic_type            | column                          | param                                  | threshold
  -----------------------+---------------------------------+-----------------------------------------+-----------
  not_null               | <colonne>                        | (vide)                                  | % max de valeurs manquantes toléré (0 = zéro toléré)
  regex                  | <colonne>                        | <motif regex>                           | % max de non-conformes (parmi non-vides) toléré
  unique                 | <colonne clé>                    | (vide)                                  | % max de lignes dupliquées toléré
  conditional_equals     | <col_condition>:<col_cible>      | <val_condition>:<val_cible>             | tolérance numérique absolue sur la comparaison
  max_age_days           | <colonne date>                   | <date de référence ISO AAAA-MM-JJ>      | âge maximum en jours toléré
  reconciliation_sum     | <col_groupe>:<col_valeur>        | <fichier_ref>:<col_groupe_ref>:<col_valeur_ref> | % max d'écart toléré par groupe

Chaque fonction :
  - reçoit le(s) DataFrame(s) déjà chargés (aucun accès disque ici),
  - retourne un dict {"total_records", "failed_records", "kpi_value", "exceptions"}
    où "exceptions" est un DataFrame contenant au moins client_id + colonne(s) fautive(s).

Aucune règle métier n'est codée en dur : ces 6 fonctions sont strictement génériques
et ne font jamais référence à un rule_id (BNF-01, BF-ENG-03).
"""

import re
from datetime import date, datetime

import pandas as pd


class EngineError(Exception):
    """Erreur explicite de configuration/données (colonne ou fichier manquant, etc.)."""


def _require_columns(df: pd.DataFrame, columns, dataset_name: str, rule_id: str):
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise EngineError(
            f"[{rule_id}] colonne(s) manquante(s) dans '{dataset_name}': {', '.join(missing)}"
        )


def _client_col(df: pd.DataFrame) -> str:
    """Colonne d'identifiant de ligne utilisée pour la traçabilité (BNF-02)."""
    return "client_id" if "client_id" in df.columns else df.columns[0]


def _get_exception_columns(df: pd.DataFrame, column: str) -> list:
    """
    Returns the list of columns to include in exceptions DataFrame.
    Avoids duplicates when id_col == column.
    """
    id_col = _client_col(df)
    if id_col == column:
        return [column]
    return [id_col, column]


# ---------------------------------------------------------------------------
# 1. not_null
# ---------------------------------------------------------------------------
def not_null(df: pd.DataFrame, rule: dict, datasets: dict) -> dict:
    column = rule["column"]
    _require_columns(df, [column], rule["dataset"], rule["rule_id"])
    threshold_pct = float(rule["threshold"]) if str(rule["threshold"]).strip() else 0.0

    is_missing = df[column].isna() | (df[column].astype(str).str.strip() == "")
    total = len(df)
    failed = int(is_missing.sum())
    rate_pct = (failed / total * 100) if total else 0.0

    exc_cols = _get_exception_columns(df, column)
    exceptions = df.loc[is_missing, exc_cols].copy()
    exceptions["reason"] = f"{column} manquant"

    return {
        "total_records": total,
        "failed_records": failed,
        "kpi_value": round(100 - rate_pct, 4),  # taux de complétude
        "exceptions": exceptions,
        "_within_tolerance": rate_pct <= threshold_pct,
    }


# ---------------------------------------------------------------------------
# 2. regex
# ---------------------------------------------------------------------------
def regex(df: pd.DataFrame, rule: dict, datasets: dict) -> dict:
    column = rule["column"]
    pattern = rule["param"]
    _require_columns(df, [column], rule["dataset"], rule["rule_id"])
    if not pattern or not str(pattern).strip():
        raise EngineError(f"[{rule['rule_id']}] param (motif regex) manquant")
    threshold_pct = float(rule["threshold"]) if str(rule["threshold"]).strip() else 0.0
    compiled = re.compile(pattern)

    values = df[column].astype(str)
    non_empty_mask = df[column].notna() & (values.str.strip() != "")
    matches = values.apply(lambda v: bool(compiled.fullmatch(v)))
    is_malformed = non_empty_mask & (~matches)

    eligible = int(non_empty_mask.sum())
    failed = int(is_malformed.sum())
    rate_pct = (failed / eligible * 100) if eligible else 0.0

    exc_cols = _get_exception_columns(df, column)
    exceptions = df.loc[is_malformed, exc_cols].copy()
    exceptions["reason"] = f"{column} non conforme au format attendu"

    return {
        "total_records": len(df),
        "failed_records": failed,
        "kpi_value": round(100 - rate_pct, 4),  # taux de conformité (parmi non-vides)
        "exceptions": exceptions,
        "_within_tolerance": rate_pct <= threshold_pct,
    }


# ---------------------------------------------------------------------------
# 3. unique
# ---------------------------------------------------------------------------
def unique(df: pd.DataFrame, rule: dict, datasets: dict) -> dict:
    column = rule["column"]
    _require_columns(df, [column], rule["dataset"], rule["rule_id"])
    threshold_pct = float(rule["threshold"]) if str(rule["threshold"]).strip() else 0.0

    dup_mask = df[column].duplicated(keep=False)
    total = len(df)
    failed = int(dup_mask.sum())
    rate_pct = (failed / total * 100) if total else 0.0

    id_col = _client_col(df)
    cols = list(dict.fromkeys([id_col, column]))  # dédoublonne si id_col == column
    exceptions = df.loc[dup_mask, cols].copy()
    exceptions["reason"] = f"{column} dupliqué"

    dup_count = df.loc[dup_mask, column].nunique()

    return {
        "total_records": total,
        "failed_records": failed,
        "kpi_value": round(rate_pct, 4),  # taux de duplication
        "exceptions": exceptions,
        "_within_tolerance": rate_pct <= threshold_pct,
        "_dup_value_count": dup_count,
    }


# ---------------------------------------------------------------------------
# 4. conditional_equals
# ---------------------------------------------------------------------------
def conditional_equals(df: pd.DataFrame, rule: dict, datasets: dict) -> dict:
    rule_id = rule["rule_id"]
    try:
        cond_col, target_col = str(rule["column"]).split(":")
        cond_val, target_val = str(rule["param"]).split(":")
    except ValueError:
        raise EngineError(
            f"[{rule_id}] format attendu pour column/param : "
            f"'col_condition:col_cible' / 'val_condition:val_cible'"
        )
    _require_columns(df, [cond_col, target_col], rule["dataset"], rule_id)
    tolerance = float(rule["threshold"]) if str(rule["threshold"]).strip() else 0.0
    target_val_num = float(target_val)

    matches_condition = df[cond_col].astype(str) == cond_val
    numeric_target = pd.to_numeric(df[target_col], errors="coerce")
    breaches = matches_condition & ((numeric_target - target_val_num).abs() > tolerance)

    total = len(df)
    failed = int(breaches.sum())

    id_col = _client_col(df)
    exc_cols = list(dict.fromkeys([id_col, cond_col, target_col]))  # deduplicate
    exceptions = df.loc[breaches, exc_cols].copy()
    exceptions["reason"] = f"{cond_col}={cond_val} mais {target_col} != {target_val}"

    return {
        "total_records": total,
        "failed_records": failed,
        "kpi_value": failed,  # nb de comptes incohérents
        "exceptions": exceptions,
        "_within_tolerance": failed == 0,
    }


# ---------------------------------------------------------------------------
# 5. max_age_days
# ---------------------------------------------------------------------------
def max_age_days(df: pd.DataFrame, rule: dict, datasets: dict) -> dict:
    rule_id = rule["rule_id"]
    column = rule["column"]
    _require_columns(df, [column], rule["dataset"], rule_id)

    ref_param = str(rule["param"]).strip()
    if not ref_param:
        raise EngineError(f"[{rule_id}] param (date de référence) manquant")
    reference_date = (
        date.today() if ref_param.lower() == "today" else datetime.fromisoformat(ref_param).date()
    )
    max_days = float(rule["threshold"]) if str(rule["threshold"]).strip() else 0.0

    parsed = pd.to_datetime(df[column], errors="coerce")
    invalid_date = parsed.isna()
    age_days = (pd.Timestamp(reference_date) - parsed).dt.days
    breaches = (~invalid_date) & (age_days > max_days)
    # une date invalide/manquante est également considérée en échec (traçabilité)
    breaches_or_invalid = breaches | invalid_date

    total = len(df)
    failed = int(breaches_or_invalid.sum())

    exc_cols = _get_exception_columns(df, column)
    exceptions = df.loc[breaches_or_invalid, exc_cols].copy()
    exceptions["reason"] = f"{column} au-delà de {int(max_days)} jours (ou date invalide)"

    return {
        "total_records": total,
        "failed_records": failed,
        "kpi_value": failed,  # nb de dépassements SLA
        "exceptions": exceptions,
        "_within_tolerance": failed == 0,
    }


# ---------------------------------------------------------------------------
# 6. reconciliation_sum
# ---------------------------------------------------------------------------
def reconciliation_sum(df: pd.DataFrame, rule: dict, datasets: dict) -> dict:
    rule_id = rule["rule_id"]
    try:
        group_col, value_col = str(rule["column"]).split(":")
        ref_file, ref_group_col, ref_value_col = str(rule["param"]).split(":")
    except ValueError:
        raise EngineError(
            f"[{rule_id}] format attendu : column='groupe:valeur', "
            f"param='fichier_ref:groupe_ref:valeur_ref'"
        )
    _require_columns(df, [group_col, value_col], rule["dataset"], rule_id)
    if ref_file not in datasets:
        raise EngineError(f"[{rule_id}] fichier de référence manquant : {ref_file}")
    ref_df = datasets[ref_file]
    _require_columns(ref_df, [ref_group_col, ref_value_col], ref_file, rule_id)

    max_deviation_pct = float(rule["threshold"]) if str(rule["threshold"]).strip() else 0.0

    numeric_values = pd.to_numeric(df[value_col], errors="coerce")
    computed = numeric_values.groupby(df[group_col]).sum()
    reference = pd.to_numeric(
        ref_df.set_index(ref_group_col)[ref_value_col], errors="coerce"
    )

    id_col = _client_col(df)
    exception_rows = []
    max_observed_deviation = 0.0
    failing_groups = []

    for group in sorted(set(computed.index) | set(reference.index)):
        computed_total = float(computed.get(group, 0.0))
        ref_total = float(reference.get(group, 0.0))
        deviation_pct = (
            abs(computed_total - ref_total) / abs(ref_total) * 100 if ref_total != 0 else
            (0.0 if computed_total == 0 else 100.0)
        )
        max_observed_deviation = max(max_observed_deviation, deviation_pct)
        if deviation_pct > max_deviation_pct:
            failing_groups.append(group)
            group_rows = df.loc[df[group_col] == group, [id_col, group_col, value_col]].copy()
            group_rows["computed_total"] = round(computed_total, 2)
            group_rows["reference_total"] = round(ref_total, 2)
            group_rows["deviation_pct"] = round(deviation_pct, 4)
            group_rows["reason"] = f"écart de réconciliation sur {group_col}={group}"
            exception_rows.append(group_rows)

    exceptions = (
        pd.concat(exception_rows, ignore_index=True) if exception_rows
        else pd.DataFrame(columns=[id_col, group_col, value_col, "computed_total", "reference_total", "deviation_pct", "reason"])
    )

    return {
        "total_records": len(df),
        "failed_records": len(exceptions),
        "kpi_value": round(max_observed_deviation, 4),  # écart max observé, en %
        "exceptions": exceptions,
        "_within_tolerance": len(failing_groups) == 0,
        "_failing_groups": failing_groups,
    }


# ---------------------------------------------------------------------------
# 7. unique_composite
# ---------------------------------------------------------------------------
def unique_composite(df: pd.DataFrame, rule: dict, datasets: dict) -> dict:
    """
    Vérifie l'unicité d'une combinaison de colonnes (clé composite).

    column : liste de colonnes séparées par ':' formant la clé composite
    threshold : % max de lignes dupliquées toléré

    Exemple : column='series_id:year' vérifie que chaque couple (series_id, year) est unique.

    Ajouté pour supporter les datasets transformés wide→long où l'unicité porte
    sur plusieurs dimensions (série + période temporelle).
    """
    columns_str = rule["column"]
    if not columns_str or ":" not in columns_str:
        raise EngineError(
            f"[{rule['rule_id']}] column doit contenir plusieurs colonnes séparées par ':' "
            f"pour unique_composite (ex: 'col1:col2')"
        )

    columns = [c.strip() for c in columns_str.split(":")]
    _require_columns(df, columns, rule["dataset"], rule["rule_id"])
    threshold_pct = float(rule["threshold"]) if str(rule["threshold"]).strip() else 0.0

    # Identifie les lignes dupliquées sur la combinaison de colonnes
    dup_mask = df.duplicated(subset=columns, keep=False)
    total = len(df)
    failed = int(dup_mask.sum())
    rate_pct = (failed / total * 100) if total else 0.0

    id_col = _client_col(df)
    # Inclut toutes les colonnes de la clé composite + l'identifiant
    cols_to_show = list(dict.fromkeys([id_col] + columns))
    exceptions = df.loc[dup_mask, cols_to_show].copy()
    exceptions["reason"] = f"Clé composite {'+'.join(columns)} dupliquée"

    dup_count = len(df.loc[dup_mask].drop_duplicates(subset=columns))

    return {
        "total_records": total,
        "failed_records": failed,
        "kpi_value": round(rate_pct, 4),  # taux de duplication
        "exceptions": exceptions,
        "_within_tolerance": rate_pct <= threshold_pct,
        "_dup_value_count": dup_count,
    }


LOGIC_TYPE_FUNCTIONS = {
    "not_null": not_null,
    "regex": regex,
    "unique": unique,
    "unique_composite": unique_composite,
    "conditional_equals": conditional_equals,
    "max_age_days": max_age_days,
    "reconciliation_sum": reconciliation_sum,
}
