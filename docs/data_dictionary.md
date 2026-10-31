# Data Dictionary

Conventions used throughout:

- **Money** is INR in integer paise (Rs 1 = 100 paise), named `*_paise`. Integers keep arithmetic exact. There is one currency and tax is excluded.
- **Dates** are text `YYYY-MM-DD`. **Timestamps** are text `YYYY-MM-DDTHH:MM:SS`, local IST with no offset.
- **IDs** follow `PREFIX-2026-NNNNNN`. The year token names the dataset year, so an account created in 2025 still has a `2026` ID. Counters are zero-padded, contiguous and immutable.
- **Req** means NOT NULL in the schema. **Unique** lists a single-column uniqueness rule; multi-column rules are noted under the table.
- A row's `status` holds its current state. The full history is in `status_event`.
- A **live invoice** is one that really bills the customer: not DRAFT, not VOID, dated by the cutoff.

## account
Master data: a customer or prospect. Created before any quote. Lifecycle: PROSPECT, then CUSTOMER on the first order.

| Field | Type | Req | Allowed values / units | Unique | Validation |
|---|---|---|---|---|---|
| account_id | TEXT | Yes | `ACC-2026-NNNNNN` | Yes (PK) | Format check; contiguous |
| account_name | TEXT | Yes | Invented synthetic company name | Yes | Non-empty |
| segment | TEXT | Yes | SMB, MID_MARKET, ENTERPRISE | No | Enum |
| region | TEXT | Yes | NORTH, SOUTH, EAST, WEST | No | Enum |
| status | TEXT | Yes | PROSPECT, CUSTOMER | No | Enum; equals latest event; CUSTOMER if and only if an order exists |
| payment_terms_days | INTEGER | Yes | 15, 30, 45, 60 (days) | No | Enum |
| credit_limit_paise | INTEGER | Yes | Paise, >= 0 | No | Non-negative. Stored for context; no rule uses it |
| created_date | TEXT | Yes | Date | No | Before the first quote |

## product
Support table: the catalogue that quote lines reference.

| Field | Type | Req | Allowed values / units | Unique | Validation |
|---|---|---|---|---|---|
| product_id | TEXT | Yes | `PRD-2026-NNNNNN` | Yes (PK) | Format check; contiguous |
| product_name | TEXT | Yes | Invented product name | Yes | Non-empty |
| category | TEXT | Yes | MECHANICAL, ELECTRICAL, CONSUMABLE, SAFETY | No | Enum |
| list_price_paise | INTEGER | Yes | Paise per unit, > 0 | No | Positive |

## quote
Commercial offer to an account. Lifecycle: DRAFT, SENT, then ACCEPTED, REJECTED or EXPIRED.

| Field | Type | Req | Allowed values / units | Unique | Validation |
|---|---|---|---|---|---|
| quote_id | TEXT | Yes | `QTE-2026-NNNNNN` | Yes (PK) | Format check; contiguous |
| account_id | TEXT | Yes | FK account | No | FK |
| quote_date | TEXT | Yes | Date | No | Inside the analysis window |
| valid_until | TEXT | Yes | Date, quote_date + 30 days | No | Not before quote_date. May be after the cutoff |
| channel | TEXT | Yes | INBOUND, OUTBOUND, PARTNER, RENEWAL | No | Enum |
| status | TEXT | Yes | DRAFT, SENT, ACCEPTED, REJECTED, EXPIRED | No | Enum; equals latest event |
| total_paise | INTEGER | Yes | Paise, derived | No | Equals the sum of line totals |

## quote_line
Priced line on a quote. Multi-column unique: (quote_id, line_number).

| Field | Type | Req | Allowed values / units | Unique | Validation |
|---|---|---|---|---|---|
| quote_line_id | TEXT | Yes | `QTL-2026-NNNNNN` | Yes (PK) | Format check; contiguous |
| quote_id | TEXT | Yes | FK quote | No | FK |
| line_number | INTEGER | Yes | 1 upward within the quote | With quote_id | Positive |
| product_id | TEXT | Yes | FK product | No | FK |
| quantity | INTEGER | Yes | Units, > 0 | No | Positive |
| list_price_paise | INTEGER | Yes | Paise per unit | No | Positive |
| discount_bps | INTEGER | Yes | 0 to 3000 basis points (100 bps = 1%) | No | Range check |
| net_unit_price_paise | INTEGER | Yes | Paise per unit, derived | No | list x (10000 - discount) / 10000, rounded once |
| line_total_paise | INTEGER | Yes | Paise, derived | No | quantity x net price |

## sales_order
Created only from an ACCEPTED quote. Lifecycle: CREATED, CONFIRMED, optional PARTIALLY_FULFILLED, FULFILLED, INVOICED, CLOSED, or CANCELLED before fulfilment.

| Field | Type | Req | Allowed values / units | Unique | Validation |
|---|---|---|---|---|---|
| order_id | TEXT | Yes | `SO-2026-NNNNNN` | Yes (PK) | Format check; contiguous |
| quote_id | TEXT | Yes | FK quote | Yes | One order per quote; quote must be ACCEPTED |
| account_id | TEXT | Yes | FK account | No | Must equal the quote's account |
| order_date | TEXT | Yes | Date | No | Not before quote_date |
| payment_terms_days | INTEGER | Yes | 15, 30, 45, 60 (days) | No | Copied from the account at order time |
| status | TEXT | Yes | CREATED, CONFIRMED, PARTIALLY_FULFILLED, FULFILLED, INVOICED, CLOSED, CANCELLED | No | Enum; equals latest event |
| total_paise | INTEGER | Yes | Paise, derived | No | Equals the sum of line totals |

## order_line
Line on an order, copied from its quote line. Multi-column unique: (order_id, line_number).

| Field | Type | Req | Allowed values / units | Unique | Validation |
|---|---|---|---|---|---|
| order_line_id | TEXT | Yes | `SOL-2026-NNNNNN` | Yes (PK) | Format check; contiguous |
| order_id | TEXT | Yes | FK sales_order | No | FK |
| quote_line_id | TEXT | Yes | FK quote_line | Yes | Must belong to the order's quote |
| line_number | INTEGER | Yes | 1 upward within the order | With order_id | Positive |
| product_id | TEXT | Yes | FK product | No | FK |
| quantity | INTEGER | Yes | Units, > 0 | No | Positive |
| unit_price_paise | INTEGER | Yes | Paise per unit | No | Net price from the quote |
| line_total_paise | INTEGER | Yes | Paise, derived | No | quantity x unit price |

## shipment
One physical dispatch for an order. Lifecycle: PLANNED, SHIPPED, DELIVERED. Only SHIPPED and DELIVERED count as fulfilled.

| Field | Type | Req | Allowed values / units | Unique | Validation |
|---|---|---|---|---|---|
| shipment_id | TEXT | Yes | `SHP-2026-NNNNNN` | Yes (PK) | Format check; contiguous |
| order_id | TEXT | Yes | FK sales_order | No | FK |
| carrier | TEXT | Yes | BLUELINE, SWIFTCARGO, TRANSINDIA, OWN_FLEET | No | Enum |
| planned_date | TEXT | Yes | Date | No | May be after the cutoff |
| shipped_date | TEXT | No | Date; null until shipped | No | Not before order_date; not after cutoff |
| delivered_date | TEXT | No | Date; null until delivered | No | Not before shipped_date; not after cutoff |
| status | TEXT | Yes | PLANNED, SHIPPED, DELIVERED | No | Enum; equals latest event |

## shipment_line
Bridge: Shipment N:M OrderLine. Multi-column unique: (shipment_id, order_line_id).

| Field | Type | Req | Allowed values / units | Unique | Validation |
|---|---|---|---|---|---|
| shipment_line_id | TEXT | Yes | `SHL-2026-NNNNNN` | Yes (PK) | Format check; contiguous |
| shipment_id | TEXT | Yes | FK shipment | With order_line_id | FK |
| order_line_id | TEXT | Yes | FK order_line | With shipment_id | Must belong to the shipment's order |
| quantity | INTEGER | Yes | Units, > 0 | No | Total shipped never exceeds ordered |

## invoice
Bill for shipped goods. Lifecycle: DRAFT, ISSUED, then PARTIALLY_PAID, PAID, DISPUTED or VOID. DRAFT and VOID invoices are excluded from every billed figure.

| Field | Type | Req | Allowed values / units | Unique | Validation |
|---|---|---|---|---|---|
| invoice_id | TEXT | Yes | `INV-2026-NNNNNN` | Yes (PK) | Format check; contiguous |
| order_id | TEXT | Yes | FK sales_order | No | FK |
| account_id | TEXT | Yes | FK account | No | Must equal the order's account |
| invoice_date | TEXT | Yes | Date | No | Not before covered shipments; not after cutoff |
| due_date | TEXT | Yes | Date | No | invoice_date + order payment terms |
| status | TEXT | Yes | DRAFT, ISSUED, PARTIALLY_PAID, PAID, DISPUTED, VOID | No | Enum; equals latest event |
| total_paise | INTEGER | Yes | Paise, derived | No | Equals the sum of line totals |
| replaces_invoice_id | TEXT | No | FK invoice; set on a reissue | No | Points at the void original |

## invoice_line
Billed line. Multi-column unique: (invoice_id, line_number).

| Field | Type | Req | Allowed values / units | Unique | Validation |
|---|---|---|---|---|---|
| invoice_line_id | TEXT | Yes | `IVL-2026-NNNNNN` | Yes (PK) | Format check; contiguous |
| invoice_id | TEXT | Yes | FK invoice | No | FK |
| order_line_id | TEXT | Yes | FK order_line | No | Must belong to the invoice's order |
| line_number | INTEGER | Yes | 1 upward within the invoice | With invoice_id | Positive |
| quantity | INTEGER | Yes | Units, > 0 | No | May exceed shipped: that is anomaly A, not a structural error |
| unit_price_paise | INTEGER | Yes | Paise per unit | No | Should equal the order price |
| line_total_paise | INTEGER | Yes | Paise, derived | No | quantity x unit price |

## invoice_shipment
Bridge: Invoice N:M Shipment. A consolidated invoice bills several shipments. Primary key: (invoice_id, shipment_id).

| Field | Type | Req | Allowed values / units | Unique | Validation |
|---|---|---|---|---|---|
| invoice_id | TEXT | Yes | FK invoice | With shipment_id | FK |
| shipment_id | TEXT | Yes | FK shipment | With invoice_id | Must belong to the invoice's order |

## payment
Cash received from an account. Lifecycle: RECEIVED, then ALLOCATED or REVERSED. A payment still RECEIVED at the cutoff is unapplied cash.

| Field | Type | Req | Allowed values / units | Unique | Validation |
|---|---|---|---|---|---|
| payment_id | TEXT | Yes | `PAY-2026-NNNNNN` | Yes (PK) | Format check; contiguous |
| account_id | TEXT | Yes | FK account | No | FK |
| payment_date | TEXT | Yes | Date | No | Not after cutoff |
| amount_paise | INTEGER | Yes | Paise, > 0 | No | Positive |
| method | TEXT | Yes | BANK_TRANSFER, UPI, CHEQUE, CARD | No | Enum |
| bank_reference | TEXT | Yes | `UTR` plus digits (synthetic) | Yes | Unique |
| status | TEXT | Yes | RECEIVED, ALLOCATED, REVERSED | No | Enum; equals latest event |

## payment_allocation
Bridge: Payment N:M Invoice. Deliberately has no unique rule on (payment_id, invoice_id), so a repeated allocation can be stored and detected.

| Field | Type | Req | Allowed values / units | Unique | Validation |
|---|---|---|---|---|---|
| allocation_id | TEXT | Yes | `ALC-2026-NNNNNN` | Yes (PK) | Format check; contiguous |
| payment_id | TEXT | Yes | FK payment | No | Payment must be ALLOCATED |
| invoice_id | TEXT | Yes | FK invoice | No | Same account as the payment; not VOID |
| allocated_paise | INTEGER | Yes | Paise, > 0 | No | Sum per payment should not exceed the payment: anomaly B if it does |
| allocated_date | TEXT | Yes | Date | No | Not before the payment or the invoice |

## dispute
Customer challenge to an invoice. Lifecycle: OPEN, UNDER_REVIEW, then RESOLVED_CREDIT, RESOLVED_NO_CREDIT or WITHDRAWN.

| Field | Type | Req | Allowed values / units | Unique | Validation |
|---|---|---|---|---|---|
| dispute_id | TEXT | Yes | `DSP-2026-NNNNNN` | Yes (PK) | Format check; contiguous |
| invoice_id | TEXT | Yes | FK invoice | No | FK |
| account_id | TEXT | Yes | FK account | No | Must equal the invoice's account |
| reason | TEXT | Yes | PRICING, QUANTITY, DAMAGED_GOODS, LATE_DELIVERY, BILLING_ERROR | No | Enum |
| opened_date | TEXT | Yes | Date | No | Not before invoice_date |
| resolved_date | TEXT | No | Date; null while open | No | Not before opened_date |
| disputed_paise | INTEGER | Yes | Paise, > 0 | No | At most the invoice total |
| credited_paise | INTEGER | Yes | Paise, >= 0; default 0 | No | Positive only for RESOLVED_CREDIT |
| status | TEXT | Yes | OPEN, UNDER_REVIEW, RESOLVED_CREDIT, RESOLVED_NO_CREDIT, WITHDRAWN | No | Enum; equals latest event |

## ar_ledger_entry
Append-only receivables sub-ledger. `amount_paise` is always positive; `entry_type` gives it meaning:
`balance = POSTED - VOIDED - APPLIED - CREDIT_MEMO`, `disputed = HOLD - RELEASE`, `collectible = balance - disputed`.

| Field | Type | Req | Allowed values / units | Unique | Validation |
|---|---|---|---|---|---|
| entry_id | TEXT | Yes | `ARL-2026-NNNNNN` | Yes (PK) | Format check; contiguous |
| invoice_id | TEXT | Yes | FK invoice | No | FK |
| entry_type | TEXT | Yes | INVOICE_POSTED, INVOICE_VOIDED, PAYMENT_APPLIED, CREDIT_MEMO, DISPUTE_HOLD, DISPUTE_RELEASE | No | Enum |
| amount_paise | INTEGER | Yes | Paise, > 0 | No | Positive |
| entry_date | TEXT | Yes | Date | No | Not after cutoff |
| source_id | TEXT | Yes | Invoice, allocation or dispute ID | No | Must resolve to a real record |

## status_event
History of every state change. Never updated in place. `entity_id` is polymorphic (it points at the table named by `entity_type`), so integrity is enforced by validation check S02 rather than a declared foreign key.

| Field | Type | Req | Allowed values / units | Unique | Validation |
|---|---|---|---|---|---|
| event_id | TEXT | Yes | `EVT-2026-NNNNNN`, chronological | Yes (PK) | Format check; contiguous |
| entity_type | TEXT | Yes | ACCOUNT, QUOTE, ORDER, SHIPMENT, INVOICE, PAYMENT, DISPUTE | No | Enum |
| entity_id | TEXT | Yes | ID of a record of that type | No | Must resolve |
| from_status | TEXT | No | Previous state; null on the first event | No | Should equal the previous event's to_status |
| to_status | TEXT | Yes | New state | No | Should be a legal transition |
| event_time | TEXT | Yes | Timestamp | No | Strictly rises per record; not after cutoff |
| actor_role | TEXT | Yes | CUSTOMER, SALES_OPS, SUPPORT_AGENT, ANALYST, SYSTEM_ADMIN, SYSTEM | No | Enum |

## finding
Detector output. Rebuilt on every run. Excluded from the source-data checksums, but checked separately for reproducibility.

| Field | Type | Req | Allowed values / units | Unique | Validation |
|---|---|---|---|---|---|
| finding_id | TEXT | Yes | `FND-2026-NNNNNN` | Yes (PK) | Assigned after sorting by rule and record |
| rule_id | TEXT | Yes | R01 to R11 | No | See `business_rules.md` |
| issue_type | TEXT | Yes | One issue type per rule | No | Matches the rule |
| severity | TEXT | Yes | HIGH, MEDIUM, LOW | No | Enum |
| source_entity | TEXT | Yes | ORDER_LINE, INVOICE, PAYMENT, ORDER, STATUS_EVENT, DISPUTE, SHIPMENT | No | Names the primary record type |
| source_id | TEXT | Yes | Primary record ID | No | Evaluation match key |
| related_ids | TEXT | Yes | JSON array of IDs | No | Valid JSON |
| rule_description | TEXT | Yes | Text | No | Non-empty |
| expected_behavior | TEXT | Yes | Text | No | Non-empty |
| observed_behavior | TEXT | Yes | Text | No | Non-empty |
| impact_type | TEXT | Yes | See `business_rules.md` | No | Impact types are never added together |
| impact_paise | INTEGER | Yes | Paise; 0 when not financial | No | Non-negative |
| delay_days | INTEGER | Yes | Days; 0 when not a delay | No | Non-negative |
| evidence | TEXT | Yes | JSON object; includes `source_events`, the IDs of the status events involved | No | Valid JSON |

## run_metadata
One row per setting for the current build. Key values: `cutoff_date`, `seed`, `scale`, `generator_version`, `anomalies_injected`.

| Field | Type | Req | Allowed values / units | Unique | Validation |
|---|---|---|---|---|---|
| key | TEXT | Yes | Setting name | Yes (PK) | None |
| value | TEXT | Yes | Setting value | No | None |

## ground_truth.csv
A file, never a database table, so the detector cannot read it. One row per expected finding.

| Field | Type | Req | Allowed values / units | Unique | Validation |
|---|---|---|---|---|---|
| gt_id | TEXT | Yes | `GT-2026-NNNNNN` (the anomaly ID) | Yes | Assigned after sorting by rule and record |
| issue_type | TEXT | Yes | One issue type per rule | No | Part of the match key |
| expected_label | TEXT | Yes | Same as issue_type | No | The label a correct detector should give |
| scenario | TEXT | Yes | Scenario code from `business_rules.md` | No | Non-empty |
| rule_id | TEXT | Yes | R01 to R11 | No | Rule expected to fire |
| source_entity | TEXT | Yes | Primary record type | No | Decides which table `primary_id` is checked against |
| primary_id | TEXT | Yes | Affected record ID | With issue_type | Must exist (check S12) |
| related_ids | TEXT | No | IDs separated by `\|` | No | Related entity references |
| expected_behavior | TEXT | Yes | Text | No | Non-empty |
| observed_behavior | TEXT | Yes | Text | No | Non-empty |
| causal_explanation | TEXT | Yes | Text | No | Says how the anomaly came to exist |
| impact_type | TEXT | Yes | Impact type, or NONE | No | Same values as `finding.impact_type` |
| expected_impact_paise | INTEGER | Yes | Paise; 0 when not financial | No | Compared with the finding's amount |
| label_source | TEXT | Yes | injected, plan, rule | No | Evaluation scores each kind separately |

## Relationships

"Lifecycle implication" is what the relationship means for state. "Effective date" is the date ordering the link must respect.

| Parent | Child | Cardinality | Optional? | Foreign key | Lifecycle implication | Effective-date rule |
|---|---|---|---|---|---|---|
| account | quote | 1:N | Account may have no quotes | quote.account_id | None | Account exists before its first quote |
| quote | quote_line | 1:N | Quote has at least one line | quote_line.quote_id | Lines fixed once sent | Same date as the quote |
| product | quote_line | 1:N | Product may be unused | quote_line.product_id | None | None |
| quote | sales_order | 1:0..1 | Only ACCEPTED quotes convert | sales_order.quote_id (unique) | Quote must be ACCEPTED first | order_date >= quote_date |
| account | sales_order | 1:N | Prospects have none | sales_order.account_id | Makes the account a CUSTOMER | As above |
| sales_order | order_line | 1:N | At least one line | order_line.order_id | Copied at creation | Same date as the order |
| quote_line | order_line | 1:0..1 | Only on converted quotes | order_line.quote_line_id (unique) | Carries the net price forward | As above |
| sales_order | shipment | 1:N | None if cancelled early | shipment.order_id | Drives FULFILLED states | shipped_date >= order_date |
| shipment | order_line | N:M via shipment_line | A line may be unshipped | shipment_line | Partial shipment when a line spreads over shipments | Only shipped rows count |
| sales_order | invoice | 1:N | None until shipped | invoice.order_id | Drives INVOICED and CLOSED | invoice_date >= covered shipped dates |
| invoice | invoice_line | 1:N | At least one line | invoice_line.invoice_id | Fixed once issued | Same date as the invoice |
| order_line | invoice_line | 1:N | A line may be unbilled | invoice_line.order_line_id | Billed quantity compared with shipped | Live invoices only |
| invoice | shipment | N:M via invoice_shipment | Unbilled shipments allowed for a time | invoice_shipment | Consolidation and duplicate evidence | invoice_date >= shipped_date |
| invoice | invoice | 1:0..1 | Only on reissues | invoice.replaces_invoice_id | The original must be VOID | Replacement dated after the original |
| account | payment | 1:N | Prospects have none | payment.account_id | None | payment_date inside the window |
| payment | invoice | N:M via payment_allocation | RECEIVED payments have none | payment_allocation | Drives PARTIALLY_PAID, PAID and ALLOCATED | allocated_date >= payment_date and invoice_date |
| invoice | dispute | 1:0..N | Most invoices have none | dispute.invoice_id | Drives DISPUTED; holds the amount | opened_date >= invoice_date |
| invoice | ar_ledger_entry | 1:N | Every invoice has at least a posting | ar_ledger_entry.invoice_id | Source of balances | entry_date <= cutoff |
| any entity | status_event | 1:N | Every record has at least one | status_event.entity_id (polymorphic) | Full state history | event_time strictly rises |
