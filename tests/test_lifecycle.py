"""Lifecycle tests: the state machines themselves, and history stored in the data."""
from __future__ import annotations

import pytest

from src.database import connect
from src.lifecycle import TRANSITIONS, is_legal, skipped_states


@pytest.mark.parametrize("entity,start,end", [
    ("QUOTE", None, "DRAFT"),
    ("QUOTE", "SENT", "ACCEPTED"),
    ("ORDER", "CONFIRMED", "FULFILLED"),
    ("ORDER", "CONFIRMED", "PARTIALLY_FULFILLED"),
    ("ORDER", "INVOICED", "CLOSED"),
    ("INVOICE", "ISSUED", "VOID"),
    ("INVOICE", "DISPUTED", "PAID"),
    ("PAYMENT", "RECEIVED", "REVERSED"),
    ("DISPUTE", "UNDER_REVIEW", "RESOLVED_CREDIT"),
])
def test_legal_transitions(entity, start, end):
    assert is_legal(entity, start, end)


@pytest.mark.parametrize("entity,start,end", [
    ("QUOTE", "DRAFT", "ACCEPTED"),
    ("ORDER", "CONFIRMED", "INVOICED"),
    ("ORDER", "CREATED", "CLOSED"),
    ("ORDER", "CLOSED", "CONFIRMED"),
    ("SHIPMENT", "PLANNED", "DELIVERED"),
    ("INVOICE", "DRAFT", "PAID"),
    ("INVOICE", "VOID", "PAID"),
    ("DISPUTE", "OPEN", "RESOLVED_CREDIT"),
])
def test_illegal_transitions(entity, start, end):
    assert not is_legal(entity, start, end)


def test_skipped_state_is_named():
    assert skipped_states("ORDER", "CONFIRMED", "INVOICED") == ["FULFILLED"]
    assert skipped_states("QUOTE", "DRAFT", "ACCEPTED") == ["SENT"]
    assert skipped_states("DISPUTE", "OPEN", "RESOLVED_CREDIT") == ["UNDER_REVIEW"]


def test_no_route_backwards():
    assert skipped_states("ORDER", "CLOSED", "CREATED") is None


def test_every_entity_has_a_starting_state():
    for machine in TRANSITIONS.values():
        assert None in machine and len(machine[None]) == 1


def test_clean_world_events_are_all_legal(clean_paths):
    conn = connect(clean_paths)
    for row in conn.execute("SELECT entity_type, from_status, to_status FROM status_event"):
        assert is_legal(row["entity_type"], row["from_status"], row["to_status"])
    conn.close()


def test_history_rebuilds_each_clean_record(clean_paths):
    """Replaying events must reach the status stored on the record: history is not overwritten."""
    conn = connect(clean_paths)
    replay: dict[str, str | None] = {}
    rows = conn.execute("SELECT * FROM status_event ORDER BY entity_type, entity_id, event_time, event_id").fetchall()
    for row in rows:
        assert row["from_status"] == replay.get(row["entity_id"]), row["event_id"]
        replay[row["entity_id"]] = row["to_status"]
    for order in conn.execute("SELECT order_id, status FROM sales_order"):
        assert replay[order["order_id"]] == order["status"]
    for invoice in conn.execute("SELECT invoice_id, status FROM invoice"):
        assert replay[invoice["invoice_id"]] == invoice["status"]
    conn.close()


def test_multi_step_history_is_kept(starter_conn):
    deepest = starter_conn.execute(
        """SELECT MAX(n) FROM (SELECT COUNT(*) AS n FROM status_event
           WHERE entity_type = 'ORDER' GROUP BY entity_id)""").fetchone()[0]
    assert deepest >= 5


def test_actors_cover_the_primary_roles(starter_conn):
    actors = {r[0] for r in starter_conn.execute("SELECT DISTINCT actor_role FROM status_event")}
    assert {"CUSTOMER", "SALES_OPS", "SUPPORT_AGENT", "ANALYST", "SYSTEM_ADMIN"} <= actors
