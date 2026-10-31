"""Generator tests: exact volumes, determinism, and realistic variation."""
from __future__ import annotations

import re
from collections import Counter, defaultdict

import pytest

from src import config as cfg
from src.database import build_database, connect, export_all
from src.generator import generate


@pytest.mark.parametrize("scale_name", ["starter", "full"])
def test_required_volumes_are_exact(scale_name):
    scale = cfg.SCALES[scale_name]
    tables = generate(scale).tables
    assert len(tables["quote"]) == scale.quotes
    assert len(tables["sales_order"]) == scale.orders
    assert len(tables["invoice"]) == scale.invoices
    assert len(tables["payment"]) == scale.payments
    assert len(tables["status_event"]) > scale.payments


def test_full_scale_meets_the_problem_statement():
    full = cfg.SCALES["full"]
    assert (full.quotes, full.orders, full.invoices, full.payments) == (10_000, 7_000, 8_000, 15_000)


def test_same_seed_gives_identical_rows():
    scale = cfg.SCALES["starter"]
    first, second = generate(scale), generate(scale)
    for table in first.tables:
        left = [{k: v for k, v in row.items() if not k.startswith("_")} for row in first.tables[table]]
        right = [{k: v for k, v in row.items() if not k.startswith("_")} for row in second.tables[table]]
        assert left == right, table
    assert first.ground_truth == second.ground_truth


def test_different_seed_gives_different_data():
    scale = cfg.SCALES["starter"]
    a = generate(scale, seed=1).tables["invoice"]
    b = generate(scale, seed=2).tables["invoice"]
    assert [i["total_paise"] for i in a] != [i["total_paise"] for i in b]


@pytest.mark.parametrize("table,column,pattern", [
    ("quote", "quote_id", r"^QTE-2026-\d{6}$"),
    ("sales_order", "order_id", r"^SO-2026-\d{6}$"),
    ("shipment", "shipment_id", r"^SHP-2026-\d{6}$"),
    ("invoice", "invoice_id", r"^INV-2026-\d{6}$"),
    ("payment", "payment_id", r"^PAY-2026-\d{6}$"),
    ("dispute", "dispute_id", r"^DSP-2026-\d{6}$"),
])
def test_id_conventions(starter_dataset, table, column, pattern):
    rows = starter_dataset.tables[table]
    assert all(re.match(pattern, r[column]) for r in rows)
    first = sorted(r[column] for r in rows)[0]
    assert first.endswith("-000001")


def test_generator_uses_exact_integer_money(starter_dataset):
    for table, column in (("quote_line", "line_total_paise"), ("invoice", "total_paise"), ("payment", "amount_paise")):
        assert all(isinstance(r[column], int) for r in starter_dataset.tables[table])


def test_acceptance_varies_by_segment(starter_dataset):
    totals, accepted = Counter(), Counter()
    for quote in starter_dataset.tables["quote"]:
        segment = quote["_account"]["segment"]
        totals[segment] += 1
        accepted[segment] += quote["status"] == "ACCEPTED"
    rates = {s: accepted[s] / totals[s] for s in totals}
    assert len(rates) == 3
    assert max(rates.values()) - min(rates.values()) > 0.03


def test_required_variety_exists(starter_dataset):
    tables = starter_dataset.tables
    shipments_per_order = Counter(s["order_id"] for s in tables["shipment"])
    invoices_per_order = Counter(i["order_id"] for i in tables["invoice"] if i["status"] != "VOID")
    allocations_per_payment = Counter(a["payment_id"] for a in tables["payment_allocation"])
    payments_per_invoice = Counter(a["invoice_id"] for a in tables["payment_allocation"])
    assert max(shipments_per_order.values()) >= 2, "partial shipments"
    assert max(invoices_per_order.values()) >= 2, "multiple invoices per order"
    assert max(allocations_per_payment.values()) >= 2, "bulk remittance"
    assert max(payments_per_invoice.values()) >= 3, "instalments"
    assert {r["status"] for r in tables["invoice"]} >= {"ISSUED", "PARTIALLY_PAID", "PAID", "DISPUTED", "VOID"}
    assert {r["status"] for r in tables["payment"]} == {"RECEIVED", "ALLOCATED", "REVERSED"}
    assert {r["status"] for r in tables["sales_order"]} >= {"CONFIRMED", "PARTIALLY_FULFILLED", "CLOSED", "CANCELLED"}


def test_scenario_targets_do_not_overlap_between_mutating_scenarios(starter_dataset):
    orders_by_issue = defaultdict(set)
    order_of_invoice = {i["invoice_id"]: i["order_id"] for i in starter_dataset.tables["invoice"]}
    order_of_line = {l["order_line_id"]: l["order_id"] for l in starter_dataset.tables["order_line"]}
    for label in starter_dataset.ground_truth:
        if label["issue_type"] in ("OVERBILLING", "UNDERBILLING"):
            orders_by_issue[label["issue_type"]].add(order_of_line[label["primary_id"]])
        elif label["issue_type"] == "CLOSED_ORDER_UNPAID":
            orders_by_issue[label["issue_type"]].add(label["primary_id"])
        elif label["issue_type"] == "DUPLICATE_INVOICE":
            orders_by_issue[label["issue_type"]].add(order_of_invoice[label["primary_id"]])
    issues = list(orders_by_issue)
    for i, left in enumerate(issues):
        for right in issues[i + 1:]:
            assert not orders_by_issue[left] & orders_by_issue[right], (left, right)


def test_all_five_mandatory_scenarios_are_labelled(starter_dataset):
    issue_types = {g["issue_type"] for g in starter_dataset.ground_truth}
    assert {"OVERBILLING", "DUPLICATE_ALLOCATION", "CLOSED_ORDER_UNPAID", "ILLEGAL_TRANSITION",
            "DISPUTE_NOT_IN_AR"} <= issue_types


def test_clean_world_has_no_labels():
    assert generate(cfg.SCALES["starter"], inject=False).ground_truth == []


def test_exports_are_written_in_three_formats(tmp_path, starter_dataset):
    db_file = tmp_path / "o2c.db"
    build_database(starter_dataset, db_file, "starter", True)
    tables = export_all(db_file, tmp_path)
    assert (tmp_path / "csv" / "invoice.csv").exists()
    assert (tmp_path / "json" / "invoice.json").exists()
    assert tables["invoice"]["rows"] == 800
    seed = (tmp_path / "seed.sql").read_text(encoding="utf-8")
    assert seed.count("INSERT INTO invoice VALUES") == 800


def test_sql_seed_rebuilds_the_same_database(tmp_path, starter_dataset):
    db_file = tmp_path / "o2c.db"
    build_database(starter_dataset, db_file, "starter", True)
    export_all(db_file, tmp_path)
    rebuilt = connect(tmp_path / "rebuilt.db")
    rebuilt.executescript(cfg.SCHEMA_SQL.read_text(encoding="utf-8"))
    rebuilt.executescript((tmp_path / "seed.sql").read_text(encoding="utf-8"))
    original = connect(db_file)
    for table in ("quote", "invoice", "payment", "status_event"):
        assert (rebuilt.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                == original.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    rebuilt.close()
    original.close()
