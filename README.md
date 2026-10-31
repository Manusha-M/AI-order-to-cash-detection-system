

# YottaFlex AI — Order-to-Cash Revenue Leakage & Process Delay Analysis

> **Candidate Project Submission**  
> A locally executable analytics system that follows a sale from quote to cash, identifies potential revenue leakage and process delays, and validates financial consistency.

The system generates a realistic synthetic business dataset, introduces known anomalies, detects them using explainable rules, and evaluates the results against separate ground-truth labels.

**Repository:** [AI-order-to-cash-detection-system](https://github.com/Manusha-M/AI-order-to-cash-detection-system)  
**Application:** Python CLI + Streamlit dashboard  
**Database:** SQLite  
**Testing:** pytest  
**Data:** Fully synthetic; no external or personal data used

> **Candidate submission:** This repository contains the executable project, setup instructions, source code, tests, supporting documentation, validation evidence, development context, and AI-use disclosure required to review the submission.

---

## Table of Contents

- [Candidate Submission and Compliance](#candidate-submission-and-compliance)
- [The Business Problem](#the-business-problem)
- [What the System Does](#what-the-system-does)
- [The Order-to-Cash Workflow](#the-order-to-cash-workflow)
- [Quick Start](#quick-start)
- [Commands](#commands)
- [Architecture and Technology](#architecture-and-technology)
- [Data Model](#data-model)
- [Data Generation](#data-generation)
- [Anomaly Scenarios](#anomaly-scenarios)
- [Detection and Evaluation](#detection-and-evaluation)
- [Financial Definitions](#financial-definitions)
- [Measured Results](#measured-results)
- [Assumptions and Trade-offs](#assumptions-and-trade-offs)
- [Known Limitations](#known-limitations)
- [Testing and Verification](#testing-and-verification)
- [Repository Structure](#repository-structure)
- [AI Usage and Prompt History](#ai-usage-and-prompt-history)
- [Development History and Evidence](#development-history-and-evidence)
- [Repository Safety](#repository-safety)
- [Reviewer Walkthrough](#reviewer-walkthrough)
- [Next Steps](#next-steps)

---

## Candidate Submission and Compliance

This project is submitted as part of the YottaFlex AI Candidate Project.

The submission guidelines emphasize four areas:

| Requirement | Evidence in this repository |
|---|---|
| **Make it run** | Installation instructions, `requirements.txt`, `run.py`, CLI commands, and dashboard instructions |
| **Show your work** | Public GitHub repository, source code, supporting documentation, and development history |
| **Use LLMs transparently** | `docs/ai_usage.md` and `docs/prompt_history.md` |
| **Make reasoning visible** | Architecture, business rules, assumptions, decisions, trade-offs, testing, and limitations |

The project is designed to be locally executable and independently reviewable. It does not require a hosted demo or paid external service for the documented workflow.

### Submission window

The YottaFlex AI project window is **72 hours from the project being sent**, as specified in the submission guidelines. Artifact timestamps are used to verify the window.

The repository is intended to remain available and editable during the submission period, with the latest version at the deadline representing the final submission.

### Individual work and ownership

This is an individual candidate submission. AI tools and public learning resources were used as disclosed in the AI-use documentation.

The candidate remains responsible for understanding the implementation, explaining the design decisions, and accurately presenting the validation results, assumptions, and limitations.

---

## The Business Problem

The Order-to-Cash process connects several business activities: quoting, ordering, fulfillment, invoicing, payment, and reconciliation.

Each transition creates an opportunity for errors or delays:

- Goods may ship without being fully invoiced.
- Customers may be billed more than the fulfilled quantity.
- An invoice may be duplicated.
- A payment may be allocated more than once.
- An order may be closed while an invoice remains unpaid.
- A required business state may be skipped.
- A dispute may not be reflected correctly in receivables.
- Payments and invoices may remain outstanding longer than expected.

Manual review can be time-consuming and difficult to reproduce. This project demonstrates a structured approach to generating business data, detecting exceptions, validating relationships, and reconciling financial outcomes.

## What the System Does

The system:

1. Generates deterministic synthetic O2C data.
2. Builds valid business records before introducing labelled anomalies.
3. Maintains event history rather than overwriting state changes.
4. Detects **11 types of exception** using deterministic, explainable rules.
5. Records evidence, severity, impact, and related source records for findings.
6. Validates structural and business-level consistency.
7. Reconciles financial identities to exactly zero paise.
8. Evaluates findings against separate ground-truth labels.
9. Runs a negative control on clean data.
10. Checks reproducibility across repeated execution.
11. Presents results through a five-tab Streamlit dashboard.

The project’s purpose is to demonstrate an explainable analytics workflow—not to claim that every possible real-world anomaly can be detected.

---

## The Order-to-Cash Workflow

```text
Account → Quote → Sales Order → Shipment → Invoice → Payment
                                               └────→ Dispute
```

A company quotes prices to customers. Accepted quotes become orders. Orders are fulfilled, sometimes in multiple shipments. Shipments are invoiced, and customers pay—sometimes late, in instalments, or with a dispute.

Every hand-off is a place where a process exception can occur without being immediately visible.

The event history records these primary actors:

- Customer
- Sales operations
- Support agent
- Analyst
- System administrator
- System

---

## Quick Start

### Prerequisites

- **Python 3.11 or newer**
- Git
- Windows PowerShell, Git Bash, or a compatible terminal
- A web browser for the local dashboard

The project was tested on **Python 3.13.6**.

### Windows PowerShell

Clone the repository:

```powershell
git clone https://github.com/Manusha-M/AI-order-to-cash-detection-system.git
cd AI-order-to-cash-detection-system
```

Create the virtual environment:

```powershell
py -3 -m venv .venv
```

Install dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Run the starter pipeline:

```powershell
.\.venv\Scripts\python.exe run.py all --scale starter
```

Launch the dashboard:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app\dashboard.py
```

Streamlit will print a local URL, usually:

```text
http://localhost:8501
```

Open the URL in your browser.

There is no need to activate the virtual environment when using its Python executable directly. This also avoids PowerShell script-execution prompts.

If `py` is not recognized, try `python` instead.

### Git Bash

```bash
git clone https://github.com/Manusha-M/AI-order-to-cash-detection-system.git
cd AI-order-to-cash-detection-system

python -m venv .venv
source .venv/Scripts/activate

python -m pip install -r requirements.txt
python run.py all --scale starter
python -m streamlit run app/dashboard.py
```

### macOS / Linux

```bash
git clone https://github.com/Manusha-M/AI-order-to-cash-detection-system.git
cd AI-order-to-cash-detection-system

python3 -m venv .venv
source .venv/bin/activate

python -m pip install -r requirements.txt
python run.py all --scale starter
python -m streamlit run app/dashboard.py
```

---

## Commands

Run commands from the repository root.

| Task | Command |
|---|---|
| Everything, starter dataset | `python run.py all --scale starter` |
| Everything, full dataset | `python run.py all --scale full` |
| Generate only | `python run.py generate --scale full` |
| Detect exceptions | `python run.py detect --scale full` |
| Validate data | `python run.py validate --scale full` |
| Reconcile balances | `python run.py reconcile --scale full` |
| Score against ground truth | `python run.py evaluate --scale full` |
| Clean-data control | `python run.py negative-control --scale full` |
| Two-run reproducibility | `python run.py reproduce --scale full` |
| Other seeds | `python scripts/seed_sweep.py --scale starter` |
| Automated tests | `python -m pytest -q` |
| Dashboard | `python -m streamlit run app/dashboard.py` |

The default seed is `20261022`. Pass `--seed` to use another seed.

The full pipeline takes approximately two minutes in the tested environment, with most of the time spent in the two-run reproducibility check.

### Execution order

The `all` command runs the stages in the correct order.

When running individual commands, run detection before reconciliation and evaluation because those stages read the generated findings. Validation also reads `ground_truth.csv` from the same run.

---

## Architecture and Technology

The project uses a **single Python process over one SQLite database**.

The core pipeline uses the Python standard library. Streamlit, Altair, pandas, and pytest support the dashboard and tests.

### Why SQLite?

The problem is relational and benefits from explicit relationships between accounts, orders, shipments, invoices, payments, and ledger entries. SQLite provides local storage without requiring a separate database server.

### Why deterministic rules instead of machine learning?

The project focuses on explainable exceptions. Each finding should be traceable to source records and business events.

A deterministic rule-based approach is appropriate for the configured scenarios because the project needs to explain **why** a record was flagged, not merely produce a prediction.

### Pipeline

```text
config → generator → anomaly injection → SQLite + exports
                             │                  │
                             ▼                  ▼
                      ground_truth.csv      detector → findings
                             │                  │
                             └──→ evaluation ←──┘
```

`ground_truth.csv` does **not** flow into the detector. It is used separately for evaluation.

The full architecture and entity relationships are documented in [`docs/architecture.md`](docs/architecture.md).

---

## Data Model

The eleven required business entities are:

- `account`
- `quote`
- `quote_line`
- `sales_order`
- `order_line`
- `shipment`
- `invoice`
- `invoice_line`
- `payment`
- `dispute`
- `status_event`

Five supporting tables make the relationships and financial records consistent:

| Table | Purpose |
|---|---|
| `shipment_line` | One shipment can carry many lines; one line can ship in parts |
| `invoice_shipment` | One invoice can bill several shipments |
| `payment_allocation` | One payment can settle several invoices, and vice versa |
| `ar_ledger_entry` | Append-only receivables record and source of balances |
| `product` | Product catalogue for quote lines |

Money is stored in **integer paise**, so financial arithmetic is exact rather than dependent on floating-point rounding.

Every field is documented in [`docs/data_dictionary.md`](docs/data_dictionary.md).

---

## Data Generation

Generation follows the business order:

```text
Products and Accounts
        ↓
Quotes
        ↓
Orders
        ↓
Shipments
        ↓
Invoices
        ↓
Disputes
        ↓
Payments
```

### Deterministic generation

The same seed produces the same generated data under the same tested environment.

Starter and full scales use the same generation code.

### Business distributions

The generator models varied business activity:

- Account activity follows a long-tail distribution.
- Quote acceptance varies by segment and channel.
- Quote volume rises around quarter-end.
- Payment behavior differs by account.
- The dataset includes in-flight orders, partially paid invoices, and open disputes.

### Data cutoff

The configured cutoff is **2026-09-30**. Transactions scheduled after that date have not yet occurred in the generated business scenario.

### Data provenance

The dataset is fully synthetic. No external or personal data was used; names are invented.

Exports are written under:

```text
data/<scale>/
```

The generated artifacts include:

- `csv/`
- `json/`
- `seed.sql`
- `ground_truth.csv`
- `manifest.json`

The manifest records the generator command, seed, row counts, and checksums.

---

## Anomaly Scenarios

The project plants the five required negative scenarios, using multiple forms where useful.

| Scenario | Example |
|---|---|
| Invoice exceeds fulfilled quantity | 10 units shipped, 12 billed |
| Payment allocated twice | The same payment is applied again to the same or another invoice |
| Order closed with unpaid invoice | Status is `CLOSED` while a balance remains open |
| Status event skips a required state | `CONFIRMED` transitions directly to `INVOICED`, skipping `FULFILLED` |
| Dispute not reflected in receivables | An open dispute has no ledger hold or an insufficient hold |

Additional scenarios include:

- Partial shipments
- Underbilling
- Duplicate invoices
- Short payments
- Long-overdue balances
- Process delays

The dataset also includes look-alike cases that should **not** be flagged, including:

- Two equal shipments billed on identical-looking invoices
- Voided and reissued invoices
- An invoice exactly 90 days past due

Anomalies change business facts without breaking database integrity. Keys remain valid, and line totals still equal quantity multiplied by price.

---

## Detection and Evaluation

Eleven deterministic rules read transactional tables and event history.

Each finding records:

- Rule and issue type
- Primary source record
- Related records
- Severity
- Expected behavior
- Observed behavior
- Financial or process impact
- Supporting evidence

The rule definitions are documented in [`docs/business_rules.md`](docs/business_rules.md).

### Evaluation methodology

Evaluation matches findings by issue type and primary record ID, so one anomaly can only count once.

The evaluation reports:

- True positives
- False positives
- False negatives
- Precision
- Recall
- F1 score
- Results by issue type
- Results by label source
- Monetary amount associated with each match

### Ground-truth label sources

Labels are not all equally independent:

| Label source | Meaning |
|---|---|
| `injected` | A record was deliberately changed; this is the independent test within the synthetic scenario |
| `plan` | The generator planned an outcome and then labelled it |
| `rule` | The label re-applies the documented rule; a perfect score is close to guaranteed |

### Interpreting a perfect score

The same project generates the data, labels, and rules. A score of 1.0 demonstrates that the configured rules behave as documented on the configured dataset.

It **does not predict performance on real or unseen data**.

An independent review also found 27 issues in an earlier version that already scored 1.0, including a bug that hid late shipments because the labels shared the same flaw. The review and resulting decisions are documented in [`docs/decisions.md`](docs/decisions.md).

---

## Financial Definitions

The complete formulas, sources, and limitations are documented in [`docs/business_rules.md`](docs/business_rules.md).

| Measure | Interpretation |
|---|---|
| Underbilled revenue | Potential income lost because goods were delivered but not billed |
| Overbilled and duplicate exposure | Customer billed too much; potential refund or credit risk, not income |
| Overdue and short-paid balances | Collection risk; the money may still arrive |
| Allocation discrepancy | Receivables appear lower than they really are |

These measures are shown separately and are **not added together**.

When a single classification is required, each rupee of receivables receives exactly one class.

---

## Measured Results

The following results are reported from executed project runs. Detailed evidence is available in:

- [`docs/validation_report.md`](docs/validation_report.md)
- [`docs/reproducibility.md`](docs/reproducibility.md)

### Execution environment

- Python: 3.13.6
- Seed: `20261022`
- Cutoff: `2026-09-30`

### Row counts

| Table | Starter | Full |
|---|---:|---:|
| account | 80 | 600 |
| product | 40 | 40 |
| quote | 1,000 | 10,000 |
| quote_line | 2,219 | 22,015 |
| sales_order | 700 | 7,000 |
| order_line | 1,536 | 15,483 |
| shipment | 954 | 9,663 |
| shipment_line | 1,902 | 19,476 |
| invoice | 800 | 8,000 |
| invoice_line | 1,651 | 16,644 |
| invoice_shipment | 928 | 9,278 |
| payment | 1,500 | 15,000 |
| payment_allocation | 1,545 | 15,549 |
| dispute | 46 | 400 |
| ar_ledger_entry | 2,426 | 24,332 |
| status_event | 15,185 | 152,107 |
| ground truth labels | 124 | 1,252 |

### Validation summary

| Check | Observed result |
|---|---:|
| Structural checks | 98 / 98 passed |
| Reconciliation identities | 6 / 6 closed to 0 paise |
| Clean-data findings | 0 |
| Reproducibility | PASS |
| Automated tests | 208 passed |

### Business picture — full dataset

| Measure | Value |
|---|---:|
| Quoted value | Rs 82.83 Cr |
| Accepted value | Rs 60.24 Cr |
| Ordered value | Rs 58.63 Cr |
| Fulfilled value | Rs 55.54 Cr |
| Invoiced value | Rs 55.04 Cr |
| Cash received | Rs 47.00 Cr |
| Unapplied cash | Rs 1.44 Cr |
| Credits issued | Rs 0.27 Cr |
| Outstanding receivables | Rs 9.06 Cr |
| On dispute hold | Rs 0.38 Cr |
| Overdue, collectible | Rs 2.87 Cr |
| Underbilled revenue | Rs 0.11 Cr |
| Overbilled exposure | Rs 0.03 Cr |
| Duplicate-billing exposure | Rs 0.28 Cr |
| Payment allocation discrepancy | Rs 0.15 Cr |

### Process delays — full dataset

| Stage | Records | Mean days | Median | P90 | Max | Over target |
|---|---:|---:|---:|---:|---:|---:|
| Order to full shipment | 6,403 | 6.54 | 5 | 11 | 57 | 173 |
| Shipment to invoice | 9,175 | 3.11 | 3 | 6 | 25 | 171 |
| Invoice to final payment | 6,419 | 38.35 | 35 | 60 | 140 | n/a |

### Detector evaluation — full dataset

| Label source | Labels | TP | FP | FN | Precision | Recall |
|---|---:|---:|---:|---:|---:|---:|
| injected | 390 | 390 | 0 | 0 | 1.0 | 1.0 |
| plan | 365 | 365 | 0 | 0 | 1.0 | 1.0 |
| rule | 497 | 497 | 0 | 0 | 1.0 | 1.0 |
| **Overall** | **1,252** | **1,252** | **0** | **0** | **1.0** | **1.0** |

| Issue type | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| CLOSED_ORDER_UNPAID | 40 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| DISPUTE_NOT_IN_AR | 40 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| DUPLICATE_ALLOCATION | 50 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| DUPLICATE_INVOICE | 50 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| FULFILMENT_DELAY | 317 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| ILLEGAL_TRANSITION | 60 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| INVOICING_DELAY | 180 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| LONG_OVERDUE | 204 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| OVERBILLING | 60 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| SHORT_PAYMENT | 161 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| UNDERBILLING | 90 | 0 | 0 | 1.0 | 1.0 | 1.0 |

These are results from the configured synthetic evaluation. They should not be interpreted as guaranteed performance on production or unseen data.

---

## Assumptions and Trade-offs

| Decision or assumption | Rationale and impact |
|---|---|
| One currency; tax excluded | Keeps the financial model focused. Tax can add lines without changing the core logic |
| 21-day fulfillment target | Configured assumption, not a source requirement |
| 7-day invoicing target | Configured assumption, not a source requirement |
| 90-day overdue threshold | Configured assumption, not a source requirement |
| Receivables ledger | Added to define what “reflected in receivables” means |
| SQLite | Suits local batch analysis, but is single-writer and loosely typed |
| Deterministic rules | Makes findings traceable, but detects only the patterns implemented |
| Synthetic data | Enables controlled testing, but cannot establish real-world performance |

The thresholds are configured in `src/config.py`.

All major decisions and their rationale are documented in [`docs/decisions.md`](docs/decisions.md).

---

## Known Limitations

- Dispute credits sit on invoices, so overbilling is reported gross, with credits shown in the evidence.
- Overbilling a line that also has shipped but unbilled goods may remain below the rule until billing catches up. Reconciliation shows the difference.
- Thresholds are single values; real targets may vary by product and customer.
- Reversed payments are modelled only before allocation.
- Rules find the patterns they were written for. Unknown patterns may be missed.
- Checksums were measured on one Python version. Another version may generate different but equally valid data.
- `run.py reproduce` verifies determinism in the environment where it is executed.
- The synthetic evaluation does not establish performance on real-world data.

---

## Testing and Verification

Run the automated tests:

```bash
python -m pytest -q
```

Run the full pipeline:

```bash
python run.py all --scale full
```

Run the clean-data control:

```bash
python run.py negative-control --scale full
```

Run the reproducibility check:

```bash
python run.py reproduce --scale full
```

The project’s verification covers structural consistency, business tie-outs, financial reconciliation, detector evaluation, negative-control behavior, and reproducibility.

A passing test suite demonstrates that the covered cases behave as expected. It does not establish that every possible real-world scenario has been tested.

---

## Repository Structure

```text
run.py                  Command-line entry point
src/                    Generator, detector, reconciliation, evaluation, validation
sql/                    Schema and analytical views
app/dashboard.py        Streamlit dashboard
tests/                  Automated tests
scripts/                Seed sweep, report writer, archive builder
data/starter/            Starter dataset
outputs/                 Measured results
docs/                   Rules, decisions, reports, data dictionary, AI disclosure
HANDOFF.md               Setup and verification guide
README.md                Project overview and reviewer instructions
```

The full dataset is regenerated locally and is excluded from version control because of its size.

---

## AI Usage and Prompt History

AI tools were used during development, as permitted by the YottaFlex AI project guidelines.

The following documents provide the project’s AI-use and development context:

- [`docs/ai_usage.md`](docs/ai_usage.md) — AI tool disclosure and contribution summary
- [`docs/prompt_history.md`](docs/prompt_history.md) — prompt history
- [`docs/development_log.md`](docs/development_log.md) — development timeline
- [`docs/decisions.md`](docs/decisions.md) — design decisions, trade-offs, and issues discovered

The prompt-history document is intended to record the prompts submitted to the AI tools used. AI responses are optional under the project FAQ. If any tool could not export its prompt history, that limitation should be disclosed.

AI assistance does not replace the candidate’s responsibility for understanding and explaining the core logic, dependencies, design choices, tests, observed results, and limitations.

---

## Development History and Evidence

The project was developed locally before being published to GitHub.

The development log is a separate record from Git history. The following documents provide context for how the solution evolved:

| Document | What it records |
|---|---|
| `docs/development_log.md` | Chronological milestones, debugging, testing, and verification |
| `docs/prompt_history.md` | AI prompts and timestamps |
| `docs/ai_usage.md` | AI usage and contribution disclosure |
| `docs/decisions.md` | Technical decisions, trade-offs, and issues discovered |
| `docs/validation_report.md` | Measured testing and validation results |
| `docs/final_audit.md` | Requirement audit and open items |
| `docs/reproducibility.md` | Reproducibility evidence |
| `docs/architecture.md` | Architecture and data flow |
| `docs/data_dictionary.md` | Data fields and definitions |
| `docs/business_rules.md` | Detection rules and financial definitions |

The repository history and development evidence should be read together when reviewing the project.

---

## Repository Safety

The project uses synthetic data generated for the demonstration. No external or personal data was used in the dataset.

The public repository should not contain:

- Secrets or credentials
- Personal or sensitive information
- Proprietary code the candidate is not authorized to publish
- Local environment files

The `.gitignore` excludes the virtual environment, selected generated data, local tool state, and common secret-file formats.

Before submission, the repository contents should be reviewed to confirm that no sensitive or unauthorized material has been committed.

---

## Reviewer Walkthrough

A reviewer can verify the project in the following order:

1. **Inspect the repository**  
   Review the source code, tests, documentation, and supporting artifacts.

2. **Set up the environment**  
   Follow the Quick Start instructions and install dependencies.

3. **Run the starter pipeline**

   ```bash
   python run.py all --scale starter
   ```

4. **Inspect the validation results**  
   Review structural checks, business tie-outs, reconciliation, and reproducibility output.

5. **Run the automated tests**

   ```bash
   python -m pytest -q
   ```

6. **Launch the dashboard**

   ```bash
   python -m streamlit run app/dashboard.py
   ```

7. **Review the reasoning and disclosure**  
   Read the architecture, business rules, decisions, assumptions, limitations, development log, and AI prompt history.

8. **Walk through the implementation**  
   The candidate should be prepared to explain the core logic, dependencies, design decisions, validation approach, and known limitations.

---

## Next Steps

Potential improvements include:

- Test on Python 3.11 and 3.12 and on a second computer.
- Obtain human review of the rules and final code.
- Match dispute credits to order lines so overbilling can be reported net of credits.
- Configure targets by product and customer instead of using a single value.
- Model a payment reversed after allocation.
- Test the rules on real, anonymised data.
- Expand edge-case testing and validation coverage.

Real, appropriately anonymised business data and domain-expert review would be necessary to evaluate whether the rules perform effectively in an operational environment.

---

## Final Note

This project demonstrates an executable and reviewable Order-to-Cash analytics workflow with synthetic data, explainable detection rules, financial reconciliation, automated tests, and documented validation.

The results should be interpreted within the boundaries of the configured dataset, rules, tests, and assumptions. The project is presented as a candidate-project demonstration—not as a production-ready financial control system.

