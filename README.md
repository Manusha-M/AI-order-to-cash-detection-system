

# Order-to-Cash Revenue Leakage and Process Delay Analysis

A local analytics system that tracks the order-to-cash (O2C) lifecycle, identifies revenue leakage and process delays, and provides explainable evidence for each detected exception.

The project generates realistic synthetic business data, introduces controlled and labelled anomalies, detects them using deterministic rules, reconciles financial records, and evaluates detection results against separate ground truth.

## Project Overview

Order-to-cash processes span multiple business entities and teams. Errors or delays between quoting, ordering, fulfilment, invoicing, payment, and dispute resolution can lead to revenue leakage, inaccurate accounts receivable, delayed collections, and operational inefficiencies.

This project provides an end-to-end local system to:

- Model the order-to-cash lifecycle.
- Generate reproducible synthetic business data.
- Preserve lifecycle changes as status events.
- Detect revenue leakage and process exceptions.
- Explain each finding with supporting evidence.
- Reconcile financial records to the paisa.
- Evaluate detection results against separate ground truth.
- Explore results through a Streamlit dashboard.

The system uses **Python, SQLite, and explainable rule-based detection**. It does not rely on an opaque machine-learning model.

## Business Workflow

The system models the following lifecycle:

```text
Account
  ↓
Quote → Quote Line
  ↓ Accepted
Sales Order → Order Line
  ↓
Shipment → Shipment Line
  ↓
Invoice → Invoice Line
  ↓
Payment → Payment Allocation
  ↓
Dispute / Accounts Receivable
```

The workflow preserves relationships between records and supports partial fulfilment, multiple invoices, payment allocation, disputes, credits, and lifecycle events.

## Key Features

### Synthetic Data Generation

- Generates deterministic synthetic business data using a configurable seed.
- Creates valid baseline records before introducing controlled anomalies.
- Supports starter and full dataset scales.
- Uses parent-first generation so dependent records reference valid parent IDs.
- Produces consistent results when regenerated with the same seed and configuration.

### Deterministic Business ID Conventions

The system uses stable, human-readable business identifiers with a fixed 2026 prefix and six-digit zero-padded sequence:

| Entity | ID format | Example |
|---|---|---|
| Quote | `QTE-2026-######` | `QTE-2026-000001` |
| Sales Order | `SO-2026-######` | `SO-2026-000001` |
| Shipment | `SHP-2026-######` | `SHP-2026-000001` |
| Invoice | `INV-2026-######` | `INV-2026-000001` |
| Payment | `PAY-2026-######` | `PAY-2026-000001` |
| Dispute | `DSP-2026-######` | `DSP-2026-000001` |

These identifiers are generated deterministically and enforced by database schema constraints. Foreign-key relationships use these identifiers to preserve traceability across the order-to-cash lifecycle.

### Explainable Exception Detection

The detection engine uses deterministic business rules to identify exceptions. Findings include the issue type, affected business record, severity, financial or operational impact, and supporting evidence.

The system includes rules for:

- Overbilling
- Underbilling
- Duplicate invoices
- Duplicate payment allocations
- Short payments
- Closed orders with unpaid balances
- Disputes not reflected in accounts receivable
- Long-overdue invoices
- Fulfilment delays
- Invoicing delays
- Illegal lifecycle transitions

### Financial Reconciliation

The system reconciles key financial relationships and uses integer paise for monetary calculations to avoid floating-point rounding errors.

Reconciliation covers:

- Invoice balances
- Payment amounts and allocations
- Accounts receivable
- Credits and dispute holds
- Ledger consistency
- Fulfilment and invoicing quantities

### Ground-Truth Evaluation

Ground-truth labels are stored separately from the input data used by the detection engine.

The evaluation process compares detected findings against labelled cases and reports:

- True positives
- False positives
- False negatives
- Precision
- Recall
- F1 score

A clean dataset is also used as a negative control to check whether the detector reports unexpected findings when no anomalies are injected.

### Streamlit Dashboard

The dashboard provides a visual interface for exploring:

- Overall order-to-cash performance
- Revenue and financial reconciliation
- Exception findings
- Process delays
- Evaluation results

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Data generation, business logic, validation, detection, evaluation |
| SQLite | Local relational database and persistence |
| SQL | Schema, relationships, views, and analytics queries |
| Streamlit | Interactive dashboard |
| Pandas | Data handling and dashboard support |
| Altair | Visualizations |
| Pytest | Automated testing |

## Project Structure

```text
.
├── app/
│   └── dashboard.py
├── data/
│   └── generated outputs
├── docs/
│   ├── ai_usage.md
│   ├── development_log.md
│   ├── prompt_history.md
│   ├── decisions.md
│   ├── validation_report.md
│   └── final_audit.md
├── sql/
│   ├── schema.sql
│   └── analytics.sql
├── src/
│   ├── generator.py
│   ├── anomaly_injection.py
│   ├── detector.py
│   ├── database.py
│   ├── validation.py
│   └── reconciliation.py
├── tests/
├── HANDOFF.md
├── README.md
├── requirements.txt
└── run.py
```

## Requirements

- Python 3.11 or newer
- Git
- Windows, macOS, or Linux

The project was tested with Python 3.13.6.

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/Manusha-M/AI-order-to-cash-detection-system.git
cd AI-order-to-cash-detection-system
```

### 2. Create a virtual environment

**Windows PowerShell:**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**Git Bash:**

```bash
py -3 -m venv .venv
./.venv/Scripts/python.exe -m pip install --upgrade pip
./.venv/Scripts/python.exe -m pip install -r requirements.txt
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run the Project

### Generate and run the starter pipeline

```bash
python run.py all --scale starter
```

### Generate and run the full pipeline

```bash
python run.py all --scale full
```

### Launch the dashboard

```bash
python -m streamlit run app/dashboard.py
```

The dashboard will open in your browser. If it does not open automatically, visit:

```text
http://localhost:8501
```

## Available Commands

Run these commands from the project root.

| Command | Purpose |
|---|---|
| `python run.py all --scale starter` | Run the complete starter pipeline |
| `python run.py all --scale full` | Run the complete full pipeline |
| `python run.py generate --scale starter` | Generate synthetic data |
| `python run.py detect --scale starter` | Run exception detection |
| `python run.py validate --scale starter` | Validate generated data |
| `python run.py reconcile --scale starter` | Run financial reconciliation |
| `python run.py evaluate --scale starter` | Evaluate detections against ground truth |
| `python run.py negative-control --scale starter` | Run the clean-data negative control |
| `python run.py reproduce --scale starter` | Check reproducibility |
| `python run.py seed_sweep` | Run checks across multiple seeds |
| `pytest` | Run automated tests |

Use `--scale full` where applicable to run the larger dataset.

## Synthetic Data

The project generates synthetic records for the following entities:

- Account
- Product
- Quote
- Quote Line
- Sales Order
- Order Line
- Shipment
- Shipment Line
- Invoice
- Invoice Line
- Invoice–Shipment relationship
- Payment
- Payment Allocation
- Dispute
- Accounts Receivable Ledger Entry
- Status Event
- Ground Truth

The full-scale dataset is designed around the project brief’s target volumes, including approximately:

| Entity | Full-scale target |
|---|---:|
| Quotes | 10,000 |
| Sales Orders | 7,000 |
| Invoices | 8,000 |
| Payments | 15,000 |
| Status Events | 150,000+ |

The generated data uses a fixed seed by default:

```text
20261022
```

The pipeline creates a valid baseline dataset first, then injects controlled anomalies. Ground-truth labels are maintained separately so the detector does not use the answer labels as input features.

## Validation and Reconciliation

The validation process checks structural and business consistency, including:

- Primary-key uniqueness
- Foreign-key integrity
- Valid lifecycle states
- Valid date ordering
- Quantity and monetary arithmetic
- Parent-child relationship consistency
- Invoice and payment allocation consistency
- Lifecycle transition validity
- Duplicate and anomaly-specific conditions

The reconciliation process checks financial identities and reports differences in paise.

## Evaluation Results

The project evaluates the detector against separate ground-truth labels. The reported synthetic-data results are documented in:

- [`docs/validation_report.md`](docs/validation_report.md)
- [`docs/final_audit.md`](docs/final_audit.md)

**Important:** Strong results on synthetic data demonstrate that the implementation detects the patterns represented in its generator and rules. They do not establish equivalent performance on real production data.

## Assumptions and Limitations

- The system uses a single currency.
- Tax is excluded from the current financial model.
- Business thresholds are configurable in `src/config.py`.
- The detection engine is deterministic and only detects patterns represented by its implemented rules.
- SQLite is used for local development and demonstration.
- Synthetic data is not a substitute for validation against independently reviewed real-world data.
- Some financial exception categories may overlap and should not automatically be summed into one total exposure figure.

Further limitations and design trade-offs are documented in [`docs/decisions.md`](docs/decisions.md).

## Testing

Run the automated test suite:

```bash
pytest
```

The project also includes commands for validation, reconciliation, reproducibility, and negative-control evaluation.

## Development History and Evidence

This project was built locally with Claude Code in one session on 30 October 2026, without Git, and published to GitHub afterwards. That is why the repository history starts with one large commit. Later commits are changes made after publication.

The development log is a separate record from the Git history. These documents show how the solution evolved before publication:

| Document | What it records |
|---|---|
| [`docs/development_log.md`](docs/development_log.md) | Chronological record of milestones, debugging, testing and final verification |
| [`docs/prompt_history.md`](docs/prompt_history.md) | AI prompts, with timestamps |
| [`docs/ai_usage.md`](docs/ai_usage.md) | AI usage and contribution disclosure |
| [`docs/decisions.md`](docs/decisions.md) | Technical decisions, trade-offs and the bugs found along the way |
| [`docs/validation_report.md`](docs/validation_report.md) | Measured testing and validation results |
| [`docs/final_audit.md`](docs/final_audit.md) | Final requirement audit and open items |

## AI-Assisted Development

This project was built with Claude Code from the prompt in [`docs/prompt_history.md`](docs/prompt_history.md). That master prompt was created with ChatGPT. AI wrote the code, tests and documentation, and ran the checks reported here. What the candidate reviewed, and how the prompts relate to the final submission, is stated in [`docs/ai_usage.md`](docs/ai_usage.md). That file is the authoritative record.

## Author

**Manusha Manne**

GitHub: [Manusha-M](https://github.com/Manusha-M)

