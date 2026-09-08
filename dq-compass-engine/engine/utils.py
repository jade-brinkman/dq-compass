"""
utils.py — fonctions utilitaires transverses du DQ Engine.
(hashing, run_id, timestamp) — aucune logique métier ici.
"""

import hashlib
import uuid
from datetime import datetime
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

PARIS_TZ = ZoneInfo("Europe/Paris") if ZoneInfo else None


def new_run_id() -> str:
    """UUID4 tronqué à 8 caractères hexadécimaux (BF-ENG-05)."""
    return uuid.uuid4().hex[:8]


def now_paris_iso() -> str:
    """Timestamp ISO 8601 avec fuseau Europe/Paris, ex. 2026-09-08T14:32:07+02:00."""
    dt = datetime.now(PARIS_TZ) if PARIS_TZ else datetime.now()
    return dt.isoformat(timespec="seconds")


def sha256_of_file(path: Path) -> str:
    """Empreinte SHA-256 d'un fichier (pour le manifest d'audit)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def count_data_rows(path: Path) -> int:
    """Nombre de lignes de données d'un CSV (hors en-tête)."""
    with open(path, "r", encoding="utf-8") as f:
        return max(sum(1 for _ in f) - 1, 0)
