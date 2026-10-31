"""Financial metrics and reconciliation identities, all computed from source tables.

The identities are the proof that balances reconcile. Each must net to zero, and each
compares two independent sources: the ledger against the transaction tables, cash against
allocations, and billing against shipments. A check whose two sides come from one table
proves nothing, so REC-6, which is only a partition check, is labelled as such.
"""
from __future__ import annotations

import sqlite3
from datetime import timedelta
from statistics import mean, median

from . import config as cfg
from .database import cutoff_of


def _scalar(conn: sqlite3.Connection, sql: str, *params) -> int:
    return conn.execute(sql, params).fetchone()[0] or 0


def _impact(conn: sqlite3.Connection, issue_type: str) -> int:
    return _scalar(conn, "SELECT SUM(impact_paise) FROM finding WHERE issue_type = ?", issue_type)


def _percentile(values: list[int], share: float) -> int:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(share * len(ordered)))]


def _delay_stats(values: list[int], sla: int | None) -> dict:
    if not values:
        return {"count": 0}
    stats = {"count": len(values), "mean_days": round(mean(values), 2), "median_days": median(values),
             "p90_days": _percentile(values, 0.9), "max_days": max(values)}
    if sla is not None:
        stats["sla_days"] = sla
        stats["over_sla"] = sum(1 for v in values if v > sla)
    return stats


def compute_delays(conn: sqlite3.Connection) -> dict:
    order_to_fulfil = [r[0] for r in conn.execute(
        """SELECT CAST(julianday(t.last_shipped_date) - julianday(t.order_date) AS INTEGER)
           FROM v_order_timeline t WHERE t.status IN ('FULFILLED', 'INVOICED', 'CLOSED')
             AND t.last_shipped_date IS NOT NULL""")]
    ship_to_invoice = [r[0] for r in conn.execute(
        "SELECT lag_days FROM v_shipment_billing WHERE lag_days IS NOT NULL")]
    invoice_to_payment = [r[0] for r in conn.execute(
        """SELECT CAST(julianday(MAX(a.allocated_date)) - julianday(i.invoice_date) AS INTEGER)
           FROM invoice i JOIN payment_allocation a ON a.invoice_id = i.invoice_id
           WHERE i.status = 'PAID' GROUP BY i.invoice_id""")]
    return {
        "order_to_fulfilment": _delay_stats(order_to_fulfil, cfg.SLA_ORDER_TO_FULFILMENT_DAYS),
        "fulfilment_to_invoice": _delay_stats(ship_to_invoice, cfg.SLA_SHIPMENT_TO_INVOICE_DAYS),
        "invoice_to_final_payment": _delay_stats(invoice_to_payment, None),
    }


def classify_receivables(conn: sqlite3.Connection) -> dict:
    """Give every rupee of outstanding receivables exactly one class.

    Short-paid and long-overdue findings can sit on the same invoice, so adding their
    impacts would double-count. This precedence (disputed, duplicate billing, long overdue,
    short paid, other overdue, not due) is the figure to use for a non-overlapping split.
    """
    flagged = {(r["issue_type"], r["source_id"]) for r in conn.execute(
        """SELECT issue_type, source_id FROM finding
           WHERE issue_type IN ('LONG_OVERDUE', 'SHORT_PAYMENT', 'DUPLICATE_INVOICE')""")}
    classes = {"disputed_on_hold": 0, "duplicate_billing": 0, "long_overdue": 0, "short_paid": 0,
               "other_overdue": 0, "not_due": 0}
    for row in conn.execute("SELECT invoice_id, reserved_paise, collectible_paise, days_past_due FROM v_invoice_balance"):
        classes["disputed_on_hold"] += row["reserved_paise"]
        if ("DUPLICATE_INVOICE", row["invoice_id"]) in flagged:
            key = "duplicate_billing"
        elif ("LONG_OVERDUE", row["invoice_id"]) in flagged:
            key = "long_overdue"
        elif ("SHORT_PAYMENT", row["invoice_id"]) in flagged:
            key = "short_paid"
        else:
            key = "other_overdue" if row["days_past_due"] > 0 else "not_due"
        classes[key] += row["collectible_paise"]
    return classes


def compute_metrics(conn: sqlite3.Connection) -> dict:
    quoted = _scalar(conn, "SELECT SUM(total_paise) FROM quote")
    accepted = _scalar(conn, "SELECT SUM(total_paise) FROM quote WHERE status = 'ACCEPTED'")
    ordered = _scalar(conn, "SELECT SUM(total_paise) FROM sales_order WHERE status <> 'CANCELLED'")
    fulfilled = _scalar(conn, "SELECT SUM(shipped_qty * unit_price_paise) FROM v_order_line_position")
    invoiced = _scalar(conn, "SELECT SUM(total_paise) FROM v_live_invoice")
    cash_received = _scalar(conn, "SELECT SUM(amount_paise) FROM payment WHERE status <> 'REVERSED'")
    cash_reversed = _scalar(conn, "SELECT SUM(amount_paise) FROM payment WHERE status = 'REVERSED'")
    applied = _scalar(conn, "SELECT SUM(allocated_paise) FROM payment_allocation")
    unapplied = _unapplied_cash(conn)
    credits = _scalar(conn, "SELECT SUM(amount_paise) FROM ar_ledger_entry WHERE entry_type = 'CREDIT_MEMO'")
    outstanding = _scalar(conn, "SELECT SUM(balance_paise) FROM v_invoice_balance")
    disputed = _scalar(conn, "SELECT SUM(reserved_paise) FROM v_invoice_balance")
    overdue = _scalar(conn, "SELECT SUM(collectible_paise) FROM v_invoice_balance "
                            "WHERE days_past_due > 0 AND collectible_paise > 0")
    aging = [dict(r) for r in conn.execute(
        """SELECT aging_bucket, COUNT(*) AS invoices, SUM(collectible_paise) AS collectible_paise
           FROM v_invoice_aging WHERE collectible_paise > 0 GROUP BY aging_bucket ORDER BY aging_bucket""")]
    return {
        "funnel_paise": {"quoted": quoted, "accepted": accepted, "ordered": ordered, "fulfilled": fulfilled,
                         "invoiced": invoiced, "cash_received": cash_received, "outstanding_ar": outstanding},
        "cash_paise": {"cash_received": cash_received, "cash_reversed": cash_reversed, "applied_to_invoices": applied,
                       "unapplied_cash": unapplied, "credits_issued": credits},
        "receivables_paise": {"outstanding": outstanding, "disputed_on_hold": disputed,
                              "collectible": outstanding - disputed, "overdue_collectible": overdue,
                              "ar_understated_by_false_allocation": _impact(conn, "DUPLICATE_ALLOCATION")},
        "aging": aging,
        "receivable_classes_paise": classify_receivables(conn),
        "leakage_paise": {
            "underbilled_revenue": _impact(conn, "UNDERBILLING"),
            "overbilled_exposure": _impact(conn, "OVERBILLING"),
            "duplicate_billing_exposure": _impact(conn, "DUPLICATE_INVOICE"),
            "payment_allocation_discrepancy": _impact(conn, "DUPLICATE_ALLOCATION"),
            "closed_order_unpaid": _impact(conn, "CLOSED_ORDER_UNPAID"),
            "dispute_not_reserved": _impact(conn, "DISPUTE_NOT_IN_AR"),
            "short_paid": _impact(conn, "SHORT_PAYMENT"),
            "long_overdue": _impact(conn, "LONG_OVERDUE"),
        },
        "delays": compute_delays(conn),
    }


def _unapplied_cash(conn: sqlite3.Connection) -> int:
    """Received cash not yet matched to an invoice, including the unused part of a payment."""
    return _scalar(conn, """SELECT SUM(MAX(p.amount_paise - COALESCE(a.allocated, 0), 0))
                            FROM payment p
                            LEFT JOIN (SELECT payment_id, SUM(allocated_paise) AS allocated
                                       FROM payment_allocation GROUP BY payment_id) a ON a.payment_id = p.payment_id
                            WHERE p.status <> 'REVERSED'""")


def _ledger_versus_allocations(conn: sqlite3.Connection) -> int:
    """Sum of per-invoice gaps, so money moved between invoices cannot cancel out."""
    return _scalar(conn, """SELECT SUM(ABS(COALESCE(l.applied, 0) - COALESCE(a.allocated, 0)))
                            FROM invoice i
                            LEFT JOIN (SELECT invoice_id, SUM(amount_paise) AS applied FROM ar_ledger_entry
                                       WHERE entry_type = 'PAYMENT_APPLIED' GROUP BY invoice_id) l
                                   ON l.invoice_id = i.invoice_id
                            LEFT JOIN (SELECT invoice_id, SUM(allocated_paise) AS allocated FROM payment_allocation
                                       GROUP BY invoice_id) a ON a.invoice_id = i.invoice_id""")


def _ledger_versus_source_balance(conn: sqlite3.Connection) -> int:
    """Per-invoice gap between the ledger balance and the balance rebuilt from source tables."""
    return _scalar(conn, """SELECT SUM(ABS(b.balance_paise
                                           - (b.total_paise - COALESCE(a.allocated, 0) - COALESCE(d.credited, 0))))
                            FROM v_invoice_balance b
                            LEFT JOIN (SELECT invoice_id, SUM(allocated_paise) AS allocated FROM payment_allocation
                                       GROUP BY invoice_id) a ON a.invoice_id = b.invoice_id
                            LEFT JOIN (SELECT invoice_id, SUM(credited_paise) AS credited FROM dispute
                                       GROUP BY invoice_id) d ON d.invoice_id = b.invoice_id""")


def reconcile(conn: sqlite3.Connection) -> list[dict]:
    """Return each reconciliation identity with its left side, right side and difference."""
    cutoff = cutoff_of(conn)
    posted = _scalar(conn, "SELECT SUM(amount_paise) FROM ar_ledger_entry WHERE entry_type = 'INVOICE_POSTED'")
    voided = _scalar(conn, "SELECT SUM(amount_paise) FROM ar_ledger_entry WHERE entry_type = 'INVOICE_VOIDED'")
    invoiced = _scalar(conn, "SELECT SUM(total_paise) FROM v_live_invoice")
    allocated = _scalar(conn, "SELECT SUM(allocated_paise) FROM payment_allocation")
    outstanding = _scalar(conn, "SELECT SUM(balance_paise) FROM v_invoice_balance")
    cash = _scalar(conn, "SELECT SUM(amount_paise) FROM payment WHERE status <> 'REVERSED'")

    # In-grace value comes from shipments no live invoice covers, not from the detector, so a
    # missed or invented underbilling finding stops the bridge closing.
    grace_start = (cutoff - timedelta(days=cfg.UNBILLED_GRACE_DAYS)).isoformat()
    in_grace = _scalar(conn, """SELECT SUM(sl.quantity * ol.unit_price_paise)
                                FROM v_shipment_billing b
                                JOIN shipment_line sl ON sl.shipment_id = b.shipment_id
                                JOIN order_line ol ON ol.order_line_id = sl.order_line_id
                                WHERE b.first_invoice_date IS NULL AND b.shipped_date > ?""", grace_start)
    fulfilled = _scalar(conn, "SELECT SUM(shipped_qty * unit_price_paise) FROM v_order_line_position")
    bridge = (fulfilled + _impact(conn, "DUPLICATE_INVOICE") + _impact(conn, "OVERBILLING")
              - _impact(conn, "UNDERBILLING") - in_grace)

    identities = [
        ("REC-1", "Live invoice headers equal ledger postings net of voids", invoiced, posted - voided),
        ("REC-2", "Per invoice: ledger payment entries equal allocations (sum of gaps)",
         _ledger_versus_allocations(conn), 0),
        ("REC-3", "Per invoice: ledger balance = total - allocations - dispute credits from source tables (sum of gaps)",
         _ledger_versus_source_balance(conn), 0),
        ("REC-4", "Cash + over-allocation found by the detector = allocations + unapplied cash",
         cash + _impact(conn, "DUPLICATE_ALLOCATION"), allocated + _unapplied_cash(conn)),
        ("REC-5", "Billing bridge: fulfilled + duplicates + overbilled - underbilled - awaiting invoice = invoiced",
         bridge, invoiced),
        ("REC-6", "Partition check: receivable classes add up to outstanding, each rupee in one class",
         sum(classify_receivables(conn).values()), outstanding),
    ]
    return [{"id": i, "description": d, "left_paise": a, "right_paise": b, "difference_paise": a - b,
             "status": "PASS" if a == b else "FAIL"} for i, d, a, b in identities]
