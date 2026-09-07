#!/usr/bin/env python3
"""
engine.py — DQ Engine (brique 2/4 — Jade)

Charge dynamiquement le catalogue de contrôles (Irmeline) et l'applique aux
jeux de données référencés, sans aucune règle codée en dur : chaque logic_type
du catalogue est exécuté par une des 6 fonctions génériques de rules.py.

Sorties, à chaque exécution (run_id), sous runs/<run_id>/ :
  - manifest.json          (BF-AUD-02 : run_id, timestamp, fichiers sources + SHA-256,
                             copie du catalogue utilisé)
  - results_summary.csv    (BF-ENG-02 : 1 ligne par règle, pass/fail + métriques)
  - exceptions/<rule_id>_exceptions.csv   (BF-REP-02 : lignes en échec extraites)
  - engine.log             (logs d'exécution, transmis à Johann pour l'Audit Layer)

Une copie "dernière exécution" de results_summary.csv et exceptions/ est aussi
écrite à la racine (--latest-dir) pour simplifier l'intégration avec le Reporting
Layer (Lucas), qui peut ainsi toujours lire le même chemin fixe.

Usage :
    python engine/engine.py \
        --catalogue catalogue/control_catalogue.csv \
        --data-dir data \
        --runs-dir runs \
        --latest-dir .
"""

import argparse
import json
import logging
import shutil
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from rules import LOGIC_TYPE_FUNCTIONS, EngineError  # noqa: E402
from utils import new_run_id, now_paris_iso, sha256_of_file, count_data_rows  # noqa: E402

EXPECTED_CATALOGUE_COLUMNS = [
    "rule_id", "control_name", "control_type", "description", "logic_type",
    "dataset", "column", "param", "threshold", "severity", "frequency",
    "owner", "output_type", "kpi", "remediation_action",
]

RESULTS_COLUMNS = [
    "rule_id", "control_name", "dimension", "severity", "status",
    "total_records", "failed_records", "kpi_value", "kpi_label",
]


def load_catalogue(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise EngineError(f"Fichier catalogue introuvable : {path}")
    df = pd.read_csv(path, dtype=str, keep_default_na=False)

    if list(df.columns) != EXPECTED_CATALOGUE_COLUMNS:
        raise EngineError(
            "control_catalogue.csv ne respecte pas le schéma attendu (BF-CAT-01).\n"
            f"  Attendu : {EXPECTED_CATALOGUE_COLUMNS}\n"
            f"  Obtenu  : {list(df.columns)}"
        )
    return df


def filter_catalogue(catalogue: pd.DataFrame, dimensions: str, rule_ids: str, log: logging.Logger) -> pd.DataFrame:
    """
    Permet au client de choisir un sous-ensemble de dimensions et/ou de règles à
    exécuter/mettre en avant pour ce run, sans toucher au fichier catalogue.
    Filtrage générique sur les colonnes control_type / rule_id — aucune règle
    métier, applicable à n'importe quel catalogue.
    """
    filtered = catalogue
    if dimensions:
        wanted = {d.strip().lower() for d in dimensions.split(",") if d.strip()}
        filtered = filtered[filtered["control_type"].str.lower().isin(wanted)]
        log.info("Filtre --dimensions=%s -> %d règle(s) retenue(s)", dimensions, len(filtered))
    if rule_ids:
        wanted_ids = {r.strip().lower() for r in rule_ids.split(",") if r.strip()}
        filtered = filtered[filtered["rule_id"].str.lower().isin(wanted_ids)]
        log.info("Filtre --rules=%s -> %d règle(s) retenue(s)", rule_ids, len(filtered))
    return filtered


def validate_and_split_catalogue(catalogue: pd.DataFrame, log: logging.Logger):
    """BF-CAT-02 : rejette (log ERROR + exclusion) toute ligne à logic_type invalide."""
    valid_rows, rejected_rows = [], []
    for _, row in catalogue.iterrows():
        if row["logic_type"] not in LOGIC_TYPE_FUNCTIONS:
            log.error(
                "Règle %s rejetée au chargement : logic_type invalide '%s' "
                "(valeurs autorisées : %s)",
                row["rule_id"], row["logic_type"], ", ".join(LOGIC_TYPE_FUNCTIONS),
            )
            rejected_rows.append(row)
        else:
            valid_rows.append(row)
    return valid_rows, rejected_rows


def resolve_dataset_files(rule_row, data_dir: Path) -> list:
    """La colonne dataset peut lister plusieurs fichiers séparés par ';'."""
    names = [n.strip() for n in str(rule_row["dataset"]).split(";") if n.strip()]
    paths = []
    for name in names:
        path = data_dir / name
        if not path.exists():
            raise EngineError(
                f"[{rule_row['rule_id']}] fichier de données introuvable : {path} "
                f"(référencé dans la colonne 'dataset' du catalogue)"
            )
        paths.append((name, path))
    return paths


def load_all_datasets(valid_rows, data_dir: Path, log: logging.Logger) -> dict:
    datasets = {}
    for row in valid_rows:
        for name, path in resolve_dataset_files(row, data_dir):
            if name not in datasets:
                log.info("Chargement du jeu de données : %s", path)
                # Chargement 100% générique : tout est lu en texte brut, chaque
                # fonction de rules.py convertit elle-même ce dont elle a besoin
                # (pd.to_numeric, pd.to_datetime) — aucune hypothèse sur les noms
                # de colonnes d'un jeu de données en particulier.
                datasets[name] = pd.read_csv(path, dtype=str, keep_default_na=False)
    return datasets


def run_rule(row, datasets: dict, log: logging.Logger) -> dict:
    rule_id = row["rule_id"]
    logic_type = row["logic_type"]
    primary_dataset_name = str(row["dataset"]).split(";")[0].strip()
    primary_df = datasets[primary_dataset_name]

    func = LOGIC_TYPE_FUNCTIONS[logic_type]
    try:
        outcome = func(primary_df, row, datasets)
        status = "PASS" if outcome["_within_tolerance"] else "FAIL"
        log.info(
            "%s (%s) -> %s | total=%s failed=%s kpi=%s",
            rule_id, logic_type, status,
            outcome["total_records"], outcome["failed_records"], outcome["kpi_value"],
        )
        return {
            "rule_id": rule_id,
            "control_name": row["control_name"],
            "dimension": row["control_type"],
            "severity": row["severity"],
            "status": status,
            "total_records": outcome["total_records"],
            "failed_records": outcome["failed_records"],
            "kpi_value": outcome["kpi_value"],
            "kpi_label": row["kpi"],
            "_exceptions": outcome["exceptions"],
        }
    except EngineError as e:
        log.error("%s (%s) -> ERROR : %s", rule_id, logic_type, e)
        return {
            "rule_id": rule_id,
            "control_name": row["control_name"],
            "dimension": row["control_type"],
            "severity": row["severity"],
            "status": "ERROR",
            "total_records": "",
            "failed_records": "",
            "kpi_value": "",
            "kpi_label": str(e),
            "_exceptions": pd.DataFrame(),
        }


def setup_logger(log_path: Path) -> logging.Logger:
    logger = logging.getLogger(f"dq_engine.{log_path}")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    return logger


def build_manifest(run_id, timestamp, data_dir, valid_rows, catalogue_path, run_dir, log, filters=None):
    sources = []
    seen = set()
    for row in valid_rows:
        for name, path in resolve_dataset_files(row, data_dir):
            if name in seen:
                continue
            seen.add(name)
            sources.append({
                "file": name,
                "path": str(path),
                "sha256": sha256_of_file(path),
                "row_count": count_data_rows(path),
            })

    catalogue_copy_name = "control_catalogue.csv"
    shutil.copyfile(catalogue_path, run_dir / catalogue_copy_name)

    manifest = {
        "run_id": run_id,
        "timestamp": timestamp,
        "engine": "dq-compass DQ Engine v1",
        "sources": sources,
        "catalogue_file": catalogue_copy_name,
        "catalogue_sha256": sha256_of_file(catalogue_path),
        "filters": filters or {},
    }
    with open(run_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    log.info("manifest.json écrit (%d source(s) référencée(s))", len(sources))
    return manifest


def main():
    parser = argparse.ArgumentParser(description="DQ Engine — exécution du catalogue de contrôles")
    parser.add_argument("--catalogue", default="catalogue/control_catalogue.csv")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--runs-dir", default="runs")
    parser.add_argument("--latest-dir", default=".", help="Copie pratique de la dernière exécution")
    parser.add_argument(
        "--dimensions", default="",
        help="Sous-ensemble de dimensions à exécuter/mettre en avant, ex. 'Complétude,Validité' "
             "(par défaut : toutes les dimensions du catalogue)",
    )
    parser.add_argument(
        "--rules", default="",
        help="Sous-ensemble de rule_id à exécuter, ex. 'DQ01,DQ03' (par défaut : toutes)",
    )
    args = parser.parse_args()

    start = time.perf_counter()
    catalogue_path = Path(args.catalogue)
    data_dir = Path(args.data_dir)
    runs_dir = Path(args.runs_dir)

    run_id = new_run_id()
    timestamp = now_paris_iso()
    run_dir = runs_dir / run_id
    exceptions_dir = run_dir / "exceptions"
    exceptions_dir.mkdir(parents=True, exist_ok=True)

    log = setup_logger(run_dir / "engine.log")
    log.info("=== DQ Engine — run %s démarré à %s ===", run_id, timestamp)

    try:
        catalogue = load_catalogue(catalogue_path)
        log.info("Catalogue chargé : %s (%d règles)", catalogue_path, len(catalogue))

        catalogue = filter_catalogue(catalogue, args.dimensions, args.rules, log)
        if catalogue.empty:
            raise EngineError(
                "Aucune règle ne correspond aux filtres --dimensions/--rules fournis."
            )

        valid_rows, rejected_rows = validate_and_split_catalogue(catalogue, log)
        datasets = load_all_datasets(valid_rows, data_dir, log)

        results = []
        for row in valid_rows:
            results.append(run_rule(row, datasets, log))

        for row in rejected_rows:
            results.append({
                "rule_id": row["rule_id"],
                "control_name": row["control_name"],
                "dimension": row["control_type"],
                "severity": row["severity"],
                "status": "ERROR",
                "total_records": "",
                "failed_records": "",
                "kpi_value": "",
                "kpi_label": f"logic_type invalide : {row['logic_type']}",
                "_exceptions": pd.DataFrame(),
            })

        # --- results_summary.csv ---
        summary_df = pd.DataFrame(
            [{k: r[k] for k in RESULTS_COLUMNS} for r in results]
        )
        summary_path = run_dir / "results_summary.csv"
        summary_df.to_csv(summary_path, index=False)
        log.info("results_summary.csv écrit (%d règles)", len(summary_df))

        # --- exceptions/<rule_id>_exceptions.csv ---
        for r in results:
            exc_df = r["_exceptions"]
            if r["status"] == "FAIL" and exc_df is not None and len(exc_df) > 0:
                sort_cols = list(dict.fromkeys(exc_df.columns))
                exc_df = exc_df.sort_values(by=sort_cols).reset_index(drop=True)
                exc_path = exceptions_dir / f"{r['rule_id']}_exceptions.csv"
                exc_df.to_csv(exc_path, index=False)
                log.info("Exceptions écrites pour %s : %s (%d lignes)", r["rule_id"], exc_path, len(exc_df))

        # --- manifest.json (BF-AUD-02) ---
        build_manifest(
            run_id, timestamp, data_dir, valid_rows, catalogue_path, run_dir, log,
            filters={"dimensions": args.dimensions or None, "rules": args.rules or None},
        )

        # --- copies "dernière exécution" pour le Reporting Layer ---
        latest_dir = Path(args.latest_dir)
        shutil.copyfile(summary_path, latest_dir / "results_summary.csv")
        latest_exc_dir = latest_dir / "exceptions"
        if latest_exc_dir.exists():
            shutil.rmtree(latest_exc_dir)
        shutil.copytree(exceptions_dir, latest_exc_dir)

        elapsed = time.perf_counter() - start
        log.info("=== Run %s terminé en %.2fs ===", run_id, elapsed)
        print(f"\nRun {run_id} terminé en {elapsed:.2f}s -> {run_dir}")
        return 0

    except EngineError as e:
        log.error("Arrêt du moteur : %s", e)
        print(f"ERREUR : {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
