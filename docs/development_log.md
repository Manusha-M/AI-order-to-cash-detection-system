# Development Log

A record of the build by Claude Code on 30 October 2026, in order. Commands were run from the project root with the local virtual environment. Results are as observed at the time; the final results are in `validation_report.md`.

## Milestone 1: Setup and reading the sources

- Started 20:18 IST with 25.7 hours to the stated deadline of 31 October 2026, 22:00 IST.
- Read `Problem statement.txt`. The two PDFs could not be rendered as pages, so their text was extracted with `pypdf` in a scratch environment. Both were single pages and read completely.
- Environment: Windows 11, PowerShell 7.6.9. `py -3` gave Python 3.13.6. `python` on this machine is only the Microsoft Store placeholder, so the docs use `py` with a fallback.
- Noted FAQ item 7 on individual work and flagged it to the operator at the start.
- Wrote `docs/requirements_matrix.md` before any code.

## Milestone 2: Schema and generator

- Files: `src/config.py`, `src/lifecycle.py`, `sql/schema.sql`, `sql/analytics.sql`, `src/generator.py`, `src/anomaly_injection.py`, `src/database.py`.
- First smoke test: starter counts were exact on the first run (1,000 / 700 / 800 / 1,500).

## Milestone 3: Detector, evaluation, validation, reproducibility

- Files: `src/detector.py`, `src/evaluation.py`, `src/reconciliation.py`, `src/validation.py`, `src/reproducibility.py`, `run.py`.
- `run.py all --scale starter`, first full run:
  - 79 of 80 structural checks passed. Invoice-line IDs had a gap, because the "line omitted" scenario deleted a row after numbering. IDs are now assigned after injection.
  - TP 120, FP 8, FN 0. All 8 false positives were short-paid invoices also over 90 days late. The detector was right and the labels were incomplete.
  - Added identity REC-6 and `classify_receivables`, because that overlap could double-count money.

## Milestone 4: Full scale and seed sweep

- `run.py all --scale full`: all required counts exact, 54.7 seconds. TP 1,282, FP 3, FN 1, and the clean-data control failed with 1 finding.
- Traced each mismatch to its records rather than adjusting thresholds. Fixed the duplicate rule and a generator ordering bug.
- Wrote `scripts/seed_sweep.py`. Other seeds exposed more cases the default seed had hidden:
  - A duplicate dated before a later, legitimate, identical invoice.
  - An illegal-transition injection that broke an invoice's history in two places.
  - Overbilling labels on lines with unbilled shipments, where nothing was actually over-billed.
- Replaced the duplicate rule's quantity test with a better question: do this invoice's own shipments justify what it bills?
- Sweep after the fixes: 10 starter seeds and 6 full-scale seeds, each with and without anomalies, with no false positives, false negatives, structural failures or identity failures.

The full list of bugs is in `decisions.md`, under "What testing changed".

## Milestone 5: Automated tests

- Files: `tests/` and `pytest.ini`.
- First run: 137 passed, 3 failed. All three were the same real bug: `KeyError` in the invoicing-delay rule when an invoice billed a shipment that had not shipped. Fixed, and added a regression test.
- Added tests that corrupt data deliberately, so that each validator is shown to be able to fail.

## Milestone 6: Dashboard

- Files: `app/dashboard.py`, `.streamlit/config.toml`, `tests/test_dashboard.py`.
- Followed the data-visualisation guidance and ran its palette validator. A six-step blue ramp for aging failed: adjacent steps were too close. No six-step ramp in the palette passed, so aging uses one colour and relies on its axis labels.
- Checked all five tabs in a real browser on the full dataset. Found and fixed metric values being cut off at narrow widths, and moved the dataset picker out of the sidebar.

## Milestone 7: Documentation

- Wrote the data dictionary, rules, architecture, decisions, disclosure, handover guide and README.
- `tests/test_docs.py` fails if a schema column, enum value, rule or threshold goes undocumented.
- Tested the learning exercise in `HANDOFF.md` on a throwaway copy. The prediction written first was vague, so the text was replaced with what actually happened.

## Milestone 8: Independent review

- Everything was passing, with detection at 1.0. Because the same author wrote the data, labels and rules, a separate AI agent was asked to break the system, given the code and the problem statement but not the author's conclusions.
- It reported 27 issues, each with a reproduction, including reconciliation identities that could not fail, balances not as of the cutoff, and a generator crash on about 1 in 8 starter seeds.
- A report is not proof, so each claim became a test first. Of 45 new tests, 43 failed on the existing code, which confirmed the claims.
- Fixed the code, then ran the suite. One older test caught a mistake in a new fix: flagging a hold above the balance would have wrongly flagged a dispute on a fully paid invoice. A generator fix also caused a new crash on some seeds, found by the tests and solved by dating consolidated invoices within the target.
- Generated 300 starter seeds in both modes: 600 runs, 0 crashes.
- The details are in `decisions.md`, under "Independent review".

## Milestone 9: Final verification

- A sweep failed with a Windows file-lock error. This was first blamed on antivirus, and the temp cleanup was relaxed. That diagnosis was wrong: the lock was a side effect of an exception that left a database open, and the relaxed cleanup is what revealed the real error, `ground truth holds two labels for the same record`.
- The real cause: underbilling hit one order twice, because the list of used orders was read once at the start of the loop. `clean_invoices` now re-checks each target. A regression test covers it.
- Ran the entire pipeline (generate, detect, validate, reconcile, evaluate) on 300 starter seeds in both modes: 600 runs, 0 with any problem.
- Rebuilt `data/` and `outputs/` from nothing on the final code. Ran all automated tests. Checked the dashboard in a browser again.
- Built the archive, extracted it to an empty folder, and followed the documented setup from a new virtual environment. The result is recorded in `final_audit.md`.

## Milestone 10: Revision from a later prompt

- After the build, the operator submitted a second, longer prompt (Prompt 4 in `prompt_history.md`) and asked for it to be stored as the prompt used to create the software.
- It was not stored that way, because the software was built from Prompt 1. It is recorded as a later prompt, with its real timestamp. Prompt 1 stays unchanged.
- The prompt was compared with the build, and the real differences were closed: finding evidence for overbilling, ground-truth fields, data-type checks, dashboard coverage, the split of payments and events, next steps in the README, and an item-by-item acceptance checklist.
- Git was checked, as the prompt asks. No repository was created and nothing was committed, because the operator has not said whose account or identity to use.

## Milestone 11: Who the candidate is

- Claude Code asked who is actually submitting. The operator answered in Prompt 5 that they are.
- Corrected the disclosure, setup guide, audit, requirement matrix and README to match. Prompt 1 stays word for word, and the difference is stated openly. Only the candidate can explain it, so that is left for them to fill in.
- No application code changed, and no data or results changed. One documentation test was added, which protects the prompt history.

## Milestone 12: Disclosure completed

- Prompt 9 asked Claude Code to complete the disclosure documents. They were completed from the session record only.
- Claude Code did not write that the candidate read code, ran tests or found bugs, because the record does not show that. It lists these as not recorded.
- Corrected an overstatement from Milestone 11: the disclosure had said the candidate stated no one else helped. The candidate said only that they are submitting.
- The audit's top-level answer changed from "no" to "yes, as an honest record, with limits", with the candidate's remaining actions listed.
- The candidate then stated the AI tools used (Prompt 11): ChatGPT to create the master prompt, and Claude Code to build the project. The ChatGPT prompts were not provided, so that is recorded as a limitation.
