

# Order-to-Cash Revenue Leakage and Process Delay Analysis

A local analytics system for identifying revenue leakage, billing exceptions, payment-allocation issues, and process delays across the Order-to-Cash (O2C) lifecycle.

The project generates a reproducible synthetic dataset, introduces known exceptions, detects them using explainable rules, evaluates the findings against separate ground-truth labels, and verifies financial reconciliation identities.

> **AI-use disclosure:** This project was developed with Claude Code. See [`docs/ai_usage.md`](docs/ai_usage.md) and [`docs/prompt_history.md`](docs/prompt_history.md) for the AI-use record. Setup and verification instructions are in [`HANDOFF.md`](HANDOFF.md). Development before GitHub publication is documented under [Development history and evidence](#development-history-and-evidence).

---

## Table of Contents

- [Project Overview](#project-overview)
- [Business Problem](#business-problem)
- [O2C Workflow](#o2c-workflow)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [Architecture](#architecture)
- [Repository Structure](#repository-structure)
- [Getting Started](#getting-started)
- [Running the Application](#running-the-application)
- [Pipeline Commands](#pipeline-commands)
- [Dashboard](#dashboard)
- [Data Model](#data-model)
- [Synthetic Data and Ground Truth](#synthetic-data-and-ground-truth)
- [Exception Detection](#exception-detection)
- [Financial Reconciliation](#financial-reconciliation)
- [Evaluation Methodology](#evaluation-methodology)
- [Measured Results](#measured-results)
- [Assumptions and Decisions](#assumptions-and-decisions)
- [Limitations](#limitations)
- [Testing and Verification](#testing-and-verification)
- [Development History and Evidence](#development-history-and-evidence)
- [AI-Assisted Development](#ai-assisted-development)
- [Future Improvements](#future-improvements)

---

## Project Overview

The system follows transactions from quote creation through order fulfilment, invoicing, payment, and accounts-receivable reconciliation.

It is designed to answer questions such as:

- Was the customer billed for the correct quantity?
- Were invoices duplicated or overbilled?
- Were shipments invoiced within the expected time?
- Were payments allocated correctly?
- Are there unpaid or overdue invoices?
- Are disputes reflected correctly in accounts receivable?
- Do the financial records reconcile?

The implementation is local-first: the data pipeline runs in Python and SQLite, and the dashboard provides an interactive view of the generated results.

## Business Problem

Order-to-Cash processes involve multiple connected business records. An inconsistency in one stage can create revenue leakage, collection delays, inaccurate accounts receivable, or customer-facing billing errors.

This project demonstrates a way to:

1. Generate a controlled O2C dataset.
2. Introduce known business exceptions.
3. detect exceptions using deterministic, explainable rules.
4. Measure detection performance against independent labels.
5. Verify that financial totals reconcile.
6. Explore the results through a dashboard.

The data is synthetic and intended for demonstration, testing, and evaluation—not as a claim of production performance on real customer data.

## O2C Workflow

The modeled business flow is:

```text
Account
   ↓
Quote
   ↓
Sales Order
   ↓
Shipment
   ↓
Invoice
   ↓
Payment
   ↓
Accounts Receivable Reconciliation
```

Disputes are modeled alongside the invoice and accounts-receivable process.

## Key Features

- **Reproducible synthetic data:** The same seed produces the same generated data.
- **Valid baseline first:** The generator creates valid business records before introducing labelled exceptions.
- **Event history:** Status changes are recorded in `status_event`.
- **Explainable detection:** Findings include the rule, affected records, evidence, severity, and estimated impact.
- **Financial reconciliation:** Six financial identities are checked and expected to reconcile to zero paise.
- **Separate ground truth:** Detection results are evaluated against a separate ground-truth file.
- **Clean-data checks:** The system checks whether the rules produce findings on a clean dataset.
- **Interactive dashboard:** A five-tab Streamlit dashboard provides views of business performance, exceptions, reconciliation, evaluation, and process delays.

## Technology Stack

| Area | Technology |
|---|---|
| Language | Python |
| Database | SQLite |
| Data processing | Python standard library, Pandas, NumPy |
| Dashboard | Streamlit, Altair |
| Testing | pytest |
| Version control | Git and GitHub |

The core pipeline is designed to run locally without a hosted database or external service.

## Architecture

```text
Synthetic Data Generator
        │
        ├── Valid baseline records
        ├── Injected exception scenarios
        └── Ground-truth labels
                │
                ▼
           SQLite Database
                │
                ▼
      Deterministic Detection Rules
                │
                ├── Exception findings
                ├── Financial reconciliation
                └── Evaluation results
                        │
                        ▼
                 Streamlit Dashboard
```

The pipeline is organized into separate stages so that data generation, detection, validation, reconciliation, and evaluation can be run independently.

### Why SQLite and deterministic rules?

SQLite keeps the project easy to run on a new laptop without configuring a database server. Deterministic rules make the findings traceable: a reviewer can inspect the condition that triggered a finding and the records supporting it.

The project uses rule-based detection rather than claiming that a trained machine-learning model is required for these scenarios.

## Repository Structure

```text
.
├── app/
│   └── dashboard.py
├── data/
│   ├── starter/
│   └── ...
├── docs/
│   ├── ai_usage.md
│   ├── decisions.md
│   ├── development_log.md
│   ├── final_audit.md
│   ├── prompt_history.md
│   └── validation_report.md
├── outputs/
├── scripts/
├── sql/
├── src/
├── tests/
├── .gitignore
├── HANDOFF.md
├── README.md
├── pytest.ini
├── requirements.txt
└── run.py
```

## Getting Started

### Requirements

- Python 3.11 or later
- Git
- Windows, macOS, or Linux

The project was tested with Python 3.13.6.

### 1. Clone the repository

```bash
git clone https://github.com/Manusha-M/AI-order-to-cash-detection-system.git
cd AI-order-to-cash-detection-system
```

### 2. Create a virtual environment

**Windows PowerShell:**

```powershell
py -3 -m venv .venv
```

**macOS / Linux:**

```bash
python3 -m venv .venv
```

### 3. Install dependencies

**Windows PowerShell:**

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**macOS / Linux:**

```bash
.venv/bin/python -m pip install -r requirements.txt
```

You can activate the virtual environment if preferred, but the commands above call its Python executable directly.

## Running the Application

### Run the starter pipeline

**Windows PowerShell:**

```powershell
.\.venv\Scripts\python.exe run.py all --scale starter
```

**macOS / Linux:**

```bash
.venv/bin/python run.py all --scale starter
```

### Run the full pipeline

**Windows PowerShell:**

```powershell
.\.venv\Scripts\python.exe run.py all --scale full
```

**macOS / Linux:**

```bash
.venv/bin/python run.py all --scale full
```

The full pipeline takes approximately two minutes on the tested environment. Runtime depends on the computer and Python environment.

### Launch the dashboard

**Windows PowerShell:**

```powershell
.\.venv\Scripts\python.exe -m streamlit run app\dashboard.py
```

**macOS / Linux:**

```bash
.venv/bin/python -m streamlit run app/dashboard.py
```

Streamlit prints a local URL in the terminal. Open that URL in your browser.

For additional setup and verification details, see [`HANDOFF.md`](HANDOFF.md).

## Pipeline Commands

The `run.py` entry point exposes individual pipeline stages.

| Command | Purpose |
|---|---|
| `all` | Run the complete pipeline |
| `generate` | Generate the synthetic dataset |
| `detect` | Run exception-detection rules |
| `validate` | Run structural and data-quality checks |
| `reconcile` | Verify financial reconciliation identities |
| `evaluate` | Compare findings against ground truth |
| `negative-control` | Run checks against clean data |
| `reproduce` | Verify reproducibility |
| `seed_sweep` | Run checks across multiple seeds |

Examples:

```bash
python run.py generate --scale starter
python run.py detect --scale starter
python run.py validate --scale starter
python run.py reconcile --scale starter
python run.py evaluate --scale starter
python run.py negative-control --scale starter
python run.py reproduce --scale starter
```

The default seed is `20261022`.

## Dashboard

The Streamlit dashboard contains five tabs for exploring the generated O2C data and pipeline results.

The dashboard is intended to help reviewers:

- Understand the overall business picture.
- Inspect detected exceptions and their supporting evidence.
- Review reconciliation checks.
- Examine detection evaluation results.
- Explore process delays across O2C stages.

## Data Model

The database models the main O2C entities and supporting records.

Core entities include:

- Account
- Product
- Quote
- Quote line
- Sales order
- Order line
- Shipment
- Invoice
- Invoice line
- Payment
- Dispute

Supporting tables include:

- `shipment_line`
- `invoice_shipment`
- `payment_allocation`
- `ar_ledger_entry`
- `status_event`

Money is stored as **integer paise** rather than floating-point currency values to avoid floating-point rounding errors in financial calculations.

## Synthetic Data and Ground Truth

The generator creates a valid baseline dataset and then introduces controlled exception scenarios.

Key properties:

- The generator uses a fixed seed for reproducibility.
- Synthetic customer and business records are used.
- A cutoff date of `2026-09-30` is used for the measured run.
- The generated dataset and manifest are stored locally.
- Ground-truth labels are maintained separately from detection findings.
- Lookalike clean cases are included to help test whether rules incorrectly flag valid records.

The ground-truth file is used for evaluation; it is not intended to be used by the detection rules to identify the injected exceptions.

## Exception Detection

The system detects business exceptions using deterministic rules.

The implemented exception categories include:

| Exception | Description |
|---|---|
| `CLOSED_ORDER_UNPAID` | An order is closed while payment remains outstanding |
| `DISPUTE_NOT_IN_AR` | A dispute is not reflected correctly in accounts receivable |
| `DUPLICATE_ALLOCATION` | A payment allocation is duplicated |
| `DUPLICATE_INVOICE` | An invoice appears to have been duplicated |
| `FULFILMENT_DELAY` | Fulfilment exceeds the configured target |
| `ILLEGAL_TRANSITION` | A record has an invalid status transition |
| `INVOICING_DELAY` | Invoicing exceeds the configured target |
| `LONG_OVERDUE` | An invoice exceeds the overdue threshold |
| `OVERBILLING` | The billed quantity or amount exceeds the supported amount |
| `SHORT_PAYMENT` | Payment received is less than the amount due |
| `UNDERBILLING` | The billed amount is lower than the supported amount |

Each finding is designed to include:

- Exception type
- Primary record identifier
- Related source records
- Severity
- Expected and observed values, where applicable
- Estimated financial impact, where applicable
- Evidence explaining why the rule fired

## Financial Reconciliation

The pipeline checks six financial identities. These checks are expected to reconcile to **zero paise**.

The system distinguishes between different financial concepts, including:

- Underbilled income potentially lost
- Overbilling exposure
- Duplicate-billing exposure
- Refund or credit exposure
- Collection risk
- Payment-allocation discrepancies

These values represent different types of exposure and should not automatically be added together as one total. Some categories can overlap.

## Evaluation Methodology

The system evaluates detection findings against separate ground-truth labels.

Evaluation includes:

- **Injected labels:** Exceptions deliberately introduced into the synthetic data.
- **Plan labels:** Exceptions specified by the generator plan.
- **Rule labels:** Labels associated with rule-defined scenarios.
- **Clean-data evaluation:** A negative-control run checks for findings on valid data.

Findings are matched using the issue type and primary record identifier.

A perfect score on synthetic data does **not** establish that the system will achieve perfect precision or recall on real-world data. Synthetic data and detection rules may share assumptions, and the evaluation should be interpreted accordingly.

## Measured Results

The following results were measured on Python 3.13.6 using seed `20261022` and cutoff date `2026-09-30`.

### Structural and reconciliation checks

| Check | Result |
|---|---:|
| Structural checks | 98 / 98 passed |
| Financial reconciliation identities | 6 / 6 passed |
| Reconciliation difference | 0 paise |
| Clean-data findings | 0 |
| Reproducibility | PASS |
| Automated tests | 208 passed |

### Dataset size

| Table | Starter | Full |
|---|---:|---:|
| `account` | 80 | 600 |
| `product` | 40 | 40 |
| `quote` | 1,000 | 10,000 |
| `quote_line` | 2,219 | 22,015 |
| `sales_order` | 700 | 7,000 |
| `order_line` | 1,536 | 15,483 |
| `shipment` | 954 | 9,663 |
| `shipment_line` | 1,902 | 19,476 |
| `invoice` | 800 | 8,000 |
| `invoice_line` | 1,651 | 16,644 |
| `invoice_shipment` | 928 | 9,278 |
| `payment` | 1,500 | 15,000 |
| `payment_allocation` | 1,545 | 15,549 |
| `dispute` | 46 | 400 |
| `ar_ledger_entry` | 2,426 | 24,332 |
| `status_event` | 15,185 | 152,107 |
| Ground-truth labels | 124 | 1,252 |

### Full dataset business picture

| Metric | Measured value |
|---|---:|
| Quoted | ₹82.83 Cr |
| Accepted | ₹60.24 Cr |
| Ordered | ₹58.63 Cr |
| Fulfilled | ₹55.54 Cr |
| Invoiced | ₹55.04 Cr |
| Cash received | ₹47.00 Cr |
| Unapplied cash | ₹1.44 Cr |
| Credits | ₹0.27 Cr |
| Accounts receivable | ₹9.06 Cr |
| Dispute hold | ₹0.38 Cr |
| Overdue collectible | ₹2.87 Cr |
| Underbilling | ₹0.11 Cr |
| Overbilling | ₹0.03 Cr |
| Duplicate billing | ₹0.28 Cr |
| Allocation discrepancy | ₹0.15 Cr |

### Full dataset process delays

| Process stage | Records | Mean | Median | P90 | Maximum | Over target |
|---|---:|---:|---:|---:|---:|---:|
| Order → full shipment | 6,403 | 6.54 days | 5 days | 11 days | 57 days | 173 |
| Shipment → invoice | 9,175 | 3.11 days | 3 days | 6 days | 25 days | 171 |
| Invoice → final payment | 6,419 | 38.35 days | 35 days | 60 days | 140 days | — |

### Full dataset evaluation

| Label group | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| Injected | 390 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Plan | 365 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Rule | 497 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Overall | 1,252 | 0 | 0 | 1.00 | 1.00 | 1.00 |

The measured overall synthetic evaluation contained 1,252 true positives, zero false positives, and zero false negatives.

### Exception counts

| Exception type | Count |
|---|---:|
| `CLOSED_ORDER_UNPAID` | 40 |
| `DISPUTE_NOT_IN_AR` | 40 |
| `DUPLICATE_ALLOCATION` | 50 |
| `DUPLICATE_INVOICE` | 50 |
| `FULFILMENT_DELAY` | 317 |
| `ILLEGAL_TRANSITION` | 60 |
| `INVOICING_DELAY` | 180 |
| `LONG_OVERDUE` | 204 |
| `OVERBILLING` | 60 |
| `SHORT_PAYMENT` | 161 |
| `UNDERBILLING` | 90 |

These results are reproducible for the documented environment and seed. They are not a benchmark against real production data.

## Assumptions and Decisions

Important assumptions and design decisions are documented in [`docs/decisions.md`](docs/decisions.md).

Current assumptions include:

- One currency is used.
- Tax is excluded from the financial calculations.
- Fulfilment, invoicing, and overdue thresholds are configured in `src/config.py`.
- The current targets include 21 days for fulfilment, 7 days for invoicing, and 90 days for overdue status.
- An accounts-receivable ledger was added to make dispute reflection explicit.
- SQLite is used as a local, serverless database.
- Detection rules are deterministic and explainable.

These thresholds are project assumptions, not universal O2C standards.

## Limitations

The current implementation has known limitations:

- Dispute credits are represented on invoices, and overbilling is shown as gross exposure with credits as supporting evidence.
- Overbilling and unbilled amounts can interact; exposure categories should be interpreted carefully.
- Thresholds are configured as single values rather than customer- or product-specific targets.
- Payment reversals are handled only before allocation.
- The rules detect only the patterns explicitly implemented.
- Reproducibility checksums were measured on one Python version.
- The `reproduce` command verifies reproducibility in the local environment.
- The measured evaluation uses synthetic data and does not establish production accuracy.
- The implementation has not yet received independent human code review.

An earlier independent review of a version with perfect synthetic evaluation results identified 27 issues, including a shared flaw that hid late shipments. This is included as a reminder that evaluation scores alone are insufficient evidence of correctness.

## Testing and Verification

Run the test suite:

```bash
python -m pytest
```

The documented measured run completed **208 tests successfully**.

For the complete verification workflow, see [`HANDOFF.md`](HANDOFF.md) and [`docs/validation_report.md`](docs/validation_report.md).

Additional project documentation:

- [`docs/final_audit.md`](docs/final_audit.md) — final requirement audit and open items
- [`docs/decisions.md`](docs/decisions.md) — technical decisions, trade-offs, and bugs found
- [`docs/development_log.md`](docs/development_log.md) — chronological development record
- [`docs/prompt_history.md`](docs/prompt_history.md) — AI prompt record
- [`docs/ai_usage.md`](docs/ai_usage.md) — AI usage and contribution disclosure

## Development history and evidence

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

## AI-assisted development

This project was built with Claude Code from the prompt in [`docs/prompt_history.md`](docs/prompt_history.md). That master prompt was created with ChatGPT. AI wrote the code, tests and documentation, and ran the checks reported here. What the candidate reviewed, and how the prompts relate to the final submission, is stated in [`docs/ai_usage.md`](docs/ai_usage.md). That file is the authoritative record.

## Future Improvements

Potential next steps include:

- Verify the project on Python 3.11 and 3.12.
- Re-run the complete workflow on a second computer.
- Conduct an independent human review of the code and findings.
- Improve net dispute-credit treatment.
- Add customer- and product-specific thresholds.
- Support payment reversals after allocation.
- Evaluate the rules against real, anonymized O2C data.

---

## Submission Notes

This repository is intended to provide:

- Executable code
- Setup and run instructions
- Verification steps
- Technical reasoning and documented assumptions
- Testing and measured results
- Known limitations and future improvements
- AI-use disclosure and prompt documentation

Before submission, confirm that the linked documentation files are present in the repository and that the setup and verification commands work from a fresh clone.

