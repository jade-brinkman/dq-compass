#!/usr/bin/env python3
"""
generate_data.py — Génère le jeu de données synthétique de test pour le DQ Engine.

Produit :
  - data/clients.csv          (>= 500 lignes, conforme au schéma section 5.1 du cahier des besoins)
  - data/reference_totals.csv (conforme au schéma section 5.2)

Graine aléatoire fixe (BNF-06) => génération 100% reproductible.
Des erreurs sont injectées volontairement pour que chacune des 6 règles DQ01-DQ06
produise au moins un FAIL sur ce jeu de test (cf. plan de recette, section 10 du
cahier des besoins).

Ce script est une fixture de test pour valider le moteur (Jade). Le jeu de données
"officiel" de l'équipe (généré/fourni par Irmeline ou l'équipe Data) doit respecter
exactement le même schéma pour être compatible avec le moteur tel quel.
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 42
N_ROWS = 520
EXTRACTION_DATE = date(2026, 9, 7)  # doit matcher le param de DQ05 dans le catalogue

REGIONS = ["FR-IDF", "FR-SUD", "FR-OUEST", "BE-BXL", "LU-LUX"]
REGION_COUNTRY = {
    "FR-IDF": "FR",
    "FR-SUD": "FR",
    "FR-OUEST": "FR",
    "BE-BXL": "BE",
    "LU-LUX": "LU",
}

FIRST_NAMES = [
    "Camille", "Lucas", "Manon", "Hugo", "Chloe", "Nathan", "Emma", "Louis",
    "Ines", "Adam", "Lea", "Jules", "Sarah", "Tom", "Julia", "Leo", "Zoe",
    "Ethan", "Anna", "Noah", "Lina", "Gabriel", "Alice", "Raphael", "Jade",
]
LAST_NAMES = [
    "Martin", "Bernard", "Dubois", "Thomas", "Robert", "Petit", "Durand",
    "Leroy", "Moreau", "Simon", "Laurent", "Lefebvre", "Michel", "Garcia",
    "David", "Bertrand", "Roux", "Vincent", "Fournier", "Girard", "Andre",
]

EMAIL_DOMAINS = ["example.com", "example.fr", "mailbox.eu"]


def make_email(first, last, idx, malformed=False, empty=False):
    if empty:
        return ""
    base = f"{first.lower()}.{last.lower()}{idx}"
    domain = random.choice(EMAIL_DOMAINS)
    if malformed:
        # quelques variantes d'email non vide mais mal formé
        variant = random.choice([
            f"{base}@",                    # domaine manquant
            f"{base}{domain}",             # arobase manquante
            f"{base}@{domain.split('.')[0]}",  # pas d'extension
            f"{base} @{domain}",           # espace
        ])
        return variant
    return f"{base}@{domain}"


def random_date_between(start: date, end: date) -> date:
    delta_days = (end - start).days
    return start + timedelta(days=random.randint(0, max(delta_days, 0)))


def generate_clients(n_rows: int):
    rows = []
    used_ids = []

    for i in range(1, n_rows + 1):
        client_id = f"CLI-{10000 + i}"
        used_ids.append(client_id)

        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        region = random.choice(REGIONS)
        country_code = REGION_COUNTRY[region]

        signup_date = random_date_between(date(2020, 1, 1), date(2026, 6, 30))
        status = random.choices(["active", "closed"], weights=[0.85, 0.15])[0]

        # last_update_ts : la plupart récents (<30j), une partie plus ancienne (DQ05)
        if random.random() < 0.06:
            last_update_ts = EXTRACTION_DATE - timedelta(days=random.randint(31, 400))
        else:
            last_update_ts = EXTRACTION_DATE - timedelta(days=random.randint(0, 29))
        if last_update_ts < signup_date:
            last_update_ts = signup_date

        if status == "closed":
            # normalement solde à 0 ; une partie des comptes clos gardent un solde (DQ04)
            balance = 0.0 if random.random() > 0.08 else round(random.uniform(5, 500), 2)
        else:
            balance = round(random.uniform(-200, 8000), 2)

        # email : la plupart valides, une partie vide (DQ01), une partie mal formée (DQ02)
        roll = random.random()
        if roll < 0.02:
            email = make_email(first, last, i, empty=True)
        elif roll < 0.06:
            email = make_email(first, last, i, malformed=True)
        else:
            email = make_email(first, last, i)

        rows.append({
            "client_id": client_id,
            "first_name": first,
            "last_name": last,
            "email": email,
            "country_code": country_code,
            "region": region,
            "signup_date": signup_date.isoformat(),
            "last_update_ts": last_update_ts.isoformat(),
            "status": status,
            "account_balance_eur": f"{balance:.2f}",
        })

    # DQ03 : injecter volontairement un doublon de client_id (duplique une ligne existante
    # avec un nouvel index de ligne mais le même client_id)
    dup_source = dict(rows[10])
    dup_source["first_name"] = "Duplicate"
    rows.append(dup_source)

    return rows


def write_clients_csv(rows, path: Path):
    fieldnames = [
        "client_id", "first_name", "last_name", "email", "country_code",
        "region", "signup_date", "last_update_ts", "status", "account_balance_eur",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_reference_totals_csv(rows, path: Path):
    totals = {r: 0.0 for r in REGIONS}
    for row in rows:
        totals[row["region"]] += float(row["account_balance_eur"])

    # DQ06 : une région (FR-SUD) est volontairement décalée de plus de 1% pour
    # provoquer un FAIL de réconciliation ; les autres régions matchent (~0%).
    out_rows = []
    for region in REGIONS:
        source_total = totals[region]
        if region == "FR-SUD":
            source_total = source_total * 1.05  # écart volontaire de 5%
        out_rows.append({
            "region": region,
            "source_total_balance_eur": f"{source_total:.2f}",
        })

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["region", "source_total_balance_eur"])
        writer.writeheader()
        writer.writerows(out_rows)


def main():
    random.seed(SEED)
    out_dir = Path(__file__).parent
    rows = generate_clients(N_ROWS)
    write_clients_csv(rows, out_dir / "clients.csv")
    write_reference_totals_csv(rows, out_dir / "reference_totals.csv")
    print(f"clients.csv : {len(rows)} lignes générées (seed={SEED})")
    print(f"reference_totals.csv : {len(REGIONS)} régions")


if __name__ == "__main__":
    main()
