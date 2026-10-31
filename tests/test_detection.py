"""Rule tests: bend one fact in a clean chain and check the rule fires, or stays quiet, at the edge."""
from __future__ import annotations

import csv
import json
from datetime import timedelta
from pathlib import Path

import pytest

from src import config as cfg
from src.detector import Detector
from src.evaluation import evaluate, load_ground_truth
from tests.conftest import ACC, INV, IVL, PAY, PRICE, QTY, SHP, SO, SOL, TOTAL


def days_before_cutoff(days: int) -> str:
    return (cfg.CUTOFF - timedelta(days=days)).isoformat()


def issues(conn) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for item in Detector(conn).run():
        grouped.setdefault(item["issue_type"], []).append(item)
    return grouped


def set_billed(conn, quantity: int) -> None:
    total = quantity * PRICE
    conn.execute("UPDATE invoice_line SET quantity = ?, line_total_paise = ? WHERE invoice_line_id = ?", (quantity, total, IVL))
    conn.execute("UPDATE invoice SET total_paise = ? WHERE invoice_id = ?", (total, INV))
    conn.execute("UPDATE ar_ledger_entry SET amount_paise = ? WHERE entry_type = 'INVOICE_POSTED'", (total,))
    conn.execute("UPDATE ar_ledger_entry SET amount_paise = ? WHERE entry_type = 'PAYMENT_APPLIED'", (total,))
    conn.execute("UPDATE payment_allocation SET allocated_paise = ?", (total,))
    conn.execute("UPDATE payment SET amount_paise = ?", (total,))


def add_invoice(conn, number: int, quantity: int, invoice_date: str, shipment_id: str | None, status: str = "ISSUED") -> str:
    invoice_id = f"INV-2026-{number:06d}"
    total = quantity * PRICE
    due = "2026-04-30"
    conn.execute("INSERT INTO invoice VALUES (?, ?, ?, ?, ?, ?, ?, NULL)", (invoice_id, SO, ACC, invoice_date, due, status, total))
    conn.execute("INSERT INTO invoice_line VALUES (?, ?, ?, 1, ?, ?, ?)",
                 (f"IVL-2026-{number:06d}", invoice_id, SOL, quantity, PRICE, total))
    if shipment_id:
        conn.execute("INSERT INTO invoice_shipment VALUES (?, ?)", (invoice_id, shipment_id))
    conn.execute("INSERT INTO ar_ledger_entry VALUES (?, ?, 'INVOICE_POSTED', ?, ?, ?)",
                 (f"ARL-2026-{number + 10:06d}", invoice_id, total, invoice_date, invoice_id))
    return invoice_id


def make_open_invoice(conn, due_date: str, paid: int = 0, last_payment: str | None = None) -> None:
    """Turn the chain's invoice into an unpaid or part-paid one due on a chosen date."""
    conn.execute("UPDATE invoice SET due_date = ?, status = 'ISSUED' WHERE invoice_id = ?", (due_date, INV))
    conn.execute("UPDATE sales_order SET status = 'INVOICED' WHERE order_id = ?", (SO,))
    if paid:
        conn.execute("UPDATE payment_allocation SET allocated_paise = ?, allocated_date = ?", (paid, last_payment))
        conn.execute("UPDATE payment SET amount_paise = ?, payment_date = ?", (paid, last_payment))
        conn.execute("UPDATE ar_ledger_entry SET amount_paise = ? WHERE entry_type = 'PAYMENT_APPLIED'", (paid,))
    else:
        conn.execute("DELETE FROM ar_ledger_entry WHERE entry_type = 'PAYMENT_APPLIED'")
        conn.execute("DELETE FROM payment_allocation")
        conn.execute("DELETE FROM payment")


def add_dispute(conn, status: str, disputed: int, hold: int | None, credited: int = 0, resolved: str | None = None) -> str:
    dispute_id = "DSP-2026-000001"
    conn.execute("INSERT INTO dispute VALUES (?, ?, ?, 'PRICING', '2026-03-10', ?, ?, ?, ?)",
                 (dispute_id, INV, ACC, resolved, disputed, credited, status))
    if hold is not None:
        conn.execute("INSERT INTO ar_ledger_entry VALUES ('ARL-2026-000050', ?, 'DISPUTE_HOLD', ?, '2026-03-10', ?)",
                     (INV, hold, dispute_id))
    return dispute_id


def test_clean_chain_has_no_findings(chain):
    assert Detector(chain).run() == []


def test_invoice_for_an_unshipped_shipment_is_reported_not_a_crash(chain):
    chain.execute("UPDATE shipment SET status = 'PLANNED', shipped_date = NULL, delivered_date = NULL")
    found = issues(chain)
    assert "OVERBILLING" in found
    assert "INVOICING_DELAY" not in found


# ---- R01 overbilling ----------------------------------------------------------------------

def test_billing_exactly_what_shipped_is_not_overbilling(chain):
    set_billed(chain, QTY)
    assert "OVERBILLING" not in issues(chain)


def test_billing_one_unit_more_than_shipped_is_overbilling(chain):
    set_billed(chain, QTY + 1)
    found = issues(chain)["OVERBILLING"]
    assert len(found) == 1
    assert found[0]["source_id"] == SOL
    assert found[0]["impact_paise"] == PRICE
    assert json.loads(found[0]["evidence"])["excess_qty"] == 1


def test_overbilling_names_the_invoice_line_and_shipment(chain):
    set_billed(chain, QTY + 1)
    found = issues(chain)["OVERBILLING"][0]
    evidence = json.loads(found["evidence"])
    assert evidence["invoice_lines"] == [IVL]
    assert evidence["shipments"] == [SHP]
    assert (evidence["shipped_qty"], evidence["billed_qty"], evidence["excess_qty"]) == (QTY, QTY + 1, 1)
    assert {IVL, SHP, INV, SO} <= set(json.loads(found["related_ids"]))


def test_planned_shipment_does_not_count_as_fulfilled(chain):
    chain.execute("UPDATE shipment SET status = 'PLANNED', shipped_date = NULL, delivered_date = NULL")
    found = issues(chain)["OVERBILLING"]
    assert found[0]["impact_paise"] == TOTAL


def test_price_above_order_is_overbilling(chain):
    higher = PRICE + 500
    chain.execute("UPDATE invoice_line SET unit_price_paise = ?, line_total_paise = ?", (higher, higher * QTY))
    assert issues(chain)["OVERBILLING"][0]["impact_paise"] == 500 * QTY


# ---- R02 underbilling ---------------------------------------------------------------------

def split_with_unbilled_second_shipment(conn, shipped_days_ago: int) -> None:
    """8 units billed on the first shipment; 2 more shipped and waiting for an invoice."""
    conn.execute("UPDATE shipment_line SET quantity = ?", (QTY - 2,))
    conn.execute("INSERT INTO shipment VALUES ('SHP-2026-000002', ?, 'BLUELINE', ?, ?, NULL, 'SHIPPED')",
                 (SO, days_before_cutoff(shipped_days_ago), days_before_cutoff(shipped_days_ago)))
    conn.execute("INSERT INTO shipment_line VALUES ('SHL-2026-000002', 'SHP-2026-000002', ?, 2)", (SOL,))
    set_billed(conn, QTY - 2)


def test_unbilled_shipment_inside_grace_period_is_not_underbilling(chain):
    split_with_unbilled_second_shipment(chain, cfg.UNBILLED_GRACE_DAYS - 1)
    assert "UNDERBILLING" not in issues(chain)


def test_unbilled_shipment_at_grace_boundary_is_underbilling(chain):
    split_with_unbilled_second_shipment(chain, cfg.UNBILLED_GRACE_DAYS)
    found = issues(chain)
    assert found["UNDERBILLING"][0]["impact_paise"] == 2 * PRICE
    assert "INVOICING_DELAY" not in found  # the same gap must not be reported twice


def test_invoice_below_order_price_is_underbilling(chain):
    lower = PRICE - 1_000
    chain.execute("UPDATE invoice_line SET unit_price_paise = ?, line_total_paise = ?", (lower, lower * QTY))
    assert issues(chain)["UNDERBILLING"][0]["impact_paise"] == 1_000 * QTY


# ---- R03 duplicate invoice ----------------------------------------------------------------

def test_second_invoice_for_same_shipment_is_duplicate_not_overbilling(chain):
    copy = add_invoice(chain, 2, QTY, "2026-03-06", SHP)
    found = issues(chain)
    assert [f["source_id"] for f in found["DUPLICATE_INVOICE"]] == [copy]
    assert found["DUPLICATE_INVOICE"][0]["impact_paise"] == TOTAL
    assert "OVERBILLING" not in found  # exposure is counted once


def test_equal_shipments_billed_separately_are_not_duplicates(chain):
    half = QTY // 2
    chain.execute("UPDATE shipment_line SET quantity = ?", (half,))
    chain.execute("INSERT INTO shipment VALUES ('SHP-2026-000002', ?, 'BLUELINE', '2026-03-05', '2026-03-06', NULL, 'SHIPPED')", (SO,))
    chain.execute("INSERT INTO shipment_line VALUES ('SHL-2026-000002', 'SHP-2026-000002', ?, ?)", (SOL, half))
    set_billed(chain, half)
    add_invoice(chain, 2, half, "2026-03-07", "SHP-2026-000002")
    assert "DUPLICATE_INVOICE" not in issues(chain)


def test_voided_and_reissued_invoice_is_not_a_duplicate(chain):
    chain.execute("UPDATE invoice SET status = 'VOID' WHERE invoice_id = ?", (INV,))
    add_invoice(chain, 2, QTY, "2026-03-06", SHP)
    assert "DUPLICATE_INVOICE" not in issues(chain)


def test_repeat_with_no_shipment_link_is_caught_by_quantity(chain):
    copy = add_invoice(chain, 2, QTY, "2026-03-06", None)
    assert [f["source_id"] for f in issues(chain)["DUPLICATE_INVOICE"]] == [copy]


def test_overbilling_that_makes_two_invoices_look_alike_stays_overbilling(chain):
    # 3 units shipped in two parts; billing 2 + 2 is one unit too many, not a repeated invoice.
    chain.execute("UPDATE order_line SET quantity = 3, line_total_paise = ?", (3 * PRICE,))
    chain.execute("UPDATE shipment_line SET quantity = 1")
    chain.execute("INSERT INTO shipment VALUES ('SHP-2026-000002', ?, 'BLUELINE', '2026-03-05', '2026-03-06', NULL, 'SHIPPED')", (SO,))
    chain.execute("INSERT INTO shipment_line VALUES ('SHL-2026-000002', 'SHP-2026-000002', ?, 2)", (SOL,))
    set_billed(chain, 2)
    add_invoice(chain, 2, 2, "2026-03-07", "SHP-2026-000002")
    found = issues(chain)
    assert "DUPLICATE_INVOICE" not in found
    assert found["OVERBILLING"][0]["impact_paise"] == PRICE
    assert "UNDERBILLING" not in found


# ---- R04 duplicate allocation -------------------------------------------------------------

def add_allocation(conn, number: int, invoice_id: str, amount: int) -> None:
    conn.execute("INSERT INTO payment_allocation VALUES (?, ?, ?, ?, '2026-04-02')",
                 (f"ALC-2026-{number:06d}", PAY, invoice_id, amount))


def test_payment_allocated_to_same_invoice_twice(chain):
    add_allocation(chain, 2, INV, TOTAL)
    found = issues(chain)["DUPLICATE_ALLOCATION"]
    assert found[0]["source_id"] == PAY
    assert found[0]["impact_paise"] == TOTAL


def test_payment_allocated_again_to_a_second_invoice(chain):
    second = add_invoice(chain, 2, 1, "2026-03-06", None)
    add_allocation(chain, 2, second, PRICE)
    assert issues(chain)["DUPLICATE_ALLOCATION"][0]["impact_paise"] == PRICE


def test_payment_split_across_invoices_within_its_amount_is_fine(chain):
    chain.execute("UPDATE payment_allocation SET allocated_paise = ?", (TOTAL - PRICE,))
    second = add_invoice(chain, 2, 1, "2026-03-06", None)
    add_allocation(chain, 2, second, PRICE)
    assert "DUPLICATE_ALLOCATION" not in issues(chain)


# ---- R05 closed order unpaid --------------------------------------------------------------

def test_closed_order_with_unpaid_invoice(chain):
    make_open_invoice(chain, "2026-09-20")
    chain.execute("UPDATE sales_order SET status = 'CLOSED'")
    found = issues(chain)["CLOSED_ORDER_UNPAID"]
    assert found[0]["source_id"] == SO
    assert found[0]["impact_paise"] == TOTAL


def test_closed_order_with_residual_at_tolerance_is_fine(chain):
    make_open_invoice(chain, "2026-09-20", paid=TOTAL - cfg.BALANCE_TOLERANCE_PAISE, last_payment="2026-09-01")
    chain.execute("UPDATE sales_order SET status = 'CLOSED'")
    assert "CLOSED_ORDER_UNPAID" not in issues(chain)


# ---- R06 lifecycle ------------------------------------------------------------------------

def test_event_skipping_required_state_is_illegal(chain):
    chain.execute("DELETE FROM status_event WHERE entity_id = ? AND to_status = 'FULFILLED'", (SO,))
    chain.execute("UPDATE status_event SET from_status = 'CONFIRMED' WHERE entity_id = ? AND to_status = 'INVOICED'", (SO,))
    found = issues(chain)["ILLEGAL_TRANSITION"]
    assert len(found) == 1
    assert json.loads(found[0]["evidence"])["skipped_states"] == ["FULFILLED"]


def test_broken_history_chain_is_flagged(chain):
    chain.execute("UPDATE status_event SET from_status = 'SENT' WHERE entity_id = ? AND to_status = 'CONFIRMED'", (SO,))
    assert "ILLEGAL_TRANSITION" in issues(chain)


# ---- R07 dispute treatment ----------------------------------------------------------------

def test_open_dispute_with_full_hold_is_fine(chain):
    add_dispute(chain, "OPEN", 5_000, 5_000)
    assert "DISPUTE_NOT_IN_AR" not in issues(chain)


def test_open_dispute_with_no_hold(chain):
    dispute_id = add_dispute(chain, "OPEN", 5_000, None)
    found = issues(chain)["DISPUTE_NOT_IN_AR"]
    assert found[0]["source_id"] == dispute_id
    assert found[0]["impact_paise"] == 5_000


def test_open_dispute_with_partial_hold(chain):
    add_dispute(chain, "UNDER_REVIEW", 5_000, 2_000)
    assert issues(chain)["DISPUTE_NOT_IN_AR"][0]["impact_paise"] == 3_000


def test_credit_granted_but_not_posted(chain):
    add_dispute(chain, "RESOLVED_CREDIT", 5_000, None, credited=4_000, resolved="2026-03-20")
    assert issues(chain)["DISPUTE_NOT_IN_AR"][0]["impact_paise"] == 4_000


def test_resolved_dispute_with_hold_never_released(chain):
    add_dispute(chain, "RESOLVED_NO_CREDIT", 5_000, 5_000, resolved="2026-03-20")
    assert issues(chain)["DISPUTE_NOT_IN_AR"][0]["impact_paise"] == 5_000


# ---- R08 short payment and R09 long overdue -----------------------------------------------

def short_paid(conn, stale_days: int, past_due_days: int) -> None:
    """Leave a balance one paisa above tolerance."""
    paid = TOTAL - (cfg.BALANCE_TOLERANCE_PAISE + 1)
    make_open_invoice(conn, days_before_cutoff(past_due_days), paid=paid, last_payment=days_before_cutoff(stale_days))


def test_short_payment_at_stale_boundary(chain):
    short_paid(chain, stale_days=cfg.SHORT_PAY_STALE_DAYS, past_due_days=cfg.SHORT_PAY_MIN_DAYS_PAST_DUE + 1)
    found = issues(chain)["SHORT_PAYMENT"]
    assert found[0]["impact_paise"] == cfg.BALANCE_TOLERANCE_PAISE + 1


def test_recent_instalment_is_not_a_short_payment(chain):
    short_paid(chain, stale_days=cfg.SHORT_PAY_STALE_DAYS - 1, past_due_days=cfg.SHORT_PAY_MIN_DAYS_PAST_DUE + 1)
    assert "SHORT_PAYMENT" not in issues(chain)


def test_not_past_due_enough_is_not_a_short_payment(chain):
    short_paid(chain, stale_days=cfg.SHORT_PAY_STALE_DAYS, past_due_days=cfg.SHORT_PAY_MIN_DAYS_PAST_DUE)
    assert "SHORT_PAYMENT" not in issues(chain)


def test_residual_at_tolerance_is_not_a_short_payment(chain):
    make_open_invoice(chain, days_before_cutoff(60), paid=TOTAL - cfg.BALANCE_TOLERANCE_PAISE,
                      last_payment=days_before_cutoff(50))
    assert "SHORT_PAYMENT" not in issues(chain)


def test_balance_parked_behind_a_dispute_is_not_short_paid(chain):
    short_paid(chain, stale_days=40, past_due_days=40)
    balance = cfg.BALANCE_TOLERANCE_PAISE + 1
    add_dispute(chain, "OPEN", balance, balance)
    assert "SHORT_PAYMENT" not in issues(chain)


def test_exactly_90_days_past_due_is_not_long_overdue(chain):
    make_open_invoice(chain, days_before_cutoff(cfg.LONG_OVERDUE_DAYS))
    assert "LONG_OVERDUE" not in issues(chain)


def test_91_days_past_due_is_long_overdue(chain):
    make_open_invoice(chain, days_before_cutoff(cfg.LONG_OVERDUE_DAYS + 1))
    found = issues(chain)["LONG_OVERDUE"]
    assert found[0]["source_id"] == INV
    assert found[0]["delay_days"] == cfg.LONG_OVERDUE_DAYS + 1


# ---- R10 and R11 delays -------------------------------------------------------------------

def test_fulfilment_on_sla_day_is_not_delayed(chain):
    chain.execute("UPDATE sales_order SET order_date = '2026-02-10'")  # shipped 21 days later
    assert "FULFILMENT_DELAY" not in issues(chain)


def test_fulfilment_one_day_past_sla_is_delayed(chain):
    chain.execute("UPDATE sales_order SET order_date = '2026-02-09'")
    assert issues(chain)["FULFILMENT_DELAY"][0]["delay_days"] == cfg.SLA_ORDER_TO_FULFILMENT_DAYS + 1


def test_unshipped_order_is_delayed_at_cutoff(chain):
    chain.execute("UPDATE shipment SET status = 'PLANNED', shipped_date = NULL, delivered_date = NULL")
    chain.execute("UPDATE sales_order SET status = 'CONFIRMED'")
    found = issues(chain)["FULFILMENT_DELAY"]
    assert json.loads(found[0]["evidence"])["units_unshipped"] == QTY


def test_cancelled_order_is_never_delayed(chain):
    chain.execute("UPDATE shipment SET status = 'PLANNED', shipped_date = NULL, delivered_date = NULL")
    chain.execute("UPDATE sales_order SET status = 'CANCELLED'")
    assert "FULFILMENT_DELAY" not in issues(chain)


def test_invoice_on_sla_day_is_not_delayed(chain):
    chain.execute("UPDATE invoice SET invoice_date = '2026-03-10'")  # shipped 2026-03-03
    assert "INVOICING_DELAY" not in issues(chain)


def test_invoice_one_day_past_sla_is_delayed(chain):
    chain.execute("UPDATE invoice SET invoice_date = '2026-03-11'")
    assert issues(chain)["INVOICING_DELAY"][0]["delay_days"] == cfg.SLA_SHIPMENT_TO_INVOICE_DAYS + 1


def test_duplicate_invoice_is_not_reported_as_late(chain):
    add_invoice(chain, 2, QTY, "2026-03-25", SHP)
    assert "INVOICING_DELAY" not in issues(chain)


def test_unbilled_shipment_past_sla_is_delayed_at_cutoff(chain):
    chain.execute("DELETE FROM invoice_shipment")
    chain.execute("UPDATE shipment SET shipped_date = ?", (days_before_cutoff(cfg.SLA_SHIPMENT_TO_INVOICE_DAYS + 1),))
    found = issues(chain)["INVOICING_DELAY"]
    assert found[0]["source_id"] == SHP


# ---- Whole dataset ------------------------------------------------------------------------

def test_clean_world_has_no_findings(clean_paths):
    from src.database import connect

    conn = connect(clean_paths)
    assert conn.execute("SELECT COUNT(*) FROM finding").fetchone()[0] == 0
    conn.close()


def test_every_required_scenario_is_detected(starter_conn, starter_paths):
    report = evaluate(starter_conn, load_ground_truth(starter_paths[1]))
    required = {"OVERBILLING", "DUPLICATE_ALLOCATION", "CLOSED_ORDER_UNPAID", "ILLEGAL_TRANSITION", "DISPUTE_NOT_IN_AR",
                "UNDERBILLING", "DUPLICATE_INVOICE", "SHORT_PAYMENT", "LONG_OVERDUE"}
    assert required <= set(report["by_issue_type"])
    for issue_type in required:
        assert report["by_issue_type"][issue_type]["tp"] > 0
        assert report["by_issue_type"][issue_type]["fn"] == 0


def test_findings_carry_traceable_evidence(starter_conn):
    columns = ("rule_id", "source_id", "severity", "rule_description", "expected_behavior", "observed_behavior")
    for row in starter_conn.execute("SELECT * FROM finding"):
        assert all(row[c] for c in columns)
        assert isinstance(json.loads(row["evidence"]), dict)
        assert isinstance(json.loads(row["related_ids"]), list)


def test_detector_never_touches_ground_truth():
    source = (cfg.ROOT / "src" / "detector.py").read_text(encoding="utf-8").lower()
    assert "ground_truth.csv" not in source and "load_ground_truth" not in source
    assert "import evaluation" not in source and "from .evaluation" not in source


def test_database_holds_no_label_columns_or_text(starter_conn):
    tables = [r[0] for r in starter_conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
    for table in tables:
        columns = [r["name"].lower() for r in starter_conn.execute(f"PRAGMA table_info({table})")]
        assert not any(word in c for c in columns for word in ("label", "ground", "anomaly", "scenario", "inject"))
    assert starter_conn.execute("SELECT COUNT(*) FROM status_event WHERE actor_role LIKE '%INJECT%'").fetchone()[0] == 0


def test_ground_truth_file_is_separate_and_complete(starter_paths):
    db_file, truth_file = starter_paths
    assert Path(truth_file).name == "ground_truth.csv"
    with Path(truth_file).open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows and all(r["primary_id"] and r["expected_behavior"] and r["observed_behavior"] for r in rows)
    assert all(r["gt_id"] and r["expected_label"] == r["issue_type"] and r["causal_explanation"] for r in rows)
