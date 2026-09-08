"""
Wrapper for calling the DQ engine from Streamlit.
Simplifies the interface and returns results in a format Streamlit can consume.

Every run triggered from the app writes a full, persistent evidence pack —
manifest.json + results_summary.csv + exceptions/*.csv + engine.log — under
the shared `dq-compass-engine/runs/<run_id>/` directory, exactly like a run
started from the command line (`engine/engine.py`). This is what makes an
app-triggered run auditable (BF-AUD-01/02): nothing is left only in the OS
temp folder any more.

Note: GDPR/personal-data detection is handled separately on the Upload page
as an informational check only. It is NOT injected into the final quality
report as a rule.
"""

import sys
from pathlib import Path
import pandas as pd
import json
from datetime import datetime

# Add the engine's path
engine_path = Path(__file__).parent.parent / "dq-compass-engine"
sys.path.insert(0, str(engine_path / "engine"))

from engine import (  # noqa: E402
    load_catalogue,
    execute_run,
    setup_logger,
    EngineError,
)
from utils import new_run_id, now_paris_iso  # noqa: E402

# GDPR check is now informational only (Upload page), not injected in the report
# from data_quality_checks import run_gdpr_check  # noqa: E402

RUNS_DIR = engine_path / "runs"

REQUIRED_CATALOGUE_COLS = [
    "rule_id", "control_name", "control_type", "description", "logic_type",
    "dataset", "column", "param", "threshold", "severity", "frequency",
    "owner", "output_type", "kpi", "remediation_action"
]


class DQEngineWrapper:
    """Simplified wrapper around the DQ engine"""

    def __init__(self, data_file_path: str, rules: list, preloaded_df: pd.DataFrame = None):
        """
        Initialize the engine wrapper

        Args:
            data_file_path: Path to the CSV data file
            rules: List of rule dictionaries
            preloaded_df: Optional pre-loaded DataFrame to avoid re-reading the file
        """
        self.data_file_path = Path(data_file_path)
        self.rules = rules
        self.results = None
        self.run_id = None
        self.exceptions = {}
        self.run_dir = None
        self.preloaded_df = preloaded_df

    def run(self, progress_callback=None):
        """
        Runs the DQ engine and returns the results

        Args:
            progress_callback: Optional function to report progress
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
        log = None
        try:
            self.run_id = new_run_id()
            timestamp = now_paris_iso()
            run_dir = RUNS_DIR / self.run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            self.run_dir = run_dir

            # Create a logger
            log = setup_logger(run_dir / "engine.log")
            log.info("=== DQ Engine (via Streamlit) — run %s démarré à %s ===", self.run_id, timestamp)

            if progress_callback:
                progress_callback(0, len(self.rules) + 2, "Initializing...")

            # Build a temporary catalogue from the rules, written directly
            # into the run's own evidence-pack folder (execute_run()/
            # build_manifest() will use this same file as "the catalogue
            # copy used for this run" — no extra copy needed).
            catalogue_path = run_dir / "control_catalogue.csv"
            catalogue_df = pd.DataFrame(self.rules)

            for col in REQUIRED_CATALOGUE_COLS:
                if col not in catalogue_df.columns:
                    catalogue_df[col] = ""

            catalogue_df = catalogue_df[REQUIRED_CATALOGUE_COLS]
            catalogue_df.to_csv(catalogue_path, index=False)

            if progress_callback:
                progress_callback(1, len(self.rules) + 2, "Loading catalogue...")

            # Sanity check the catalogue loads (surfaces schema errors early
            # with the same explicit message the CLI would give).
            load_catalogue(catalogue_path)

            if progress_callback:
                progress_callback(2, len(self.rules) + 2, "Running rules...")

            # NOTE: GDPR/personal-data detection is now informational only,
            # displayed during the Upload step. It is NOT injected as a rule
            # in the final report (per user request: "RGPD c'est juste une info
            # au moment de la pré-analyse du dataset").

            data_dir = self.data_file_path.parent
            outcome = execute_run(
                catalogue_path=catalogue_path,
                data_dir=data_dir,
                run_dir=run_dir,
                run_id=self.run_id,
                timestamp=timestamp,
                log=log,
                extra_results=[],
            )

            if progress_callback:
                progress_callback(len(self.rules) + 2, len(self.rules) + 2, "Done")

            self.results = {
                'summary': outcome["summary_df"],
                'exceptions': outcome["exceptions"],
                'run_id': self.run_id,
                'timestamp': timestamp,
                'status': 'success',
                'message': f'{len(outcome["results"])} rule(s) executed successfully',
                'log_file': str(run_dir / "engine.log"),
                'run_dir': str(run_dir),
                'manifest': outcome["manifest"],
            }

            return self.results

        except EngineError as e:
            error_msg = f"Engine error: {str(e)}"
            if log:
                log.error(error_msg)
            return {
                'summary': pd.DataFrame(),
                'exceptions': {},
                'run_id': self.run_id,
                'timestamp': datetime.now().isoformat(),
                'status': 'error',
                'message': error_msg,
                'run_dir': str(self.run_dir) if self.run_dir else None,
            }

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            return {
                'summary': pd.DataFrame(),
                'exceptions': {},
                'run_id': self.run_id,
                'timestamp': datetime.now().isoformat(),
                'status': 'error',
                'message': error_msg,
                'run_dir': str(self.run_dir) if self.run_dir else None,
            }

    def get_summary_stats(self):
        """Returns aggregated statistics for the results"""
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
