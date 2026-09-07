# DQ Engine — brique 2/4 (Jade)

Moteur d'exécution générique du catalogue de contrôles qualité. Aucune règle
métier n'est codée en dur : les 6 `logic_type` sont implémentés par 6
fonctions génériques dans `engine/rules.py`, appliquées dynamiquement à
n'importe quel jeu de règles respectant le format du catalogue.

## Structure

```
catalogue/control_catalogue.csv   Catalogue (6 règles DQ01-DQ06) — fichier séparé du code
data/generate_data.py             Générateur du jeu de données de test (fixture, seed fixe)
data/clients.csv                  Jeu de données synthétique (521 lignes)
data/reference_totals.csv         Totaux de référence par région
engine/rules.py                   Les 6 fonctions génériques (logic_type)
engine/engine.py                  Orchestrateur (chargement, exécution, sorties)
engine/utils.py                   run_id, timestamp, SHA-256
runs/<run_id>/                    Une exécution = un dossier (evidence pack)
  ├─ manifest.json                run_id, timestamp, sources + SHA-256, copie du catalogue
  ├─ results_summary.csv          1 ligne par règle (pass/fail + métriques)
  ├─ exceptions/<rule_id>_exceptions.csv   lignes en échec, par règle
  └─ engine.log                   logs d'exécution
results_summary.csv, exceptions/  Copie "dernière exécution" à la racine (pratique pour Lucas)
```

## Lancer une exécution

```bash
pip install pandas
python3 data/generate_data.py         # génère/regénère le jeu de test (une seule fois)
python3 engine/engine.py              # exécute le moteur sur le catalogue courant
```

Chaque exécution crée un nouveau `runs/<run_id>/`. Deux exécutions sur les
mêmes fichiers produisent un `results_summary.csv` identique à l'octet près
(hors `run_id`/`timestamp`, qui ne sont même pas des colonnes de ce fichier —
ils vivent dans `manifest.json` et le nom du dossier). Vérifié : cf. section
Tests ci-dessous.

## Contrat catalogue ↔ moteur (à partager avec Irmeline)

Le catalogue (`catalogue/control_catalogue.csv`) doit respecter exactement
les colonnes de BF-CAT-01, dans cet ordre :

```
rule_id, control_name, control_type, description, logic_type, dataset,
column, param, threshold, severity, frequency, owner, output_type, kpi,
remediation_action
```

`logic_type` ne prend que l'une des 6 valeurs supportées ; toute autre
valeur est rejetée au chargement (log ERROR + règle marquée `ERROR` dans
`results_summary.csv`, le run continue sur les règles valides).

Pour chaque `logic_type`, voici comment remplir `dataset` / `column` / `param`
/ `threshold` — c'est la seule "convention" à connaître, elle est générique
et vaut pour n'importe quelle règle qui utilise ce `logic_type` (pas
seulement DQ01-DQ06) :

| logic_type | dataset | column | param | threshold |
|---|---|---|---|---|
| `not_null` | `fichier.csv` | `colonne` | *(vide)* | % max de valeurs manquantes toléré |
| `regex` | `fichier.csv` | `colonne` | motif regex | % max de non-conformes toléré (parmi les valeurs non vides) |
| `unique` | `fichier.csv` | `colonne clé` | *(vide)* | % max de lignes dupliquées toléré |
| `conditional_equals` | `fichier.csv` | `col_condition:col_cible` | `val_condition:val_cible` | tolérance numérique absolue |
| `max_age_days` | `fichier.csv` | `colonne date` | date de référence ISO (`AAAA-MM-JJ`) ou `today` | âge max en jours |
| `reconciliation_sum` | `fichier1.csv;fichier2.csv` | `col_groupe:col_valeur` | `fichier_ref.csv:col_groupe_ref:col_valeur_ref` | % max d'écart par groupe |

Ajouter une 7e règle (DQ07) qui réutilise un `logic_type` déjà supporté ne
demande **aucune** modification de `engine/` — juste une ligne CSV en plus
(testé, voir ci-dessous).

## Ce que produit le moteur pour les autres briques

- **Lucas (Reporting)** : `results_summary.csv` (colonnes exactes BF-ENG-02)
  + `exceptions/<rule_id>_exceptions.csv` pour chaque règle en échec — les
  enregistrements fautifs sont extraits, pas seulement comptés.
- **Johann (Audit)** : `runs/<run_id>/` complet avec `manifest.json`
  (run_id, timestamp, SHA-256 + nb de lignes des fichiers sources, copie du
  catalogue utilisé) et `engine.log`. Cette structure couvre déjà BF-AUD-01 /
  BF-AUD-02 — à adapter/enrichir si l'Audit Layer a besoin de plus.

## Tests effectués (checklist)

- [x] Exécution complète 6 règles / 521 lignes / 2 fichiers en ~0,05 s (< 10 s, BF-ENG-06)
- [x] Deux runs consécutifs → `results_summary.csv` et tous les `exceptions/*.csv` identiques à l'octet près (BF-ENG-04)
- [x] Colonne référencée renommée → erreur explicite nommant la colonne, run des autres règles non interrompu (BF-ENG-01)
- [x] `logic_type` invalide ajouté → règle rejetée avec log ERROR explicite, reste du catalogue exécuté normalement (BF-CAT-02)
- [x] Règle DQ07 ajoutée (logic_type `not_null` déjà supporté) sans toucher à `engine/` → apparaît dans `results_summary.csv` (BF-CAT-05)
- [x] Sur le jeu de test généré, DQ01 à DQ06 sont tous passés au moins une fois en `FAIL` (plan de recette, section 10 du cahier des besoins)

## Portabilité multi-jeux de données / multi-entreprises

Le moteur ne connaît rien du domaine "banque/clients" : il ne fait que lire
un catalogue et des CSV dont les noms de fichiers/colonnes sont indiqués
dans ce catalogue. Preuve dans `examples/hr-domain/` : un jeu de données RH
totalement différent (employés, salaires, départements) avec son propre
`catalogue_rh.csv` réutilisant les 4 mêmes `logic_type`, exécuté avec la
commande suivante, **sans modifier une seule ligne de `engine/`** :

```bash
python3 engine/engine.py \
  --catalogue examples/hr-domain/catalogue_rh.csv \
  --data-dir examples/hr-domain/data \
  --runs-dir examples/hr-domain/runs \
  --latest-dir examples/hr-domain
```

Pour adapter le moteur à un nouveau client, il suffit d'écrire son propre
`control_catalogue.csv` (même 15 colonnes, même 6 `logic_type`) pointant
vers ses propres fichiers/colonnes. Zéro ligne de code à toucher — c'est
précisément ce que demande BF-CAT-05/BNF-03.

Un point qui restait implicite jusqu'ici a été corrigé pour cette
portabilité : la détection des colonnes numériques (montants, totaux) ne
repose plus sur un nom de colonne particulier ("balance", "total"...) mais
sur une conversion générique (`pd.to_numeric`) faite dans les fonctions de
`rules.py` elles-mêmes — donc valable pour n'importe quel nom de colonne
chez n'importe quel client.

## Choisir les dimensions à mettre en avant

Le client peut restreindre une exécution à un sous-ensemble de dimensions
ou de règles, sans toucher au fichier catalogue :

```bash
python3 engine/engine.py --dimensions "Complétude,Réconciliation"
python3 engine/engine.py --rules "DQ01,DQ04"
```

Le filtre appliqué est tracé dans `manifest.json` (`filters.dimensions` /
`filters.rules`) pour que l'audit sache toujours ce qui a été exécuté sur ce
run précis. C'est un filtre générique sur les colonnes `control_type` /
`rule_id` du catalogue — pas une règle métier de plus.

## Faut-il un "agent" (IA) plutôt qu'un moteur de règles ?

Non, pas pour le cœur du moteur : BNF-01 exige que 100% des verdicts
PASS/FAIL reposent sur une logique déterministe, et le cahier des besoins
classe explicitement l'IA comme "optionnelle et strictement assistive"
(jamais décisionnaire). Un agent LLM qui déciderait des verdicts serait donc
hors périmètre et introduirait de la non-reproductibilité (contraire à
BF-ENG-04). La portabilité et le choix des dimensions se résolvent très
bien avec de la configuration (catalogue + filtres CLI), comme démontré
ci-dessus.

Une piste IA restant dans le périmètre "assistive" : un assistant qui aide
à *rédiger* le catalogue d'un nouveau client (proposer des règles à partir
d'un aperçu de ses colonnes) — mais qui ne déciderait jamais du PASS/FAIL
lui-même. Piste à mentionner en ouverture/scalabilité si utile pour le
pitch, pas nécessaire pour le MVP.

## Points à clarifier avec l'équipe

- Le jeu de données `data/clients.csv` / `reference_totals.csv` est une
  **fixture de test** générée par `generate_data.py` pour valider le moteur
  de bout en bout. Le jeu de données "officiel" du groupe doit respecter le
  même schéma (section 5 du cahier des besoins) pour être compatible tel
  quel avec le moteur.
- Le catalogue `catalogue/control_catalogue.csv` fourni ici respecte le
  format et les 6 règles de la section 6.2 — à remplacer par la version
  d'Irmeline dès qu'elle est prête (même schéma de colonnes).
- `manifest.json` / `engine.log` sont un premier jet pour débloquer
  l'intégration avant que Johann ne construise sa propre couche d'audit ;
  à ajuster ensemble si le format attendu diffère.
