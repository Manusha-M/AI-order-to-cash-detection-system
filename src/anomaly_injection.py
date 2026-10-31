"""Inject labelled anomalies into a valid baseline and write the ground truth.

Each scenario picks its own targets, and an order touched by one scenario is not reused by
another, so unrelated rows stay intact. Every change keeps keys and arithmetic valid (line
total = quantity x price, invoice total = sum of lines): the data is wrong as a business
fact, not corrupted as a database. If a scenario cannot find enough targets it raises
rather than quietly producing fewer anomalies than the ground truth promises.
"""
from __future__ import annotations

import random
from collections.abc import Iterator
from datetime import date, timedelta

from . import config as cfg
from .generator import Dataset


class Injector:
    def __init__(self, ds: Dataset, scale: cfg.Scale, seed: int):
        self.ds = ds
        self.scale = scale
        self.seed = seed
        self.t = ds.tables
        self.cutoff = ds.cutoff
        self.used_orders: set[str] = set()
        self.payment_of_allocation = {p["payment_id"]: p for p in self.t["payment"]}

    def stream(self, name: str) -> random.Random:
        return random.Random(f"{self.seed}:inject:{name}")

    def label(self, issue_type: str, scenario: str, rule_id: str, entity: str, primary_id: str | None,
              related: list[str], expected: str, observed: str, impact_type: str, impact: int,
              source: str = "injected", event: dict | None = None) -> None:
        causes = {"injected": f"Scenario {scenario} changed a valid record.",
                  "plan": f"The generator planned this outcome ({scenario}).",
                  "rule": "Generated dates crossed the documented limit."}
        row = {"issue_type": issue_type, "expected_label": issue_type, "scenario": scenario, "rule_id": rule_id,
               "source_entity": entity, "primary_id": primary_id, "related_ids": "|".join(related),
               "expected_behavior": expected, "observed_behavior": observed,
               "causal_explanation": f"{causes[source]} {observed}", "impact_type": impact_type,
               "expected_impact_paise": impact, "label_source": source}
        if event is not None:
            row["_event"] = event
        self.ds.ground_truth.append(row)

    def clean_invoices(self, rng: random.Random, *statuses: str) -> Iterator[dict]:
        """Invoices with an ordinary story, on orders no scenario has touched.

        Yields one at a time and re-checks each, because the caller may use an order mid-loop.
        """
        rows = [i for i in self.t["invoice"]
                if i["status"] in statuses and i["_fate"] == "NORMAL" and i["_dispute"] is None]
        rng.shuffle(rows)
        for row in rows:
            if row["order_id"] not in self.used_orders:
                yield row

    def payable_single_allocation(self, invoice: dict) -> dict | None:
        """The invoice's last allocation, if changing it cannot disturb another invoice."""
        allocations = self.ds.allocations_by_invoice[invoice["invoice_id"]]
        if not allocations:
            return None
        allocation = allocations[-1]
        return allocation if len(self.ds.allocations_by_payment[allocation["payment_id"]]) == 1 else None

    def change_invoice_total(self, invoice: dict, delta: int) -> None:
        """Keep totals and ledger consistent after a line changes. PAID invoices stay paid in full."""
        invoice["total_paise"] += delta
        for entry in self.ds.ledger_by_invoice[invoice["invoice_id"]]:
            if entry["entry_type"] == "INVOICE_POSTED":
                entry["amount_paise"] += delta
        if invoice["status"] != "PAID":
            return
        allocation = self.payable_single_allocation(invoice)
        allocation["allocated_paise"] += delta
        self.payment_of_allocation[allocation["payment_id"]]["amount_paise"] += delta
        for entry in self.ds.ledger_by_invoice[invoice["invoice_id"]]:
            if entry["source_id"] == allocation["allocation_id"]:
                entry["amount_paise"] += delta

    def unbilled_quantity(self, order_line_id: str) -> int:
        """Shipped minus billed for one order line, ignoring void invoices."""
        void = {i["invoice_id"] for i in self.t["invoice"] if i["status"] == "VOID"}
        billed = sum(l["quantity"] for l in self.t["invoice_line"]
                     if l["order_line_id"] == order_line_id and l["invoice_id"] not in void)
        shipped_ids = {s["shipment_id"] for s in self.t["shipment"] if s["shipped_date"]}
        shipped = sum(l["quantity"] for l in self.t["shipment_line"]
                      if l["order_line_id"] == order_line_id and l["shipment_id"] in shipped_ids)
        return shipped - billed

    def need(self, name: str, wanted: int, made: int) -> None:
        if made < wanted:
            raise RuntimeError(f"scenario {name}: only {made} of {wanted} targets available")

    # ---- Scenario B: payment allocated twice -------------------------------------------

    def duplicate_allocations(self) -> None:
        rng = self.stream("duplicate-allocation")
        wanted = self.scale.scenario_count("duplicate_allocation")
        same_invoice_target = (wanted + 1) // 2
        made = 0
        for invoice in self.clean_invoices(rng, "PARTIALLY_PAID"):
            if made == same_invoice_target:
                break
            allocation = self.payable_single_allocation(invoice)
            if allocation is None or self.ds.balance(invoice) <= allocation["allocated_paise"]:
                continue
            payment = self.payment_of_allocation[allocation["payment_id"]]
            when = date.fromisoformat(allocation["allocated_date"])
            again = self.ds.add_allocation(payment, invoice, allocation["allocated_paise"], when)
            self.used_orders.add(invoice["order_id"])
            self.label("DUPLICATE_ALLOCATION", "B1_SAME_INVOICE", "R04", "PAYMENT", payment["payment_id"],
                       [invoice["invoice_id"], allocation["allocation_id"], again["allocation_id"]],
                       "Total allocated from a payment must not exceed the payment amount.",
                       "The same payment was allocated twice to the same invoice.",
                       "PAYMENT_ALLOCATION_DISCREPANCY", allocation["allocated_paise"])
            made += 1

        open_by_account: dict[str, list[dict]] = {}
        for invoice in self.clean_invoices(rng, "ISSUED"):
            if date.fromisoformat(invoice["due_date"]) >= self.cutoff:
                open_by_account.setdefault(invoice["account_id"], []).append(invoice)
        for paid in self.clean_invoices(rng, "PAID"):
            if made == wanted:
                break
            allocation = self.payable_single_allocation(paid)
            others = [i for i in open_by_account.get(paid["account_id"], [])
                      if i["order_id"] != paid["order_id"] and i["order_id"] not in self.used_orders]
            if allocation is None or not others:
                continue
            amount = allocation["allocated_paise"]
            target = next((i for i in others if i["total_paise"] > amount), None)
            if target is None:
                continue
            payment = self.payment_of_allocation[allocation["payment_id"]]
            when = max(date.fromisoformat(payment["payment_date"]), date.fromisoformat(target["invoice_date"]))
            again = self.ds.add_allocation(payment, target, amount, when)
            self.ds.transition("INVOICE", target, "PARTIALLY_PAID", when, "SYSTEM")
            self.used_orders.update((paid["order_id"], target["order_id"]))
            self.label("DUPLICATE_ALLOCATION", "B2_SECOND_INVOICE", "R04", "PAYMENT", payment["payment_id"],
                       [paid["invoice_id"], target["invoice_id"], allocation["allocation_id"], again["allocation_id"]],
                       "Total allocated from a payment must not exceed the payment amount.",
                       "The full payment was applied to one invoice and again to a second invoice.",
                       "PAYMENT_ALLOCATION_DISCREPANCY", amount)
            made += 1
        self.need("duplicate_allocation", wanted, made)

    # ---- Scenario E: dispute not reflected in receivables ------------------------------

    def disputes_not_in_ar(self) -> None:
        rng = self.stream("dispute-not-in-ar")
        wanted = self.scale.scenario_count("dispute_not_in_ar")
        latest_due_gap = timedelta(days=25)
        candidates = [d for d in self.t["dispute"] if d["status"] in ("OPEN", "UNDER_REVIEW")]
        rng.shuffle(candidates)
        by_id = {i["invoice_id"]: i for i in self.t["invoice"]}
        made = 0
        for dispute in candidates:
            if made == wanted:
                break
            invoice = by_id[dispute["invoice_id"]]
            if date.fromisoformat(invoice["due_date"]) < self.cutoff - latest_due_gap:
                continue
            if invoice["order_id"] in self.used_orders:
                continue
            entries = self.ds.ledger_by_invoice[invoice["invoice_id"]]
            hold = next(e for e in entries if e["entry_type"] == "DISPUTE_HOLD")
            disputed = dispute["disputed_paise"]
            if made % 2 == 0:
                scenario, reflected = "E1_NO_HOLD", 0
                entries.remove(hold)
                self.t["ar_ledger_entry"].remove(hold)
                observed = "No hold was posted to the receivables ledger for this open dispute."
            else:
                scenario = "E2_PARTIAL_HOLD"
                reflected = max(1, round(disputed * rng.uniform(0.3, 0.7)))
                hold["amount_paise"] = reflected
                observed = "The hold posted to the ledger is smaller than the disputed amount."
            self.used_orders.add(invoice["order_id"])
            self.label("DISPUTE_NOT_IN_AR", scenario, "R07", "DISPUTE", dispute["dispute_id"],
                       [invoice["invoice_id"]],
                       "An open dispute must hold its full disputed amount out of collectible receivables.",
                       observed, "DISPUTED_NOT_RESERVED", disputed - reflected)
            made += 1
        self.need("dispute_not_in_ar", wanted, made)

    # ---- Scenario C: order closed with unpaid invoice ----------------------------------

    def closed_orders_with_unpaid_invoice(self) -> None:
        rng = self.stream("closed-unpaid")
        wanted = self.scale.scenario_count("closed_unpaid")
        orders = [o for o in self.t["sales_order"] if o["status"] == "INVOICED" and o["order_id"] not in self.used_orders]
        rng.shuffle(orders)
        made = 0
        for order in orders:
            if made == wanted:
                break
            invoices = [i for i in self.ds.invoices_by_order[order["order_id"]] if i["status"] != "VOID"]
            if any(i["_fate"] != "NORMAL" or i["_dispute"] is not None for i in invoices):
                continue
            unpaid = [i for i in invoices if self.ds.balance(i) > cfg.BALANCE_TOLERANCE_PAISE]
            if not unpaid:
                continue
            when = self.cutoff - timedelta(days=rng.randint(0, 5))
            self.ds.transition("ORDER", order, "CLOSED", when, "SALES_OPS")
            self.used_orders.add(order["order_id"])
            self.label("CLOSED_ORDER_UNPAID", "C_CLOSED_UNPAID", "R05", "ORDER", order["order_id"],
                       [i["invoice_id"] for i in unpaid],
                       "An order may close only when every invoice on it is settled.",
                       "The order is CLOSED while an invoice still has an unpaid balance.",
                       "UNCOLLECTED_RECEIVABLE", sum(self.ds.balance(i) for i in unpaid))
            made += 1
        self.need("closed_unpaid", wanted, made)

    # ---- Duplicate invoice -------------------------------------------------------------

    def duplicate_invoices(self) -> None:
        rng = self.stream("duplicate-invoice")
        wanted = self.scale.scenario_count("duplicate_invoice")
        made = 0
        for original in self.clean_invoices(rng, "ISSUED", "PARTIALLY_PAID", "PAID"):
            if made == wanted:
                break
            order = original["_order"]
            issued = date.fromisoformat(original["invoice_date"]) + timedelta(days=rng.randint(1, 10))
            issued = min(issued, self.cutoff)
            due = issued + timedelta(days=order["payment_terms_days"])
            copy = {"invoice_id": self.ds.new_id("INV"), "order_id": original["order_id"],
                    "account_id": original["account_id"], "invoice_date": issued.isoformat(),
                    "due_date": due.isoformat(), "status": None, "total_paise": original["total_paise"],
                    "replaces_invoice_id": None, "_order": order, "_fate": "DUPLICATE", "_dispute": None}
            for line in self.ds.lines_by_invoice[original["invoice_id"]]:
                duplicate_line = dict(line, invoice_line_id=None, invoice_id=copy["invoice_id"])
                self.t["invoice_line"].append(duplicate_line)
                self.ds.lines_by_invoice[copy["invoice_id"]].append(duplicate_line)
            for shipment_id in self.ds.shipment_ids_by_invoice[original["invoice_id"]]:
                self.t["invoice_shipment"].append({"invoice_id": copy["invoice_id"], "shipment_id": shipment_id})
                self.ds.shipment_ids_by_invoice[copy["invoice_id"]].append(shipment_id)
            self.t["invoice"].append(copy)
            self.ds.invoices_by_order[order["order_id"]].append(copy)
            self.ds.transition("INVOICE", copy, "DRAFT", issued, "SYSTEM")
            self.ds.transition("INVOICE", copy, "ISSUED", issued, "SYSTEM")
            self.ds.post_ledger(copy, "INVOICE_POSTED", copy["total_paise"], issued, copy["invoice_id"])
            self.used_orders.add(order["order_id"])
            self.label("DUPLICATE_INVOICE", "F_DUPLICATE_INVOICE", "R03", "INVOICE", copy["invoice_id"],
                       [original["invoice_id"], order["order_id"]],
                       "Each shipped quantity is billed once.",
                       "A second invoice repeats the same order lines and quantities for the same shipment.",
                       "DUPLICATE_BILLING_EXPOSURE", copy["total_paise"])
            made += 1
        self.need("duplicate_invoice", wanted, made)

    # ---- Scenario A: invoice exceeds fulfilled quantity --------------------------------

    def overbilling(self) -> None:
        rng = self.stream("overbilling")
        wanted = self.scale.scenario_count("overbilling")
        made = 0
        for invoice in self.clean_invoices(rng, "ISSUED", "PAID"):
            if made == wanted:
                break
            if invoice["status"] == "PAID" and self.payable_single_allocation(invoice) is None:
                continue
            line = rng.choice(self.ds.lines_by_invoice[invoice["invoice_id"]])
            if self.unbilled_quantity(line["order_line_id"]) != 0:
                continue  # a raised quantity would only eat into shipped-but-unbilled goods
            excess = rng.randint(1, max(1, min(5, line["quantity"] // 3)))
            before = line["quantity"]
            line["quantity"] += excess
            delta = excess * line["unit_price_paise"]
            line["line_total_paise"] += delta
            self.change_invoice_total(invoice, delta)
            self.used_orders.add(invoice["order_id"])
            variant = "A2_OVERBILLED_AND_COLLECTED" if invoice["status"] == "PAID" else "A1_OVERBILLED_OPEN"
            self.label("OVERBILLING", variant, "R01", "ORDER_LINE", line["order_line_id"],
                       [invoice["invoice_id"], invoice["order_id"]],
                       "Billed quantity must not exceed fulfilled quantity.",
                       f"Invoice line quantity was raised from {before} to {line['quantity']}, beyond what shipped.",
                       "OVERBILLED_EXPOSURE", delta)
            made += 1
        self.need("overbilling", wanted, made)

    # ---- Underbilling ------------------------------------------------------------------

    def underbilling(self) -> None:
        rng = self.stream("underbilling")
        wanted = self.scale.scenario_count("underbilling")
        aged_before = self.cutoff - timedelta(days=cfg.UNBILLED_GRACE_DAYS)
        made = 0
        for invoice in self.clean_invoices(rng, "ISSUED", "PAID"):
            if made == wanted:
                break
            order = invoice["_order"]
            shipments = self.ds.shipments_by_order[order["order_id"]]
            all_aged = all(s["shipped_date"] and date.fromisoformat(s["shipped_date"]) <= aged_before for s in shipments)
            if order["status"] not in ("INVOICED", "CLOSED") or not all_aged:
                continue
            lines = self.ds.lines_by_invoice[invoice["invoice_id"]]
            line = rng.choice(lines)
            variant = ("G1_PRICE", "G2_QUANTITY", "G3_LINE_OMITTED")[made % 3]
            if variant == "G1_PRICE":
                new_price = line["unit_price_paise"] - max(1, round(line["unit_price_paise"] * rng.uniform(0.05, 0.2)))
                delta = line["quantity"] * (line["unit_price_paise"] - new_price)
            elif variant == "G2_QUANTITY":
                if line["quantity"] < 2:
                    continue
                dropped = rng.randint(1, line["quantity"] - 1)
                delta = dropped * line["unit_price_paise"]
            else:
                if len(lines) < 2:
                    continue
                delta = line["line_total_paise"]
            if invoice["status"] == "PAID":
                allocation = self.payable_single_allocation(invoice)
                if allocation is None or allocation["allocated_paise"] <= delta:
                    continue
            if variant == "G1_PRICE":
                line["unit_price_paise"] = new_price
                line["line_total_paise"] -= delta
            elif variant == "G2_QUANTITY":
                line["quantity"] -= dropped
                line["line_total_paise"] -= delta
            else:
                lines.remove(line)
                self.t["invoice_line"].remove(line)
                for number, kept in enumerate(lines, start=1):
                    kept["line_number"] = number
            self.change_invoice_total(invoice, -delta)
            self.used_orders.add(invoice["order_id"])
            self.label("UNDERBILLING", variant, "R02", "ORDER_LINE", line["order_line_id"],
                       [invoice["invoice_id"], invoice["order_id"]],
                       "Fulfilled quantity must be billed in full at the order price.",
                       "Billed value is lower than fulfilled value for this order line.",
                       "UNDERBILLED_REVENUE", delta)
            made += 1
        self.need("underbilling", wanted, made)

    # ---- Scenario D: status event skips a required state -------------------------------

    def illegal_transitions(self) -> None:
        rng = self.stream("illegal-transition")
        wanted = self.scale.scenario_count("illegal_transition")
        # (entity table, entity type, id column, first hop, second hop)
        patterns = (
            ("sales_order", "ORDER", "order_id", ("CONFIRMED", "FULFILLED"), ("FULFILLED", "INVOICED")),
            ("quote", "QUOTE", "quote_id", ("DRAFT", "SENT"), ("SENT", "ACCEPTED")),
            ("invoice", "INVOICE", "invoice_id", ("DRAFT", "ISSUED"), ("ISSUED", "PAID")),
            ("shipment", "SHIPMENT", "shipment_id", ("PLANNED", "SHIPPED"), ("SHIPPED", "DELIVERED")),
            ("dispute", "DISPUTE", "dispute_id", ("OPEN", "UNDER_REVIEW"), ("UNDER_REVIEW", "RESOLVED_CREDIT")),
        )
        pools = {}
        for table, entity_type, id_column, first, second in patterns:
            ids = []
            for row in self.t[table]:
                order_id = row.get("order_id")
                if order_id is not None and order_id in self.used_orders:
                    continue
                events = self.ds.events_by_entity[(entity_type, row[id_column])]
                hops = [(e["from_status"], e["to_status"]) for e in events]
                # The two hops must be neighbours, or removing one would break the chain somewhere else.
                if first in hops and second in hops and hops.index(second) == hops.index(first) + 1:
                    ids.append(row[id_column])
            rng.shuffle(ids)
            pools[entity_type] = ids

        made = 0
        positions = {entity_type: 0 for entity_type in pools}
        while made < wanted:
            progressed = False
            for table, entity_type, id_column, first, second in patterns:
                if made == wanted or positions[entity_type] >= len(pools[entity_type]):
                    continue
                entity_id = pools[entity_type][positions[entity_type]]
                positions[entity_type] += 1
                self.skip_state(entity_type, entity_id, first, second)
                progressed = True
                made += 1
            if not progressed:
                break
        self.need("illegal_transition", wanted, made)

    def skip_state(self, entity_type: str, entity_id: str, first: tuple, second: tuple) -> None:
        """Replace two legal hops with one direct jump, so the middle state is never recorded."""
        history = self.ds.events_by_entity[(entity_type, entity_id)]
        first_event = next(e for e in history if (e["from_status"], e["to_status"]) == first)
        second_event = next(e for e in history if (e["from_status"], e["to_status"]) == second)
        history.remove(first_event)
        self.t["status_event"].remove(first_event)
        second_event["from_status"] = first_event["from_status"]
        if entity_type in ("ORDER", "INVOICE"):
            row = next(r for r in self.t["sales_order" if entity_type == "ORDER" else "invoice"]
                       if r[f"{entity_type.lower()}_id"] == entity_id)
            self.used_orders.add(row["order_id"])
        self.label("ILLEGAL_TRANSITION", f"D_{entity_type}_SKIP_{first[1]}", "R06", "STATUS_EVENT", None,
                   [entity_id], f"{entity_type} must pass through {first[1]}.",
                   f"Event history jumps {first[0]} -> {second[1]}, skipping {first[1]}.",
                   "NONE", 0, event=second_event)

    # ---- Labels that follow from the plan, not from a mutation -------------------------

    def label_receivable_outcomes(self) -> None:
        for invoice in self.t["invoice"]:
            fate = invoice["_fate"]
            collectible = self.ds.balance(invoice) - self.ds.held(invoice)
            days_past_due = (self.cutoff - date.fromisoformat(invoice["due_date"])).days
            # A short-paid invoice old enough is long overdue as well: two true labels on one record.
            aged_short_pay = fate == "SHORT_PAY" and days_past_due > cfg.LONG_OVERDUE_DAYS
            if fate in ("LONG_ZERO", "LONG_PARTIAL") or aged_short_pay:
                self.label("LONG_OVERDUE", fate, "R09", "INVOICE", invoice["invoice_id"], [invoice["order_id"]],
                           f"Balances should not stay unpaid more than {cfg.LONG_OVERDUE_DAYS} days past due.",
                           "The invoice is long overdue at the cutoff.", "OVERDUE_RECEIVABLE", collectible, "plan")
            if fate in ("SHORT_PAY", "LONG_PARTIAL"):
                self.label("SHORT_PAYMENT", fate, "R08", "INVOICE", invoice["invoice_id"], [invoice["order_id"]],
                           "A customer who starts paying should clear the invoice.",
                           "Payments stopped with a balance still open.", "SHORT_PAID_RECEIVABLE", collectible, "plan")

    def label_process_delays(self) -> None:
        shipped_of = {}
        for shipment in self.t["shipment"]:
            if shipment["shipped_date"]:
                shipped_of[shipment["shipment_id"]] = date.fromisoformat(shipment["shipped_date"])
        invoice_date_of = {i["invoice_id"]: i["invoice_date"] for i in self.t["invoice"]}

        for order in self.t["sales_order"]:
            if order["status"] == "CANCELLED":
                continue
            order_date = date.fromisoformat(order["order_date"])
            shipments = self.ds.shipments_by_order[order["order_id"]]
            ended = order.get("_fulfilled_date") or self.cutoff
            elapsed = (ended - order_date).days
            if elapsed > cfg.SLA_ORDER_TO_FULFILMENT_DAYS:
                self.label("FULFILMENT_DELAY", "PLAN_SLOW_OR_BACKORDER", "R10", "ORDER", order["order_id"],
                           [s["shipment_id"] for s in shipments],
                           f"Orders should be fully shipped within {cfg.SLA_ORDER_TO_FULFILMENT_DAYS} days.",
                           f"Fulfilment took {elapsed} days.", "NONE", 0, "rule")

        covered: set[str] = set()
        def billed_on(invoice: dict) -> str:
            return invoice_date_of.get(invoice["replaces_invoice_id"], invoice["invoice_date"])

        invoices = [i for i in self.t["invoice"] if i["status"] != "VOID"]
        invoices.sort(key=lambda i: (billed_on(i), i["invoice_id"]))
        for invoice in invoices:
            shipment_ids = self.ds.shipment_ids_by_invoice[invoice["invoice_id"]]
            fresh = [s for s in shipment_ids if s not in covered]
            covered.update(shipment_ids)
            if not fresh:
                continue
            lag = (date.fromisoformat(billed_on(invoice)) - min(shipped_of[s] for s in fresh)).days
            if lag > cfg.SLA_SHIPMENT_TO_INVOICE_DAYS:
                self.label("INVOICING_DELAY", "PLAN_SLOW_BILLING", "R11", "INVOICE", invoice["invoice_id"],
                           fresh, f"Shipments should be invoiced within {cfg.SLA_SHIPMENT_TO_INVOICE_DAYS} days.",
                           f"Invoice raised {lag} days after shipment.", "NONE", 0, "rule")
        for shipment_id, shipped in sorted(shipped_of.items()):
            age = (self.cutoff - shipped).days
            if shipment_id not in covered and cfg.SLA_SHIPMENT_TO_INVOICE_DAYS < age < cfg.UNBILLED_GRACE_DAYS:
                self.label("INVOICING_DELAY", "PLAN_NOT_YET_BILLED", "R11", "SHIPMENT", shipment_id, [],
                           f"Shipments should be invoiced within {cfg.SLA_SHIPMENT_TO_INVOICE_DAYS} days.",
                           f"Shipment still unbilled {age} days after shipping.", "NONE", 0, "rule")

    def run(self) -> None:
        self.duplicate_allocations()
        self.disputes_not_in_ar()
        self.closed_orders_with_unpaid_invoice()
        self.duplicate_invoices()
        self.overbilling()
        self.underbilling()
        self.illegal_transitions()
        self.label_receivable_outcomes()
        self.label_process_delays()


def inject_anomalies(ds: Dataset, scale: cfg.Scale, seed: int) -> None:
    Injector(ds, scale, seed).run()
