"""Executable data checks.

Two kinds of result are kept apart on purpose:

* STRUCTURAL checks must find zero problems. A failure means the data is broken.
* BUSINESS checks count deliberate rule breaks. They are expected to be non-zero in the
  labelled dataset, must be zero in the clean negative control, and each must equal what
  the ground truth says was planted, so an anomaly can never pass as a normal record.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from . import config as cfg
from .database import PRIMARY_KEYS, cutoff_of, table_columns
from .evaluation import load_ground_truth
from .generator import TABLE_ORDER
from .lifecycle import is_legal

ID_PREFIXES = {
    "product": ("product_id", "PRD"), "account": ("account_id", "ACC"), "quote": ("quote_id", "QTE"),
    "quote_line": ("quote_line_id", "QTL"), "sales_order": ("order_id", "SO"), "order_line": ("order_line_id", "SOL"),
    "shipment": ("shipment_id", "SHP"), "shipment_line": ("shipment_line_id", "SHL"), "invoice": ("invoice_id", "INV"),
    "invoice_line": ("invoice_line_id", "IVL"), "payment": ("payment_id", "PAY"),
    "payment_allocation": ("allocation_id", "ALC"), "dispute": ("dispute_id", "DSP"),
    "ar_ledger_entry": ("entry_id", "ARL"), "status_event": ("event_id", "EVT"),
}

ENTITY_TABLES = {"ACCOUNT": ("account", "account_id"), "QUOTE": ("quote", "quote_id"), "ORDER": ("sales_order", "order_id"),
                 "SHIPMENT": ("shipment", "shipment_id"), "INVOICE": ("invoice", "invoice_id"),
                 "PAYMENT": ("payment", "payment_id"), "DISPUTE": ("dispute", "dispute_id")}

# Each query returns the offending rows, so any non-zero count is a real problem to inspect.
RELATIONSHIP_CHECKS = {
    "order account matches quote account":
        "SELECT o.order_id FROM sales_order o JOIN quote q ON q.quote_id = o.quote_id WHERE o.account_id <> q.account_id",
    "orders come only from accepted quotes":
        "SELECT o.order_id FROM sales_order o JOIN quote q ON q.quote_id = o.quote_id WHERE q.status <> 'ACCEPTED'",
    "order line belongs to the order's quote":
        """SELECT ol.order_line_id FROM order_line ol JOIN sales_order o ON o.order_id = ol.order_id
           JOIN quote_line ql ON ql.quote_line_id = ol.quote_line_id WHERE ql.quote_id <> o.quote_id""",
    "shipment line belongs to the shipment's order":
        """SELECT sl.shipment_line_id FROM shipment_line sl JOIN shipment s ON s.shipment_id = sl.shipment_id
           JOIN order_line ol ON ol.order_line_id = sl.order_line_id WHERE ol.order_id <> s.order_id""",
    "invoice account matches order account":
        "SELECT i.invoice_id FROM invoice i JOIN sales_order o ON o.order_id = i.order_id WHERE i.account_id <> o.account_id",
    "invoice line belongs to the invoice's order":
        """SELECT il.invoice_line_id FROM invoice_line il JOIN invoice i ON i.invoice_id = il.invoice_id
           JOIN order_line ol ON ol.order_line_id = il.order_line_id WHERE ol.order_id <> i.order_id""",
    "invoice covers shipments of its own order":
        """SELECT b.invoice_id FROM invoice_shipment b JOIN invoice i ON i.invoice_id = b.invoice_id
           JOIN shipment s ON s.shipment_id = b.shipment_id WHERE s.order_id <> i.order_id""",
    "allocation stays within one account":
        """SELECT a.allocation_id FROM payment_allocation a JOIN payment p ON p.payment_id = a.payment_id
           JOIN invoice i ON i.invoice_id = a.invoice_id WHERE p.account_id <> i.account_id""",
    "no allocation on a reversed or unallocated payment":
        """SELECT a.allocation_id FROM payment_allocation a JOIN payment p ON p.payment_id = a.payment_id
           WHERE p.status <> 'ALLOCATED'""",
    "no allocation against a void invoice":
        """SELECT a.allocation_id FROM payment_allocation a JOIN invoice i ON i.invoice_id = a.invoice_id
           WHERE i.status = 'VOID'""",
    "dispute account matches invoice account":
        "SELECT d.dispute_id FROM dispute d JOIN invoice i ON i.invoice_id = d.invoice_id WHERE d.account_id <> i.account_id",
    "order line matches its quote line":
        """SELECT ol.order_line_id FROM order_line ol JOIN quote_line ql ON ql.quote_line_id = ol.quote_line_id
           WHERE ol.unit_price_paise <> ql.net_unit_price_paise OR ol.quantity <> ql.quantity
              OR ol.product_id <> ql.product_id""",
    "payment ledger entry sits on its allocation's invoice":
        """SELECT e.entry_id FROM ar_ledger_entry e JOIN payment_allocation a ON a.allocation_id = e.source_id
           WHERE e.invoice_id <> a.invoice_id""",
    "dispute ledger entry sits on its dispute's invoice":
        """SELECT e.entry_id FROM ar_ledger_entry e JOIN dispute d ON d.dispute_id = e.source_id
           WHERE e.invoice_id <> d.invoice_id""",
    "every ledger entry on a real source":
        """SELECT e.entry_id FROM ar_ledger_entry e WHERE e.source_id NOT IN (SELECT invoice_id FROM invoice)
           AND e.source_id NOT IN (SELECT allocation_id FROM payment_allocation)
           AND e.source_id NOT IN (SELECT dispute_id FROM dispute)""",
}

DATE_CHECKS = {
    "quote valid_until after quote_date": "SELECT quote_id FROM quote WHERE valid_until < quote_date",
    "order not before its quote":
        "SELECT o.order_id FROM sales_order o JOIN quote q ON q.quote_id = o.quote_id WHERE o.order_date < q.quote_date",
    "shipment not before its order":
        "SELECT s.shipment_id FROM shipment s JOIN sales_order o ON o.order_id = s.order_id WHERE s.shipped_date < o.order_date",
    "delivery not before shipping": "SELECT shipment_id FROM shipment WHERE delivered_date < shipped_date",
    "invoice not before the shipments it covers":
        """SELECT i.invoice_id FROM invoice i JOIN invoice_shipment b ON b.invoice_id = i.invoice_id
           JOIN shipment s ON s.shipment_id = b.shipment_id WHERE i.invoice_date < s.shipped_date""",
    "due date equals invoice date plus terms":
        """SELECT i.invoice_id FROM invoice i JOIN sales_order o ON o.order_id = i.order_id
           WHERE i.due_date <> date(i.invoice_date, '+' || o.payment_terms_days || ' days')""",
    "allocation not before its payment":
        """SELECT a.allocation_id FROM payment_allocation a JOIN payment p ON p.payment_id = a.payment_id
           WHERE a.allocated_date < p.payment_date""",
    "allocation not before its invoice":
        """SELECT a.allocation_id FROM payment_allocation a JOIN invoice i ON i.invoice_id = a.invoice_id
           WHERE a.allocated_date < i.invoice_date""",
    "dispute not before its invoice":
        "SELECT d.dispute_id FROM dispute d JOIN invoice i ON i.invoice_id = d.invoice_id WHERE d.opened_date < i.invoice_date",
    "dispute resolved after it opened": "SELECT dispute_id FROM dispute WHERE resolved_date < opened_date",
    "no shipment dated after cutoff": "SELECT shipment_id FROM shipment WHERE shipped_date > :cutoff OR delivered_date > :cutoff",
    "no invoice dated after cutoff": "SELECT invoice_id FROM invoice WHERE invoice_date > :cutoff",
    "no payment dated after cutoff": "SELECT payment_id FROM payment WHERE payment_date > :cutoff",
    "no event dated after cutoff": "SELECT event_id FROM status_event WHERE substr(event_time, 1, 10) > :cutoff",
    "no allocation dated after cutoff": "SELECT allocation_id FROM payment_allocation WHERE allocated_date > :cutoff",
    "no ledger entry dated after cutoff": "SELECT entry_id FROM ar_ledger_entry WHERE entry_date > :cutoff",
    "no dispute dated after cutoff": "SELECT dispute_id FROM dispute WHERE opened_date > :cutoff OR resolved_date > :cutoff",
}

# A record's status must agree with the facts around it, not only with its own history.
STATE_CHECKS = {
    "FULFILLED or later orders are fully shipped":
        """SELECT DISTINCT o.order_id FROM sales_order o JOIN v_order_line_position p ON p.order_id = o.order_id
           WHERE o.status IN ('FULFILLED', 'INVOICED', 'CLOSED') AND p.shipped_qty < p.ordered_qty""",
    "partly fulfilled orders have shipped some but not all":
        """SELECT o.order_id FROM sales_order o JOIN v_order_line_position p ON p.order_id = o.order_id
           WHERE o.status = 'PARTIALLY_FULFILLED' GROUP BY o.order_id
           HAVING SUM(p.shipped_qty) = 0 OR SUM(p.shipped_qty) >= SUM(p.ordered_qty)""",
    "orders not yet fulfilled have shipped nothing":
        """SELECT DISTINCT o.order_id FROM sales_order o JOIN v_order_line_position p ON p.order_id = o.order_id
           WHERE o.status IN ('CREATED', 'CONFIRMED', 'CANCELLED') AND p.shipped_qty > 0""",
    "INVOICED or CLOSED orders have every shipment billed":
        """SELECT b.shipment_id FROM v_shipment_billing b JOIN sales_order o ON o.order_id = b.order_id
           WHERE o.status IN ('INVOICED', 'CLOSED') AND b.first_invoice_date IS NULL""",
    "shipped shipments have a shipped date":
        "SELECT shipment_id FROM shipment WHERE status <> 'PLANNED' AND shipped_date IS NULL",
    "planned shipments have no shipped date":
        "SELECT shipment_id FROM shipment WHERE status = 'PLANNED' AND shipped_date IS NOT NULL",
    "delivered shipments have a delivered date":
        "SELECT shipment_id FROM shipment WHERE status = 'DELIVERED' AND delivered_date IS NULL",
    "customers have an order and prospects do not":
        """SELECT a.account_id FROM account a WHERE (a.status = 'CUSTOMER') <>
           EXISTS (SELECT 1 FROM sales_order o WHERE o.account_id = a.account_id)""",
    "credit stays within the disputed amount":
        "SELECT dispute_id FROM dispute WHERE credited_paise > disputed_paise",
    "only credited disputes carry a credit":
        "SELECT dispute_id FROM dispute WHERE (credited_paise > 0) <> (status = 'RESOLVED_CREDIT')",
}

ARITHMETIC_CHECKS = {
    "quote line total = qty x net price":
        "SELECT quote_line_id FROM quote_line WHERE line_total_paise <> quantity * net_unit_price_paise",
    "quote line net price = list less discount":
        """SELECT quote_line_id FROM quote_line
           WHERE net_unit_price_paise <> (list_price_paise * (10000 - discount_bps) + 5000) / 10000""",
    "order line total = qty x price":
        "SELECT order_line_id FROM order_line WHERE line_total_paise <> quantity * unit_price_paise",
    "invoice line total = qty x price":
        "SELECT invoice_line_id FROM invoice_line WHERE line_total_paise <> quantity * unit_price_paise",
    "quote total = sum of lines":
        """SELECT q.quote_id FROM quote q JOIN (SELECT quote_id, SUM(line_total_paise) AS t FROM quote_line GROUP BY quote_id) l
           ON l.quote_id = q.quote_id WHERE q.total_paise <> l.t""",
    "order total = sum of lines":
        """SELECT o.order_id FROM sales_order o JOIN (SELECT order_id, SUM(line_total_paise) AS t FROM order_line GROUP BY order_id) l
           ON l.order_id = o.order_id WHERE o.total_paise <> l.t""",
    "invoice total = sum of lines":
        """SELECT i.invoice_id FROM invoice i JOIN (SELECT invoice_id, SUM(line_total_paise) AS t FROM invoice_line GROUP BY invoice_id) l
           ON l.invoice_id = i.invoice_id WHERE i.total_paise <> l.t""",
    "every header has at least one line":
        """SELECT invoice_id FROM invoice WHERE invoice_id NOT IN (SELECT invoice_id FROM invoice_line)
           UNION ALL SELECT order_id FROM sales_order WHERE order_id NOT IN (SELECT order_id FROM order_line)
           UNION ALL SELECT quote_id FROM quote WHERE quote_id NOT IN (SELECT quote_id FROM quote_line)""",
    "shipped quantity never exceeds ordered":
        "SELECT order_line_id FROM v_order_line_position WHERE shipped_qty > ordered_qty",
    "ledger posting = invoice total":
        """SELECT i.invoice_id FROM invoice i JOIN v_ledger_by_invoice l ON l.invoice_id = i.invoice_id
           WHERE l.posted_paise <> i.total_paise""",
    "ledger balance never negative": "SELECT invoice_id FROM v_invoice_balance WHERE balance_paise < 0",
    "paid invoices have zero balance": "SELECT invoice_id FROM v_invoice_balance WHERE status = 'PAID' AND balance_paise <> 0",
}

# Live invoices that bill a shipment some other live invoice also bills.
SHARED_SHIPMENT_INVOICES = """SELECT DISTINCT b.invoice_id, b.shipment_id FROM invoice_shipment b
    JOIN invoice i ON i.invoice_id = b.invoice_id AND i.status <> 'VOID'
    JOIN invoice_shipment other ON other.shipment_id = b.shipment_id AND other.invoice_id <> b.invoice_id
    JOIN invoice j ON j.invoice_id = other.invoice_id AND j.status <> 'VOID'"""

# Rule breaks that are deliberate. Counts must tie out to the ground truth.
BUSINESS_CHECKS = {
    "OVERBILLING": f"""SELECT p.order_line_id FROM v_order_line_position p
        WHERE p.billed_qty > p.shipped_qty AND p.order_line_id NOT IN (
            SELECT il.order_line_id FROM invoice_line il
            JOIN ({SHARED_SHIPMENT_INVOICES}) d ON d.invoice_id = il.invoice_id)""",
    "DUPLICATE_INVOICE": f"""SELECT d.invoice_id FROM ({SHARED_SHIPMENT_INVOICES}) d
        JOIN invoice i ON i.invoice_id = d.invoice_id
        WHERE EXISTS (SELECT 1 FROM ({SHARED_SHIPMENT_INVOICES}) e
                      JOIN invoice j ON j.invoice_id = e.invoice_id
                      WHERE e.shipment_id = d.shipment_id
                        AND (j.invoice_date, j.invoice_id) < (i.invoice_date, i.invoice_id))""",
    "DUPLICATE_ALLOCATION": """SELECT p.payment_id FROM payment p JOIN payment_allocation a ON a.payment_id = p.payment_id
        GROUP BY p.payment_id HAVING SUM(a.allocated_paise) > p.amount_paise""",
    "CLOSED_ORDER_UNPAID": f"""SELECT DISTINCT o.order_id FROM sales_order o JOIN v_invoice_balance b ON b.order_id = o.order_id
        WHERE o.status = 'CLOSED' AND b.balance_paise > :tolerance AND b.invoice_id NOT IN (
            SELECT d.invoice_id FROM ({SHARED_SHIPMENT_INVOICES}) d JOIN invoice i ON i.invoice_id = d.invoice_id
            WHERE EXISTS (SELECT 1 FROM ({SHARED_SHIPMENT_INVOICES}) e JOIN invoice j ON j.invoice_id = e.invoice_id
                          WHERE e.shipment_id = d.shipment_id
                            AND (j.invoice_date, j.invoice_id) < (i.invoice_date, i.invoice_id)))""",
    "DISPUTE_NOT_IN_AR": """SELECT d.dispute_id FROM dispute d
        LEFT JOIN (SELECT source_id, SUM(CASE WHEN entry_type = 'DISPUTE_HOLD' THEN amount_paise ELSE -amount_paise END) AS h
                   FROM ar_ledger_entry WHERE entry_type IN ('DISPUTE_HOLD', 'DISPUTE_RELEASE') GROUP BY source_id) l
        ON l.source_id = d.dispute_id
        WHERE d.status IN ('OPEN', 'UNDER_REVIEW') AND COALESCE(l.h, 0) <> d.disputed_paise""",
}


DATE_COLUMNS = {
    "account": ("created_date",), "quote": ("quote_date", "valid_until"), "sales_order": ("order_date",),
    "shipment": ("planned_date", "shipped_date", "delivered_date"), "invoice": ("invoice_date", "due_date"),
    "payment": ("payment_date",), "payment_allocation": ("allocated_date",),
    "dispute": ("opened_date", "resolved_date"), "ar_ledger_entry": ("entry_date",),
}


def _result(check_id: str, category: str, description: str, failures: int, sample: list | None = None) -> dict:
    return {"check_id": check_id, "category": category, "description": description, "problems": failures,
            "status": "PASS" if failures == 0 else "FAIL", "sample": (sample or [])[:5]}


def _run_group(conn: sqlite3.Connection, prefix: str, checks: dict, params: dict) -> list[dict]:
    results = []
    for number, (description, sql) in enumerate(checks.items(), start=1):
        rows = [r[0] for r in conn.execute(sql, params).fetchall()]
        results.append(_result(f"{prefix}.{number:02d}", "STRUCTURAL", description, len(rows), rows))
    return results


def check_primary_keys(conn: sqlite3.Connection) -> list[dict]:
    results = []
    for table in TABLE_ORDER:
        key = PRIMARY_KEYS[table]
        total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        distinct = conn.execute(f"SELECT COUNT(*) FROM (SELECT DISTINCT {key} FROM {table})").fetchone()[0]
        results.append(_result(f"S01.{table}", "STRUCTURAL", f"{table} primary key unique", total - distinct))
    return results


def check_foreign_keys(conn: sqlite3.Connection) -> list[dict]:
    broken = conn.execute("PRAGMA foreign_key_check").fetchall()
    results = [_result("S02.fk", "STRUCTURAL", "Declared foreign keys resolve", len(broken), [tuple(r) for r in broken])]
    orphans = []
    for entity_type, (table, key) in ENTITY_TABLES.items():
        orphans += [r[0] for r in conn.execute(
            f"""SELECT event_id FROM status_event WHERE entity_type = ?
                AND entity_id NOT IN (SELECT {key} FROM {table})""", (entity_type,))]
    results.append(_result("S02.events", "STRUCTURAL", "Every status event points at a real record", len(orphans), orphans))
    return results


def check_required_values(conn: sqlite3.Connection) -> list[dict]:
    problems = []
    for table in TABLE_ORDER:
        for row in conn.execute(f"PRAGMA table_info({table})"):
            if row["notnull"]:
                nulls = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {row['name']} IS NULL").fetchone()[0]
                if nulls:
                    problems.append(f"{table}.{row['name']}: {nulls}")
    return [_result("S03", "STRUCTURAL", "Required columns are populated", len(problems), problems)]


def check_enums(conn: sqlite3.Connection) -> list[dict]:
    problems = []
    for (table, column), allowed in cfg.ENUMS.items():
        marks = ", ".join("?" for _ in allowed)
        bad = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {column} NOT IN ({marks})", allowed).fetchone()[0]
        if bad:
            problems.append(f"{table}.{column}: {bad}")
    return [_result("S04", "STRUCTURAL", "Enumerated columns hold allowed values", len(problems), problems)]


def check_ids(conn: sqlite3.Connection) -> list[dict]:
    results = []
    for table, (column, prefix) in ID_PREFIXES.items():
        pattern = re.compile(rf"^{prefix}-2026-(\d{{6}})$")
        numbers = []
        malformed = []
        for (value,) in conn.execute(f"SELECT {column} FROM {table}").fetchall():
            match = pattern.match(value)
            if match:
                numbers.append(int(match.group(1)))
            else:
                malformed.append(value)
        contiguous = sorted(numbers) == list(range(1, len(numbers) + 1))
        results.append(_result(f"S05.{table}", "STRUCTURAL", f"{table} IDs well-formed and contiguous",
                               len(malformed) + (0 if contiguous else 1), malformed))
    return results


def check_event_history(conn: sqlite3.Connection) -> list[dict]:
    """Current status must equal the last event, and time must rise with event ID in each record."""
    mismatches = []
    time_order = []
    for entity_type, (table, key) in ENTITY_TABLES.items():
        last_event = {}
        previous_time = {}
        for row in conn.execute(
            """SELECT entity_id, to_status, event_time FROM status_event WHERE entity_type = ?
               ORDER BY entity_id, event_id""", (entity_type,)):
            if previous_time.get(row["entity_id"], "") >= row["event_time"]:
                time_order.append(row["entity_id"])
            previous_time[row["entity_id"]] = row["event_time"]
            last_event[row["entity_id"]] = row["to_status"]
        for row in conn.execute(f"SELECT {key} AS id, status FROM {table}"):
            if last_event.get(row["id"]) != row["status"]:
                mismatches.append(row["id"])
    return [_result("S10.status", "STRUCTURAL", "Record status equals its latest event", len(mismatches), mismatches),
            _result("S10.order", "STRUCTURAL", "Event times strictly rise with event ID per record", len(time_order), time_order)]


def check_data_types(conn: sqlite3.Connection) -> list[dict]:
    """SQLite stores whatever it is given, so types need checking rather than assuming."""
    numbers, dates = [], []
    for table in TABLE_ORDER:
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall():
            if row["type"] == "INTEGER":
                bad = conn.execute(f"""SELECT COUNT(*) FROM {table} WHERE {row['name']} IS NOT NULL
                                       AND typeof({row['name']}) <> 'integer'""").fetchone()[0]
                if bad:
                    numbers.append(f"{table}.{row['name']}: {bad}")
    for table, columns in DATE_COLUMNS.items():
        for column in columns:
            bad = conn.execute(f"""SELECT COUNT(*) FROM {table} WHERE {column} IS NOT NULL
                                   AND (date({column}) IS NULL OR date({column}) <> {column})""").fetchone()[0]
            if bad:
                dates.append(f"{table}.{column}: {bad}")
    stamps = conn.execute("""SELECT COUNT(*) FROM status_event
                             WHERE strftime('%Y-%m-%dT%H:%M:%S', event_time) IS NOT event_time""").fetchone()[0]
    if stamps:
        dates.append(f"status_event.event_time: {stamps}")
    return [_result("S13.integers", "STRUCTURAL", "Integer columns hold integers", len(numbers), numbers),
            _result("S13.dates", "STRUCTURAL", "Date columns hold valid ISO dates", len(dates), dates)]


def check_counts(conn: sqlite3.Connection, scale: cfg.Scale) -> list[dict]:
    expected = {"quote": scale.quotes, "sales_order": scale.orders, "invoice": scale.invoices, "payment": scale.payments}
    results = []
    for table, count in expected.items():
        actual = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        results.append(_result(f"S11.{table}", "STRUCTURAL", f"{table} row count is {count:,} (found {actual:,})",
                               abs(actual - count)))
    return results


def check_ground_truth(conn: sqlite3.Connection, ground_truth: list[dict]) -> list[dict]:
    """Every label must point at a record that exists."""
    lookups = {"ORDER_LINE": ("order_line", "order_line_id"), "INVOICE": ("invoice", "invoice_id"),
               "PAYMENT": ("payment", "payment_id"), "ORDER": ("sales_order", "order_id"),
               "STATUS_EVENT": ("status_event", "event_id"), "DISPUTE": ("dispute", "dispute_id"),
               "SHIPMENT": ("shipment", "shipment_id")}
    missing = []
    for label in ground_truth:
        table, key = lookups[label["source_entity"]]
        if conn.execute(f"SELECT 1 FROM {table} WHERE {key} = ?", (label["primary_id"],)).fetchone() is None:
            missing.append(label["gt_id"])
    return [_result("S12", "STRUCTURAL", "Ground-truth labels point at existing records", len(missing), missing)]


def check_business_anomalies(conn: sqlite3.Connection, ground_truth: list[dict]) -> list[dict]:
    """Count rule breaks directly in the data and tie them to the planted labels."""
    params = {"tolerance": cfg.BALANCE_TOLERANCE_PAISE}
    planted: dict[str, int] = {}
    for label in ground_truth:
        planted[label["issue_type"]] = planted.get(label["issue_type"], 0) + 1

    results = []
    for issue_type, sql in BUSINESS_CHECKS.items():
        found = len({r[0] for r in conn.execute(sql, params).fetchall()})
        wanted = planted.get(issue_type, 0)
        results.append({"check_id": f"B.{issue_type}", "category": "BUSINESS", "description": f"{issue_type} present in data",
                        "problems": found, "planted": wanted, "status": "PASS" if found == wanted else "FAIL",
                        "sample": []})

    illegal = 0
    for row in conn.execute("SELECT entity_type, from_status, to_status FROM status_event"):
        if not is_legal(row["entity_type"], row["from_status"], row["to_status"]):
            illegal += 1
    wanted = planted.get("ILLEGAL_TRANSITION", 0)
    results.append({"check_id": "B.ILLEGAL_TRANSITION", "category": "BUSINESS", "description": "Illegal transitions present",
                    "problems": illegal, "planted": wanted, "status": "PASS" if illegal == wanted else "FAIL",
                    "sample": []})
    return results


def validate(conn: sqlite3.Connection, scale: cfg.Scale, ground_truth_path: Path | None) -> dict:
    params = {"cutoff": cutoff_of(conn).isoformat()}
    ground_truth = load_ground_truth(ground_truth_path) if ground_truth_path else []
    results = []
    results += check_primary_keys(conn)
    results += check_foreign_keys(conn)
    results += check_required_values(conn)
    results += check_enums(conn)
    results += check_ids(conn)
    results += _run_group(conn, "S06", RELATIONSHIP_CHECKS, params)
    results += _run_group(conn, "S07", DATE_CHECKS, params)
    results += _run_group(conn, "S08", ARITHMETIC_CHECKS, params)
    results += _run_group(conn, "S09", STATE_CHECKS, params)
    results += check_event_history(conn)
    results += check_data_types(conn)
    results += check_counts(conn, scale)
    results += check_ground_truth(conn, ground_truth)
    results += check_business_anomalies(conn, ground_truth)
    structural = [r for r in results if r["category"] == "STRUCTURAL"]
    business = [r for r in results if r["category"] == "BUSINESS"]
    return {
        "structural_checks": len(structural),
        "structural_failed": sum(1 for r in structural if r["status"] == "FAIL"),
        "business_checks": len(business),
        "business_failed": sum(1 for r in business if r["status"] == "FAIL"),
        "results": results,
    }
