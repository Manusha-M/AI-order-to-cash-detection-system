"""Central configuration: seed, cutoff, business thresholds, enums and scale profiles.

Every threshold lives here, and the generator reads the same values, so a change is one
number and a re-run. Setting a target tighter than normal behaviour (fulfilment under 19
days, for example) makes ordinary records look late, which is what that change means.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_SQL = ROOT / "sql" / "schema.sql"
ANALYTICS_SQL = ROOT / "sql" / "analytics.sql"

DEFAULT_SEED = 20261022
GENERATOR_VERSION = "1.0"

# All data lives in one analysis window. Aging and "still open" are measured at CUTOFF.
WINDOW_START = date(2026, 1, 1)
CUTOFF = date(2026, 9, 30)

# Business thresholds (days unless stated). See docs/business_rules.md.
SLA_ORDER_TO_FULFILMENT_DAYS = 21
SLA_SHIPMENT_TO_INVOICE_DAYS = 7
UNBILLED_GRACE_DAYS = 30
LONG_OVERDUE_DAYS = 90
SHORT_PAY_MIN_DAYS_PAST_DUE = 30
SHORT_PAY_STALE_DAYS = 30
BALANCE_TOLERANCE_PAISE = 10_000  # Rs 100: residuals at or below this are not chased.

# Severity bands for money findings.
SEVERITY_HIGH_PAISE = 10_000_000  # Rs 1,00,000
SEVERITY_MEDIUM_PAISE = 1_000_000  # Rs 10,000

ENUMS = {
    ("account", "segment"): ("SMB", "MID_MARKET", "ENTERPRISE"),
    ("account", "region"): ("NORTH", "SOUTH", "EAST", "WEST"),
    ("account", "status"): ("PROSPECT", "CUSTOMER"),
    ("product", "category"): ("MECHANICAL", "ELECTRICAL", "CONSUMABLE", "SAFETY"),
    ("quote", "channel"): ("INBOUND", "OUTBOUND", "PARTNER", "RENEWAL"),
    ("quote", "status"): ("DRAFT", "SENT", "ACCEPTED", "REJECTED", "EXPIRED"),
    ("sales_order", "status"): (
        "CREATED", "CONFIRMED", "PARTIALLY_FULFILLED", "FULFILLED", "INVOICED", "CLOSED", "CANCELLED",
    ),
    ("shipment", "status"): ("PLANNED", "SHIPPED", "DELIVERED"),
    ("shipment", "carrier"): ("BLUELINE", "SWIFTCARGO", "TRANSINDIA", "OWN_FLEET"),
    ("invoice", "status"): ("DRAFT", "ISSUED", "PARTIALLY_PAID", "PAID", "DISPUTED", "VOID"),
    ("payment", "method"): ("BANK_TRANSFER", "UPI", "CHEQUE", "CARD"),
    ("payment", "status"): ("RECEIVED", "ALLOCATED", "REVERSED"),
    ("dispute", "reason"): ("PRICING", "QUANTITY", "DAMAGED_GOODS", "LATE_DELIVERY", "BILLING_ERROR"),
    ("dispute", "status"): ("OPEN", "UNDER_REVIEW", "RESOLVED_CREDIT", "RESOLVED_NO_CREDIT", "WITHDRAWN"),
    ("ar_ledger_entry", "entry_type"): (
        "INVOICE_POSTED", "INVOICE_VOIDED", "PAYMENT_APPLIED", "CREDIT_MEMO", "DISPUTE_HOLD", "DISPUTE_RELEASE",
    ),
    ("status_event", "entity_type"): ("ACCOUNT", "QUOTE", "ORDER", "SHIPMENT", "INVOICE", "PAYMENT", "DISPUTE"),
    ("status_event", "actor_role"): ("CUSTOMER", "SALES_OPS", "SUPPORT_AGENT", "ANALYST", "SYSTEM_ADMIN", "SYSTEM"),
}

# Full-scale counts of each labelled scenario. Starter uses factor-scaled counts with a floor.
FULL_SCENARIO_COUNTS = {
    "overbilling": 60,
    "duplicate_allocation": 50,
    "closed_unpaid": 40,
    "illegal_transition": 60,
    "dispute_not_in_ar": 40,
    "underbilling": 90,
    "duplicate_invoice": 50,
    "short_payment": 120,
    "long_overdue": 150,
}
MIN_SCENARIO_COUNT = 6


@dataclass(frozen=True)
class Scale:
    name: str
    factor: float
    quotes: int
    orders: int
    invoices: int
    payments: int
    accounts: int
    products: int

    def scenario_count(self, key: str) -> int:
        return max(MIN_SCENARIO_COUNT, round(FULL_SCENARIO_COUNTS[key] * self.factor))

    def scaled(self, full_value: int, floor: int = 1) -> int:
        return max(floor, round(full_value * self.factor))


SCALES = {
    "starter": Scale("starter", 0.1, 1_000, 700, 800, 1_500, 80, 40),
    "full": Scale("full", 1.0, 10_000, 7_000, 8_000, 15_000, 600, 40),
}


def data_dir(scale_name: str) -> Path:
    return ROOT / "data" / scale_name


def output_dir(scale_name: str) -> Path:
    return ROOT / "outputs" / scale_name
