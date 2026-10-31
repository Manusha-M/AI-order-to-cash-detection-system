# Design Decisions and Assumptions

Each entry says what was chosen, why, and what it costs. The source documents leave most of these open, and FAQ item 11 asks for reasonable assumptions to be stated.

## Stack

**Python and SQLite, with Streamlit for the dashboard.** The problem is relational, so SQL is the natural tool, and SQLite needs no server. The pipeline itself uses only the standard library; Streamlit, Altair, pandas and pytest are the only installs.

*Cost:* SQLite does not enforce types strictly and handles one writer at a time. That is fine for a batch analysis and would not suit a live multi-user system.

## Money as integer paise

Floats cannot hold most decimal amounts exactly, and a reconciliation that must equal zero cannot survive that. Net price is rounded once, on the quote line. After that every amount is an integer multiple.

*Assumptions:* one currency (INR), and tax excluded. GST would add a tax line to every document without changing the logic being evaluated.

## "15,000 payments/events" means 15,000 payment rows

The phrase can be read as payments plus events combined. This project uses the stricter reading: exactly 15,000 rows in `payment`, plus every status event on top. That exceeds the requirement under either reading (the full dataset has over 140,000 status events).

The other counts are exact too, and they include injected rows: 8,000 invoices means 8,000 after duplicates are added.

## A receivables ledger

"Dispute not reflected in receivables" needs a definition of what reflecting means. The simplest option is an `is_disputed` flag on the invoice, but a flag overwrites history and offers nothing to reconcile against.

An append-only `ar_ledger_entry` table gives a concrete rule (a hold must exist for the full amount) and a second source of truth to compare with invoices and allocations.

*Cost:* one more table and a slightly longer learning curve.

## Three bridge tables

- `shipment_line`: a shipment carries many lines, and a line can ship in parts.
- `payment_allocation`: a payment can settle many invoices, and an invoice can take many payments.
- `invoice_shipment`: a consolidated invoice bills several shipments. This link turned out to matter. See "What testing changed" below.

## Status on the row and history in events

The row's `status` is a convenience for querying. The truth is `status_event`, which is never updated. Validation check S10 proves the two agree.

Using one polymorphic history table means `entity_id` cannot be a declared foreign key, so check S02 enforces it instead. The alternative, one history table per entity, would mean six near-identical tables.

## IDs do not reveal injected rows

Duplicate invoices and repeated allocations are created after the baseline, so they would naturally get the last IDs, and an ID alone could give away the answer. `Dataset.finalize` therefore renumbers invoices and allocations by date once injection is finished.

## Labels come from the plan, then from the rule

Labels differ in how much they prove, so the `label_source` column records three kinds, and evaluation scores them separately:

- `injected`: a valid record was deliberately changed. This is the independent test.
- `plan`: the generator planned the outcome, such as a customer who stops paying, then labelled it.
- `rule`: the label re-applies the documented rule to generated dates (fulfilment and invoicing delays). A perfect score here is close to guaranteed: it only shows that two implementations of one rule agree.

This follows the source's instruction to derive labels from documented rules, not random assignment. The headline figures use `injected` labels.

## Evaluation is by record

A finding matches a label when both `issue_type` and the primary record ID are equal, so one anomaly can only match one finding. Each rule works at its natural grain: order line for billing, invoice for duplicates and aging, payment for allocation, order for closure, status event for lifecycle, dispute for receivables.

Matched findings that carry money are also checked for the exact amount. Findings with no money are left out of that check, because 0 equals 0 proves nothing.

## What a perfect score means here

The score is 1.0 on every seed tested, and that deserves suspicion rather than pride. The same project wrote the generator, the labels and the rules, so the score shows the rules do what the documents say. It does not estimate performance on real company data, where the patterns would be messier and unknown.

The clearest proof of this: an independent review scored the detector at 1.0 with a bug that hid late shipments, because the labels shared the same flaw, and it found 27 issues the perfect score had not revealed.

Stronger evidence is listed in `validation_report.md`: zero findings on clean data, reconciliation identities that fail when data is tampered with, and validators tested by corrupting data on purpose.

## What testing changed

These bugs were found by running the system, not by reading it. They are kept here because they are the best evidence of how the rules were tested.

| Found by | Problem | Change |
|---|---|---|
| First evaluation | 8 "false" long-overdue findings. The detector was right: short-paid invoices can also be 90 days late, and the labels had missed this. | Label both conditions, and add `classify_receivables` so the overlap cannot double-count money |
| Full-scale run | An overbilled quantity made two invoices identical (2 + 2 on a 3-unit line), giving a false duplicate, a missed overbill and a false underbill together | First tried a stricter quantity test |
| Clean-data control | The generator let a customer pay the disputed remainder before the undisputed part, which really does look like a stalled invoice | Fixed the generator so the disputed part settles last |
| Seed sweep | Three identical invoices: comparing each to the oldest flagged a valid one | Shipment-link proof now runs first, and the excess is spent newest-first |
| Seed sweep | A valid invoice identical to another, on an order where a different invoice carried the excess | Replaced the quantity test with the real question: do this invoice's own shipments justify what it bills? |
| Seed sweep | Injection removed `DRAFT → ISSUED` from an invoice with a dispute loop, breaking the chain in two places | The two hops being merged must now be neighbours |
| Seed sweep | Raising a quantity on a line with unbilled shipments does not exceed fulfilment, so the label was wrong | Injection skips those lines |
| Unit test | The detector crashed on an invoice for a shipment that had not shipped, which is exactly the bad data it exists to find | Rule now handles it; overbilling reports it |
| Test design | A shipment exactly 30 days old could fall under two rules | The invoicing-delay window now stops before the grace boundary |

## Independent review

After the rules passed everything above, a separate AI agent was given the code and the problem statement, but not these conclusions, and asked to break it. It reported 27 issues, each with a reproduction. Each was then written as a failing test before being fixed: 43 of the 45 new tests failed on the old code. They are in `tests/test_review_regressions.py`.

| Finding | Change |
|---|---|
| Reconciliation could not see money posted to the wrong invoice. REC-3 and REC-6 took both sides from the ledger, and REC-5's in-grace figure was a plug that cancelled R02 | Rebuilt REC-2, REC-3 and REC-5 to compare independent sources; labelled REC-6 as a partition check |
| Balances were not as of the cutoff: later entries still counted | Views now filter by date, and new checks flag anything dated after the cutoff |
| The generator crashed on about 1 in 8 starter seeds | Fixed. The whole pipeline now runs clean on 300 seeds in both modes |
| One shipment of 10 billed as 5 + 5 was called a duplicate, and caused a false underbill | Sharing a shipment is no longer proof; the invoices must bill more than it carried |
| A late shipment could hide behind a newer one on the same invoice, and recall was still 1.0 because the labels shared the flaw | R11 and its labels now measure from the oldest shipment |
| An old aged shipment was missed when a newer one had been billed | R02 now uses shipment coverage, which removes a limitation documented earlier |
| Collections were told to chase a duplicate invoice | R05, R08 and R09 skip reported duplicates |
| Evaluation overstated: 40% of labels re-applied the rule, and 45% of impact checks were 0 = 0 | Scores are split by label source; zero-value rows are excluded |
| The last IDs gave away injected rows | IDs are renumbered by date |
| Account stage changes had no history | Accounts now have status events |
| Few findings cited status events | Every finding now lists its `source_events` |
| Draft invoices counted as billed; a hold larger than the balance made collectible negative; holds on the wrong invoice were missed; order status was never checked against shipments | Each fixed, with new validation checks where they apply |

The fixes caused two new bugs, which is worth recording. Making more shipments available raised the chance of one order being picked twice by a scenario, because the "already used" list was only read once; two labels then pointed at one record. A 600-run sweep was added afterwards to look for anything else that appears only on some seeds.

Not changed: dispute credits are shown in overbilling evidence rather than netted, because a credit sits on the invoice and cannot be matched to a line. 18 of the structural checks (S01, S03, S04) repeat what the schema already enforces, so they can only fail for data loaded some other way.

## Known limitations

- **Dispute credits are not matched to lines.** Overbilling is reported gross, with credits on the invoice shown in its evidence.
- **Overbilling hidden by unbilled goods.** Over-billing a line that also has shipped but unbilled quantity does not exceed fulfilment yet, so R01 stays quiet. REC-5 shows it as a difference.
- **Invoice-level dispute rules assume one dispute at a time.** The generator never creates two on one invoice, although R07 evaluates each dispute separately.
- **SLAs are single numbers.** Real targets vary by product, region and customer.
- **The rules are thresholds.** No statistical or learned detection is attempted, because the problem does not need it and explainability matters more here.
- **`credit_limit_paise` is stored but no rule uses it.**
- **Payments are not linked to specific bank statements.** Reversed payments are modelled only before allocation, so a reversal after allocation is not represented.
- **Dates are local with no offset.** One time zone is assumed.
- **Status columns are as generated.** Moving the cutoff on an existing database re-ages balances but does not rewind statuses. Regenerate to change the cutoff properly.

## Choices left out

- **No `.env` file.** The project has no secrets or environment-specific settings. All configuration is in `src/config.py`.
- **No authentication or data-entry screens.** The problem is analytical, so these would add code without adding evidence.
- **No machine learning.** Rules are explainable and traceable to evidence, which the acceptance criteria ask for.
- **No full-scale data in the repository.** It is about 160 MB and regenerates byte-for-byte in under a minute. `data/full/manifest.json` records what to expect.
