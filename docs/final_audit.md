# Final Requirement Audit

Written by Claude Code on 30 October 2026 after the final build. Statuses are PASS, PARTIAL, FAIL or NOT VERIFIED. They describe the project on the development machine, and do not show that the candidate has reviewed anything.

## Can this be submitted as it is?

**Yes, as an honest record, with limits.** The package is complete, and the disclosure states what the session record shows, including what the candidate has not done. FAQ items 6 and 11 accept stated limits. Four things are left, and only the candidate can do them:

| # | Open item |
|---|---|
| 1 | Read `ai_usage.md` and `prompt_history.md`, and confirm they are true. Add the prompts sent to ChatGPT, if they can be retrieved |
| 2 | Be ready to explain why Prompt 1 describes a friend, and to walk through the code without notes. The disclosure says no code review by the candidate is on record |
| 3 | Run the checks in `HANDOFF.md` section C, and add the results to `ai_usage.md` |
| 4 | Create the public GitHub repository and send the link from the registered email before the deadline |

## Audit

| Requirement | Status | Evidence |
|---|---|---|
| All required entities exist | PASS | `tests/test_integrity.py`; all 11 entities, 5 support tables, and `run_metadata` and `finding` |
| Keys and relationships are valid | PASS | Validation S01, S02, S06; foreign-key check; 98 of 98 structural checks passed |
| Lifecycle events are retained | PASS | `status_event` has 152,107 rows at full scale; `test_history_rebuilds_each_clean_record` replays history to each record's status |
| Required data volumes are generated | PASS | Exactly 10,000 quotes, 7,000 orders, 8,000 invoices, 15,000 payments (validation S11) |
| IDs follow the specified patterns | PASS | Schema format checks; validation S05 checks format and contiguity |
| Derived values reconcile | PASS | Validation S08; six identities at 0 paise, comparing independent sources |
| Mandatory five anomalies exist | PASS | All five planted and detected: `validation_report.md` |
| Additional exception cases are represented | PASS | Partial shipment, underbilling, duplicate invoice, short payment, long overdue, delays |
| Ground truth is separate | PASS | `data/<scale>/ground_truth.csv`; no label columns or text in the database (test) |
| Detection works independently of labels | PASS | `test_detector_never_touches_ground_truth`; IDs renumbered so they reveal nothing |
| Financial metrics are explainable | PASS | Formulas, sources and limits in `business_rules.md` |
| Aging cutoff is documented | PASS | 2026-09-30, in `run_metadata`; views are as-of the cutoff; boundary tests on every bucket |
| Data quality checks execute | PASS | `run.py validate`; tests corrupt data on purpose to prove the checks can fail |
| Evaluation metrics are measured | PASS | 390 of 390 injected anomalies found, 0 false positives on those types. Read the caveat in `decisions.md` |
| Two-run reproducibility is demonstrated | PASS | Two separate processes with different hash seeds gave identical checksums: `reproducibility.md` |
| Exports and manifest are available | PASS | CSV, JSON, SQL seed and `manifest.json` in `data/<scale>/` |
| README commands are verified | PASS | Setup, starter, full, tests and dashboard run from a new folder and environment |
| Prompt history is preserved to the extent available | PARTIAL | All Claude Code prompts are exported verbatim. ChatGPT created the master prompt, and the prompts sent to it were not provided. The limitation is stated |
| AI disclosure is honest | PASS | `ai_usage.md` is written from the session record and states what is not on record. The candidate should confirm it |
| The local project is portable | PARTIAL | Passed from the archive in a new folder with a new environment, with matching checksums. **Not tried on a second computer** |
| Individual work (FAQ item 7) | PARTIAL | AI help is allowed, and Prompt 5 states the operator is the candidate. The session record shows no other person. Claude Code cannot verify anything outside that record |
| No personal or company GitHub accounts were used | PASS | No GitHub command or account was used during the build |
| No GitHub push, publication or deployment occurred | PASS | No `.git` folder exists; nothing was uploaded; the dashboard ran on localhost only |

## Acceptance checklist (Prompt 4, section 22)

| # | Item | Status | Evidence |
|---:|---|---|---|
| 1 | All 11 required entities implemented | PASS | `sql/schema.sql`, `tests/test_integrity.py` |
| 2 | Correct primary and foreign keys | PASS | Validation S01, S02 |
| 3 | Relationship cardinality documented | PASS | `data_dictionary.md`, Relationships |
| 4 | Valid lifecycle state modeling | PASS | `src/lifecycle.py`, `tests/test_lifecycle.py` |
| 5 | Historical StatusEvent records retained | PASS | 152,107 events; history replays to each record's status |
| 6 | Required deterministic ID conventions | PASS | Validation S05 |
| 7 | 10,000 quotes generated | PASS | Validation S11 |
| 8 | 7,000 orders generated | PASS | Validation S11 |
| 9 | 8,000 invoices generated | PASS | Validation S11 |
| 10 | 15,000 payments/events baseline satisfied | PASS | 15,000 payment rows, plus events. Split in `validation_report.md` |
| 11 | Partial shipment scenarios included | PASS | Multi-shipment orders and backorders in the data |
| 12 | Underbilling scenarios included | PASS | 90 labelled, 90 detected |
| 13 | Duplicate invoice scenarios included | PASS | 50 labelled, 50 detected |
| 14 | Short payment scenarios included | PASS | 161 labelled, 161 detected |
| 15 | Long-overdue balances included | PASS | 204 labelled, 204 detected |
| 16 | Invoice exceeding fulfilled quantity | PASS | 60 labelled, 60 detected |
| 17 | Payment allocated twice | PASS | 50 labelled, 50 detected |
| 18 | Closed order with unpaid invoice | PASS | 40 labelled, 40 detected |
| 19 | Invalid lifecycle-state transition | PASS | 60 labelled, 60 detected |
| 20 | Dispute not reflected in receivables | PASS | 40 labelled, 40 detected |
| 21 | Ground truth generated separately | PASS | `ground_truth.csv`, never in the database |
| 22 | Independent exception detection working | PASS | Detector reads the database only (test) |
| 23 | Financial balances reconciled | PASS | Six identities at 0 paise |
| 24 | Aging cutoff documented | PASS | 2026-09-30; boundary tests |
| 25 | Structural validations executed | PASS | 98 of 98 |
| 26 | Automated tests executed | PASS | 208 passed |
| 27 | Evaluation metrics calculated | PASS | `validation_report.md`. Read its caveat |
| 28 | Fixed-seed reproducibility verified twice | PASS | `reproducibility.md` |
| 29 | CSV/JSON/SQL exports provided | PASS | `data/<scale>/` |
| 30 | Data dictionary and schema documented | PASS | `data_dictionary.md`; a test fails on any undocumented column |
| 31 | Source manifest included | PASS | `data/<scale>/manifest.json` |
| 32 | README commands verified | PASS | Clean-folder test below |
| 33 | AI usage disclosed accurately | PASS | Complete, and limited to what the session record shows. The candidate should confirm it |
| 34 | Prompt history preserved | PARTIAL | All Claude Code prompts exported verbatim. ChatGPT prompts were not provided; the limitation is stated |
| 35 | Repository contents reviewed for safety | PARTIAL | The archive scan found no secrets. No repository exists yet to review. The prompt history holds local paths and a company name |
| 36 | Submission readiness checked | PARTIAL | The package is complete. Publication and the candidate's own checks remain. See the open items at the top |

Other parts of Prompt 4:

- **Publication:** no repository was created and nothing was committed. Git 2.51.0 is installed. Prompt 4 requires authorization before anything public, and the account to use has not been stated.
- **Suggested layout:** `src/anomaly_injection.py` plays the role of `anomalies.py`, and assumptions are in `decisions.md` rather than a separate `assumptions.md`. The prompt allows simpler layouts.

## Clean-folder test

The archive was extracted to an empty folder and set up as `HANDOFF.md` describes, on the development computer.

| Step | Result |
|---|---|
| Archive contents | 94 files; no `.venv`, no database, no full dataset |
| New environment and `pip install` | Succeeded in 232 seconds |
| `run.py all --scale starter` | Succeeded in 15 seconds; all checks passed |
| `run.py all --scale full` | Succeeded in 129 seconds; all checks passed |
| Automated tests | 206 passed. Two documentation tests were added afterwards; all 208 then passed on the development build |
| Checksums against the development build | Identical at both scales |
| Dashboard | Answered its health check 5 seconds after starting. An earlier fresh install took over 12 seconds on its first start, so the guide allows 20 |

Python 3.13.6 only. Python 3.11 and 3.12 were not tested.

## What has not been verified

- Any other computer, or any Python version except 3.13.6.
- Streamlit's first-run behaviour on a computer that has never used it.
- Review by a person. The independent reviewer was an AI, and its report ended with fixes rather than a clean second review, so more bugs may remain.
- Performance on real business data. The data, labels and rules share one author.
