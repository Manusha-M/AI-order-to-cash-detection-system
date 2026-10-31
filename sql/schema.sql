-- Order-to-Cash relational schema. All money is INR stored as integer paise (Rs 1 = 100 paise).
-- Dates are 'YYYY-MM-DD'; timestamps are 'YYYY-MM-DDTHH:MM:SS' local (IST) with no offset.
--
-- CHECK constraints guard structure (formats, enums, positive numbers). They deliberately do NOT
-- forbid business anomalies such as billing more than was shipped: those must be storable so the
-- detector can find them.

CREATE TABLE run_metadata (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE product (
    product_id       TEXT PRIMARY KEY CHECK (product_id GLOB 'PRD-2026-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    product_name     TEXT NOT NULL UNIQUE,
    category         TEXT NOT NULL CHECK (category IN ('MECHANICAL', 'ELECTRICAL', 'CONSUMABLE', 'SAFETY')),
    list_price_paise INTEGER NOT NULL CHECK (list_price_paise > 0)
);

CREATE TABLE account (
    account_id         TEXT PRIMARY KEY CHECK (account_id GLOB 'ACC-2026-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    account_name       TEXT NOT NULL UNIQUE,
    segment            TEXT NOT NULL CHECK (segment IN ('SMB', 'MID_MARKET', 'ENTERPRISE')),
    region             TEXT NOT NULL CHECK (region IN ('NORTH', 'SOUTH', 'EAST', 'WEST')),
    status             TEXT NOT NULL CHECK (status IN ('PROSPECT', 'CUSTOMER')),
    payment_terms_days INTEGER NOT NULL CHECK (payment_terms_days IN (15, 30, 45, 60)),
    credit_limit_paise INTEGER NOT NULL CHECK (credit_limit_paise >= 0),
    created_date       TEXT NOT NULL
);

CREATE TABLE quote (
    quote_id    TEXT PRIMARY KEY CHECK (quote_id GLOB 'QTE-2026-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    account_id  TEXT NOT NULL REFERENCES account (account_id),
    quote_date  TEXT NOT NULL,
    valid_until TEXT NOT NULL,
    channel     TEXT NOT NULL CHECK (channel IN ('INBOUND', 'OUTBOUND', 'PARTNER', 'RENEWAL')),
    status      TEXT NOT NULL CHECK (status IN ('DRAFT', 'SENT', 'ACCEPTED', 'REJECTED', 'EXPIRED')),
    total_paise INTEGER NOT NULL CHECK (total_paise >= 0)
);

CREATE TABLE quote_line (
    quote_line_id        TEXT PRIMARY KEY CHECK (quote_line_id GLOB 'QTL-2026-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    quote_id             TEXT NOT NULL REFERENCES quote (quote_id),
    line_number          INTEGER NOT NULL CHECK (line_number > 0),
    product_id           TEXT NOT NULL REFERENCES product (product_id),
    quantity             INTEGER NOT NULL CHECK (quantity > 0),
    list_price_paise     INTEGER NOT NULL CHECK (list_price_paise > 0),
    discount_bps         INTEGER NOT NULL CHECK (discount_bps BETWEEN 0 AND 3000),
    net_unit_price_paise INTEGER NOT NULL CHECK (net_unit_price_paise > 0),
    line_total_paise     INTEGER NOT NULL CHECK (line_total_paise > 0),
    UNIQUE (quote_id, line_number)
);

-- A quote converts to at most one order (quote 1 : 0..1 order), enforced by UNIQUE quote_id.
CREATE TABLE sales_order (
    order_id           TEXT PRIMARY KEY CHECK (order_id GLOB 'SO-2026-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    quote_id           TEXT NOT NULL UNIQUE REFERENCES quote (quote_id),
    account_id         TEXT NOT NULL REFERENCES account (account_id),
    order_date         TEXT NOT NULL,
    payment_terms_days INTEGER NOT NULL CHECK (payment_terms_days IN (15, 30, 45, 60)),
    status             TEXT NOT NULL CHECK (status IN ('CREATED', 'CONFIRMED', 'PARTIALLY_FULFILLED', 'FULFILLED',
                                                       'INVOICED', 'CLOSED', 'CANCELLED')),
    total_paise        INTEGER NOT NULL CHECK (total_paise > 0)
);

CREATE TABLE order_line (
    order_line_id    TEXT PRIMARY KEY CHECK (order_line_id GLOB 'SOL-2026-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    order_id         TEXT NOT NULL REFERENCES sales_order (order_id),
    quote_line_id    TEXT NOT NULL UNIQUE REFERENCES quote_line (quote_line_id),
    line_number      INTEGER NOT NULL CHECK (line_number > 0),
    product_id       TEXT NOT NULL REFERENCES product (product_id),
    quantity         INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_paise INTEGER NOT NULL CHECK (unit_price_paise > 0),
    line_total_paise INTEGER NOT NULL CHECK (line_total_paise > 0),
    UNIQUE (order_id, line_number)
);

CREATE TABLE shipment (
    shipment_id    TEXT PRIMARY KEY CHECK (shipment_id GLOB 'SHP-2026-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    order_id       TEXT NOT NULL REFERENCES sales_order (order_id),
    carrier        TEXT NOT NULL CHECK (carrier IN ('BLUELINE', 'SWIFTCARGO', 'TRANSINDIA', 'OWN_FLEET')),
    planned_date   TEXT NOT NULL,
    shipped_date   TEXT,
    delivered_date TEXT,
    status         TEXT NOT NULL CHECK (status IN ('PLANNED', 'SHIPPED', 'DELIVERED'))
);

-- Bridge: Shipment N:M OrderLine (one shipment carries many lines; one line can ship in parts).
CREATE TABLE shipment_line (
    shipment_line_id TEXT PRIMARY KEY CHECK (shipment_line_id GLOB 'SHL-2026-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    shipment_id      TEXT NOT NULL REFERENCES shipment (shipment_id),
    order_line_id    TEXT NOT NULL REFERENCES order_line (order_line_id),
    quantity         INTEGER NOT NULL CHECK (quantity > 0),
    UNIQUE (shipment_id, order_line_id)
);

CREATE TABLE invoice (
    invoice_id          TEXT PRIMARY KEY CHECK (invoice_id GLOB 'INV-2026-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    order_id            TEXT NOT NULL REFERENCES sales_order (order_id),
    account_id          TEXT NOT NULL REFERENCES account (account_id),
    invoice_date        TEXT NOT NULL,
    due_date            TEXT NOT NULL,
    status              TEXT NOT NULL CHECK (status IN ('DRAFT', 'ISSUED', 'PARTIALLY_PAID', 'PAID', 'DISPUTED', 'VOID')),
    total_paise         INTEGER NOT NULL CHECK (total_paise > 0),
    replaces_invoice_id TEXT REFERENCES invoice (invoice_id)
);

CREATE TABLE invoice_line (
    invoice_line_id  TEXT PRIMARY KEY CHECK (invoice_line_id GLOB 'IVL-2026-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    invoice_id       TEXT NOT NULL REFERENCES invoice (invoice_id),
    order_line_id    TEXT NOT NULL REFERENCES order_line (order_line_id),
    line_number      INTEGER NOT NULL CHECK (line_number > 0),
    quantity         INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_paise INTEGER NOT NULL CHECK (unit_price_paise > 0),
    line_total_paise INTEGER NOT NULL CHECK (line_total_paise > 0),
    UNIQUE (invoice_id, line_number)
);

-- Bridge: Invoice N:M Shipment (a consolidated invoice bills several shipments; a duplicate
-- invoice points at a shipment that is already billed).
CREATE TABLE invoice_shipment (
    invoice_id  TEXT NOT NULL REFERENCES invoice (invoice_id),
    shipment_id TEXT NOT NULL REFERENCES shipment (shipment_id),
    PRIMARY KEY (invoice_id, shipment_id)
);

CREATE TABLE payment (
    payment_id     TEXT PRIMARY KEY CHECK (payment_id GLOB 'PAY-2026-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    account_id     TEXT NOT NULL REFERENCES account (account_id),
    payment_date   TEXT NOT NULL,
    amount_paise   INTEGER NOT NULL CHECK (amount_paise > 0),
    method         TEXT NOT NULL CHECK (method IN ('BANK_TRANSFER', 'UPI', 'CHEQUE', 'CARD')),
    bank_reference TEXT NOT NULL UNIQUE,
    status         TEXT NOT NULL CHECK (status IN ('RECEIVED', 'ALLOCATED', 'REVERSED'))
);

-- Bridge: Payment N:M Invoice. No UNIQUE (payment_id, invoice_id): a repeated allocation row is a
-- business anomaly the detector must be able to see, not a structural error.
CREATE TABLE payment_allocation (
    allocation_id   TEXT PRIMARY KEY CHECK (allocation_id GLOB 'ALC-2026-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    payment_id      TEXT NOT NULL REFERENCES payment (payment_id),
    invoice_id      TEXT NOT NULL REFERENCES invoice (invoice_id),
    allocated_paise INTEGER NOT NULL CHECK (allocated_paise > 0),
    allocated_date  TEXT NOT NULL
);

CREATE TABLE dispute (
    dispute_id     TEXT PRIMARY KEY CHECK (dispute_id GLOB 'DSP-2026-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    invoice_id     TEXT NOT NULL REFERENCES invoice (invoice_id),
    account_id     TEXT NOT NULL REFERENCES account (account_id),
    reason         TEXT NOT NULL CHECK (reason IN ('PRICING', 'QUANTITY', 'DAMAGED_GOODS', 'LATE_DELIVERY', 'BILLING_ERROR')),
    opened_date    TEXT NOT NULL,
    resolved_date  TEXT,
    disputed_paise INTEGER NOT NULL CHECK (disputed_paise > 0),
    credited_paise INTEGER NOT NULL DEFAULT 0 CHECK (credited_paise >= 0),
    status         TEXT NOT NULL CHECK (status IN ('OPEN', 'UNDER_REVIEW', 'RESOLVED_CREDIT', 'RESOLVED_NO_CREDIT', 'WITHDRAWN'))
);

-- Append-only receivables sub-ledger. amount_paise is always positive; entry_type gives its meaning:
--   balance     = POSTED - VOIDED - APPLIED - CREDIT_MEMO
--   disputed    = DISPUTE_HOLD - DISPUTE_RELEASE
--   collectible = balance - disputed
CREATE TABLE ar_ledger_entry (
    entry_id     TEXT PRIMARY KEY CHECK (entry_id GLOB 'ARL-2026-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    invoice_id   TEXT NOT NULL REFERENCES invoice (invoice_id),
    entry_type   TEXT NOT NULL CHECK (entry_type IN ('INVOICE_POSTED', 'INVOICE_VOIDED', 'PAYMENT_APPLIED',
                                                     'CREDIT_MEMO', 'DISPUTE_HOLD', 'DISPUTE_RELEASE')),
    amount_paise INTEGER NOT NULL CHECK (amount_paise > 0),
    entry_date   TEXT NOT NULL,
    source_id    TEXT NOT NULL
);

-- Polymorphic history: entity_id points at the table named by entity_type, so it cannot be a
-- declared foreign key. Validation check S02 verifies every entity_id resolves.
CREATE TABLE status_event (
    event_id    TEXT PRIMARY KEY CHECK (event_id GLOB 'EVT-2026-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    entity_type TEXT NOT NULL CHECK (entity_type IN ('ACCOUNT', 'QUOTE', 'ORDER', 'SHIPMENT', 'INVOICE', 'PAYMENT', 'DISPUTE')),
    entity_id   TEXT NOT NULL,
    from_status TEXT,
    to_status   TEXT NOT NULL,
    event_time  TEXT NOT NULL,
    actor_role  TEXT NOT NULL CHECK (actor_role IN ('CUSTOMER', 'SALES_OPS', 'SUPPORT_AGENT', 'ANALYST', 'SYSTEM_ADMIN', 'SYSTEM'))
);

-- Detector output. Filled by src/detector.py; never read by the generator.
CREATE TABLE finding (
    finding_id        TEXT PRIMARY KEY,
    rule_id           TEXT NOT NULL,
    issue_type        TEXT NOT NULL,
    severity          TEXT NOT NULL CHECK (severity IN ('HIGH', 'MEDIUM', 'LOW')),
    source_entity     TEXT NOT NULL,
    source_id         TEXT NOT NULL,
    related_ids       TEXT NOT NULL,
    rule_description  TEXT NOT NULL,
    expected_behavior TEXT NOT NULL,
    observed_behavior TEXT NOT NULL,
    impact_type       TEXT NOT NULL,
    impact_paise      INTEGER NOT NULL DEFAULT 0,
    delay_days        INTEGER NOT NULL DEFAULT 0,
    evidence          TEXT NOT NULL
);

CREATE INDEX idx_quote_line_quote ON quote_line (quote_id);
CREATE INDEX idx_order_line_order ON order_line (order_id);
CREATE INDEX idx_shipment_order ON shipment (order_id);
CREATE INDEX idx_shipment_line_shipment ON shipment_line (shipment_id);
CREATE INDEX idx_shipment_line_order_line ON shipment_line (order_line_id);
CREATE INDEX idx_invoice_order ON invoice (order_id);
CREATE INDEX idx_invoice_line_invoice ON invoice_line (invoice_id);
CREATE INDEX idx_invoice_line_order_line ON invoice_line (order_line_id);
CREATE INDEX idx_allocation_payment ON payment_allocation (payment_id);
CREATE INDEX idx_allocation_invoice ON payment_allocation (invoice_id);
CREATE INDEX idx_dispute_invoice ON dispute (invoice_id);
CREATE INDEX idx_ledger_invoice ON ar_ledger_entry (invoice_id);
CREATE INDEX idx_ledger_source ON ar_ledger_entry (source_id);
CREATE INDEX idx_event_entity ON status_event (entity_type, entity_id);
CREATE INDEX idx_finding_issue ON finding (issue_type);
