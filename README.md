# Order-to-Cash Revenue Leakage and Process Delay Analysis

A local analytics system that follows a sale from quote to cash, then finds where money leaks, where the process stalls, and why.

It generates a realistic synthetic business dataset, plants known problems in it, detects them with explainable rules that never see the answers, and proves the books balance to the paisa.

> **AI disclosure:** this project was generated with Claude Code. See [`docs/ai_usage.md`](docs/ai_usage.md) and [`docs/prompt_history.md`](docs/prompt_history.md). Setup on a new laptop and the checks to run are in [`HANDOFF.md`](HANDOFF.md). How the project was built before it reached GitHub is under [Development history and evidence](#development-history-and-evidence).

## The business workflow

```text
Account → Quote → Sales Order → Shipment → Invoice → Payment
                                              └────→ Dispute
```

A company quotes prices to customers. Accepted quotes become orders, orders ship (sometimes in parts), shipments get invoiced, and customers pay (sometimes late, sometimes in instalments, sometimes disputing the bill). Each hand-off is a place for something to go wrong without anyone noticing. Goods ship but are never billed. An invoice goes out twice. A payment is applied to two invoices. An order is closed while money is still owed.

Primary actors recorded in the event history: customer, sales operations, support agent, analyst, system administrator, and the system itself.

## What it does

- **Generates data deterministically.** The same seed gives the same data, byte for byte. Starter and full sizes use the same code.
- **Builds a valid world first, then plants labelled anomalies.** Totals are summed from lines and balances come from a ledger; nothing derived is random.
- **Keeps full history.** Every state change is a row in `status_event`. Nothing is overwritten.
- **Detects 11 types of exception** with deterministic rules, each with evidence, severity and impact.
- **Reconciles the books.** Six identities must equal exactly zero paise, comparing the ledger against the source tables.
- **Scores itself** against a separate ground-truth file, split by how much each label really proves, and on a clean dataset where the right answer is nothing.
- **Shows the results** in a five-tab Streamlit dashboard.

## Quick start (Windows PowerShell)

You need Python 3.11 or newer. Tested on Python 3.13.6.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py all --scale starter
.\.venv\Scripts\python.exe -m streamlit run app\dashboard.py
```

If `py` is not recognised, use `python` instead. If Windows offers the Microsoft Store, Python is not really installed: install it from python.org.

There is no need to activate the environment, which also avoids PowerShell's script-execution prompt.

## Commands

| Task | Command |
|---|---|
| Everything, starter dataset | `.\.venv\Scripts\python.exe run.py all --scale starter` |
| Everything, full dataset | `.\.venv\Scripts\python.exe run.py all --scale full` |
| Generate only | `.\.venv\Scripts\python.exe run.py generate --scale full` |
| Detect exceptions | `.\.venv\Scripts\python.exe run.py detect --scale full` |
| Validate data | `.\.venv\Scripts\python.exe run.py validate --scale full` |
| Reconcile balances | `.\.venv\Scripts\python.exe run.py reconcile --scale full` |
| Score against ground truth | `.\.venv\Scripts\python.exe run.py evaluate --scale full` |
| Clean-data control | `.\.venv\Scripts\python.exe run.py negative-control --scale full` |
| Two-run reproducibility | `.\.venv\Scripts\python.exe run.py reproduce --scale full` |
| Other seeds | `.\.venv\Scripts\python.exe scripts\seed_sweep.py --scale starter` |
| Automated tests | `.\.venv\Scripts\python.exe -m pytest -q` |
| Dashboard | `.\.venv\Scripts\python.exe -m streamlit run app\dashboard.py` |

The default seed is `20261022`. Pass `--seed` to use another. The full pipeline takes about two minutes, most of it the two-run reproducibility check.

Run `detect` before `reconcile` and `evaluate`, because they read the findings. `all` does this for you. `validate` also reads `ground_truth.csv` from the same run.

## Architecture and technology

A single Python process over one SQLite file. The pipeline uses only the standard library. Streamlit, Altair, pandas and pytest are for the dashboard and tests.

SQLite suits this work because the problem is relational and it needs no server. A set of explainable rules suits it better than machine learning, because each exception must be traced to its source events, and nothing here requires a model.

```text
config → generator → anomaly injection → SQLite + exports
                            │                  │
                            ▼                  ▼
                     ground_truth.csv      detector → findings
                            │                  │
                            └──→ evaluation ←──┘
```

`ground_truth.csv` never flows into the detector. The diagrams in [`docs/architecture.md`](docs/architecture.md) show the full flow and entity relationships.

## Data model

The eleven required entities are `account`, `quote`, `quote_line`, `sales_order`, `order_line`, `shipment`, `invoice`, `invoice_line`, `payment`, `dispute` and `status_event`.

Five support tables make them correct:

| Table | Why it exists |
|---|---|
| `shipment_line` | One shipment carries many lines; one line can ship in parts |
| `invoice_shipment` | One invoice can bill several shipments |
| `payment_allocation` | One payment can settle several invoices, and the reverse |
| `ar_ledger_entry` | Append-only receivables record, the source of every balance |
| `product` | Catalogue for quote lines |

Money is INR in integer paise, so arithmetic is exact. Every field is documented in [`docs/data_dictionary.md`](docs/data_dictionary.md).

## How the data is generated

Generation follows the business order: products and accounts, quotes, orders, shipments, invoices, disputes, payments.

- **Volumes are exact.** The full scale has 10,000 quotes, 7,000 orders, 8,000 invoices and 15,000 payment rows, plus over 140,000 status events. "15,000 payments/events" is read as 15,000 payments, the stricter meaning.
- **Distributions vary.** Account activity follows a long tail, acceptance varies by segment and channel, quote volume rises at quarter-end, and payment behaviour differs by account.
- **The cutoff is real.** Anything scheduled after 2026-09-30 has not happened, so the data contains in-flight orders, part-paid invoices and open disputes.
- **Provenance:** fully synthetic. No external or personal data was used. Names are invented.

Exports are in `data/<scale>/`: `csv/`, `json/`, `seed.sql`, `ground_truth.csv` and `manifest.json` (generator command, seed, row counts, checksums).

## Anomalies

All five required negative scenarios are planted, each in more than one form where that adds value:

| Scenario | Example |
|---|---|
| Invoice exceeds fulfilled quantity | 10 units shipped, 12 billed |
| Payment allocated twice | Same payment applied again, to the same or another invoice |
| Order closed with unpaid invoice | Status CLOSED while a balance is open |
| Status event skips a required state | CONFIRMED straight to INVOICED, skipping FULFILLED |
| Dispute not reflected in receivables | Open dispute with no ledger hold, or too small a hold |

Partial shipments, underbilling, duplicate invoices, short payments, long-overdue balances and process delays are covered too.

The data also contains **look-alikes that must not be flagged**, including two equal shipments billed on identical-looking invoices, voided and reissued invoices, and an invoice exactly 90 days past due.

Anomalies change business facts without breaking the database: keys stay valid, and line totals still equal quantity times price.

## Detection and evaluation

Eleven rules read the transactional tables and event history. Each finding records the rule, source record, related records, severity, expected behaviour, observed behaviour, impact and evidence. The logic is in [`docs/business_rules.md`](docs/business_rules.md).

Evaluation matches on issue type and primary record ID, so one anomaly can only count once. It reports true positives, false positives, false negatives, precision, recall and F1, overall, by type and by label source, and also checks the money amount of each match.

Labels are not all equal. `injected` labels mark a record that was deliberately changed, and are the independent test. `plan` labels mark outcomes the generator planned. `rule` labels re-apply the documented rule, so a perfect score there is close to guaranteed.

**How to read a perfect score:** the same project wrote the data, the labels and the rules, so a score of 1.0 shows the rules do what the documents say. It does not predict performance on real data. This is not hypothetical: an independent review found 27 issues in a version that already scored 1.0, including a bug that hid late shipments because the labels shared the flaw. See [`docs/decisions.md`](docs/decisions.md).

## Financial definitions

Full formulas, sources and limits are in [`docs/business_rules.md`](docs/business_rules.md). The key distinction:

| Measure | What it really means |
|---|---|
| Underbilled revenue | Income lost: goods delivered but not billed |
| Overbilled and duplicate exposure | Customer billed too much: refund or credit risk, not income |
| Overdue and short-paid balances | Collection risk: the money may still arrive |
| Allocation discrepancy | Receivables look lower than they really are |

These are shown separately and never added together. When a single split is needed, each rupee of receivables gets exactly one class.

## Measured results

Generated by `scripts/write_reports.py` from executed runs. Details are in [`docs/validation_report.md`](docs/validation_report.md) and [`docs/reproducibility.md`](docs/reproducibility.md).

<!-- MEASURED:START -->

Measured on Python 3.13.6, seed 20261022, cutoff 2026-09-30.

**Row counts**

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

**Checks:** 98 of 98 structural checks passed; 6 of 6 reconciliation identities closed to 0 paise; 0 findings on clean data; reproducibility PASS; tests: 208 passed in 67.89s.

**Business picture (full dataset)**

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
| Underbilled revenue (leakage) | Rs 0.11 Cr |
| Overbilled exposure | Rs 0.03 Cr |
| Duplicate-billing exposure | Rs 0.28 Cr |
| Payment allocation discrepancy | Rs 0.15 Cr |

**Process delays (full dataset)**

| Stage | Records | Mean days | Median | P90 | Max | Over target |
|---|---:|---:|---:|---:|---:|---:|
| Order to full shipment | 6,403 | 6.54 | 5 | 11 | 57 | 173 |
| Shipment to invoice | 9,175 | 3.11 | 3 | 6 | 25 | 171 |
| Invoice to final payment | 6,419 | 38.35 | 35 | 60 | 140 | n/a |

**Detector evaluation (full dataset)**

| Label source | Labels | TP | FP | FN | Precision | Recall | What it means |
|---|---:|---:|---:|---:|---:|---:|---|
| injected | 390 | 390 | 0 | 0 | 1.0 | 1.0 | A valid record was deliberately changed. The independent test |
| plan | 365 | 365 | 0 | 0 | 1.0 | 1.0 | The generator planned the outcome, then labelled it |
| rule | 497 | 497 | 0 | 0 | 1.0 | 1.0 | The label re-applies the rule. Close to guaranteed; proves little |

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
| **Overall** | **1,252** | **0** | **0** | **1.0** | **1.0** | **1.0** |

<!-- MEASURED:END -->

## Assumptions and trade-offs

- One currency, tax excluded. Tax would add lines without changing the logic.
- The targets (21-day fulfilment, 7-day invoicing, 90-day overdue) are assumptions, not source requirements. They are all in `src/config.py`.
- A receivables ledger was added because "reflected in receivables" needs a concrete definition.
- SQLite is single-writer and loosely typed, which suits a batch analysis but not a live system.

All decisions are explained in [`docs/decisions.md`](docs/decisions.md).

## Known limitations

- Dispute credits sit on invoices, so overbilling is reported gross, with credits shown in its evidence.
- Over-billing a line that also has shipped but unbilled goods stays below the rule until billing catches up. Reconciliation shows it as a difference.
- Thresholds are single numbers; real targets vary by product and customer.
- Reversed payments are modelled only before allocation.
- Rules find the patterns they were written for. Unknown patterns will be missed.
- Checksums were measured on one Python version. Another version may give different but equally valid data. `run.py reproduce` proves determinism on the version you run.

## Next steps

- Test on Python 3.11 and 3.12, and on a second computer.
- Have a person review the rules and the final code. The review so far was by an AI.
- Match dispute credits to order lines, so overbilling can be reported net of credits.
- Set targets by product and customer instead of one number for each.
- Model a payment reversed after it has been allocated.
- Try the rules on real, anonymised data. That is the only way to learn how they really perform.

## Repository layout

```text
run.py              Command-line entry point
src/                Generator, detector, reconciliation, evaluation, validation
sql/                Schema and analytical views
app/dashboard.py    Streamlit dashboard
tests/              Automated tests
scripts/            Seed sweep, report writer, archive builder
data/starter/       Sample dataset (full dataset regenerates locally)
outputs/            Measured results
docs/               Dictionary, rules, decisions, reports, AI disclosure
HANDOFF.md          Setup and verification guide
```

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
