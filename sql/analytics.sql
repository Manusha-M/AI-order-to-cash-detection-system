-- Reusable analytical views. Every number comes from source tables; nothing here is stored.
-- The cutoff lives in run_metadata, and these views are as-of that date: anything dated later
-- has not happened yet. Record status columns describe the data as generated, so moving the
-- cutoff re-ages balances but does not rewind statuses.

CREATE VIEW v_cutoff AS
SELECT value AS cutoff_date FROM run_metadata WHERE key = 'cutoff_date';

-- A live invoice is one that really bills the customer: issued, not void, dated by the cutoff.
CREATE VIEW v_live_invoice AS
SELECT i.*
FROM invoice i
CROSS JOIN v_cutoff c
WHERE i.status NOT IN ('DRAFT', 'VOID') AND i.invoice_date <= c.cutoff_date;

CREATE VIEW v_ledger_by_invoice AS
SELECT l.invoice_id,
       SUM(CASE WHEN l.entry_type = 'INVOICE_POSTED' THEN l.amount_paise ELSE 0 END)  AS posted_paise,
       SUM(CASE WHEN l.entry_type = 'INVOICE_VOIDED' THEN l.amount_paise ELSE 0 END)  AS voided_paise,
       SUM(CASE WHEN l.entry_type = 'PAYMENT_APPLIED' THEN l.amount_paise ELSE 0 END) AS applied_paise,
       SUM(CASE WHEN l.entry_type = 'CREDIT_MEMO' THEN l.amount_paise ELSE 0 END)     AS credited_paise,
       SUM(CASE WHEN l.entry_type = 'DISPUTE_HOLD' THEN l.amount_paise
                WHEN l.entry_type = 'DISPUTE_RELEASE' THEN -l.amount_paise ELSE 0 END) AS held_paise
FROM ar_ledger_entry l
CROSS JOIN v_cutoff c
WHERE l.entry_date <= c.cutoff_date
GROUP BY l.invoice_id;

-- One row per live invoice. balance = what the customer still owes. reserved = the part parked
-- behind a dispute hold, never more than the balance. collectible = what is left to chase.
CREATE VIEW v_invoice_balance AS
SELECT b.*,
       MIN(b.held_paise, MAX(b.balance_paise, 0)) AS reserved_paise,
       b.balance_paise - MIN(b.held_paise, MAX(b.balance_paise, 0)) AS collectible_paise
FROM (SELECT i.invoice_id, i.order_id, i.account_id, i.invoice_date, i.due_date, i.status, i.total_paise,
             l.applied_paise, l.credited_paise, l.held_paise,
             l.posted_paise - l.voided_paise - l.applied_paise - l.credited_paise AS balance_paise,
             CAST(julianday(c.cutoff_date) - julianday(i.due_date) AS INTEGER) AS days_past_due
      FROM v_live_invoice i
      JOIN v_ledger_by_invoice l ON l.invoice_id = i.invoice_id
      CROSS JOIN v_cutoff c) b;

CREATE VIEW v_invoice_aging AS
SELECT *,
       CASE WHEN days_past_due <= 0 THEN '0 Not due'
            WHEN days_past_due <= 30 THEN '1 1-30 days'
            WHEN days_past_due <= 60 THEN '2 31-60 days'
            WHEN days_past_due <= 90 THEN '3 61-90 days'
            WHEN days_past_due <= 120 THEN '4 91-120 days'
            ELSE '5 Over 120 days' END AS aging_bucket
FROM v_invoice_balance;

-- Ordered, shipped and billed quantity side by side for each order line.
-- Only SHIPPED or DELIVERED shipments count as fulfilled; PLANNED ones do not.
CREATE VIEW v_order_line_position AS
SELECT ol.order_line_id, ol.order_id, ol.quantity AS ordered_qty, ol.unit_price_paise,
       COALESCE(s.shipped_qty, 0) AS shipped_qty,
       COALESCE(b.billed_qty, 0) AS billed_qty,
       COALESCE(b.billed_paise, 0) AS billed_paise
FROM order_line ol
LEFT JOIN (SELECT sl.order_line_id, SUM(sl.quantity) AS shipped_qty
           FROM shipment_line sl
           JOIN shipment sh ON sh.shipment_id = sl.shipment_id
           CROSS JOIN v_cutoff c
           WHERE sh.status IN ('SHIPPED', 'DELIVERED') AND sh.shipped_date <= c.cutoff_date
           GROUP BY sl.order_line_id) s ON s.order_line_id = ol.order_line_id
LEFT JOIN (SELECT il.order_line_id, SUM(il.quantity) AS billed_qty, SUM(il.line_total_paise) AS billed_paise
           FROM invoice_line il
           JOIN v_live_invoice i ON i.invoice_id = il.invoice_id
           GROUP BY il.order_line_id) b ON b.order_line_id = ol.order_line_id;

CREATE VIEW v_order_timeline AS
SELECT o.order_id, o.order_date, o.status,
       MIN(s.shipped_date) AS first_shipped_date,
       MAX(s.shipped_date) AS last_shipped_date
FROM sales_order o
LEFT JOIN shipment s ON s.order_id = o.order_id AND s.status IN ('SHIPPED', 'DELIVERED')
GROUP BY o.order_id;

-- When each shipped shipment was first billed. A reissue keeps the date of the invoice it
-- replaced, because the customer was billed on time and the correction came later.
-- first_invoice_date is NULL for a shipment no live invoice covers.
CREATE VIEW v_shipment_billing AS
SELECT s.shipment_id, s.order_id, s.shipped_date,
       MIN(COALESCE(original.invoice_date, i.invoice_date)) AS first_invoice_date,
       CAST(julianday(MIN(COALESCE(original.invoice_date, i.invoice_date))) - julianday(s.shipped_date) AS INTEGER)
           AS lag_days
FROM shipment s
LEFT JOIN invoice_shipment b ON b.shipment_id = s.shipment_id
LEFT JOIN v_live_invoice i ON i.invoice_id = b.invoice_id
LEFT JOIN invoice original ON original.invoice_id = i.replaces_invoice_id
WHERE s.status IN ('SHIPPED', 'DELIVERED') AND s.shipped_date IS NOT NULL
GROUP BY s.shipment_id;
