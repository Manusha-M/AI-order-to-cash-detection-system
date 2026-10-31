"""Shared fixtures.

`chain` builds the smallest valid order-to-cash story by hand: one account, one quote, one
order, one shipment, one invoice, one payment. Rule tests bend one fact at a time, so each
boundary is tested on its own. `starter` is the real generated dataset, built once.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src import config as cfg
from src.database import build_database, connect, write_ground_truth
from src.detector import run_detection
from src.generator import generate

ACC = "ACC-2026-000001"
PRD = "PRD-2026-000001"
QTE = "QTE-2026-000001"
QTL = "QTL-2026-000001"
SO = "SO-2026-000001"
SOL = "SOL-2026-000001"
SHP = "SHP-2026-000001"
SHL = "SHL-2026-000001"
INV = "INV-2026-000001"
IVL = "IVL-2026-000001"
PAY = "PAY-2026-000001"
ALC = "ALC-2026-000001"
PRICE = 10_000  # Rs 100 per unit
QTY = 10
TOTAL = PRICE * QTY

HISTORY = [
    ("QUOTE", QTE, None, "DRAFT", "2026-02-20T10:00:00", "SALES_OPS"),
    ("QUOTE", QTE, "DRAFT", "SENT", "2026-02-21T10:00:00", "SALES_OPS"),
    ("QUOTE", QTE, "SENT", "ACCEPTED", "2026-02-28T10:00:00", "CUSTOMER"),
    ("ORDER", SO, None, "CREATED", "2026-03-01T10:00:00", "SYSTEM"),
    ("ORDER", SO, "CREATED", "CONFIRMED", "2026-03-01T11:00:00", "SALES_OPS"),
    ("ORDER", SO, "CONFIRMED", "FULFILLED", "2026-03-03T10:00:00", "SYSTEM"),
    ("ORDER", SO, "FULFILLED", "INVOICED", "2026-03-04T10:00:00", "SYSTEM"),
    ("ORDER", SO, "INVOICED", "CLOSED", "2026-04-01T11:00:00", "SALES_OPS"),
    ("SHIPMENT", SHP, None, "PLANNED", "2026-03-01T12:00:00", "SYSTEM"),
    ("SHIPMENT", SHP, "PLANNED", "SHIPPED", "2026-03-03T10:00:00", "SYSTEM"),
    ("SHIPMENT", SHP, "SHIPPED", "DELIVERED", "2026-03-05T10:00:00", "CUSTOMER"),
    ("INVOICE", INV, None, "DRAFT", "2026-03-04T10:00:00", "SYSTEM"),
    ("INVOICE", INV, "DRAFT", "ISSUED", "2026-03-04T10:30:00", "SYSTEM"),
    ("INVOICE", INV, "ISSUED", "PAID", "2026-04-01T10:00:00", "SYSTEM"),
    ("PAYMENT", PAY, None, "RECEIVED", "2026-04-01T09:00:00", "SYSTEM"),
    ("PAYMENT", PAY, "RECEIVED", "ALLOCATED", "2026-04-01T10:00:00", "SYSTEM"),
]


def seed_chain(conn) -> None:
    conn.executemany("INSERT INTO run_metadata VALUES (?, ?)",
                     [("cutoff_date", cfg.CUTOFF.isoformat()), ("seed", "0"), ("scale", "chain")])
    conn.execute("INSERT INTO product VALUES (?, 'Test Valve', 'MECHANICAL', ?)", (PRD, PRICE))
    conn.execute("INSERT INTO account VALUES (?, 'Test Co', 'SMB', 'NORTH', 'CUSTOMER', 30, 100000, '2025-06-01')", (ACC,))
    conn.execute("INSERT INTO quote VALUES (?, ?, '2026-02-20', '2026-03-22', 'INBOUND', 'ACCEPTED', ?)", (QTE, ACC, TOTAL))
    conn.execute("INSERT INTO quote_line VALUES (?, ?, 1, ?, ?, ?, 0, ?, ?)", (QTL, QTE, PRD, QTY, PRICE, PRICE, TOTAL))
    conn.execute("INSERT INTO sales_order VALUES (?, ?, ?, '2026-03-01', 30, 'CLOSED', ?)", (SO, QTE, ACC, TOTAL))
    conn.execute("INSERT INTO order_line VALUES (?, ?, ?, 1, ?, ?, ?, ?)", (SOL, SO, QTL, PRD, QTY, PRICE, TOTAL))
    conn.execute("INSERT INTO shipment VALUES (?, ?, 'BLUELINE', '2026-03-02', '2026-03-03', '2026-03-05', 'DELIVERED')",
                 (SHP, SO))
    conn.execute("INSERT INTO shipment_line VALUES (?, ?, ?, ?)", (SHL, SHP, SOL, QTY))
    conn.execute("INSERT INTO invoice VALUES (?, ?, ?, '2026-03-04', '2026-04-03', 'PAID', ?, NULL)", (INV, SO, ACC, TOTAL))
    conn.execute("INSERT INTO invoice_line VALUES (?, ?, ?, 1, ?, ?, ?)", (IVL, INV, SOL, QTY, PRICE, TOTAL))
    conn.execute("INSERT INTO invoice_shipment VALUES (?, ?)", (INV, SHP))
    conn.execute("INSERT INTO payment VALUES (?, ?, '2026-04-01', ?, 'UPI', 'UTR1', 'ALLOCATED')", (PAY, ACC, TOTAL))
    conn.execute("INSERT INTO payment_allocation VALUES (?, ?, ?, ?, '2026-04-01')", (ALC, PAY, INV, TOTAL))
    ledger = [("ARL-2026-000001", INV, "INVOICE_POSTED", TOTAL, "2026-03-04", INV),
              ("ARL-2026-000002", INV, "PAYMENT_APPLIED", TOTAL, "2026-04-01", ALC)]
    conn.executemany("INSERT INTO ar_ledger_entry VALUES (?, ?, ?, ?, ?, ?)", ledger)
    for number, event in enumerate(HISTORY, start=1):
        conn.execute("INSERT INTO status_event VALUES (?, ?, ?, ?, ?, ?, ?)", (f"EVT-2026-{number:06d}", *event))
    conn.commit()


@pytest.fixture
def chain(tmp_path):
    conn = connect(tmp_path / "chain.db")
    conn.executescript(cfg.SCHEMA_SQL.read_text(encoding="utf-8"))
    conn.executescript(cfg.ANALYTICS_SQL.read_text(encoding="utf-8"))
    seed_chain(conn)
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def starter_dataset():
    return generate(cfg.SCALES["starter"])


@pytest.fixture(scope="session")
def starter_paths(tmp_path_factory, starter_dataset) -> tuple[Path, Path]:
    directory = tmp_path_factory.mktemp("starter")
    db_file = directory / "o2c.db"
    truth_file = directory / "ground_truth.csv"
    build_database(starter_dataset, db_file, "starter", True)
    write_ground_truth(starter_dataset, truth_file)
    conn = connect(db_file)
    run_detection(conn)
    conn.close()
    return db_file, truth_file


@pytest.fixture
def starter_conn(starter_paths):
    conn = connect(starter_paths[0])
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def clean_paths(tmp_path_factory) -> Path:
    directory = tmp_path_factory.mktemp("clean")
    db_file = directory / "clean.db"
    build_database(generate(cfg.SCALES["starter"], inject=False), db_file, "starter", False)
    conn = connect(db_file)
    run_detection(conn)
    conn.close()
    return db_file
