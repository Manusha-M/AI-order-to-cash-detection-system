"""Financial tests: balances, aging, reconciliation identities, and evaluation arithmetic."""
from __future__ import annotations

import shutil

import pytest

from src.database import connect
from src.detector import run_detection
from src.evaluation import _scores, evaluate
from src.reconciliation import classify_receivables, compute_metrics, reconcile
from src.reproducibility import verify_reproducibility
from tests.conftest import INV, TOTAL


def test_paid_chain_has_zero_balance(chain):
    row = chain.execute("SELECT * FROM v_invoice_balance WHERE invoice_id = ?", (INV,)).fetchone()
    assert row["balance_paise"] == 0
    assert row["applied_paise"] == TOTAL


def test_partial_payment_leaves_correct_balance(chain):
    chain.execute("UPDATE ar_ledger_entry SET amount_paise = 40000 WHERE entry_type = 'PAYMENT_APPLIED'")
    assert chain.execute("SELECT balance_paise FROM v_invoice_balance").fetchone()[0] == TOTAL - 40_000


def test_credit_memo_reduces_balance_and_hold_reduces_collectible(chain):
    chain.execute("UPDATE ar_ledger_entry SET amount_paise = 40000 WHERE entry_type = 'PAYMENT_APPLIED'")
    chain.execute("INSERT INTO ar_ledger_entry VALUES ('ARL-2026-000060', ?, 'CREDIT_MEMO', 10000, '2026-05-01', ?)", (INV, INV))
    chain.execute("INSERT INTO ar_ledger_entry VALUES ('ARL-2026-000061', ?, 'DISPUTE_HOLD', 5000, '2026-05-01', ?)", (INV, INV))
    row = chain.execute("SELECT balance_paise, collectible_paise FROM v_invoice_balance").fetchone()
    assert row["balance_paise"] == TOTAL - 50_000
    assert row["collectible_paise"] == TOTAL - 55_000


def test_void_invoice_drops_out_of_receivables(chain):
    chain.execute("UPDATE invoice SET status = 'VOID'")
    assert chain.execute("SELECT COUNT(*) FROM v_invoice_balance").fetchone()[0] == 0


@pytest.mark.parametrize("days_past_due,bucket", [
    (-5, "0 Not due"), (0, "0 Not due"), (1, "1 1-30 days"), (30, "1 1-30 days"), (31, "2 31-60 days"),
    (60, "2 31-60 days"), (61, "3 61-90 days"), (90, "3 61-90 days"), (91, "4 91-120 days"),
    (120, "4 91-120 days"), (121, "5 Over 120 days"),
])
def test_aging_bucket_boundaries(chain, days_past_due, bucket):
    chain.execute("UPDATE invoice SET due_date = date('2026-09-30', ? || ' days')", (str(-days_past_due),))
    assert chain.execute("SELECT aging_bucket FROM v_invoice_aging").fetchone()[0] == bucket


def test_aging_moves_with_the_cutoff(chain):
    chain.execute("UPDATE invoice SET due_date = '2026-09-01'")
    assert chain.execute("SELECT days_past_due FROM v_invoice_balance").fetchone()[0] == 29
    chain.execute("UPDATE run_metadata SET value = '2026-10-01' WHERE key = 'cutoff_date'")
    assert chain.execute("SELECT days_past_due FROM v_invoice_balance").fetchone()[0] == 30


def test_all_identities_close_on_generated_data(starter_conn):
    for identity in reconcile(starter_conn):
        assert identity["status"] == "PASS", identity


def test_identities_close_on_the_clean_world(clean_paths):
    conn = connect(clean_paths)
    assert all(i["status"] == "PASS" for i in reconcile(conn))
    conn.close()


def test_receivable_classes_do_not_overlap(starter_conn):
    outstanding = compute_metrics(starter_conn)["receivables_paise"]["outstanding"]
    assert sum(classify_receivables(starter_conn).values()) == outstanding


def test_some_invoices_are_both_short_paid_and_long_overdue(starter_conn):
    """This overlap is why classify_receivables exists: adding the two impacts would double-count."""
    both = starter_conn.execute(
        """SELECT COUNT(*) FROM finding a JOIN finding b ON a.source_id = b.source_id
           WHERE a.issue_type = 'SHORT_PAYMENT' AND b.issue_type = 'LONG_OVERDUE'""").fetchone()[0]
    assert both > 0


def test_reconciliation_notices_a_tampered_ledger(starter_paths, tmp_path):
    copy = tmp_path / "copy.db"
    shutil.copy(starter_paths[0], copy)
    conn = connect(copy)
    conn.execute("""UPDATE ar_ledger_entry SET amount_paise = amount_paise + 100
                    WHERE entry_id = (SELECT MIN(entry_id) FROM ar_ledger_entry WHERE entry_type = 'PAYMENT_APPLIED')""")
    conn.commit()
    failed = {i["id"] for i in reconcile(conn) if i["status"] == "FAIL"}
    conn.close()
    assert "REC-2" in failed


def test_billing_bridge_notices_an_undetected_change(starter_paths, tmp_path):
    """Raise a billed price after detection: the bridge stops closing because nothing explains it."""
    copy = tmp_path / "copy.db"
    shutil.copy(starter_paths[0], copy)
    conn = connect(copy)
    conn.execute("""UPDATE invoice_line SET unit_price_paise = unit_price_paise + 100,
                    line_total_paise = line_total_paise + 100 * quantity
                    WHERE invoice_line_id = 'IVL-2026-000010'""")
    conn.execute("""UPDATE invoice SET total_paise = total_paise + 100 * (
                        SELECT quantity FROM invoice_line WHERE invoice_line_id = 'IVL-2026-000010')
                    WHERE invoice_id = (SELECT invoice_id FROM invoice_line WHERE invoice_line_id = 'IVL-2026-000010')""")
    conn.commit()
    before = {i["id"]: i["status"] for i in reconcile(conn)}
    assert before["REC-5"] == "FAIL"
    run_detection(conn)  # re-running the detector explains the change as overbilling
    after = {i["id"]: i["status"] for i in reconcile(conn)}
    conn.close()
    assert after["REC-5"] == "PASS"


def test_metrics_funnel_narrows(starter_conn):
    funnel = compute_metrics(starter_conn)["funnel_paise"]
    assert funnel["quoted"] > funnel["accepted"] >= funnel["ordered"] >= funnel["fulfilled"]
    assert funnel["cash_received"] < funnel["invoiced"]


def test_leakage_categories_stay_separate(starter_conn):
    leakage = compute_metrics(starter_conn)["leakage_paise"]
    assert leakage["underbilled_revenue"] > 0 and leakage["overbilled_exposure"] > 0
    assert leakage["underbilled_revenue"] != leakage["overbilled_exposure"]


def test_delay_metrics_exist_for_each_stage(starter_conn):
    delays = compute_metrics(starter_conn)["delays"]
    for stage in ("order_to_fulfilment", "fulfilment_to_invoice", "invoice_to_final_payment"):
        assert delays[stage]["count"] > 0


# ---- Evaluation arithmetic ----------------------------------------------------------------

def test_scores_on_a_hand_worked_example():
    result = _scores(tp=8, fp=2, fn=2)
    assert result["precision"] == 0.8
    assert result["recall"] == 0.8
    assert result["f1"] == 0.8


def test_scores_with_nothing_found():
    assert _scores(tp=0, fp=0, fn=3)["recall"] == 0.0


def _label(issue_type: str, primary_id: str, impact: int = 0) -> dict:
    return {"issue_type": issue_type, "primary_id": primary_id, "expected_impact_paise": str(impact)}


def _finding(conn, number: int, issue_type: str, source_id: str, impact: int = 0) -> None:
    conn.execute(
        """INSERT INTO finding VALUES (?, 'R01', ?, 'LOW', 'X', ?, '[]', 'd', 'e', 'o', 'NONE', ?, 0, '{}')""",
        (f"FND-{number}", issue_type, source_id, impact))


def test_evaluation_counts_each_outcome(chain):
    _finding(chain, 1, "OVERBILLING", "A", 100)
    _finding(chain, 2, "OVERBILLING", "B")
    report = evaluate(chain, [_label("OVERBILLING", "A", 100), _label("OVERBILLING", "C")])
    assert report["overall"]["tp"] == 1
    assert report["overall"]["fp"] == 1
    assert report["overall"]["fn"] == 1
    assert report["impact_accuracy"]["exact"] == 1


def test_evaluation_rejects_a_label_counted_twice(chain):
    with pytest.raises(ValueError):
        evaluate(chain, [_label("OVERBILLING", "A"), _label("OVERBILLING", "A")])


def test_right_record_wrong_issue_is_not_a_match(chain):
    _finding(chain, 1, "UNDERBILLING", "A")
    report = evaluate(chain, [_label("OVERBILLING", "A")])
    assert report["overall"]["tp"] == 0


def test_two_runs_with_the_same_seed_match():
    report = verify_reproducibility("starter")
    assert report["status"] == "PASS"
    assert report["combined_sha256_a"] == report["combined_sha256_b"]
    assert report["findings_a"] == report["findings_b"]
