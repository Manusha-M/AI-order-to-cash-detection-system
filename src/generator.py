"""Deterministic synthetic Order-to-Cash generator.

The flow mirrors the real business process: accounts and quotes first, then orders,
shipments, invoices, disputes and payments. Each phase owns a named random stream, so a
change in one phase does not reshuffle the others. Totals are always summed from lines and
balances from the ledger: nothing derived is drawn at random.

Keys starting with "_" on a row are generator-only planning notes. They are never written
to the database, so the detector cannot see them.
"""
from __future__ import annotations

import random
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta

from . import config as cfg
from .lifecycle import is_legal

TABLE_ORDER = (
    "product", "account", "quote", "quote_line", "sales_order", "order_line", "shipment", "shipment_line",
    "invoice", "invoice_line", "invoice_shipment", "payment", "payment_allocation", "dispute",
    "ar_ledger_entry", "status_event",
)

ID_COLUMN = {"ACCOUNT": "account_id", "QUOTE": "quote_id", "ORDER": "order_id", "SHIPMENT": "shipment_id",
             "INVOICE": "invoice_id", "PAYMENT": "payment_id", "DISPUTE": "dispute_id"}

COMPANY_FIRST = ("Aster", "Bluepeak", "Cedar", "Deccan", "Evergreen", "Fernhill", "Granite", "Harbor", "Indus",
                 "Juniper", "Kaveri", "Lotus", "Meridian", "Nimbus", "Orchid", "Pinnacle", "Quartz", "Ridgeway",
                 "Sahyadri", "Teak", "Umbra", "Vertex", "Willow", "Xenon", "Yarrow", "Zenith")
COMPANY_SECOND = ("Industries", "Engineering", "Logistics", "Textiles", "Foods", "Pharma", "Automotive", "Packaging",
                  "Electricals", "Constructions", "Agro", "Polymers")
PRODUCT_STEMS = {
    "MECHANICAL": ("Bearing Kit", "Gear Assembly", "Hydraulic Hose", "Pump Seal", "Valve Set"),
    "ELECTRICAL": ("Control Panel", "Cable Drum", "Motor Starter", "Relay Module", "Sensor Pack"),
    "CONSUMABLE": ("Lubricant Drum", "Filter Cartridge", "Welding Rod Pack", "Coolant Can", "Abrasive Disc Box"),
    "SAFETY": ("Helmet Pack", "Glove Carton", "Harness Set", "Fire Blanket", "Goggle Box"),
}
PRODUCT_GRADES = ("Standard", "Heavy Duty", "Compact", "Premium")


def net_unit_price(list_price_paise: int, discount_bps: int) -> int:
    """Discounted price, rounded half up in integers so Python and SQL always agree."""
    return (list_price_paise * (10_000 - discount_bps) + 5_000) // 10_000


def business_days(start: date, end: date) -> list[date]:
    days = (start + timedelta(days=i) for i in range((end - start).days + 1))
    return [d for d in days if d.weekday() < 5]


class Dataset:
    """In-memory tables plus the indexes the generator and injector both need."""

    def __init__(self, seed: int, cutoff: date):
        self.seed = seed
        self.cutoff = cutoff
        self.tables: dict[str, list[dict]] = {name: [] for name in TABLE_ORDER}
        self.ground_truth: list[dict] = []
        self.counters: Counter = Counter()
        self.time_rng = random.Random(f"{seed}:event-times")
        self.events_by_entity: dict[tuple, list[dict]] = defaultdict(list)
        self.ledger_by_invoice: dict[str, list[dict]] = defaultdict(list)
        self.lines_by_order: dict[str, list[dict]] = defaultdict(list)
        self.lines_by_invoice: dict[str, list[dict]] = defaultdict(list)
        self.allocations_by_invoice: dict[str, list[dict]] = defaultdict(list)
        self.allocations_by_payment: dict[str, list[dict]] = defaultdict(list)
        self.invoices_by_order: dict[str, list[dict]] = defaultdict(list)
        self.shipments_by_order: dict[str, list[dict]] = defaultdict(list)
        self.shipment_ids_by_invoice: dict[str, list[str]] = defaultdict(list)

    def new_id(self, prefix: str) -> str:
        self.counters[prefix] += 1
        return f"{prefix}-2026-{self.counters[prefix]:06d}"

    def transition(self, entity_type: str, row: dict, to_status: str, when: date, actor: str,
                   enforce_legal: bool = True) -> dict:
        """Move a record to a new status and keep the old one as a history event."""
        from_status = row.get("status")
        if enforce_legal and not is_legal(entity_type, from_status, to_status):
            raise ValueError(f"illegal baseline transition {entity_type} {from_status} -> {to_status}")
        if when > self.cutoff:
            raise ValueError(f"event after cutoff: {entity_type} {when}")
        stamp = datetime.combine(when, time(9)) + timedelta(minutes=self.time_rng.randrange(540))
        last = row.get("_last_ts")
        if last is not None and stamp <= last:
            stamp = last + timedelta(minutes=self.time_rng.randint(1, 30))
        row["_last_ts"] = stamp
        row["status"] = to_status
        event = {"event_id": None, "entity_type": entity_type, "entity_id": row[ID_COLUMN[entity_type]],
                 "from_status": from_status, "to_status": to_status, "event_time": stamp.isoformat(),
                 "actor_role": actor}
        self.tables["status_event"].append(event)
        self.events_by_entity[(entity_type, event["entity_id"])].append(event)
        return event

    def post_ledger(self, invoice: dict, entry_type: str, amount: int, when: date, source_id: str) -> dict:
        entry = {"entry_id": None, "invoice_id": invoice["invoice_id"], "entry_type": entry_type,
                 "amount_paise": amount, "entry_date": when.isoformat(), "source_id": source_id}
        self.tables["ar_ledger_entry"].append(entry)
        self.ledger_by_invoice[invoice["invoice_id"]].append(entry)
        return entry

    def _ledger_sum(self, invoice_id: str, *types: str) -> int:
        return sum(e["amount_paise"] for e in self.ledger_by_invoice[invoice_id] if e["entry_type"] in types)

    def balance(self, invoice: dict) -> int:
        iid = invoice["invoice_id"]
        return (self._ledger_sum(iid, "INVOICE_POSTED")
                - self._ledger_sum(iid, "INVOICE_VOIDED", "PAYMENT_APPLIED", "CREDIT_MEMO"))

    def held(self, invoice: dict) -> int:
        iid = invoice["invoice_id"]
        return self._ledger_sum(iid, "DISPUTE_HOLD") - self._ledger_sum(iid, "DISPUTE_RELEASE")

    def add_allocation(self, payment: dict, invoice: dict, amount: int, when: date) -> dict:
        allocation = {"allocation_id": self.new_id("ALC"), "payment_id": payment["payment_id"],
                      "invoice_id": invoice["invoice_id"], "allocated_paise": amount,
                      "allocated_date": when.isoformat()}
        self.tables["payment_allocation"].append(allocation)
        self.allocations_by_invoice[invoice["invoice_id"]].append(allocation)
        self.allocations_by_payment[payment["payment_id"]].append(allocation)
        self.post_ledger(invoice, "PAYMENT_APPLIED", amount, when, allocation["allocation_id"])
        return allocation

    def _renumber(self) -> None:
        invoices = sorted(self.tables["invoice"], key=lambda r: (r["invoice_date"], r["invoice_id"]))
        allocations = sorted(self.tables["payment_allocation"], key=lambda r: (r["allocated_date"], r["allocation_id"]))
        renamed = {r["invoice_id"]: f"INV-2026-{i:06d}" for i, r in enumerate(invoices, start=1)}
        renamed.update({r["allocation_id"]: f"ALC-2026-{i:06d}" for i, r in enumerate(allocations, start=1)})
        columns = {"invoice": ("invoice_id", "replaces_invoice_id"), "invoice_line": ("invoice_id",),
                   "invoice_shipment": ("invoice_id",), "dispute": ("invoice_id",),
                   "payment_allocation": ("allocation_id", "invoice_id"),
                   "ar_ledger_entry": ("invoice_id", "source_id"), "status_event": ("entity_id",)}
        for table, names in columns.items():
            for row in self.tables[table]:
                for name in names:
                    row[name] = renamed.get(row[name], row[name])
        self.tables["invoice"].sort(key=lambda r: r["invoice_id"])
        self.tables["payment_allocation"].sort(key=lambda r: r["allocation_id"])
        for label in self.ground_truth:
            label["primary_id"] = renamed.get(label["primary_id"], label["primary_id"])
            label["related_ids"] = "|".join(renamed.get(i, i) for i in label["related_ids"].split("|"))

    def finalize(self) -> None:
        """Number rows once the data stops changing, so IDs have no gaps and reveal nothing.

        Invoices and allocations are renumbered by date. Otherwise rows added by injection
        would sit at the end of the sequence and an ID alone could give them away.
        """
        self._renumber()
        lines = self.tables["invoice_line"]
        lines.sort(key=lambda l: (l["invoice_id"], l["line_number"]))
        for i, line in enumerate(lines, start=1):
            line["invoice_line_id"] = f"IVL-2026-{i:06d}"
        events = self.tables["status_event"]
        events.sort(key=lambda e: (e["event_time"], e["entity_type"], e["entity_id"], e["to_status"]))
        for i, event in enumerate(events, start=1):
            event["event_id"] = f"EVT-2026-{i:06d}"
        ledger = self.tables["ar_ledger_entry"]
        ledger.sort(key=lambda e: (e["entry_date"], e["invoice_id"], e["entry_type"], e["source_id"], e["amount_paise"]))
        for i, entry in enumerate(ledger, start=1):
            entry["entry_id"] = f"ARL-2026-{i:06d}"
        for label in self.ground_truth:
            event = label.pop("_event", None)
            if event is not None:
                label["primary_id"] = event["event_id"]


class Generator:
    def __init__(self, scale: cfg.Scale, seed: int, cutoff: date, inject: bool):
        self.scale = scale
        self.seed = seed
        self.cutoff = cutoff
        self.inject = inject
        self.ds = Dataset(seed, cutoff)
        self.t = self.ds.tables
        self.applied_chunks: list[dict] = []

    def stream(self, name: str) -> random.Random:
        return random.Random(f"{self.seed}:{name}")

    def run(self) -> Dataset:
        self.make_products()
        self.make_accounts()
        self.make_quotes()
        self.make_orders()
        self.make_shipments()
        self.make_invoices()
        self.plan_invoice_fates()
        self.make_disputes()
        self.make_payments()
        self.replay_receivables()
        self.advance_orders()
        return self.ds

    # ---- Master data -------------------------------------------------------------------

    def make_products(self) -> None:
        rng = self.stream("products")
        catalog = [(category, f"{stem} {grade}")
                   for category, stems in PRODUCT_STEMS.items() for stem in stems for grade in PRODUCT_GRADES]
        for category, name in catalog[: self.scale.products]:
            rupees = min(75_000, max(500, round(rng.lognormvariate(8.0, 0.9), -1)))
            self.t["product"].append({"product_id": self.ds.new_id("PRD"), "product_name": name,
                                      "category": category, "list_price_paise": int(rupees) * 100})

    def make_accounts(self) -> None:
        rng = self.stream("accounts")
        terms_by_segment = {"SMB": ((15, 30), (0.4, 0.6)), "MID_MARKET": ((30, 45), (0.7, 0.3)),
                            "ENTERPRISE": ((45, 60), (0.6, 0.4))}
        credit_by_segment = {"SMB": 500_000, "MID_MARKET": 2_500_000, "ENTERPRISE": 10_000_000}
        for n in range(1, self.scale.accounts + 1):
            segment = rng.choices(("SMB", "MID_MARKET", "ENTERPRISE"), (0.55, 0.33, 0.12))[0]
            terms, weights = terms_by_segment[segment]
            name = f"{rng.choice(COMPANY_FIRST)} {rng.choice(COMPANY_SECOND)} {n:04d}"
            created = date(2025, 1, 1) + timedelta(days=rng.randrange(360))
            self.t["account"].append({
                "account_id": self.ds.new_id("ACC"), "account_name": name, "segment": segment,
                "region": rng.choice(cfg.ENUMS[("account", "region")]), "status": None,
                "payment_terms_days": rng.choices(terms, weights)[0],
                "credit_limit_paise": credit_by_segment[segment] * 100, "created_date": created.isoformat(),
                # Pareto activity gives a realistic long tail: a few accounts buy a lot.
                "_activity": min(50.0, rng.paretovariate(1.3)),
                "_behaviour": rng.choices(("PROMPT", "NORMAL", "SLOW", "VERY_SLOW"), (0.30, 0.48, 0.17, 0.05))[0],
            })
            self.ds.transition("ACCOUNT", self.t["account"][-1], "PROSPECT", created, "SALES_OPS")

    # ---- Quotes and orders -------------------------------------------------------------

    def make_quotes(self) -> None:
        rng = self.stream("quotes")
        accounts = self.t["account"]
        products = self.t["product"]
        days = business_days(cfg.WINDOW_START, self.cutoff - timedelta(days=3))
        day_weights = [1.8 if d.month % 3 == 0 and d.day >= 22 else 1.0 for d in days]  # quarter-end rush
        n = self.scale.quotes
        quote_days = sorted(rng.choices(days, weights=day_weights, k=n))
        buyers = rng.choices(accounts, weights=[a["_activity"] for a in accounts], k=n)
        qty_mu = {"SMB": 1.5, "MID_MARKET": 2.3, "ENTERPRISE": 3.0}
        discounts = {"SMB": (0, 250, 500), "MID_MARKET": (0, 500, 750, 1000), "ENTERPRISE": (500, 1000, 1500, 2000)}
        accept_weight = {"SMB": 0.9, "MID_MARKET": 1.1, "ENTERPRISE": 1.3, "RENEWAL": 1.4, "PARTNER": 1.1,
                         "INBOUND": 1.0, "OUTBOUND": 0.8}

        for day, account in zip(quote_days, buyers):
            channel = rng.choices(("INBOUND", "OUTBOUND", "PARTNER", "RENEWAL"), (0.35, 0.30, 0.15, 0.20))[0]
            quote = {"quote_id": self.ds.new_id("QTE"), "account_id": account["account_id"],
                     "quote_date": day.isoformat(), "valid_until": (day + timedelta(days=30)).isoformat(),
                     "channel": channel, "status": None, "total_paise": 0, "_account": account, "_lines": []}
            line_count = rng.choices((1, 2, 3, 4, 5), (0.35, 0.30, 0.20, 0.10, 0.05))[0]
            discount_bps = rng.choice(discounts[account["segment"]])
            for number, product in enumerate(rng.sample(products, line_count), start=1):
                quantity = min(500, max(1, round(rng.lognormvariate(qty_mu[account["segment"]], 0.8))))
                # Net price is rounded once here; every later amount is exact integer arithmetic.
                net_price = net_unit_price(product["list_price_paise"], discount_bps)
                line = {"quote_line_id": self.ds.new_id("QTL"), "quote_id": quote["quote_id"],
                        "line_number": number, "product_id": product["product_id"], "quantity": quantity,
                        "list_price_paise": product["list_price_paise"], "discount_bps": discount_bps,
                        "net_unit_price_paise": net_price, "line_total_paise": quantity * net_price}
                self.t["quote_line"].append(line)
                quote["_lines"].append(line)
                quote["total_paise"] += line["line_total_paise"]
            weight = accept_weight[account["segment"]] * accept_weight[channel]
            if discount_bps >= 1000:
                weight *= 1.15
            quote["_score"] = rng.random() ** (1.0 / weight)
            self.t["quote"].append(quote)

        # Weighted ranking gives varied acceptance by segment and still exactly the target order count.
        ranked = sorted(self.t["quote"], key=lambda q: (-q["_score"], q["quote_id"]))
        accepted = {q["quote_id"] for q in ranked[: self.scale.orders]}

        for quote in self.t["quote"]:
            day = date.fromisoformat(quote["quote_date"])
            self.ds.transition("QUOTE", quote, "DRAFT", day, "SALES_OPS")
            is_accepted = quote["quote_id"] in accepted
            if not is_accepted and day >= self.cutoff - timedelta(days=6) and rng.random() < 0.25:
                continue  # still being drafted at the cutoff
            sent = day + timedelta(days=rng.randint(0, 1))
            self.ds.transition("QUOTE", quote, "SENT", sent, "SALES_OPS")
            if is_accepted:
                decided = min(sent + timedelta(days=rng.randint(1, 7)), self.cutoff - timedelta(days=1))
                self.ds.transition("QUOTE", quote, "ACCEPTED", decided, "CUSTOMER")
                quote["_accepted_date"] = decided
                continue
            decided = sent + timedelta(days=rng.randint(1, 14))
            valid_until = date.fromisoformat(quote["valid_until"])
            if rng.random() < 0.6 and decided <= self.cutoff:
                self.ds.transition("QUOTE", quote, "REJECTED", decided, "CUSTOMER")
            elif valid_until + timedelta(days=1) <= self.cutoff:
                self.ds.transition("QUOTE", quote, "EXPIRED", valid_until + timedelta(days=1), "SYSTEM")

    def make_orders(self) -> None:
        rng = self.stream("orders")
        accepted = [q for q in self.t["quote"] if q["status"] == "ACCEPTED"]
        accepted.sort(key=lambda q: (q["_accepted_date"], q["quote_id"]))
        for quote in accepted:
            account = quote["_account"]
            order_date = min(quote["_accepted_date"] + timedelta(days=rng.randint(0, 1)), self.cutoff)
            if account["status"] == "PROSPECT":
                self.ds.transition("ACCOUNT", account, "CUSTOMER", order_date, "SALES_OPS")
            order = {"order_id": self.ds.new_id("SO"), "quote_id": quote["quote_id"],
                     "account_id": account["account_id"], "order_date": order_date.isoformat(),
                     "payment_terms_days": account["payment_terms_days"], "status": None,
                     "total_paise": quote["total_paise"], "_account": account, "_fate": "NORMAL"}
            draw = rng.random()
            if draw < 0.025:
                order["_fate"] = "CANCELLED"
            elif self.inject and draw < 0.055:
                order["_fate"] = "SLOW"
            elif self.inject and draw < 0.08:
                order["_fate"] = "BACKORDER"
            for number, quote_line in enumerate(quote["_lines"], start=1):
                line = {"order_line_id": self.ds.new_id("SOL"), "order_id": order["order_id"],
                        "quote_line_id": quote_line["quote_line_id"], "line_number": number,
                        "product_id": quote_line["product_id"], "quantity": quote_line["quantity"],
                        "unit_price_paise": quote_line["net_unit_price_paise"],
                        "line_total_paise": quote_line["line_total_paise"]}
                self.t["order_line"].append(line)
                self.ds.lines_by_order[order["order_id"]].append(line)
            self.t["sales_order"].append(order)
            self.ds.transition("ORDER", order, "CREATED", order_date, "SYSTEM")
            confirmed = order_date + timedelta(days=rng.randint(0, 1))
            if confirmed > self.cutoff:
                continue
            self.ds.transition("ORDER", order, "CONFIRMED", confirmed, "SALES_OPS")
            order["_confirmed_date"] = confirmed
            if order["_fate"] == "CANCELLED":
                cancelled = confirmed + timedelta(days=rng.randint(0, 3))
                if cancelled <= self.cutoff:
                    self.ds.transition("ORDER", order, "CANCELLED", cancelled, "SALES_OPS")

    # ---- Fulfilment --------------------------------------------------------------------

    @staticmethod
    def split_quantities(rng: random.Random, lines: list[dict], parts: int, equal: bool) -> list[dict]:
        """Share each line's quantity across shipments. Empty shipments are dropped."""
        buckets: list[dict] = [{} for _ in range(parts)]
        for line in lines:
            quantity = line["quantity"]
            if equal:
                share = quantity // parts
                for bucket in buckets:
                    bucket[line["order_line_id"]] = share
            elif parts == 1 or quantity < parts or rng.random() < 0.35:
                buckets[rng.randrange(parts)][line["order_line_id"]] = quantity
            else:
                cuts = sorted(rng.sample(range(1, quantity), parts - 1))
                pieces = [b - a for a, b in zip([0] + cuts, cuts + [quantity])]
                for bucket, piece in zip(buckets, pieces):
                    bucket[line["order_line_id"]] = piece
        return [b for b in buckets if b]

    def make_shipments(self) -> None:
        rng = self.stream("shipments")
        plans = []
        for order in self.t["sales_order"]:
            if order["status"] != "CONFIRMED":
                continue
            lines = self.ds.lines_by_order[order["order_id"]]
            parts = rng.choices((1, 2, 3), (0.58, 0.32, 0.10))[0]
            if order["_fate"] == "BACKORDER":
                parts = max(parts, 2)
            # Boundary decoy: two equal shipments billed on two identical-looking but valid invoices.
            equal = (len(lines) == 1 and lines[0]["quantity"] % 2 == 0 and lines[0]["quantity"] >= 2
                     and order["_fate"] == "NORMAL" and rng.random() < 0.08)
            if equal:
                parts = 2
                order["_equal_split"] = True
            buckets = self.split_quantities(rng, lines, parts, equal)
            if order["_fate"] == "BACKORDER" and len(buckets) > 1:
                buckets = buckets[:-1]  # the remainder stays unshipped: a genuine partial shipment
            slip = rng.randint(22, 45) if order["_fate"] == "SLOW" else 0
            planned = order["_confirmed_date"] + timedelta(days=rng.randint(1, 6))
            for index, bucket in enumerate(buckets):
                plans.append({"order": order, "bucket": bucket, "planned": planned,
                              "shipped": planned + timedelta(days=slip), "index": index})
                planned += timedelta(days=rng.randint(2, 6))

        plans.sort(key=lambda p: (p["shipped"], p["order"]["order_id"], p["index"]))
        carriers = cfg.ENUMS[("shipment", "carrier")]
        for plan in plans:
            order = plan["order"]
            shipment = {"shipment_id": self.ds.new_id("SHP"), "order_id": order["order_id"],
                        "carrier": rng.choice(carriers), "planned_date": plan["planned"].isoformat(),
                        "shipped_date": None, "delivered_date": None, "status": None, "_lines": plan["bucket"]}
            self.t["shipment"].append(shipment)
            self.ds.shipments_by_order[order["order_id"]].append(shipment)
            for order_line_id, quantity in plan["bucket"].items():
                self.t["shipment_line"].append({"shipment_line_id": self.ds.new_id("SHL"),
                                                "shipment_id": shipment["shipment_id"],
                                                "order_line_id": order_line_id, "quantity": quantity})
            self.ds.transition("SHIPMENT", shipment, "PLANNED", order["_confirmed_date"], "SYSTEM")
            if plan["shipped"] > self.cutoff:
                continue
            shipment["shipped_date"] = plan["shipped"].isoformat()
            self.ds.transition("SHIPMENT", shipment, "SHIPPED", plan["shipped"], "SYSTEM")
            delivered = plan["shipped"] + timedelta(days=rng.randint(1, 6))
            if delivered <= self.cutoff:
                shipment["delivered_date"] = delivered.isoformat()
                self.ds.transition("SHIPMENT", shipment, "DELIVERED", delivered, "CUSTOMER")

        for order in self.t["sales_order"]:
            shipped_so_far: Counter = Counter()
            ordered = {l["order_line_id"]: l["quantity"] for l in self.ds.lines_by_order[order["order_id"]]}
            for shipment in self.ds.shipments_by_order[order["order_id"]]:
                if shipment["shipped_date"] is None:
                    continue
                shipped_so_far.update(shipment["_lines"])
                when = date.fromisoformat(shipment["shipped_date"])
                if all(shipped_so_far[k] >= v for k, v in ordered.items()):
                    self.ds.transition("ORDER", order, "FULFILLED", when, "SYSTEM")
                    order["_fulfilled_date"] = when
                elif order["status"] != "PARTIALLY_FULFILLED":
                    self.ds.transition("ORDER", order, "PARTIALLY_FULFILLED", when, "SYSTEM")

    # ---- Invoicing ---------------------------------------------------------------------

    def make_invoices(self) -> None:
        rng = self.stream("invoices")
        void_count = self.scale.scaled(40, floor=3)
        duplicates = self.scale.scenario_count("duplicate_invoice") if self.inject else 0
        target = self.scale.invoices - duplicates - void_count

        groups = []
        for order in self.t["sales_order"]:
            for shipment in self.ds.shipments_by_order[order["order_id"]]:
                if shipment["shipped_date"] is None:
                    continue
                lag = rng.randint(0, 5)
                if self.inject and rng.random() < 0.03:
                    lag += rng.randint(8, 20)  # slow billing, picked up by the invoicing-delay rule
                invoice_date = date.fromisoformat(shipment["shipped_date"]) + timedelta(days=lag)
                if invoice_date <= self.cutoff:
                    groups.append({"order": order, "shipments": [shipment], "date": invoice_date, "lag": lag})

        # Consolidate shipments onto one invoice until the invoice count hits the target exactly.
        by_order = defaultdict(list)
        for group in groups:
            by_order[group["order"]["order_id"]].append(group)
        mergeable = [oid for oid, g in by_order.items() if len(g) > 1 and not g[0]["order"].get("_equal_split")]
        rng.shuffle(mergeable)
        excess = len(groups) - target
        if excess < 0:
            raise RuntimeError(f"only {len(groups)} invoiceable shipments for a target of {target}")
        merged_away = set()
        while excess > 0:
            if not mergeable:
                raise RuntimeError("ran out of multi-shipment orders while consolidating invoices")
            order_id = mergeable.pop()
            first, second = by_order[order_id][0], by_order[order_id][1]
            # A consolidated invoice goes out in time for its oldest shipment, or not at all.
            oldest = date.fromisoformat(first["shipments"][0]["shipped_date"])
            latest = date.fromisoformat(second["shipments"][-1]["shipped_date"])
            on_time_by = oldest + timedelta(days=cfg.SLA_SHIPMENT_TO_INVOICE_DAYS)
            if latest > on_time_by:
                continue
            by_order[order_id].pop(0)
            second["date"] = min(second["date"], on_time_by)
            second["shipments"] = first["shipments"] + second["shipments"]
            merged_away.add(id(first))
            if len(by_order[order_id]) > 1:
                mergeable.insert(0, order_id)
            excess -= 1
        groups = [g for g in groups if id(g) not in merged_away]

        # Voided and reissued invoices: legitimate corrections that must not look like duplicates.
        eligible = [g for g in groups if g["lag"] <= 3 and g["date"] <= self.cutoff - timedelta(days=5)
                    and not g["order"].get("_equal_split")]
        for original in rng.sample(eligible, void_count):
            replacement = {"order": original["order"], "shipments": original["shipments"],
                           "date": original["date"] + timedelta(days=rng.randint(1, 3)), "lag": 0,
                           "replaces": original}
            original["voided_on"] = replacement["date"]
            groups.append(replacement)

        groups.sort(key=lambda g: (g["date"], g["order"]["order_id"], g["shipments"][0]["shipment_id"]))
        for group in groups:
            self._create_invoice(group)

    def _create_invoice(self, group: dict) -> None:
        order = group["order"]
        invoice_date = group["date"]
        quantities: Counter = Counter()
        for shipment in group["shipments"]:
            quantities.update(shipment["_lines"])
        invoice = {"invoice_id": self.ds.new_id("INV"), "order_id": order["order_id"],
                   "account_id": order["account_id"], "invoice_date": invoice_date.isoformat(),
                   "due_date": (invoice_date + timedelta(days=order["payment_terms_days"])).isoformat(),
                   "status": None, "total_paise": 0, "replaces_invoice_id": None,
                   "_order": order, "_fate": "NORMAL", "_dispute": None}
        group["invoice"] = invoice
        if "replaces" in group:
            invoice["replaces_invoice_id"] = group["replaces"]["invoice"]["invoice_id"]
        number = 0
        for line in self.ds.lines_by_order[order["order_id"]]:
            quantity = quantities.get(line["order_line_id"], 0)
            if quantity == 0:
                continue
            number += 1
            invoice_line = {"invoice_line_id": None, "invoice_id": invoice["invoice_id"],
                            "order_line_id": line["order_line_id"], "line_number": number, "quantity": quantity,
                            "unit_price_paise": line["unit_price_paise"],
                            "line_total_paise": quantity * line["unit_price_paise"]}
            self.t["invoice_line"].append(invoice_line)
            self.ds.lines_by_invoice[invoice["invoice_id"]].append(invoice_line)
            invoice["total_paise"] += invoice_line["line_total_paise"]
        for shipment in group["shipments"]:
            self.t["invoice_shipment"].append({"invoice_id": invoice["invoice_id"],
                                               "shipment_id": shipment["shipment_id"]})
            self.ds.shipment_ids_by_invoice[invoice["invoice_id"]].append(shipment["shipment_id"])
        self.t["invoice"].append(invoice)
        self.ds.invoices_by_order[order["order_id"]].append(invoice)
        self.ds.transition("INVOICE", invoice, "DRAFT", invoice_date, "SYSTEM")
        self.ds.transition("INVOICE", invoice, "ISSUED", invoice_date, "SYSTEM")
        self.ds.post_ledger(invoice, "INVOICE_POSTED", invoice["total_paise"], invoice_date, invoice["invoice_id"])
        if "voided_on" in group:
            invoice["_fate"] = "VOID"
            self.ds.transition("INVOICE", invoice, "VOID", group["voided_on"], "SYSTEM_ADMIN")
            self.ds.post_ledger(invoice, "INVOICE_VOIDED", invoice["total_paise"], group["voided_on"],
                                invoice["invoice_id"])

    def plan_invoice_fates(self) -> None:
        """Decide how each invoice's collection story ends, before any payment exists."""
        rng = self.stream("invoice-fates")
        pool = [i for i in self.t["invoice"] if i["_fate"] == "NORMAL"]
        rng.shuffle(pool)
        by_due = defaultdict(list)
        for invoice in pool:
            by_due[date.fromisoformat(invoice["due_date"])].append(invoice)

        def assign(candidates: list[dict], count: int, fate: str) -> list[dict]:
            chosen = [i for i in candidates if i["_fate"] == "NORMAL"][:count]
            for invoice in chosen:
                invoice["_fate"] = fate
            return chosen

        # Boundary decoys that the rules must NOT flag.
        assign(by_due[self.cutoff - timedelta(days=cfg.LONG_OVERDUE_DAYS)], self.scale.scaled(12, 2), "BOUNDARY_90")
        settled_window = cfg.SHORT_PAY_MIN_DAYS_PAST_DUE + 15  # room for the last instalment to go stale
        old_enough = [i for i in pool
                      if date.fromisoformat(i["due_date"]) <= self.cutoff - timedelta(days=settled_window)]
        assign(old_enough, self.scale.scaled(15, 3), "RESIDUAL")
        if not self.inject:
            return

        long_due = self.scale.scenario_count("long_overdue")
        boundary = assign(by_due[self.cutoff - timedelta(days=cfg.LONG_OVERDUE_DAYS + 1)],
                          self.scale.scaled(12, 2), "LONG_ZERO")
        overdue_pool = [i for i in pool if date.fromisoformat(i["due_date"])
                        < self.cutoff - timedelta(days=cfg.LONG_OVERDUE_DAYS + 1)]
        remaining = long_due - len(boundary)
        partial = round(remaining * 0.3)
        assign(overdue_pool, partial, "LONG_PARTIAL")
        assign(overdue_pool, remaining - partial, "LONG_ZERO")
        short_pool = [i for i in old_enough if i["total_paise"] >= 500_000]
        assign(short_pool, self.scale.scenario_count("short_payment"), "SHORT_PAY")

    def make_disputes(self) -> None:
        rng = self.stream("disputes")
        candidates = [i for i in self.t["invoice"] if i["_fate"] == "NORMAL"]
        recent_start = self.cutoff - timedelta(days=35)
        recent = [i for i in candidates if date.fromisoformat(i["invoice_date"]) >= recent_start]
        forced_open = rng.sample(recent, min(len(recent), self.scale.scenario_count("dispute_not_in_ar") * 3))
        forced_ids = {i["invoice_id"] for i in forced_open}
        others = [i for i in candidates if i["invoice_id"] not in forced_ids]
        plans = [(i, True) for i in forced_open] + [(i, False) for i in rng.sample(others, self.scale.scaled(280))]

        reasons = cfg.ENUMS[("dispute", "reason")]
        schedule = []
        for invoice, stay_open in plans:
            invoice_date = date.fromisoformat(invoice["invoice_date"])
            opened = min(invoice_date + timedelta(days=rng.randint(2, 20)), self.cutoff)
            total = invoice["total_paise"]
            disputed = total if rng.random() < 0.25 else max(100, round(total * rng.uniform(0.05, 0.6)))
            review = opened + timedelta(days=rng.randint(1, 5))
            outcome = rng.choices(("RESOLVED_CREDIT", "RESOLVED_NO_CREDIT", "WITHDRAWN"), (0.45, 0.35, 0.20))[0]
            close = review + timedelta(days=rng.randint(1, 15) if outcome == "WITHDRAWN" else rng.randint(5, 35))
            if stay_open:
                close = self.cutoff + timedelta(days=30)
            credited = round(disputed * rng.uniform(0.5, 1.0)) if outcome == "RESOLVED_CREDIT" else 0
            schedule.append({"invoice": invoice, "opened": opened, "review": review, "close": close,
                             "outcome": outcome, "disputed": disputed, "credited": credited,
                             "reason": rng.choice(reasons)})
        schedule.sort(key=lambda s: (s["opened"], s["invoice"]["invoice_id"]))
        for plan in schedule:
            invoice = plan["invoice"]
            dispute = {"dispute_id": self.ds.new_id("DSP"), "invoice_id": invoice["invoice_id"],
                       "account_id": invoice["account_id"], "reason": plan["reason"],
                       "opened_date": plan["opened"].isoformat(), "resolved_date": None,
                       "disputed_paise": plan["disputed"], "credited_paise": 0, "status": None, "_plan": plan}
            self.t["dispute"].append(dispute)
            invoice["_dispute"] = dispute

    # ---- Payments ----------------------------------------------------------------------

    def _schedule_chunks(self, rng: random.Random, invoice: dict, amount: int, final: date) -> list[dict]:
        """Split an amount into instalments that finish on the final date."""
        invoice_date = date.fromisoformat(invoice["invoice_date"])
        count = 1 if amount < 200_000 else rng.choices((1, 2, 3, 4), (0.35, 0.30, 0.20, 0.15))[0]
        weights = [rng.uniform(0.5, 1.5) for _ in range(count)]
        total_weight = sum(weights)
        amounts = [int(amount * w / total_weight) for w in weights[:-1]]
        amounts.append(amount - sum(amounts))
        chunks, day = [], final
        for share in reversed(amounts):
            chunks.append({"invoice": invoice, "date": max(day, invoice_date), "amount": share})
            day -= timedelta(days=rng.randint(4, 12))
        return chunks

    def _final_payment_date(self, rng: random.Random, invoice: dict) -> date:
        due = date.fromisoformat(invoice["due_date"])
        behaviour = invoice["_order"]["_account"]["_behaviour"]
        latest = cfg.LONG_OVERDUE_DAYS - 10  # normal customers stay short of long overdue
        low, high = {"PROMPT": (-12, 3), "NORMAL": (-5, min(15, latest)), "SLOW": (5, min(45, latest)),
                     "VERY_SLOW": (min(46, latest - 5), latest)}[behaviour]
        return max(date.fromisoformat(invoice["invoice_date"]), due + timedelta(days=rng.randint(low, high)))

    def _plan_invoice_chunks(self, rng: random.Random, invoice: dict) -> list[dict]:
        fate = invoice["_fate"]
        total = invoice["total_paise"]
        due = date.fromisoformat(invoice["due_date"])
        if fate in ("VOID", "LONG_ZERO", "BOUNDARY_90"):
            return []
        if fate == "SHORT_PAY":
            shortfall = max(cfg.BALANCE_TOLERANCE_PAISE + 1_000, round(total * rng.uniform(0.01, 0.08)))
            return self._schedule_chunks(rng, invoice, total - shortfall, due + timedelta(days=rng.randint(0, 10)))
        if fate == "LONG_PARTIAL":
            paid = round(total * rng.uniform(0.2, 0.6))
            return self._schedule_chunks(rng, invoice, paid, due + timedelta(days=rng.randint(-5, 20)))
        if fate == "RESIDUAL":
            residual = rng.randint(100, cfg.BALANCE_TOLERANCE_PAISE)
            return self._schedule_chunks(rng, invoice, total - residual, due + timedelta(days=rng.randint(-5, 10)))

        dispute = invoice["_dispute"]
        if dispute is None:
            return self._schedule_chunks(rng, invoice, total, self._final_payment_date(rng, invoice))
        plan = dispute["_plan"]
        chunks = []
        undisputed = total - plan["disputed"]
        if undisputed > 0:
            chunks = self._schedule_chunks(rng, invoice, undisputed, self._final_payment_date(rng, invoice))
        remainder = plan["disputed"] - plan["credited"]
        if remainder > 0:
            # The disputed part is settled last, so a customer never looks stalled mid-way.
            settle = plan["close"] + timedelta(days=rng.randint(3, 10))
            settle = max([settle] + [c["date"] for c in chunks])
            chunks.append({"invoice": invoice, "amount": remainder, "date": settle})
        return chunks

    def make_payments(self) -> None:
        rng = self.stream("payments")
        chunks = []
        for invoice in self.t["invoice"]:
            chunks.extend(c for c in self._plan_invoice_chunks(rng, invoice) if c["date"] <= self.cutoff)

        # Bulk remittance: one payment settling chunks from several invoices of one account.
        by_account = defaultdict(list)
        for chunk in chunks:
            by_account[chunk["invoice"]["account_id"]].append(chunk)
        groups: list[list[dict]] = []
        for account_id in sorted(by_account):
            ordered = sorted(by_account[account_id], key=lambda c: (c["date"], c["invoice"]["invoice_id"]))
            current = [ordered[0]]
            for chunk in ordered[1:]:
                combinable = (len(current) < 3 and (chunk["date"] - current[-1]["date"]).days <= 3
                              and all(c["invoice"] is not chunk["invoice"] for c in current))
                if combinable and rng.random() < 0.10:
                    current.append(chunk)
                else:
                    groups.append(current)
                    current = [chunk]
            groups.append(current)

        unapplied = self.scale.scaled(150, floor=5)
        reversed_count = self.scale.scaled(130, floor=5)
        needed = self.scale.payments - unapplied - reversed_count
        groups = self._fit_payment_count(rng, groups, needed)

        customers = [a for a in self.t["account"] if a["status"] == "CUSTOMER"]
        extras = []
        for _ in range(unapplied):
            day = self.cutoff - timedelta(days=rng.randrange(20))
            extras.append({"date": day, "account": rng.choice(customers), "kind": "UNAPPLIED"})
        window_days = (self.cutoff - cfg.WINDOW_START).days
        for _ in range(reversed_count):
            day = cfg.WINDOW_START + timedelta(days=rng.randrange(window_days - 10))
            extras.append({"date": day, "account": rng.choice(customers), "kind": "REVERSED"})

        records = []
        for group in groups:
            records.append({"date": max(c["date"] for c in group), "account_id": group[0]["invoice"]["account_id"],
                            "chunks": group, "sort": group[0]["invoice"]["invoice_id"]})
        for extra in extras:
            records.append({"date": extra["date"], "account_id": extra["account"]["account_id"], "chunks": [],
                            "kind": extra["kind"], "sort": ""})
        records.sort(key=lambda r: (r["date"], r["account_id"], r["sort"]))

        methods = cfg.ENUMS[("payment", "method")]
        for record in records:
            day = record["date"]
            amount = sum(c["amount"] for c in record["chunks"]) or rng.randint(500_000, 20_000_000)
            sequence = self.ds.counters["PAY"] + 1
            payment = {"payment_id": self.ds.new_id("PAY"), "account_id": record["account_id"],
                       "payment_date": day.isoformat(), "amount_paise": amount,
                       "method": rng.choices(methods, (0.55, 0.25, 0.15, 0.05))[0],
                       "bank_reference": f"UTR{sequence:06d}{rng.randrange(10 ** 8):08d}", "status": None}
            self.t["payment"].append(payment)
            self.ds.transition("PAYMENT", payment, "RECEIVED", day, "SYSTEM")
            if record.get("kind") == "REVERSED":
                self.ds.transition("PAYMENT", payment, "REVERSED", day + timedelta(days=rng.randint(1, 5)), "SYSTEM")
            for chunk in record["chunks"]:
                extra_days = rng.randint(1, 2) if rng.random() < 0.05 else 0
                chunk["applied"] = min(day + timedelta(days=extra_days), self.cutoff)
                chunk["payment"] = payment
                self.applied_chunks.append(chunk)

    def _fit_payment_count(self, rng: random.Random, groups: list[list[dict]], needed: int) -> list[list[dict]]:
        """Merge or split instalments so the payment table hits the target count exactly."""
        order = list(range(len(groups)))
        rng.shuffle(order)
        singles = [groups[i] for i in order if len(groups[i]) == 1]
        if len(groups) < needed:
            for group in singles:
                if len(groups) == needed:
                    break
                chunk = group[0]
                later = chunk["date"] + timedelta(days=rng.randint(1, 4))
                if chunk["amount"] >= 200_000 and later <= self.cutoff and chunk["invoice"]["_fate"] == "NORMAL":
                    half = chunk["amount"] // 2
                    chunk["amount"] -= half
                    groups.append([{"invoice": chunk["invoice"], "date": later, "amount": half}])
        elif len(groups) > needed:
            by_invoice = defaultdict(list)
            for group in singles:
                by_invoice[group[0]["invoice"]["invoice_id"]].append(group)
            removed = set()
            for invoice_id in sorted(by_invoice):
                siblings = by_invoice[invoice_id]
                while len(siblings) > 1 and len(groups) - len(removed) > needed:
                    drop = siblings.pop()
                    keep = siblings[-1]
                    keep[0]["amount"] += drop[0]["amount"]
                    keep[0]["date"] = max(keep[0]["date"], drop[0]["date"])
                    removed.add(id(drop))
            groups = [g for g in groups if id(g) not in removed]
        if len(groups) != needed:
            raise RuntimeError(f"could not fit payments: {len(groups)} groups for {needed} needed")
        return groups

    # ---- Receivables replay ------------------------------------------------------------

    def replay_receivables(self) -> None:
        """Replay each invoice's payments and dispute steps in date order.

        This is the only place invoice and dispute statuses advance, so the ledger,
        allocations and status history all come from one sequence of facts.
        """
        by_invoice = defaultdict(list)
        for chunk in self.applied_chunks:
            by_invoice[chunk["invoice"]["invoice_id"]].append(chunk)

        for invoice in self.t["invoice"]:
            if invoice["_fate"] == "VOID":
                continue
            steps = [(c["applied"], 3, c["payment"]["payment_id"], "payment", c)
                     for c in by_invoice[invoice["invoice_id"]]]
            dispute = invoice["_dispute"]
            if dispute is not None:
                plan = dispute["_plan"]
                steps.append((plan["opened"], 0, "", "open", dispute))
                if plan["review"] <= self.cutoff:
                    steps.append((plan["review"], 1, "", "review", dispute))
                if plan["close"] <= self.cutoff:
                    steps.append((plan["close"], 2, "", "close", dispute))
            for when, _, _, kind, item in sorted(steps, key=lambda s: s[:3]):
                getattr(self, f"_step_{kind}")(invoice, item, when)

        # Payment status follows its allocations, so it runs after every chunk is applied.
        for payment in self.t["payment"]:
            allocations = self.ds.allocations_by_payment[payment["payment_id"]]
            if allocations:
                last = max(date.fromisoformat(a["allocated_date"]) for a in allocations)
                self.ds.transition("PAYMENT", payment, "ALLOCATED", last, "SYSTEM")

    def _step_payment(self, invoice: dict, chunk: dict, when: date) -> None:
        self.ds.add_allocation(chunk["payment"], invoice, chunk["amount"], when)
        if invoice["status"] == "DISPUTED":
            return
        if self.ds.balance(invoice) == 0:
            self.ds.transition("INVOICE", invoice, "PAID", when, "SYSTEM")
            invoice["_settled_date"] = when
        elif invoice["status"] != "PARTIALLY_PAID":
            self.ds.transition("INVOICE", invoice, "PARTIALLY_PAID", when, "SYSTEM")

    def _step_open(self, invoice: dict, dispute: dict, when: date) -> None:
        self.ds.transition("DISPUTE", dispute, "OPEN", when, "CUSTOMER")
        self.ds.post_ledger(invoice, "DISPUTE_HOLD", dispute["disputed_paise"], when, dispute["dispute_id"])
        if invoice["status"] in ("ISSUED", "PARTIALLY_PAID"):
            self.ds.transition("INVOICE", invoice, "DISPUTED", when, "SUPPORT_AGENT")

    def _step_review(self, invoice: dict, dispute: dict, when: date) -> None:
        self.ds.transition("DISPUTE", dispute, "UNDER_REVIEW", when, "SUPPORT_AGENT")

    def _step_close(self, invoice: dict, dispute: dict, when: date) -> None:
        plan = dispute["_plan"]
        actor = "CUSTOMER" if plan["outcome"] == "WITHDRAWN" else "ANALYST"
        self.ds.transition("DISPUTE", dispute, plan["outcome"], when, actor)
        dispute["resolved_date"] = when.isoformat()
        self.ds.post_ledger(invoice, "DISPUTE_RELEASE", dispute["disputed_paise"], when, dispute["dispute_id"])
        if plan["credited"]:
            dispute["credited_paise"] = plan["credited"]
            self.ds.post_ledger(invoice, "CREDIT_MEMO", plan["credited"], when, dispute["dispute_id"])
        if invoice["status"] != "DISPUTED":
            return
        if self.ds.balance(invoice) == 0:
            self.ds.transition("INVOICE", invoice, "PAID", when, "ANALYST")
            invoice["_settled_date"] = when
        elif self.ds.allocations_by_invoice[invoice["invoice_id"]]:
            self.ds.transition("INVOICE", invoice, "PARTIALLY_PAID", when, "ANALYST")
        else:
            self.ds.transition("INVOICE", invoice, "ISSUED", when, "ANALYST")

    def advance_orders(self) -> None:
        """Move fulfilled orders to INVOICED and CLOSED once the facts support it."""
        for order in self.t["sales_order"]:
            if order["status"] != "FULFILLED":
                continue
            shipped = {s["shipment_id"] for s in self.ds.shipments_by_order[order["order_id"]] if s["shipped_date"]}
            invoices = [i for i in self.ds.invoices_by_order[order["order_id"]] if i["status"] != "VOID"]
            covered = {sid for i in invoices for sid in self.ds.shipment_ids_by_invoice[i["invoice_id"]]}
            if shipped - covered:
                continue
            last_invoice = max(date.fromisoformat(i["invoice_date"]) for i in invoices)
            invoiced_on = max(order["_fulfilled_date"], last_invoice)
            self.ds.transition("ORDER", order, "INVOICED", invoiced_on, "SYSTEM")
            if all(self.ds.balance(i) == 0 for i in invoices):
                settled = max(i["_settled_date"] for i in invoices)
                self.ds.transition("ORDER", order, "CLOSED", max(invoiced_on, settled), "SALES_OPS")


def generate(scale: cfg.Scale, seed: int = cfg.DEFAULT_SEED, cutoff: date = cfg.CUTOFF,
             inject: bool = True) -> Dataset:
    """Build a dataset. With inject=False the result is the clean negative-control world."""
    from .anomaly_injection import inject_anomalies

    generator = Generator(scale, seed, cutoff, inject)
    dataset = generator.run()
    if inject:
        inject_anomalies(dataset, scale, seed)
    dataset.finalize()
    return dataset
