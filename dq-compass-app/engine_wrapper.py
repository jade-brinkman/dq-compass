"""
Wrapper pour appeler le moteur DQ depuis Streamlit.
Simplifie l'interface et retourne les résultats dans un format exploitable par Streamlit.
"""

import sys
from pathlib import Path
import pandas as pd
import tempfile
import json
from datetime import datetime

# Ajouter le chemin du moteur
engine_path = Path(__file__).parent.parent / "dq-compass-engine"
sys.path.insert(0, str(engine_path / "engine"))

from engine import (
    load_catalogue,
    filter_catalogue,
    validate_and_split_catalogue,
    load_all_datasets,
    run_rule,
    setup_logger,
    build_manifest,
    EngineError
)
from utils import new_run_id, now_paris_iso


class DQEngineWrapper:
    """Wrapper simplifié pour le moteur DQ"""

    def __init__(self, data_file_path: str, rules: list):
        """
        Initialize the engine wrapper

        Args:
            data_file_path: Path to the CSV data file
            rules: List of rule dictionaries
        """
        self.data_file_path = Path(data_file_path)
        self.rules = rules
        self.results = None
        self.run_id = None
        self.exceptions = {}

    def run(self, progress_callback=None):
        """
        Exécute le moteur DQ et retourne les résultats

        Args:
            progress_callback: Fonction optionnelle pour mettre à jour la progression
                               Signature: callback(current, total, message)

        Returns:
            dict: {
                'summary': DataFrame with results_summary
                'exceptions': dict of {rule_id: DataFrame}
                'run_id': str
                'timestamp': str
                'status': 'success' or 'error'
                'message': str
            }
        """
        try:
            # Créer un répertoire temporaire pour cette exécution
            temp_dir = Path(tempfile.gettempdir()) / "dq_compass" / "runs"
            temp_dir.mkdir(parents=True, exist_ok=True)

            self.run_id = new_run_id()
            timestamp = now_paris_iso()
            run_dir = temp_dir / self.run_id
            run_dir.mkdir(parents=True, exist_ok=True)

            # Créer un logger
            log = setup_logger(run_dir / "engine.log")

            if progress_callback:
                progress_callback(0, len(self.rules) + 2, "Initialisation...")

            # Créer un catalogue temporaire à partir des règles
            catalogue_path = run_dir / "control_catalogue.csv"
            catalogue_df = pd.DataFrame(self.rules)

            # S'assurer que toutes les colonnes requises sont présentes
            required_cols = [
                "rule_id", "control_name", "control_type", "description", "logic_type",
                "dataset", "column", "param", "threshold", "severity", "frequency",
                "owner", "output_type", "kpi", "remediation_action"
            ]

            for col in required_cols:
                if col not in catalogue_df.columns:
                    catalogue_df[col] = ""

            catalogue_df = catalogue_df[required_cols]
            catalogue_df.to_csv(catalogue_path, index=False)

            if progress_callback:
                progress_callback(1, len(self.rules) + 2, "Chargement du catalogue...")

            # Charger le catalogue
            catalogue = load_catalogue(catalogue_path)

            # Valider le catalogue
            valid_rows, rejected_rows = validate_and_split_catalogue(catalogue, log)

            if progress_callback:
                progress_callback(2, len(self.rules) + 2, "Chargement des données...")

            # Charger les données
            data_dir = self.data_file_path.parent
            datasets = load_all_datasets(valid_rows, data_dir, log)

            # Exécuter les règles
            results = []
            for idx, row in enumerate(valid_rows):
                if progress_callback:
                    progress_callback(
                        3 + idx,
                        len(self.rules) + 2,
                        f"Exécution de la règle {row['rule_id']}..."
                    )

                result = run_rule(row, datasets, log)
                results.append(result)

            # Ajouter les règles rejetées
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

            # Créer le DataFrame de résumé
            summary_columns = [
                "rule_id", "control_name", "dimension", "severity", "status",
                "total_records", "failed_records", "kpi_value", "kpi_label"
            ]

            summary_df = pd.DataFrame(
                [{k: r[k] for k in summary_columns} for r in results]
            )

            # Extraire les exceptions
            exceptions = {}
            for r in results:
                if r["status"] == "FAIL" and r["_exceptions"] is not None and len(r["_exceptions"]) > 0:
                    exceptions[r["rule_id"]] = r["_exceptions"]

            self.results = {
                'summary': summary_df,
                'exceptions': exceptions,
                'run_id': self.run_id,
                'timestamp': timestamp,
                'status': 'success',
                'message': f'{len(results)} règles exécutées avec succès',
                'log_file': str(run_dir / "engine.log")
            }

            if progress_callback:
                progress_callback(len(self.rules) + 2, len(self.rules) + 2, "Terminé !")

            return self.results

        except EngineError as e:
            error_msg = f"Erreur du moteur : {str(e)}"
            log.error(error_msg)
            return {
                'summary': pd.DataFrame(),
                'exceptions': {},
                'run_id': None,
                'timestamp': datetime.now().isoformat(),
                'status': 'error',
                'message': error_msg
            }

        except Exception as e:
            error_msg = f"Erreur inattendue : {str(e)}"
            return {
                'summary': pd.DataFrame(),
                'exceptions': {},
                'run_id': None,
                'timestamp': datetime.now().isoformat(),
                'status': 'error',
                'message': error_msg
            }

    def get_summary_stats(self):
        """Retourne des statistiques agrégées sur les résultats"""
        if self.results is None or self.results['summary'].empty:
            return None

        df = self.results['summary']

        stats = {
            'total_rules': len(df),
            'passed': len(df[df['status'] == 'PASS']),
            'failed': len(df[df['status'] == 'FAIL']),
            'errors': len(df[df['status'] == 'ERROR']),
            'pass_rate': len(df[df['status'] == 'PASS']) / len(df) * 100 if len(df) > 0 else 0,
            'by_dimension': df.groupby('dimension')['status'].value_counts().to_dict(),
            'by_severity': df.groupby('severity')['status'].value_counts().to_dict(),
        }

        return stats
