# DQ Compass - Universal Data Quality Platform

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?logo=pandas&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-3F4F75?logo=plotly&logoColor=white)
![Matplotlib](https://img.shields.io/badge/Matplotlib-11557C?logo=matplotlib&logoColor=white)

<img width="850" alt="image" src="https://github.com/user-attachments/assets/dd661ef5-20db-49c5-9fec-a4ac85c34c2d" />

## Table of contents

- [Project vision](#project-vision)
- [Quick start](#quick-start)
- [Project structure](#project-structure)
- [3-step workflow](#3-step-workflow)
- [Available control types](#available-control-types)
- [How it works](#how-it-works)
- [Example generated report](#example-generated-report)
- [Going further](#going-further)
- [Team](#team)

## Project vision

DQ Compass is a data quality control platform designed to adapt to any business domain and any type of data. No business rule is hardcoded: everything is driven by configuration.

In practice, the user:

1. Uploads a CSV file, regardless of its format or structure
2. Defines their own quality rules through a Streamlit form
3. Gets a visual report of detected anomalies, generated automatically

Project built for the MBA Big Data & AI Datathon (MBA ESG).

---

## Quick start

### Run the Streamlit app (recommended)

```bash
cd dq-compass-app-en

# Windows
run.bat

# Linux/Mac
chmod +x run.sh
./run.sh
```

The app opens at `http://localhost:8501`.

### Use the engine from the command line

```bash
cd dq-compass-engine
python engine/engine.py --catalogue catalogue/control_catalogue.csv --data-dir data
```

### Prerequisites

- Python 3.8+
- pip

### Installation

```bash
git clone <repo_url>
cd dq-compass

# Streamlit app dependencies
cd dq-compass-app-en
pip install -r requirements.txt

# The engine on its own only needs pandas
cd ../dq-compass-engine
pip install pandas
```

No additional configuration is needed: temporary files are created automatically in `/tmp/dq_compass/` (Linux/Mac) or `%TEMP%\dq_compass\` (Windows).

---

## Project structure

```
dq-compass/
│
├── dq-compass-app-en/            Streamlit application
│   ├── Home.py                    Home page
│   ├── pages/
│   │   ├── 1_Upload_Data.py        Step 1: CSV upload
│   │   ├── 2_Define_Rules.py       Step 2: rule form
│   │   └── 3_Quality_Report.py     Step 3: visual report
│   ├── engine_wrapper.py          Wrapper that calls the engine
│   ├── requirements.txt           Dependencies (streamlit, pandas, plotly)
│   ├── README.md                  Detailed app documentation
│   └── run.bat / run.sh           Launch scripts
│
├── dq-compass-engine/            Rules engine (backend)
│   ├── engine/
│   │   ├── engine.py               Generic orchestrator
│   │   ├── rules.py                7 generic logic_types
│   │   └── utils.py                Utilities (SHA-256, run_id...)
│   ├── catalogue/
│   │   └── control_catalogue.csv   Rule catalogue
│   ├── data/                       Datasets
│   └── runs/                       Run history (evidence packs)
│
└── README.md                      This file
```

---

## 3-step workflow

### 1. Upload Data

<img width="850" alt="image" src="https://github.com/user-attachments/assets/e5d4639d-0715-42e0-a104-d003193720f1" />
<img width="850" alt="image" src="https://github.com/user-attachments/assets/20dc71e0-421f-433c-926c-d2167343dc99" />

- CSV file upload
- Automatic separator detection (`,` `;` `\t` `|`)
- Automatic detection of wide format (time-based columns) and transformation into long format
- Data preview and completeness statistics

The automatic wide-to-long transformation makes it possible to process pivoted datasets directly, for example BIS data with year columns.

An initial automatic analysis is run, letting the user get a first look at the dataset's characteristics.

<img width="850" alt="image" src="https://github.com/user-attachments/assets/c124430a-9045-493a-94fc-4988d6c0cf28" />

The user can then select the scope of the analysis.

<img width="850" alt="image" src="https://github.com/user-attachments/assets/982c5d83-234d-4162-ad81-98dd0eb3c7f0" />

### 2. Define Rules

- Interactive form to create quality rules
- Contextual instructions based on the selected rule type
- 7 available control types (see table below)
- Import / export of rules in JSON format

This screen lets you select the basic quality rules or create your own custom rules.

<img width="850" alt="image" src="https://github.com/user-attachments/assets/3c668dda-0111-45bf-9a70-07800f599ee8" />


<img width="850" alt="image" src="https://github.com/user-attachments/assets/e913c274-2c12-4840-a54e-701f1724efc6" />
<img width="850" alt="image" src="https://github.com/user-attachments/assets/589c142f-0601-4c06-99ab-82c0849fa525" />

If the user already has a full catalogue of standardized rules, it can be imported directly into the app. A template is available for download to help build that catalogue.

<img width="850" alt="image" src="https://github.com/user-attachments/assets/5960bf87-ac46-4fbb-b7ae-92bfd9435654" />

The form keeps a standardized structure, the same regardless of the business domain, while staying flexible enough to adapt to very different use cases.

### 3. Quality Report

- One-click report generation, with a progress bar
- Visual KPIs: success rate, number of failures
- Plotly visualizations: PASS / FAIL / ERROR breakdown, results by dimension, results by severity
- Detailed table with filters, list of exceptions per rule
- CSV / JSON export of results and exceptions
- Automatic recommendations based on the results

<img width="850" alt="image" src="https://github.com/user-attachments/assets/8121a62c-39ee-4099-84a1-b6cf9b694cb8" />

<img width="850" alt="image" src="https://github.com/user-attachments/assets/9853015e-5f99-49fb-b5df-9a9ed7535ece" />

Once the report is generated, the user can download it in several formats.

<img width="850" alt="image" src="https://github.com/user-attachments/assets/cd994517-a944-4b3f-a0d4-2386191d9a46" />

---

## Available control types

| # | logic_type | Description | Example use case |
|---|---|---|---|
| 1 | `not_null` | Checks that a column has no missing values | Required email |
| 2 | `regex` | Checks a format using a regular expression | Email, phone, IBAN format |
| 3 | `unique` | Detects duplicates on a column | Unique client ID |
| 4 | `unique_composite` | Detects duplicates on a combination of columns | Unique (series_id + year) |
| 5 | `conditional_equals` | Checks conditional consistency between columns | If status = closed then balance = 0 |
| 6 | `max_age_days` | Checks how recent a date is | Update less than 30 days old |
| 7 | `reconciliation_sum` | Compares totals between files or groups | Sum of regions = national total |

These 7 types are strictly generic: none of them refers to a specific business domain or dataset.

---

## How it works

1. The user uploads a CSV via Streamlit
2. Streamlit saves the file to a temporary folder
3. The user defines rules through the form
4. Streamlit generates a temporary CSV catalogue
5. The Engine Wrapper calls the engine with the catalogue and the data
6. The engine loads the data (automatic transformation if wide format), runs the generic rules, and returns a summary (`results_summary`) along with the exceptions
7. Streamlit displays the report with its visualizations, and the user can get a report ready to share

### Output contract (reproducibility)

`results_summary.csv` (9 fixed columns):

```
rule_id, control_name, dimension, severity, status,
total_records, failed_records, kpi_value, kpi_label
```

`exceptions/{rule_id}_exceptions.csv`: row identifier, offending column(s), reason.

`manifest.json`: run_id, timestamp, sources (SHA-256 and row count), a copy of the catalogue used.

Two runs on the same files produce a byte-identical `results_summary.csv`.

---

## Example generated report

```
Total rules   : 6
Passed        : 5
Failed        : 1
Errors        : 0
Success rate  : 83.3%
```

Charts: PASS / FAIL split (83% / 17%), results by dimension (completeness 100%, reconciliation 0%), results by severity (High 75%, Medium 100%).

Example exceptions (rule DQ06, balance reconciliation by region):

```
rule_id: DQ06
failed_records: 15
kpi_value: 2.45 (max deviation in %)

client_id | region | balance | computed_total | reference_total | deviation_pct
C001      | North  | 1500    | 45678.00       | 45000.00        | 1.51
...
```

---

## Going further

### Adding an 8th logic_type

1. Open `dq-compass-engine/engine/rules.py`
2. Create a generic function, following the same pattern as the 7 existing ones
3. Add it to the `LOGIC_TYPE_FUNCTIONS` dictionary
4. Update the Streamlit form to include it

Example: a `value_range` logic_type to check that a value stays within a [min, max] interval.

### Automation

The Streamlit app is well suited to interactive exploration. For automation, the engine can be used directly from the command line:

```bash
cd dq-compass-engine
python engine/engine.py --catalogue my_catalogue.csv --data-dir my_data/
```

### CI/CD integration

```yaml
# Example GitLab CI
quality_check:
  script:
    - cd dq-compass-engine
    - python engine/engine.py --catalogue production_rules.csv --data-dir data/
    - python check_results.py
```

---

## Team

Project built for the MBA Big Data & AI Datathon.

- **Jade**
- **Irmeline**
- **Karima**
- **Melissa**
- **Axel**
- **Johann**
- **Lucas**
