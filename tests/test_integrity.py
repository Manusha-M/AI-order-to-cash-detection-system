"""Schema and validator tests. A validator that can never fail proves nothing, so several
tests corrupt a copy of the data on purpose and check the matching check goes red."""
from __future__ import annotations

import shutil
import sqlite3

import pytest

from src import config as cfg
from src.database import connect
from src.validation import validate
from tests.conftest import ACC, QTE


def by_id(report: dict) -> dict:
    return {r["check_id"]: r for r in report["results"]}


@pytest.fixture
def corruptible(starter_paths, tmp_path):
    copy = tmp_path / "copy.db"
    shutil.copy(starter_paths[0], copy)
    conn = connect(copy)
    conn.execute("PRAGMA foreign_keys = OFF")
    yield conn, starter_paths[1]
    conn.close()


def test_all_eleven_core_entities_exist(starter_conn):
    tables = {r[0] for r in starter_conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {"account", "quote", "quote_line", "sales_order", "order_line", "shipment", "invoice", "invoice_line",
            "payment", "dispute", "status_event"} <= tables


def test_foreign_keys_are_enforced(chain):
    with pytest.raises(sqlite3.IntegrityError):
        chain.execute("INSERT INTO quote VALUES ('QTE-2026-000009', 'ACC-2026-999999', '2026-01-01', '2026-01-31', "
                      "'INBOUND', 'DRAFT', 0)")


def test_schema_rejects_a_bad_enum(chain):
    with pytest.raises(sqlite3.IntegrityError):
        chain.execute("UPDATE invoice SET status = 'NOT_A_STATUS'")


def test_schema_rejects_a_malformed_id(chain):
    with pytest.raises(sqlite3.IntegrityError):
        chain.execute("INSERT INTO quote VALUES ('QTE-1', ?, '2026-01-01', '2026-01-31', 'INBOUND', 'DRAFT', 0)", (ACC,))


def test_schema_rejects_a_second_order_for_one_quote(chain):
    with pytest.raises(sqlite3.IntegrityError):
        chain.execute("INSERT INTO sales_order VALUES ('SO-2026-000002', ?, ?, '2026-03-01', 30, 'CREATED', 100)", (QTE, ACC))


def test_schema_allows_a_business_anomaly_to_be_stored(chain):
    """Billing more than shipped must be storable, or the detector could never see it."""
    chain.execute("UPDATE invoice_line SET quantity = 999, line_total_paise = unit_price_paise * 999")
    chain.commit()


def test_generated_dataset_passes_every_structural_check(starter_conn, starter_paths):
    report = validate(starter_conn, cfg.SCALES["starter"], starter_paths[1])
    failed = [r for r in report["results"] if r["category"] == "STRUCTURAL" and r["status"] == "FAIL"]
    assert failed == []
    assert report["structural_checks"] >= 70


def test_business_anomalies_are_reported_not_hidden(starter_conn, starter_paths):
    report = validate(starter_conn, cfg.SCALES["starter"], starter_paths[1])
    business = [r for r in report["results"] if r["category"] == "BUSINESS"]
    assert {r["check_id"] for r in business} >= {"B.OVERBILLING", "B.DUPLICATE_ALLOCATION", "B.CLOSED_ORDER_UNPAID",
                                                 "B.DISPUTE_NOT_IN_AR", "B.ILLEGAL_TRANSITION", "B.DUPLICATE_INVOICE"}
    for result in business:
        assert result["problems"] > 0, result["check_id"]
        assert result["problems"] == result["planted"], result["check_id"]


@pytest.mark.parametrize("sql,check_prefix", [
    ("UPDATE invoice SET total_paise = total_paise + 1 WHERE invoice_id = 'INV-2026-000001'", "S08"),
    ("UPDATE invoice_line SET line_total_paise = line_total_paise + 1 WHERE invoice_line_id = 'IVL-2026-000001'", "S08"),
    ("UPDATE sales_order SET account_id = 'ACC-2026-000002' WHERE order_id = 'SO-2026-000001'", "S06"),
    ("UPDATE sales_order SET order_date = '2025-01-01' WHERE order_id = 'SO-2026-000001'", "S07"),
    ("UPDATE invoice SET due_date = '2030-01-01' WHERE invoice_id = 'INV-2026-000001'", "S07"),
    ("UPDATE invoice SET account_id = 'ACC-9999' WHERE invoice_id = 'INV-2026-000001'", "S02"),
    ("UPDATE status_event SET entity_id = 'SO-2026-999999' WHERE event_id = 'EVT-2026-000500'", "S02"),
    ("DELETE FROM quote WHERE quote_id = 'QTE-2026-000500'", "S05"),
    ("UPDATE sales_order SET status = 'CREATED' WHERE order_id = 'SO-2026-000001'", "S10"),
])
def test_validator_catches_real_corruption(corruptible, sql, check_prefix):
    conn, truth_file = corruptible
    conn.execute(sql)
    conn.commit()
    report = validate(conn, cfg.SCALES["starter"], truth_file)
    failed = [r["check_id"] for r in report["results"] if r["status"] == "FAIL"]
    assert any(c.startswith(check_prefix) for c in failed), failed


@pytest.mark.parametrize("sql,check_id", [
    ("UPDATE invoice SET total_paise = 'abc' WHERE invoice_id = 'INV-2026-000001'", "S13.integers"),
    ("UPDATE payment SET amount_paise = 10.5 WHERE payment_id = 'PAY-2026-000001'", "S13.integers"),
    ("UPDATE invoice SET due_date = '2026-13-45' WHERE invoice_id = 'INV-2026-000001'", "S13.dates"),
    ("UPDATE quote SET quote_date = '31/01/2026' WHERE quote_id = 'QTE-2026-000001'", "S13.dates"),
    ("UPDATE status_event SET event_time = 'yesterday' WHERE event_id = 'EVT-2026-000001'", "S13.dates"),
])
def test_validator_catches_wrong_data_types(corruptible, sql, check_id):
    conn, truth_file = corruptible
    conn.execute(sql)
    conn.commit()
    assert by_id(validate(conn, cfg.SCALES["starter"], truth_file))[check_id]["status"] == "FAIL"


def test_validator_catches_a_wrong_row_count(corruptible):
    conn, truth_file = corruptible
    conn.execute("DELETE FROM status_event WHERE entity_id = 'PAY-2026-001500'")
    conn.execute("DELETE FROM ar_ledger_entry WHERE source_id IN (SELECT allocation_id FROM payment_allocation "
                 "WHERE payment_id = 'PAY-2026-001500')")
    conn.execute("DELETE FROM payment_allocation WHERE payment_id = 'PAY-2026-001500'")
    conn.execute("DELETE FROM payment WHERE payment_id = 'PAY-2026-001500'")
    conn.commit()
    results = by_id(validate(conn, cfg.SCALES["starter"], truth_file))
    assert results["S11.payment"]["status"] == "FAIL"


def test_validator_catches_an_unrecorded_extra_anomaly(corruptible):
    """An anomaly nobody labelled must fail the tie-out rather than pass as normal."""
    conn, truth_file = corruptible
    conn.execute("""UPDATE invoice_line SET quantity = quantity + 50, line_total_paise = unit_price_paise * (quantity + 50)
                    WHERE invoice_line_id = 'IVL-2026-000001'""")
    conn.commit()
    results = by_id(validate(conn, cfg.SCALES["starter"], truth_file))
    assert results["B.OVERBILLING"]["status"] == "FAIL"

