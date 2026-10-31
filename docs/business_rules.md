# Business Rules

All thresholds live in `src/config.py`, and the generator reads the same values, so a reviewer can change one number and re-run. A target tighter than normal behaviour makes ordinary records look late: that is what the change means, not a fault.

| Setting | Value | Why this value |
|---|---|---|
| Analysis cutoff | 2026-09-30 | End of a fiscal half; all aging is measured against it |
| Data window | 2026-01-01 to 2026-09-30 | Gives every overdue bucket time to fill |
| Order-to-fulfilment target | 21 days | Assumption: an ordinary B2B dispatch promise |
| Shipment-to-invoice target | 7 days | Assumption: weekly billing run at worst |
| Unbilled grace period | 30 days | After a month an unbilled shipment is treated as missed, not late |
| Long overdue | More than 90 days past due | Common credit-control line |
| Short payment | More than 30 days past due and 30 days without activity | Separates a stalled payer from one still paying in instalments |
| Balance tolerance | Rs 100 | Below this, chasing costs more than it recovers |

These are design assumptions. The source documents do not prescribe any of them.

## Lifecycles

Anything not listed below is an illegal transition. The code version is `src/lifecycle.py`.

| Entity | Allowed transitions |
|---|---|
| Account | start → PROSPECT → CUSTOMER |
| Quote | start → DRAFT → SENT → ACCEPTED / REJECTED / EXPIRED |
| Sales order | start → CREATED → CONFIRMED; CREATED or CONFIRMED → CANCELLED; CONFIRMED → PARTIALLY_FULFILLED or FULFILLED; PARTIALLY_FULFILLED → FULFILLED; FULFILLED → INVOICED → CLOSED |
| Shipment | start → PLANNED → SHIPPED → DELIVERED |
| Invoice | start → DRAFT → ISSUED; ISSUED → PARTIALLY_PAID, PAID, DISPUTED or VOID; PARTIALLY_PAID → PAID or DISPUTED; DISPUTED → ISSUED, PARTIALLY_PAID or PAID |
| Payment | start → RECEIVED → ALLOCATED or REVERSED |
| Dispute | start → OPEN → UNDER_REVIEW or WITHDRAWN; UNDER_REVIEW → RESOLVED_CREDIT, RESOLVED_NO_CREDIT or WITHDRAWN |

State meanings that matter:

- **INVOICED** on an order means every shipped quantity has been invoiced.
- **CLOSED** on an order means every invoice on it is settled.
- **DISPUTED** on an invoice pauses normal status movement. Payments can still arrive.

## Receivables treatment of disputes

The source requires detecting a "dispute not reflected in receivables", so the rule has to be defined. This project's rule:

1. When a dispute opens, a `DISPUTE_HOLD` for the full disputed amount is posted. The money stays in the balance but leaves collectible receivables.
2. When a dispute closes, a `DISPUTE_RELEASE` reverses the hold.
3. If a credit is granted, a `CREDIT_MEMO` for that amount reduces the balance.

A dispute breaks this rule if the ledger's hold differs from what its status requires, or if a granted credit is not fully posted.

## Detection rules

Rule order matters only once: duplicates run first, so overbilling does not report the same excess quantity again.

| Rule | Issue type | Grain | Logic | Money reported as |
|---|---|---|---|---|
| R01 | OVERBILLING | Order line | Billed quantity (live invoices, less what R03 explains) above shipped quantity, or invoice price above order price | OVERBILLED_EXPOSURE |
| R02 | UNDERBILLING | Order line | Shipped quantity not billed and not simply awaiting an invoice, or invoice price below order price. "Awaiting" means on a shipment no live invoice covers yet, shipped under 30 days ago. An invoice that bills less than its shipment is short at once | UNDERBILLED_REVENUE |
| R03 | DUPLICATE_INVOICE | Invoice | Same lines, quantities and prices as an earlier live invoice on the order, **and** proof it is a repeat: it shares a shipment that cannot carry both invoices, or its own shipments do not justify it and the billed excess can hold the whole invoice | DUPLICATE_BILLING_EXPOSURE |
| R04 | DUPLICATE_ALLOCATION | Payment | Sum of allocations above the payment amount (impact is the excess), or an identical allocation row repeated within the amount (impact 0, because the cash is there; it is a data-entry warning) | PAYMENT_ALLOCATION_DISCREPANCY |
| R05 | CLOSED_ORDER_UNPAID | Order | Status CLOSED with a live invoice balance above tolerance, ignoring invoices R03 reported, which should be cancelled rather than collected | UNCOLLECTED_RECEIVABLE |
| R06 | ILLEGAL_TRANSITION | Status event | Transition not in the state machine, or `from_status` differs from the previous event | None |
| R07 | DISPUTE_NOT_IN_AR | Dispute | Ledger hold or credit on the dispute's own invoice differs from what its status requires, or the hold exceeds the money still owed | DISPUTED_NOT_RESERVED |
| R08 | SHORT_PAYMENT | Invoice | Some payment made, collectible above tolerance, more than 30 days past due, and no payment or dispute activity for 30 days | SHORT_PAID_RECEIVABLE |
| R09 | LONG_OVERDUE | Invoice | Collectible above tolerance and more than 90 days past due, ignoring invoices R03 reported | OVERDUE_RECEIVABLE |
| R10 | FULFILMENT_DELAY | Order | Over 21 days from order to full shipment, or to the cutoff if still short. Cancelled orders excluded | None |
| R11 | INVOICING_DELAY | Invoice or shipment | Invoice raised more than 7 days after its **oldest** newly billed shipment, so a late shipment cannot hide behind a newer one on the same invoice; or a shipment unbilled for more than 7 and under 30 days at the cutoff. A reissue keeps the date of the invoice it replaced | None |

Boundaries are exact: 90 days past due is not long overdue, and 91 is. Billing exactly what shipped is not overbilling. `tests/test_detection.py` tests both sides of each edge.

### Severity

Money findings: HIGH from Rs 1,00,000, MEDIUM from Rs 10,000, otherwise LOW. Delay findings: HIGH at twice the target, otherwise MEDIUM. A closed order with an unpaid invoice is always HIGH. An illegal transition is always MEDIUM.

## Anomaly scenarios

| Code | Scenario | How it is created | Required by |
|---|---|---|---|
| A1, A2 | Invoice exceeds fulfilled quantity | Raise a billed quantity on an open invoice (A1) or a paid one, where the customer also overpaid (A2) | Mandatory |
| B1, B2 | Payment allocated twice | Repeat the allocation on the same invoice (B1), or apply the full payment again to a second invoice of the account (B2) | Mandatory |
| C | Order closed with unpaid invoice | Add a legal INVOICED → CLOSED event while a balance is open | Mandatory |
| D | Status event skips a required state | Replace two neighbouring legal events with one direct jump, across orders, quotes, invoices, shipments and disputes | Mandatory |
| E1, E2 | Dispute not reflected in receivables | Remove the hold (E1) or post a smaller one (E2) | Mandatory |
| F | Duplicate invoice | Copy an invoice and its shipment links under a new ID | Coverage |
| G1 to G3 | Underbilling | Lower the billed price (G1), lower the billed quantity (G2), omit a shipped line (G3) | Coverage |
| Plan | Short payment, long overdue | The baseline plans a customer who stops paying, then labels it | Coverage |
| Rule | Fulfilment and invoicing delays | Labelled by re-applying the documented rule to the generated dates | Coverage |

Boundary look-alikes the rules must **not** flag, all present in the data:

- Two equal shipments billed on two identical-looking invoices.
- Voided and reissued invoices.
- Unpaid invoices exactly 90 days past due.
- Stale residual balances at or below tolerance.
- Bulk payments split across invoices within the payment amount.
- Instalments still arriving.

## Avoiding double counting

Findings can overlap because one invoice can be both short-paid and long overdue. Four controls stop that misleading anyone:

1. **Impact types are never added together.** The dashboard shows them apart.
2. **Billing rules exclude duplicates.** R01 and R02 leave out invoices R03 reported, so the same excess or price gap is reported once.
3. **Collection rules exclude duplicates.** R05, R08 and R09 ignore a reported duplicate, because the right action is to cancel it, not chase the customer.
4. **`classify_receivables` gives every rupee one class**, by precedence: disputed, duplicate billing, long overdue, short paid, other overdue, not due.

Do not add these together: underbilled revenue is **lost income**, overbilled and duplicate amounts are **customer-facing billing errors**, and overdue amounts are **collection risk** that may still arrive.

## Metrics

All are computed by `src/reconciliation.py` from source tables at the cutoff.

Money is reported in paise and delays in days. Filters are part of each formula below. All balances are as of the cutoff: ledger entries and invoices dated later are ignored. Status columns describe the data as generated, so moving the cutoff on an existing database re-ages balances but does not rewind statuses.

| Metric | Formula | Source | Interpretation and limits |
|---|---|---|---|
| Quoted value | Sum of quote totals, all statuses | quote | Pipeline, not revenue |
| Accepted value | Sum of ACCEPTED quote totals | quote | Commitments won |
| Ordered value | Sum of order totals, excluding CANCELLED | sales_order | Live orders |
| Fulfilled value | Shipped quantity x order price | shipment_line, shipment, order_line | Value of goods actually dispatched; excludes PLANNED |
| Invoiced value | Sum of live invoice totals | invoice | Includes billing errors; compare with fulfilled |
| Cash received | Sum of payments excluding REVERSED | payment | Includes unapplied cash |
| Applied to invoices | Sum of allocations | payment_allocation | Overstated by duplicate allocations |
| Unapplied cash | Sum of the unallocated part of each non-reversed payment | payment, payment_allocation | Cash not yet matched to an invoice, including the rest of a part-allocated payment |
| Outstanding receivables | Posted - voided - applied - credits | ar_ledger_entry | Understated by false allocations, inflated by duplicate invoices |
| Disputed balances | Holds - releases, capped at the balance | ar_ledger_entry | Only what the ledger recorded; R07 shows the gaps |
| Collectible | Outstanding - disputed | ar_ledger_entry | What collections can chase; never pushed negative by an oversized hold |
| Overdue balances | Collectible where past due | v_invoice_balance | Depends on the cutoff |
| Underbilled value | Sum of R02 impact | finding | True leakage |
| Overbilled exposure | Sum of R01 impact | finding | Refund or credit risk |
| Duplicate-billing exposure | Sum of R03 impact | finding | Refund or credit risk |
| Allocation discrepancy | Sum of R04 impact | finding | Amount by which receivables look too low |
| Order to fulfilment | Last shipped date - order date | v_order_timeline | Completed orders only; open ones appear under R10 |
| Fulfilment to invoice | First live invoice date - shipped date, per shipment | v_shipment_billing | Counts shipments, so "over target" differs from the number of R11 findings, which count invoices |
| Invoice to payment | Last allocation date - invoice date | payment_allocation, invoice | PAID invoices only |

## Reconciliation identities

Each must net to exactly zero paise. An identity is only worth having if its two sides come from different places, so that is stated for each one.

| ID | Identity | Compares | Proves |
|---|---|---|---|
| REC-1 | Live invoice totals = posted - voided | Invoice headers with the ledger | Headers agree with the ledger overall |
| REC-2 | Per invoice, ledger payment entries = allocations | Ledger with `payment_allocation` | The ledger saw every allocation, on the right invoice. Gaps are summed as absolute values, so money moved between invoices cannot cancel out |
| REC-3 | Per invoice, ledger balance = total - allocations - dispute credits | Ledger with invoice, allocation and dispute tables | Every balance can be rebuilt without the ledger |
| REC-4 | Cash + over-allocation = allocations + unapplied | Payments and allocations with R04's findings | Cash ties out, and the gap is exactly what the detector reported |
| REC-5 | Fulfilled + duplicates + overbilled - underbilled - awaiting invoice = invoiced | Shipments and invoices with R01 to R03 findings | Billing exposures fully explain the gap between shipped and billed. "Awaiting invoice" comes from shipments no live invoice covers, not from the detector |
| REC-6 | Receivable classes sum to outstanding | Same source on both sides | Partition check only: each rupee has one class. It cannot detect a wrong balance |

An independent review showed that earlier versions of REC-3 and REC-5 took both sides from one source, so they could not fail when they should. They were rebuilt, and `tests/test_review_regressions.py` now moves money between invoices, deletes ledger entries and removes findings, to prove the identities notice.

Limits: a dispute credit is posted on the invoice, not a line, so REC-5 uses gross billing. Overbilling on a line that also has shipped but unbilled quantity stays below R01's threshold, and REC-5 shows it as a non-zero difference to investigate.
