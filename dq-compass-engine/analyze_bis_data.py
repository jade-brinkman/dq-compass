#!/usr/bin/env python3
"""
Script temporaire pour analyser le fichier BIS et déterminer les seuils
appropriés pour les règles de qualité.
"""
import pandas as pd

# Charger le fichier
df = pd.read_csv("data/WS_DER_OTC_TOV_csv_col.csv", dtype=str, keep_default_na=False)

print(f"=== Analyse du fichier BIS ===")
print(f"Nombre total de lignes : {len(df)}")
print(f"Nombre de colonnes : {len(df.columns)}")
print()

# 1. Vérifier TITLE_TS
print("1. Analyse TITLE_TS")
title_ts_empty = df["TITLE_TS"].str.strip() == ""
print(f"   Lignes avec TITLE_TS vide : {title_ts_empty.sum()} / {len(df)} ({title_ts_empty.sum() / len(df) * 100:.2f}%)")
print()

# 2. Vérifier les colonnes de code
code_cols = ["FREQ", "DER_TYPE", "DER_INSTR", "DER_RISK", "DER_REP_CTY",
             "DER_SECTOR_CPY", "DER_CPC", "DER_SECTOR_UDL", "DER_CURR_LEG1",
             "DER_CURR_LEG2", "DER_ISSUE_MAT", "DER_RATING", "DER_EX_METHOD", "DER_BASIS"]

print("2. Complétude des 14 colonnes de code")
for col in code_cols:
    empty = (df[col].str.strip() == "") | df[col].isna()
    print(f"   {col:20s} : {empty.sum():6d} vides / {len(df)} ({empty.sum() / len(df) * 100:.2f}%)")
print()

# 3. Vérifier la cohérence Series vs colonnes de code
print("3. Cohérence Series vs colonnes de code")
df["computed_series"] = df[code_cols].apply(lambda row: ":".join(row), axis=1)
mismatch = df["Series"] != df["computed_series"]
print(f"   Incohérences : {mismatch.sum()} / {len(df)}")
if mismatch.sum() > 0:
    print(f"   Exemples d'incohérences :")
    for idx in df[mismatch].head(3).index:
        print(f"      Ligne {idx}: Series='{df.loc[idx, 'Series'][:50]}...'")
        print(f"                  Computed='{df.loc[idx, 'computed_series'][:50]}...'")
print()

# 4. Identifier les colonnes-année et compter les lignes après transformation
year_cols = [col for col in df.columns if str(col).strip().isdigit() and len(str(col).strip()) == 4]
print(f"4. Colonnes-année détectées : {len(year_cols)} colonnes (de {min(year_cols)} à {max(year_cols)})")

# Estimer le nombre de lignes après transformation (sans faire la transformation complète)
total_values = 0
for col in year_cols:
    non_empty = (df[col].str.strip() != "")
    total_values += non_empty.sum()
print(f"   Nombre estimé de lignes après wide→long : {total_values:,}")
print()

# 5. Analyser DER_INSTR pour la réconciliation
print("5. Analyse DER_INSTR pour réconciliation")
instr_counts = df["DER_INSTR"].value_counts()
print(f"   Valeurs de DER_INSTR :")
for val, count in instr_counts.items():
    print(f"      {val}: {count:6d} lignes")
total_a = instr_counts.get("A", 0)
total_others = sum(v for k, v in instr_counts.items() if k != "A")
print(f"   Total (A) : {total_a} lignes, Composantes (autres) : {total_others} lignes")
print()

# 6. Analyser DER_REP_CTY
print("6. Analyse DER_REP_CTY")
cty_counts = df["DER_REP_CTY"].value_counts()
print(f"   Nombre de valeurs distinctes : {len(cty_counts)}")
print(f"   '5J' (All countries) : {cty_counts.get('5J', 0)} lignes")
print(f"   Autres pays : {len(df[df['DER_REP_CTY'] != '5J'])} lignes")
print()

print("=== Analyse terminée ===")
