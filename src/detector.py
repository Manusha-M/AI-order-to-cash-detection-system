"""Rule-based exception detector.

Reads only transactional tables and event history. It never opens the ground-truth file:
the evaluation step compares results afterwards. Each rule is a small function returning
findings, so a reviewer can read one business rule at a time.

Money is reported under an impact_type, and impact types are never added together:
overbilling, unpaid receivables and lost revenue are different things.
"""
from __future__ import annotations

import json
import sqlite3
from collections import Counter, defaultdict
from datetime import date, timedelta

from . import config as cfg
from .database import cutoff_of
from .lifecycle import is_legal, skipped_states

RULES = {
    "R01": ("OVERBILLING", "Billed quantity exceeds what shipped, or billed price exceeds the order price."),
    "R02": ("UNDERBILLING", "Shipped goods unbilled past the grace period, short on their invoice, or below the order price."),
    "R03": ("DUPLICATE_INVOICE", "A second live invoice repeats the same lines for already-billed goods."),
    "R04": ("DUPLICATE_ALLOCATION", "Allocations exceed the payment amount, or an identical allocation repeats."),
    "R05": ("CLOSED_ORDER_UNPAID", "A closed order still has an unpaid invoice."),
    "R06": ("ILLEGAL_TRANSITION", "A status event is not allowed by the lifecycle state machine."),
    "R07": ("DISPUTE_NOT_IN_AR", "A dispute's hold or credit is not reflected in the receivables ledger."),
    "R08": ("SHORT_PAYMENT", "Part-paid invoice with no recent activity and a balance above tolerance."),
    "R09": ("LONG_OVERDUE", f"Collectible balance more than {cfg.LONG_OVERDUE_DAYS} days past due."),
    "R10": ("FULFILMENT_DELAY", f"Order not fully shipped within {cfg.SLA_ORDER_TO_FULFILMENT_DAYS} days."),
    "R11": ("INVOICING_DELAY", f"Shipment not invoiced within {cfg.SLA_SHIPMENT_TO_INVOICE_DAYS} days."),
}


def rupees(paise: int) -> str:
    return f"Rs {paise / 100:,.2f}"


def severity_for_money(paise: int) -> str:
    if paise >= cfg.SEVERITY_HIGH_PAISE:
        return "HIGH"
    return "MEDIUM" if paise >= cfg.SEVERITY_MEDIUM_PAISE else "LOW"


def severity_for_delay(days: int, sla: int) -> str:
    return "HIGH" if days >= 2 * sla else "MEDIUM"


def finding(rule_id: str, severity: str, entity: str, source_id: str, related: list[str], expected: str,
            observed: str, impact_type: str, impact: int, evidence: dict, delay_days: int = 0) -> dict:
    issue_type, description = RULES[rule_id]
    return {"finding_id": None, "rule_id": rule_id, "issue_type": issue_type, "severity": severity,
            "source_entity": entity, "source_id": source_id, "related_ids": json.dumps(sorted(set(related))),
            "rule_description": description, "expected_behavior": expected, "observed_behavior": observed,
            "impact_type": impact_type, "impact_paise": impact, "delay_days": delay_days,
            "evidence": json.dumps(evidence, sort_keys=True)}


class Detector:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.cutoff = cutoff_of(conn)
        self.positions = {r["order_line_id"]: dict(r) for r in conn.execute("SELECT * FROM v_order_line_position")}
        self.invoice_lines = defaultdict(list)
        self.billing_by_line = defaultdict(list)
        for row in conn.execute(
            """SELECT il.*, i.order_id, i.invoice_date FROM invoice_line il
               JOIN v_live_invoice i ON i.invoice_id = il.invoice_id
               ORDER BY il.invoice_line_id"""
        ):
            self.invoice_lines[row["invoice_id"]].append(dict(row))
            self.billing_by_line[row["order_line_id"]].append(dict(row))
        self.covers = defaultdict(set)
        for row in conn.execute(
            """SELECT b.invoice_id, b.shipment_id FROM invoice_shipment b
               JOIN v_live_invoice i ON i.invoice_id = b.invoice_id"""
        ):
            self.covers[row["invoice_id"]].add(row["shipment_id"])
        self.shipped_by_shipment: dict[tuple, int] = defaultdict(int)
        for row in conn.execute(
            """SELECT sl.shipment_id, sl.order_line_id, sl.quantity FROM shipment_line sl
               JOIN shipment s ON s.shipment_id = sl.shipment_id
               WHERE s.status IN ('SHIPPED', 'DELIVERED')"""
        ):
            self.shipped_by_shipment[(row["shipment_id"], row["order_line_id"])] = row["quantity"]
        self.duplicate_qty: dict[str, int] = defaultdict(int)
        self.repeat_invoices: set[str] = set()

    def billing_of(self, order_line_id: str) -> list[dict]:
        """Invoice lines for an order line, leaving out invoices the duplicate rule already reported."""
        return [l for l in self.billing_by_line[order_line_id] if l["invoice_id"] not in self.repeat_invoices]

    def bills_past_shared_shipments(self, candidate: str, kept: list[str], fingerprint: tuple) -> str | None:
        """Return the earlier invoice this one repeats, if together they bill more than shipped.

        Sharing a shipment proves nothing alone: one shipment of 10 can fairly be billed as 5 + 5.
        """
        sharing = [i for i in kept if self.covers[candidate] & self.covers[i]]
        if not sharing:
            return None
        shipments = set(self.covers[candidate]).union(*(self.covers[i] for i in sharing))
        for order_line_id, quantity, _ in fingerprint:
            carried = sum(self.shipped_by_shipment[(s, order_line_id)] for s in shipments)
            if quantity * (len(sharing) + 1) <= carried:
                return None
        return sharing[0]

    def own_shipments_justify(self, invoice_id: str, fingerprint: tuple) -> bool:
        """True when the shipments linked to this invoice carried the quantity it bills."""
        return all(sum(self.shipped_by_shipment[(s, order_line_id)] for s in self.covers[invoice_id]) >= quantity
                   for order_line_id, quantity, _ in fingerprint)

    def net_billed_qty(self, order_line_id: str) -> int:
        """Billed quantity after removing what the duplicate-invoice rule already explains."""
        return self.positions[order_line_id]["billed_qty"] - self.duplicate_qty[order_line_id]

    def rule_duplicate_invoice(self) -> list[dict]:
        groups = defaultdict(list)
        for invoice_id, lines in self.invoice_lines.items():
            fingerprint = tuple(sorted((l["order_line_id"], l["quantity"], l["unit_price_paise"]) for l in lines))
            groups[(lines[0]["order_id"], fingerprint)].append(invoice_id)

        results = []
        for (order_id, fingerprint), invoice_ids in sorted(groups.items()):
            if len(invoice_ids) < 2:
                continue
            invoice_ids.sort(key=lambda i: (self.invoice_lines[i][0]["invoice_date"], i))
            # Identical lines alone are not enough: two equal shipments billed separately are valid.
            # A repeat needs proof. Strongest first: it re-bills a shipment that cannot carry both
            # invoices. Failing that, the billed excess must be big enough to hold the whole invoice.
            excess = {ol: self.positions[ol]["billed_qty"] - self.positions[ol]["shipped_qty"]
                      for ol, _, _ in fingerprint}
            repeats = {}
            kept: list[str] = []
            for candidate in invoice_ids:
                original = self.bills_past_shared_shipments(candidate, kept, fingerprint)
                if original is None:
                    kept.append(candidate)
                else:
                    repeats[candidate] = original
                    for order_line_id, quantity, _ in fingerprint:
                        excess[order_line_id] -= quantity
            for position in range(len(invoice_ids) - 1, 0, -1):  # newest first, so excess is spent once
                candidate = invoice_ids[position]
                if candidate in repeats or self.own_shipments_justify(candidate, fingerprint):
                    continue
                if not all(excess[ol] >= qty for ol, qty, _ in fingerprint):
                    continue
                repeats[candidate] = invoice_ids[0]
                for order_line_id, quantity, _ in fingerprint:
                    excess[order_line_id] -= quantity

            for candidate, original in repeats.items():
                total = sum(l["line_total_paise"] for l in self.invoice_lines[candidate])
                self.repeat_invoices.add(candidate)
                for order_line_id, quantity, _ in fingerprint:
                    self.duplicate_qty[order_line_id] += quantity
                results.append(finding(
                    "R03", severity_for_money(total), "INVOICE", candidate, [original, order_id],
                    "Each shipped quantity is billed once.",
                    f"{candidate} repeats the lines of {original} on order {order_id}.",
                    "DUPLICATE_BILLING_EXPOSURE", total,
                    {"original_invoice": original, "duplicate_invoice": candidate,
                     "shared_shipments": sorted(self.covers[candidate] & self.covers[original]),
                     "lines": [list(item) for item in fingerprint]}))
        return results

    def rule_overbilling(self) -> list[dict]:
        credits = {r["invoice_id"]: r["credited_paise"] for r in self.conn.execute(
            "SELECT invoice_id, credited_paise FROM v_invoice_balance")}
        results = []
        for order_line_id, position in sorted(self.positions.items()):
            shipped = position["shipped_qty"]
            excess_qty = max(0, self.net_billed_qty(order_line_id) - shipped)
            price = position["unit_price_paise"]
            billing = self.billing_of(order_line_id)
            price_excess = sum(l["quantity"] * (l["unit_price_paise"] - price)
                               for l in billing if l["unit_price_paise"] > price)
            impact = excess_qty * price + price_excess
            if impact <= 0:
                continue
            invoices = sorted({l["invoice_id"] for l in billing})
            invoice_lines = sorted(l["invoice_line_id"] for l in billing)
            shipments = sorted(s for s, line in self.shipped_by_shipment if line == order_line_id)
            results.append(finding(
                "R01", severity_for_money(impact), "ORDER_LINE", order_line_id,
                invoices + invoice_lines + shipments + [position["order_id"]],
                "Billed quantity must not exceed fulfilled quantity, and price must match the order.",
                f"Billed {position['billed_qty']} against {shipped} shipped ({excess_qty} excess).",
                "OVERBILLED_EXPOSURE", impact,
                {"ordered_qty": position["ordered_qty"], "shipped_qty": shipped, "billed_qty": position["billed_qty"],
                 "duplicate_qty_excluded": self.duplicate_qty[order_line_id], "excess_qty": excess_qty,
                 "order_unit_price_paise": price, "invoices": invoices, "invoice_lines": invoice_lines,
                 "shipments": shipments,
                 # Dispute credits sit on the invoice, not the line, so they are shown rather than netted.
                 "credits_on_invoices_paise": sum(credits.get(i, 0) for i in invoices)}))
        return results

    def awaiting_invoice(self) -> dict[str, int]:
        """Quantity on recent shipments no live invoice covers yet: normal timing, not leakage."""
        covered = set().union(*self.covers.values())
        grace_start = (self.cutoff - timedelta(days=cfg.UNBILLED_GRACE_DAYS)).isoformat()
        waiting: dict[str, int] = defaultdict(int)
        for row in self.conn.execute(
            """SELECT sl.shipment_id, sl.order_line_id, sl.quantity FROM shipment_line sl
               JOIN shipment s ON s.shipment_id = sl.shipment_id
               WHERE s.status IN ('SHIPPED', 'DELIVERED') AND s.shipped_date > ?""", (grace_start,)):
            if row["shipment_id"] not in covered:
                waiting[row["order_line_id"]] += row["quantity"]
        return waiting

    def rule_underbilling(self) -> list[dict]:
        waiting = self.awaiting_invoice()
        results = []
        for order_line_id, position in sorted(self.positions.items()):
            price = position["unit_price_paise"]
            unbilled_qty = max(0, position["shipped_qty"] - self.net_billed_qty(order_line_id))
            short_qty = max(0, unbilled_qty - waiting[order_line_id])
            billing = self.billing_of(order_line_id)
            price_gap = sum(l["quantity"] * (price - l["unit_price_paise"])
                            for l in billing if l["unit_price_paise"] < price)
            impact = short_qty * price + price_gap
            if impact <= 0:
                continue
            invoices = sorted({l["invoice_id"] for l in billing})
            results.append(finding(
                "R02", severity_for_money(impact), "ORDER_LINE", order_line_id, invoices + [position["order_id"]],
                "Fulfilled quantity must be billed in full at the order price.",
                f"{short_qty} shipped units not billed and not awaiting an invoice; "
                f"price shortfall {rupees(price_gap)}.",
                "UNDERBILLED_REVENUE", impact,
                {"shipped_qty": position["shipped_qty"], "awaiting_invoice_qty": waiting[order_line_id],
                 "billed_qty": position["billed_qty"], "unbilled_qty": short_qty, "price_gap_paise": price_gap,
                 "order_unit_price_paise": price, "invoices": invoices}))
        return results

    def rule_duplicate_allocation(self) -> list[dict]:
        amounts = {r["payment_id"]: r["amount_paise"] for r in self.conn.execute(
            "SELECT payment_id, amount_paise FROM payment")}
        by_payment = defaultdict(list)
        for row in self.conn.execute("SELECT * FROM payment_allocation ORDER BY allocation_id"):
            by_payment[row["payment_id"]].append(dict(row))

        results = []
        for payment_id in sorted(by_payment):
            allocations = by_payment[payment_id]
            amount = amounts[payment_id]
            allocated = sum(a["allocated_paise"] for a in allocations)
            excess = max(0, allocated - amount)
            rows = Counter((a["invoice_id"], a["allocated_paise"], a["allocated_date"]) for a in allocations)
            repeated = max(rows.values()) > 1
            if not excess and not repeated:
                continue
            invoices = sorted({a["invoice_id"] for a in allocations})
            if repeated:
                pattern = "with the same allocation entered twice"
            elif len(allocations) == 1:
                pattern = "in a single allocation larger than the payment"
            else:
                pattern = "across more than one invoice"
            results.append(finding(
                "R04", severity_for_money(excess), "PAYMENT", payment_id,
                invoices + [a["allocation_id"] for a in allocations],
                "Allocations must not exceed the payment, and each should be entered once.",
                f"{rupees(allocated)} allocated from a {rupees(amount)} payment, {pattern}.",
                "PAYMENT_ALLOCATION_DISCREPANCY", excess,
                {"payment_amount_paise": amount, "allocated_paise": allocated, "allocations": allocations}))
        return results

    def rule_closed_order_unpaid(self) -> list[dict]:
        rows = self.conn.execute(
            """SELECT o.order_id, b.invoice_id, b.balance_paise FROM sales_order o
               JOIN v_invoice_balance b ON b.order_id = o.order_id
               WHERE o.status = 'CLOSED' AND b.balance_paise > ? ORDER BY o.order_id, b.invoice_id""",
            (cfg.BALANCE_TOLERANCE_PAISE,)).fetchall()
        by_order = defaultdict(list)
        for row in rows:
            if row["invoice_id"] not in self.repeat_invoices:  # a duplicate should be cancelled, not collected
                by_order[row["order_id"]].append(dict(row))
        results = []
        for order_id, invoices in by_order.items():
            impact = sum(i["balance_paise"] for i in invoices)
            ids = [i["invoice_id"] for i in invoices]
            results.append(finding(
                "R05", "HIGH", "ORDER", order_id, ids,
                "An order may close only when every invoice on it is settled.",
                f"Order is CLOSED with {rupees(impact)} unpaid on {', '.join(ids)}.",
                "UNCOLLECTED_RECEIVABLE", impact,
                {"unpaid_invoices": [{"invoice_id": i["invoice_id"], "balance_paise": i["balance_paise"]}
                                     for i in invoices]}))
        return results

    def rule_illegal_transition(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM status_event ORDER BY entity_type, entity_id, event_time, event_id").fetchall()
        results = []
        previous = None
        for row in rows:
            same_entity = (previous is not None and previous["entity_type"] == row["entity_type"]
                           and previous["entity_id"] == row["entity_id"])
            expected_from = previous["to_status"] if same_entity else None
            legal = is_legal(row["entity_type"], row["from_status"], row["to_status"])
            if not legal or row["from_status"] != expected_from:
                skipped = skipped_states(row["entity_type"], expected_from, row["to_status"])
                what = (f"skipping {', '.join(skipped)}" if skipped else "with no legal route")
                results.append(finding(
                    "R06", "MEDIUM", "STATUS_EVENT", row["event_id"], [row["entity_id"]],
                    f"{row['entity_type']} must follow its documented lifecycle.",
                    f"{row['entity_id']} moved {row['from_status']} -> {row['to_status']}, {what}.",
                    "NONE", 0,
                    {"entity_type": row["entity_type"], "entity_id": row["entity_id"],
                     "from_status": row["from_status"], "to_status": row["to_status"],
                     "previous_status": expected_from, "skipped_states": skipped or [],
                     "event_time": row["event_time"]}))
            previous = row
        return results

    def rule_dispute_not_in_ar(self) -> list[dict]:
        rows = self.conn.execute(
            """SELECT d.*,
                      COALESCE(SUM(CASE WHEN l.entry_type = 'DISPUTE_HOLD' THEN l.amount_paise END), 0) AS hold,
                      COALESCE(SUM(CASE WHEN l.entry_type = 'DISPUTE_RELEASE' THEN l.amount_paise END), 0) AS released,
                      COALESCE(SUM(CASE WHEN l.entry_type = 'CREDIT_MEMO' THEN l.amount_paise END), 0) AS credited
               FROM dispute d
               LEFT JOIN ar_ledger_entry l ON l.source_id = d.dispute_id AND l.invoice_id = d.invoice_id
               GROUP BY d.dispute_id ORDER BY d.dispute_id""").fetchall()
        balances = {r["invoice_id"]: r["balance_paise"] for r in self.conn.execute(
            "SELECT invoice_id, balance_paise FROM v_invoice_balance")}
        results = []
        for row in rows:
            is_open = row["status"] in ("OPEN", "UNDER_REVIEW")
            expected_hold = row["disputed_paise"] if is_open else 0
            actual_hold = row["hold"] - row["released"]
            hold_gap = expected_hold - actual_hold
            credit_gap = row["credited_paise"] - row["credited"]
            # A fully paid invoice can be disputed too: with nothing collectible, its hold overstates nothing.
            balance = balances.get(row["invoice_id"], 0)
            over_hold = max(0, actual_hold - balance) if is_open and balance > 0 else 0
            if hold_gap == 0 and credit_gap == 0 and over_hold == 0:
                continue
            impact = abs(hold_gap) + abs(credit_gap) + over_hold
            results.append(finding(
                "R07", severity_for_money(impact), "DISPUTE", row["dispute_id"], [row["invoice_id"]],
                "An open dispute holds its full amount out of collectible AR; a credit must be posted as a credit memo.",
                f"Status {row['status']}: ledger holds {rupees(actual_hold)} against {rupees(expected_hold)} expected; "
                f"credit memos {rupees(row['credited'])} against {rupees(row['credited_paise'])} granted.",
                "DISPUTED_NOT_RESERVED", impact,
                {"dispute_status": row["status"], "disputed_paise": row["disputed_paise"],
                 "ledger_hold_paise": actual_hold, "hold_above_balance_paise": over_hold,
                 "credited_paise": row["credited_paise"], "ledger_credit_paise": row["credited"]}))
        return results

    def rule_short_payment(self) -> list[dict]:
        rows = self.conn.execute(
            """SELECT b.*, a.last_payment, d.last_dispute
               FROM v_invoice_balance b
               JOIN (SELECT invoice_id, MAX(allocated_date) AS last_payment
                     FROM payment_allocation GROUP BY invoice_id) a ON a.invoice_id = b.invoice_id
               LEFT JOIN (SELECT invoice_id, MAX(MAX(opened_date), MAX(COALESCE(resolved_date, ''))) AS last_dispute
                          FROM dispute GROUP BY invoice_id) d ON d.invoice_id = b.invoice_id
               WHERE b.collectible_paise > ? AND b.days_past_due > ?
               ORDER BY b.invoice_id""",
            (cfg.BALANCE_TOLERANCE_PAISE, cfg.SHORT_PAY_MIN_DAYS_PAST_DUE)).fetchall()
        stale_before = self.cutoff - timedelta(days=cfg.SHORT_PAY_STALE_DAYS)
        results = []
        for row in rows:
            last_activity = date.fromisoformat(max(row["last_payment"], row["last_dispute"] or ""))
            if last_activity > stale_before or row["invoice_id"] in self.repeat_invoices:
                continue  # instalments are still arriving, or a dispute only just moved
            impact = row["collectible_paise"]
            results.append(finding(
                "R08", severity_for_money(impact), "INVOICE", row["invoice_id"], [row["order_id"]],
                "A customer who starts paying should clear the invoice.",
                f"{rupees(row['applied_paise'])} paid of {rupees(row['total_paise'])}; "
                f"no activity since {last_activity}.",
                "SHORT_PAID_RECEIVABLE", impact,
                {"total_paise": row["total_paise"], "applied_paise": row["applied_paise"],
                 "credited_paise": row["credited_paise"], "collectible_paise": impact,
                 "days_past_due": row["days_past_due"], "last_activity": last_activity.isoformat()}))
        return results

    def rule_long_overdue(self) -> list[dict]:
        rows = self.conn.execute(
            """SELECT * FROM v_invoice_balance WHERE collectible_paise > ? AND days_past_due > ?
               ORDER BY invoice_id""", (cfg.BALANCE_TOLERANCE_PAISE, cfg.LONG_OVERDUE_DAYS)).fetchall()
        return [finding(
            "R09", severity_for_money(r["collectible_paise"]), "INVOICE", r["invoice_id"], [r["order_id"]],
            f"Balances should not stay unpaid more than {cfg.LONG_OVERDUE_DAYS} days past due.",
            f"{rupees(r['collectible_paise'])} is {r['days_past_due']} days past due at {self.cutoff}.",
            "OVERDUE_RECEIVABLE", r["collectible_paise"],
            {"due_date": r["due_date"], "cutoff": self.cutoff.isoformat(), "days_past_due": r["days_past_due"],
             "total_paise": r["total_paise"], "applied_paise": r["applied_paise"]},
            delay_days=r["days_past_due"]) for r in rows if r["invoice_id"] not in self.repeat_invoices]

    def rule_fulfilment_delay(self) -> list[dict]:
        unshipped = defaultdict(int)
        for position in self.positions.values():
            unshipped[position["order_id"]] += max(0, position["ordered_qty"] - position["shipped_qty"])
        rows = self.conn.execute(
            "SELECT * FROM v_order_timeline WHERE status <> 'CANCELLED' ORDER BY order_id").fetchall()
        results = []
        for row in rows:
            complete = unshipped[row["order_id"]] == 0
            end = date.fromisoformat(row["last_shipped_date"]) if complete and row["last_shipped_date"] else self.cutoff
            elapsed = (end - date.fromisoformat(row["order_date"])).days
            if elapsed <= cfg.SLA_ORDER_TO_FULFILMENT_DAYS:
                continue
            state = "fully shipped" if complete else f"still {unshipped[row['order_id']]} units short at cutoff"
            results.append(finding(
                "R10", severity_for_delay(elapsed, cfg.SLA_ORDER_TO_FULFILMENT_DAYS), "ORDER", row["order_id"], [],
                f"Orders should be fully shipped within {cfg.SLA_ORDER_TO_FULFILMENT_DAYS} days.",
                f"{elapsed} days from order to {state}.", "NONE", 0,
                {"order_date": row["order_date"], "first_shipped_date": row["first_shipped_date"],
                 "last_shipped_date": row["last_shipped_date"], "units_unshipped": unshipped[row["order_id"]]},
                delay_days=elapsed))
        return results

    def rule_invoicing_delay(self) -> list[dict]:
        shipped_on = {r["shipment_id"]: date.fromisoformat(r["shipped_date"]) for r in self.conn.execute(
            """SELECT shipment_id, shipped_date FROM shipment
               WHERE status IN ('SHIPPED', 'DELIVERED') AND shipped_date IS NOT NULL""")}
        # A reissue keeps its original's date: the customer was billed on time, then corrected.
        invoice_dates = {r["invoice_id"]: r["billed_on"] for r in self.conn.execute(
            """SELECT i.invoice_id, COALESCE(o.invoice_date, i.invoice_date) AS billed_on
               FROM v_live_invoice i LEFT JOIN invoice o ON o.invoice_id = i.replaces_invoice_id""")}
        results = []
        covered: set[str] = set()
        for invoice_id in sorted(invoice_dates, key=lambda i: (invoice_dates[i], i)):
            # A shipment not yet shipped has no lag to measure; billing it is the overbilling rule's job.
            shipment_ids = self.covers[invoice_id] & shipped_on.keys()
            fresh = sorted(shipment_ids - covered)
            covered |= shipment_ids
            if not fresh:
                continue  # every shipment was billed earlier, so this is a duplicate, not a late invoice
            # Measured from the oldest shipment, so a late one cannot hide behind a newer one.
            lag = (date.fromisoformat(invoice_dates[invoice_id]) - min(shipped_on[s] for s in fresh)).days
            if lag > cfg.SLA_SHIPMENT_TO_INVOICE_DAYS:
                results.append(finding(
                    "R11", severity_for_delay(lag, cfg.SLA_SHIPMENT_TO_INVOICE_DAYS), "INVOICE", invoice_id, fresh,
                    f"Shipments should be invoiced within {cfg.SLA_SHIPMENT_TO_INVOICE_DAYS} days.",
                    f"Invoice raised {lag} days after the oldest shipment it newly bills.", "NONE", 0,
                    {"invoice_date": invoice_dates[invoice_id],
                     "shipments": {s: shipped_on[s].isoformat() for s in fresh}}, delay_days=lag))
        for shipment_id in sorted(set(shipped_on) - covered):
            age = (self.cutoff - shipped_on[shipment_id]).days
            # Past the grace period the quantity is reported as underbilling instead, so it is not counted twice.
            if cfg.SLA_SHIPMENT_TO_INVOICE_DAYS < age < cfg.UNBILLED_GRACE_DAYS:
                results.append(finding(
                    "R11", severity_for_delay(age, cfg.SLA_SHIPMENT_TO_INVOICE_DAYS), "SHIPMENT", shipment_id, [],
                    f"Shipments should be invoiced within {cfg.SLA_SHIPMENT_TO_INVOICE_DAYS} days.",
                    f"Shipment still unbilled {age} days after shipping.", "NONE", 0,
                    {"shipped_date": shipped_on[shipment_id].isoformat(), "cutoff": self.cutoff.isoformat()},
                    delay_days=age))
        return results

    def run(self) -> list[dict]:
        # Duplicates run first so overbilling can exclude the quantity they already explain.
        findings = self.rule_duplicate_invoice()
        for rule in (self.rule_overbilling, self.rule_underbilling, self.rule_duplicate_allocation,
                     self.rule_closed_order_unpaid, self.rule_illegal_transition, self.rule_dispute_not_in_ar,
                     self.rule_short_payment, self.rule_long_overdue, self.rule_fulfilment_delay,
                     self.rule_invoicing_delay):
            findings.extend(rule())
        findings.sort(key=lambda f: (f["rule_id"], f["source_id"]))
        self.attach_event_trail(findings)
        for number, item in enumerate(findings, start=1):
            item["finding_id"] = f"FND-2026-{number:06d}"
        return findings

    def attach_event_trail(self, findings: list[dict]) -> None:
        """Cite the status events of every record a finding touches, so it traces to source events."""
        trail = defaultdict(list)
        for row in self.conn.execute("SELECT entity_id, event_id FROM status_event ORDER BY event_id"):
            trail[row["entity_id"]].append(row["event_id"])
        for item in findings:
            records = [item["source_id"]] + json.loads(item["related_ids"])
            evidence = json.loads(item["evidence"])
            evidence["source_events"] = sorted({event for record in records for event in trail[record]})
            item["evidence"] = json.dumps(evidence, sort_keys=True)


def run_detection(conn: sqlite3.Connection) -> list[dict]:
    """Run every rule and replace the finding table's contents."""
    findings = Detector(conn).run()
    conn.execute("DELETE FROM finding")
    if findings:
        columns = list(findings[0])
        placeholders = ", ".join("?" for _ in columns)
        conn.executemany(f"INSERT INTO finding ({', '.join(columns)}) VALUES ({placeholders})",
                         ([f[c] for c in columns] for f in findings))
    conn.commit()
    return findings
