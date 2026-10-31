"""Regression tests for bugs proven by an independent review.

Each test reproduces a scenario that gave a wrong answer before its fix. Most use data the
generator never produces, which is the point: rules must be right for the data they could
meet, not only for the data they were written beside.
"""
from __future__ import annotations

import json
import shutil

import pytest

from src import config as cfg
from src.database import build_database, connect, write_ground_truth
from src.detector import run_detection
from src.evaluation import evaluate, load_ground_truth
from src.generator import generate, net_unit_price
from src.reconciliation import classify_receivables, compute_metrics, reconcile
from src.validation import validate
from tests.conftest import INV, PAY, PRICE, QTY, SHP, SO, SOL, TOTAL
from tests.test_detection import add_allocation, add_dispute, add_invoice, days_before_cutoff, issues, make_open_invoice, set_billed


def failed_checks(conn) -> set[str]:
    report = validate(conn, cfg.SCALES["starter"], None)
    return {r["description"] for r in report["results"] if r["status"] == "FAIL"}


def failed_identities(conn) -> set[str]:
    return {i["id"] for i in reconcile(conn) if i["status"] == "FAIL"}


def add_shipment(conn, number: int, quantity: int, shipped: str) -> str:
    shipment_id = f"SHP-2026-{number:06d}"
    conn.execute("INSERT INTO shipment VALUES (?, ?, 'BLUELINE', ?, ?, NULL, 'SHIPPED')", (shipment_id, SO, shipped, shipped))
    conn.execute("INSERT INTO shipment_line VALUES (?, ?, ?, ?)", (f"SHL-2026-{number:06d}", shipment_id, SOL, quantity))
    return shipment_id


# ---- Duplicate invoices ------------------------------------------------------------------

def test_one_shipment_billed_in_two_parts_is_not_a_duplicate(chain):
    set_billed(chain, 5)
    add_invoice(chain, 2, 5, "2026-03-06", SHP)
    found = issues(chain)
    assert "DUPLICATE_INVOICE" not in found
    assert "UNDERBILLING" not in found


def test_third_part_billing_past_the_shipment_is_a_duplicate(chain):
    set_billed(chain, 5)
    add_invoice(chain, 2, 5, "2026-03-06", SHP)
    third = add_invoice(chain, 3, 5, "2026-03-07", SHP)
    assert [f["source_id"] for f in issues(chain)["DUPLICATE_INVOICE"]] == [third]


def test_duplicate_of_a_price_inflated_invoice_counts_once(chain):
    high = PRICE + 1_000
    copy = add_invoice(chain, 2, QTY, "2026-03-06", SHP)
    chain.execute("UPDATE invoice_line SET unit_price_paise = ?, line_total_paise = ?", (high, high * QTY))
    chain.execute("UPDATE invoice SET total_paise = ?", (high * QTY,))
    found = issues(chain)
    assert [f["source_id"] for f in found["DUPLICATE_INVOICE"]] == [copy]
    assert found["DUPLICATE_INVOICE"][0]["impact_paise"] == high * QTY
    assert found["OVERBILLING"][0]["impact_paise"] == 1_000 * QTY


def test_unpaid_duplicate_is_not_sent_to_collections(chain):
    add_invoice(chain, 2, QTY, "2026-03-06", SHP)
    found = issues(chain)
    assert "DUPLICATE_INVOICE" in found
    assert "CLOSED_ORDER_UNPAID" not in found
    assert "LONG_OVERDUE" not in found


# ---- Underbilling and billing state ------------------------------------------------------

def test_aged_unbilled_shipment_is_found_when_a_newer_one_was_billed(chain):
    chain.execute("UPDATE shipment_line SET quantity = 5")
    add_shipment(chain, 2, 5, days_before_cutoff(100))
    chain.execute("UPDATE shipment SET shipped_date = ? WHERE shipment_id = ?", (days_before_cutoff(5), SHP))
    set_billed(chain, 5)
    found = issues(chain)
    assert found["UNDERBILLING"][0]["impact_paise"] == 5 * PRICE


def test_invoice_billing_less_than_its_shipment_is_flagged_straight_away(chain):
    chain.execute("UPDATE shipment SET shipped_date = ?", (days_before_cutoff(3),))
    set_billed(chain, QTY - 2)
    assert issues(chain)["UNDERBILLING"][0]["impact_paise"] == 2 * PRICE


def test_draft_invoice_does_not_count_as_billed(chain):
    chain.execute("UPDATE invoice SET status = 'DRAFT'")
    chain.execute("DELETE FROM ar_ledger_entry")
    chain.execute("DELETE FROM payment_allocation")
    chain.execute("DELETE FROM payment")
    chain.execute("UPDATE sales_order SET status = 'FULFILLED'")
    found = issues(chain)
    assert found["UNDERBILLING"][0]["impact_paise"] == TOTAL
    assert not failed_identities(chain) - {"REC-5"}


def test_billing_a_credited_invoice_shows_the_credit_in_evidence(chain):
    set_billed(chain, QTY + 2)
    chain.execute("INSERT INTO ar_ledger_entry VALUES ('ARL-2026-000070', ?, 'CREDIT_MEMO', ?, '2026-05-01', ?)",
                  (INV, 2 * PRICE, INV))
    evidence = json.loads(issues(chain)["OVERBILLING"][0]["evidence"])
    assert evidence["credits_on_invoices_paise"] == 2 * PRICE


# ---- Payments ----------------------------------------------------------------------------

def test_identical_allocation_rows_within_the_payment_are_flagged(chain):
    half = TOTAL // 2
    chain.execute("UPDATE payment_allocation SET allocated_paise = ?, allocated_date = '2026-04-02'", (half,))
    add_allocation(chain, 2, INV, half)
    found = issues(chain)["DUPLICATE_ALLOCATION"]
    assert found[0]["source_id"] == PAY
    assert found[0]["impact_paise"] == 0


def test_single_oversize_allocation_is_described_correctly(chain):
    chain.execute("UPDATE payment_allocation SET allocated_paise = ?", (TOTAL + 500,))
    observed = issues(chain)["DUPLICATE_ALLOCATION"][0]["observed_behavior"]
    assert "twice" not in observed


def test_part_allocated_payment_reconciles(chain):
    chain.execute("UPDATE payment_allocation SET allocated_paise = 60000")
    chain.execute("UPDATE ar_ledger_entry SET amount_paise = 60000 WHERE entry_type = 'PAYMENT_APPLIED'")
    run_detection(chain)
    assert "REC-4" not in failed_identities(chain)


# ---- Disputes and receivables ------------------------------------------------------------

def test_hold_posted_to_the_wrong_invoice_is_flagged(chain):
    second = add_invoice(chain, 2, 1, "2026-03-06", None)
    dispute_id = add_dispute(chain, "OPEN", 5_000, None)
    chain.execute("INSERT INTO ar_ledger_entry VALUES ('ARL-2026-000071', ?, 'DISPUTE_HOLD', 5000, '2026-03-10', ?)",
                  (second, dispute_id))
    assert issues(chain)["DISPUTE_NOT_IN_AR"][0]["source_id"] == dispute_id


def test_hold_above_the_balance_cannot_make_collectible_negative(chain):
    make_open_invoice(chain, days_before_cutoff(10), paid=40_000, last_payment=days_before_cutoff(20))
    add_dispute(chain, "OPEN", 90_000, 90_000)
    row = chain.execute("SELECT balance_paise, collectible_paise FROM v_invoice_balance").fetchone()
    assert row["balance_paise"] == TOTAL - 40_000
    assert row["collectible_paise"] == 0
    assert issues(chain)["DISPUTE_NOT_IN_AR"][0]["impact_paise"] == 30_000
    assert compute_metrics(chain)["receivables_paise"]["overdue_collectible"] == 0
    assert sum(classify_receivables(chain).values()) == TOTAL - 40_000


# ---- Aging is measured as of the cutoff -----------------------------------------------------

def test_money_dated_after_the_cutoff_is_ignored(chain):
    chain.execute("UPDATE ar_ledger_entry SET entry_date = '2026-10-15' WHERE entry_type = 'PAYMENT_APPLIED'")
    assert chain.execute("SELECT balance_paise FROM v_invoice_balance").fetchone()[0] == TOTAL


def test_invoices_dated_after_the_cutoff_are_excluded(chain):
    chain.execute("UPDATE run_metadata SET value = '2026-03-01' WHERE key = 'cutoff_date'")
    assert chain.execute("SELECT COUNT(*) FROM v_invoice_balance").fetchone()[0] == 0


def test_validator_flags_money_dated_after_the_cutoff(chain):
    chain.execute("UPDATE payment_allocation SET allocated_date = '2026-10-15'")
    chain.execute("UPDATE ar_ledger_entry SET entry_date = '2026-10-15' WHERE entry_type = 'PAYMENT_APPLIED'")
    failed = failed_checks(chain)
    assert "no allocation dated after cutoff" in failed
    assert "no ledger entry dated after cutoff" in failed


# ---- Reconciliation must be able to fail ---------------------------------------------------

@pytest.fixture
def tamperable(starter_paths, tmp_path):
    copy = tmp_path / "copy.db"
    shutil.copy(starter_paths[0], copy)
    conn = connect(copy)
    yield conn
    conn.close()


def test_money_moved_to_another_invoice_is_noticed(tamperable):
    entry, invoice = tamperable.execute(
        "SELECT entry_id, invoice_id FROM ar_ledger_entry WHERE entry_type = 'PAYMENT_APPLIED' LIMIT 1").fetchone()
    other = tamperable.execute("SELECT invoice_id FROM invoice WHERE invoice_id <> ? LIMIT 1", (invoice,)).fetchone()[0]
    tamperable.execute("UPDATE ar_ledger_entry SET invoice_id = ? WHERE entry_id = ?", (other, entry))
    tamperable.commit()
    assert {"REC-2", "REC-3"} <= failed_identities(tamperable)
    assert "payment ledger entry sits on its allocation's invoice" in failed_checks(tamperable)


def test_deleted_payment_entries_are_noticed(tamperable):
    tamperable.execute("""DELETE FROM ar_ledger_entry WHERE entry_id IN (
        SELECT entry_id FROM ar_ledger_entry WHERE entry_type = 'PAYMENT_APPLIED' LIMIT 100)""")
    tamperable.commit()
    assert "REC-3" in failed_identities(tamperable)


def test_bridge_fails_when_an_underbilling_finding_is_missing(tamperable):
    tamperable.execute("DELETE FROM finding WHERE issue_type = 'UNDERBILLING'")
    tamperable.commit()
    assert "REC-5" in failed_identities(tamperable)


# ---- Validation of state ------------------------------------------------------------------

def test_fulfilled_order_with_units_unshipped_fails_validation(chain):
    chain.execute("UPDATE shipment_line SET quantity = 5")
    assert "FULFILLED or later orders are fully shipped" in failed_checks(chain)


def test_shipped_row_without_a_date_is_handled(chain):
    chain.execute("UPDATE shipment SET shipped_date = NULL")
    issues(chain)  # must not crash
    assert "shipped shipments have a shipped date" in failed_checks(chain)


def test_credit_above_the_disputed_amount_fails_validation(chain):
    add_dispute(chain, "RESOLVED_CREDIT", 5_000, None, credited=90_000, resolved="2026-03-20")
    assert "credit stays within the disputed amount" in failed_checks(chain)


def test_order_priced_away_from_its_quote_fails_validation(chain):
    chain.execute("UPDATE order_line SET unit_price_paise = 8000, line_total_paise = 80000")
    assert "order line matches its quote line" in failed_checks(chain)


# ---- Lifecycle ----------------------------------------------------------------------------

def test_deleted_middle_event_names_the_missing_state(chain):
    chain.execute("DELETE FROM status_event WHERE entity_id = ? AND to_status = 'FULFILLED'", (SO,))
    found = issues(chain)["ILLEGAL_TRANSITION"]
    assert json.loads(found[0]["evidence"])["skipped_states"] == ["FULFILLED"]


def test_account_stage_changes_are_kept_as_events(starter_conn):
    customers = starter_conn.execute("SELECT COUNT(*) FROM account WHERE status = 'CUSTOMER'").fetchone()[0]
    moved = starter_conn.execute(
        """SELECT COUNT(*) FROM status_event WHERE entity_type = 'ACCOUNT'
           AND from_status = 'PROSPECT' AND to_status = 'CUSTOMER'""").fetchone()[0]
    assert customers == moved > 0


def test_every_finding_cites_status_events(starter_conn):
    for row in starter_conn.execute("SELECT finding_id, evidence FROM finding"):
        assert json.loads(row["evidence"])["source_events"], row["finding_id"]


# ---- Invoicing delay ----------------------------------------------------------------------

def test_invoice_measures_from_its_oldest_new_shipment(chain):
    chain.execute("UPDATE shipment_line SET quantity = 5")
    second = add_shipment(chain, 2, 5, "2026-04-20")
    chain.execute("INSERT INTO invoice_shipment VALUES (?, ?)", (INV, second))
    chain.execute("UPDATE invoice SET invoice_date = '2026-04-21'")
    assert issues(chain)["INVOICING_DELAY"][0]["delay_days"] == 49


def test_reissue_of_a_prompt_invoice_is_not_late(chain):
    chain.execute("UPDATE invoice SET status = 'VOID'")
    reissue = add_invoice(chain, 2, QTY, "2026-03-20", SHP)
    chain.execute("UPDATE invoice SET replaces_invoice_id = ? WHERE invoice_id = ?", (INV, reissue))
    assert "INVOICING_DELAY" not in issues(chain)


# ---- Generator ----------------------------------------------------------------------------

@pytest.mark.parametrize("seed", [12, 35, 45, 55, 57, 72, 77, 99, 123])
def test_seeds_that_used_to_crash_now_generate(seed):
    assert len(generate(cfg.SCALES["starter"], seed).tables["invoice"]) == 800


@pytest.mark.parametrize("seed", [5, 20261022])
def test_no_record_is_labelled_twice_for_one_issue(seed):
    labels = generate(cfg.SCALES["starter"], seed).ground_truth
    keys = [(g["issue_type"], g["primary_id"]) for g in labels]
    assert len(keys) == len(set(keys))


def test_ids_do_not_reveal_which_rows_were_injected(starter_dataset):
    invoices = sorted(starter_dataset.tables["invoice"], key=lambda r: r["invoice_id"])
    assert [i["invoice_date"] for i in invoices] == sorted(i["invoice_date"] for i in invoices)
    allocations = sorted(starter_dataset.tables["payment_allocation"], key=lambda r: r["allocation_id"])
    assert [a["allocated_date"] for a in allocations] == sorted(a["allocated_date"] for a in allocations)


def test_net_price_rounds_the_same_in_python_and_sql(chain):
    assert net_unit_price(30, 2500) == 23
    chain.execute("""UPDATE quote_line SET list_price_paise = 30, discount_bps = 2500, net_unit_price_paise = 23,
                     line_total_paise = 230""")
    assert "quote line net price = list less discount" not in failed_checks(chain)


@pytest.mark.parametrize("days", [60, 120])
def test_changing_the_overdue_threshold_keeps_labels_and_rules_in_step(monkeypatch, tmp_path, days):
    monkeypatch.setattr(cfg, "LONG_OVERDUE_DAYS", days)
    dataset = generate(cfg.SCALES["starter"])
    db_file, truth_file = tmp_path / "o2c.db", tmp_path / "truth.csv"
    build_database(dataset, db_file, "starter", True)
    write_ground_truth(dataset, truth_file)
    conn = connect(db_file)
    run_detection(conn)
    overall = evaluate(conn, load_ground_truth(truth_file))["overall"]
    conn.close()
    assert (overall["fp"], overall["fn"]) == (0, 0)


# ---- Evaluation honesty -------------------------------------------------------------------

def test_scores_are_split_by_where_the_label_came_from(starter_conn, starter_paths):
    report = evaluate(starter_conn, load_ground_truth(starter_paths[1]))
    assert set(report["by_label_source"]) == {"injected", "plan", "rule"}
    assert report["by_label_source"]["rule"]["tp"] > 0


def test_impact_accuracy_ignores_rows_with_no_money(starter_conn, starter_paths):
    report = evaluate(starter_conn, load_ground_truth(starter_paths[1]))
    zero_impact = starter_conn.execute("SELECT COUNT(*) FROM finding WHERE impact_paise = 0").fetchone()[0]
    assert report["impact_accuracy"]["checked"] == report["overall"]["tp"] - zero_impact


def test_two_findings_for_one_record_are_refused(chain):
    insert = """INSERT INTO finding VALUES (?, 'R01', 'OVERBILLING', 'LOW', 'ORDER_LINE', 'A', '[]', 'd', 'e', 'o',
                                            'NONE', 0, 0, '{}')"""
    chain.execute(insert, ("FND-1",))
    chain.execute(insert, ("FND-2",))
    with pytest.raises(ValueError):
        evaluate(chain, [])

