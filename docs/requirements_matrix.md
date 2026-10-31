# Requirement Traceability Matrix

Sources: **PS** = `Problem statement.txt`, **SG** = Submission Guidelines PDF, **FAQ** = Candidate Project FAQ PDF,
**ENG** = engineering choices added on top of the sources (not YottaFlex requirements).

| ID | Source | Requirement | Priority | Implementation | Verification | Status |
|---|---|---|---|---|---|---|
| PS-01 | PS Business Workflow 1 | Master data first: Account, Quote, QuoteLine, SalesOrder, OrderLine | Mandatory | `src/generator.py` | `tests/test_integrity.py`, validation S02 | Pass |
| PS-02 | PS Business Workflow 2 | Dependent records use valid parent IDs | Mandatory | `src/generator.py`, `sql/schema.sql` | FK pragma check, validation S02/S06 | Pass |
| PS-03 | PS Business Workflow 3 | Quotes → orders → shipments → invoices → payments/disputes → aging, exceptions | Mandatory | `src/generator.py`, `src/detector.py` | `tests/test_lifecycle.py`, `tests/test_financials.py` | Pass |
| PS-04 | PS Business Workflow 4 | State changes persisted as events; history not overwritten | Mandatory | `status_event` table, `Dataset.transition` | Validation S10, `tests/test_lifecycle.py` | Pass |
| PS-05 | PS Business Workflow 5 | Outcomes and labels from documented rules, not random assignment | Mandatory | `src/anomaly_injection.py`, `src/generator.py` | `docs/business_rules.md`, evaluation | Pass |
| PS-06 | PS Entities | All 11 core entities with PKs and FKs | Mandatory | `sql/schema.sql` | `tests/test_integrity.py` | Pass |
| PS-07 | PS Entities | Document cardinality, optionality, effective dates, lifecycle states | Mandatory | `docs/data_dictionary.md`, `docs/architecture.md` | Doc coverage test | Pass |
| PS-08 | PS Entities | Bridge tables for N:M; event history; joins validated | Mandatory | `shipment_line`, `invoice_shipment`, `payment_allocation` | Validation S06 | Pass |
| PS-09 | PS Entities | Anomalies labelled, not silently corrupting unrelated rows | Mandatory | `ground_truth.csv`, disjoint target selection | Negative-control run | Pass |
| PS-10 | PS IDs | QTE/SO/SHP/INV/PAY/DSP-2026-000001 format; zero-padded, immutable, consistent | Mandatory | `Dataset.new_id`, schema GLOB checks | Validation S05 | Pass |
| PS-11 | PS Step 1 | Data dictionary: type, required, allowed values, units, uniqueness, validation | Mandatory | `docs/data_dictionary.md` | `tests/test_docs.py` (every column documented) | Pass |
| PS-12 | PS Step 4 | Baseline: 10,000 quotes, 7,000 orders, 8,000 invoices, 15,000 payments/events | Mandatory | `src/config.py` scale profiles | Validation S11 | Pass |
| PS-13 | PS Step 4 | Partial shipment, underbilling, duplicate invoice, short payment, long overdue | Mandatory | `src/generator.py`, `src/anomaly_injection.py` | Evaluation by type | Pass |
| PS-14 | PS Step 4 | Fixed seed; parameterized scale; same generator for starter and full | Mandatory | `run.py --scale`, `src/config.py` | Run both scales | Pass |
| PS-15 | PS Step 5 | Valid baseline first, then 5 labelled edge cases | Mandatory | `src/anomaly_injection.py` | Evaluation by type; negative control | Pass |
| PS-16 | PS Step 6 | Derived values computed from source records | Mandatory | Generator, `sql/analytics.sql` views | Validation S08/S09 | Pass |
| PS-17 | PS Step 7 | Separate ground truth; never an input feature | Mandatory | `data/<scale>/ground_truth.csv` | Test: detector source and DB contain no labels | Pass |
| PS-18 | PS Step 8 | PK, FK, enums, dates, arithmetic, lifecycle, duplicate checks | Mandatory | `src/validation.py` | `outputs/<scale>/validation.json` | Pass |
| PS-19 | PS Step 9 | Export CSV/JSON/SQL plus README, dictionary, generator command, seed, manifest, validation summary | Mandatory | `src/database.py`, docs | File presence audit | Pass |
| PS-20 | PS Step 10 | Regenerate twice, compare row counts and checksums | Mandatory | `src/reproducibility.py` | `outputs/<scale>/reproducibility.json` | Pass |
| PS-21 | PS Acceptance | Order-to-cash state consistent | Mandatory | Validation, detector | Validation + tests | Pass |
| PS-22 | PS Acceptance | Balances reconcile | Mandatory | `src/reconciliation.py` | Reconciliation identities = 0 | Pass |
| PS-23 | PS Acceptance | Exceptions traceable to source events | Mandatory | `finding` evidence fields | `tests/test_detection.py` | Pass |
| PS-24 | PS Acceptance | Aging uses defined cutoff dates | Mandatory | `run_metadata.cutoff_date`, `v_invoice_balance` | Boundary tests | Pass |
| PS-25 | PS Objective | Expose decisions and exceptions; measurable outputs; evaluation metrics | Mandatory | `src/evaluation.py`, dashboard | `outputs/<scale>/evaluation.json` | Pass |
| PS-26 | PS Evaluation Focus | Realistic distributions; normal, boundary, failure coverage | Mandatory | Generator decoys and boundary cases | Distribution report; boundary tests | Pass |
| PS-27 | PS Public Data | External data optional; synthetic data needs lawful provenance | Mandatory | Manifest states no external data | `data/<scale>/manifest.json` | Pass |
| SG-01 | SG 01 | Working code, clear install/run/verify steps for another person | Mandatory | `README.md`, `HANDOFF.md`, `run.py` | Clean-environment test | Pass |
| SG-02 | SG 02 | Public GitHub repo with meaningful commits | Mandatory (candidate only) | `HANDOFF.md` section D | Candidate action; not done here by design | Not done here by design: candidate action |
| SG-03 | SG 03 | Prompt history; AI acceleration, reliance, personal review disclosed | Mandatory | `docs/prompt_history.md`, `docs/ai_usage.md` | Manual review | Pass: complete from the session record; candidate to confirm |
| SG-04 | SG 04 | Assumptions, decisions, trade-offs, testing, limitations explained | Mandatory | `docs/decisions.md`, `README.md` | Manual review | Pass |
| FAQ-06 | FAQ 6 | All prompts to every AI tool; disclose export limits | Mandatory | `docs/prompt_history.md` | Manual review | Partial: ChatGPT prompts not provided; limitation stated |
| FAQ-07 | FAQ 7 | Individual work; no implementation help from other people | Mandatory | `docs/ai_usage.md`, `HANDOFF.md` section 0 | Prompt 5 and the session record | Partial: the record shows no other person; nothing outside it can be verified here |
| FAQ-08 | FAQ 8 | Free/local services; avoid large dependencies | Mandatory | `requirements.txt` | Clean install | Pass |
| FAQ-10 | FAQ 10 | No complete imported solution; attribution where required | Mandatory | Only standard dependencies | `requirements.txt` review | Pass |
| FAQ-12 | FAQ 12 | No secrets, credentials or personal data in the repository | Mandatory | `.gitignore`, synthetic data only | Archive content scan | Pass |
| ENG-01 | Master prompt 11 | Findings carry rule, evidence, severity, impact | Engineering | `src/detector.py` | `tests/test_detection.py` | Pass |
| ENG-02 | Master prompt 12 | TP/FP/FN, precision, recall, F1 by type with stable matching | Engineering | `src/evaluation.py` | `outputs/<scale>/evaluation.json` | Pass |
| ENG-03 | Master prompt 13 | Metric formulas; exposures not double-counted | Engineering | `src/reconciliation.py`, `docs/business_rules.md` | Billing bridge residual = 0 | Pass |
| ENG-04 | Master prompt 16 | Dashboard if time allows; every metric from real data | Optional | `app/dashboard.py` | Streamlit AppTest + browser check | Pass |
| ENG-05 | Master prompt 22 | Handover guide and clean archive | Engineering | `HANDOFF.md`, `scripts/make_handover_zip.py` | Archive inspection | Pass |
| ENG-06 | Prompt 4, section 7.1 | Overbilling finding names invoice line and shipment | Engineering | `src/detector.py` | `test_overbilling_names_the_invoice_line_and_shipment` | Pass |
| ENG-07 | Prompt 4, section 10 | Ground truth has expected label and causal explanation | Engineering | `src/anomaly_injection.py`, `src/database.py` | `test_ground_truth_file_is_separate_and_complete` | Pass |
| ENG-08 | Prompt 4, section 12 | Data types validated | Engineering | `check_data_types` in `src/validation.py` | `test_validator_catches_wrong_data_types` | Pass |
| ENG-09 | Prompt 4, section 14 | Overview shows potential leakage; delays tab shows payment delay and aging | Engineering | `app/dashboard.py` | `tests/test_dashboard.py` and browser check | Pass |
| ENG-10 | Prompt 4, section 6 | Exact split of payments and events documented | Engineering | `scripts/write_reports.py` | `docs/validation_report.md` | Pass |
| ENG-11 | Prompt 4, section 16 | README lists next steps | Engineering | `README.md` | Manual review | Pass |
| ENG-12 | Prompt 4, section 22 | Acceptance checklist reported item by item | Engineering | `docs/final_audit.md` | Manual review | Pass |
