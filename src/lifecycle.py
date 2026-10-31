"""Lifecycle state machines shared by the generator, detector and validator.

A key of ``None`` means "no previous state": the transition that creates the record.
"""
from __future__ import annotations

from collections import deque

TRANSITIONS: dict[str, dict[str | None, set[str]]] = {
    "ACCOUNT": {
        None: {"PROSPECT"},
        "PROSPECT": {"CUSTOMER"},
    },
    "QUOTE": {
        None: {"DRAFT"},
        "DRAFT": {"SENT"},
        "SENT": {"ACCEPTED", "REJECTED", "EXPIRED"},
    },
    "ORDER": {
        None: {"CREATED"},
        "CREATED": {"CONFIRMED", "CANCELLED"},
        "CONFIRMED": {"PARTIALLY_FULFILLED", "FULFILLED", "CANCELLED"},
        "PARTIALLY_FULFILLED": {"FULFILLED"},
        "FULFILLED": {"INVOICED"},
        "INVOICED": {"CLOSED"},
    },
    "SHIPMENT": {
        None: {"PLANNED"},
        "PLANNED": {"SHIPPED"},
        "SHIPPED": {"DELIVERED"},
    },
    "INVOICE": {
        None: {"DRAFT"},
        "DRAFT": {"ISSUED"},
        "ISSUED": {"PARTIALLY_PAID", "PAID", "DISPUTED", "VOID"},
        "PARTIALLY_PAID": {"PAID", "DISPUTED"},
        "DISPUTED": {"ISSUED", "PARTIALLY_PAID", "PAID"},
    },
    "PAYMENT": {
        None: {"RECEIVED"},
        "RECEIVED": {"ALLOCATED", "REVERSED"},
    },
    "DISPUTE": {
        None: {"OPEN"},
        "OPEN": {"UNDER_REVIEW", "WITHDRAWN"},
        "UNDER_REVIEW": {"RESOLVED_CREDIT", "RESOLVED_NO_CREDIT", "WITHDRAWN"},
    },
}


def is_legal(entity_type: str, from_status: str | None, to_status: str) -> bool:
    return to_status in TRANSITIONS[entity_type].get(from_status, set())


def skipped_states(entity_type: str, from_status: str | None, to_status: str) -> list[str] | None:
    """Return the states bypassed by an illegal jump, or None if no legal route exists.

    Example: ORDER CONFIRMED -> INVOICED returns ["FULFILLED"].
    """
    machine = TRANSITIONS[entity_type]
    queue = deque([(from_status, [])])
    seen = {from_status}
    while queue:
        state, path = queue.popleft()
        for nxt in sorted(machine.get(state, set())):
            if nxt == to_status:
                return path
            if nxt not in seen:
                seen.add(nxt)
                queue.append((nxt, path + [nxt]))
    return None
