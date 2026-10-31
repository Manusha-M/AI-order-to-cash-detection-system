"""SQLite build and deterministic exports (CSV, JSON, SQL seed) with checksums."""
from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from datetime import date
from pathlib import Path

from . import config as cfg
from .generator import TABLE_ORDER, Dataset

PRIMARY_KEYS = {
    "product": "product_id", "account": "account_id", "quote": "quote_id", "quote_line": "quote_line_id",
    "sales_order": "order_id", "order_line": "order_line_id", "shipment": "shipment_id",
    "shipment_line": "shipment_line_id", "invoice": "invoice_id", "invoice_line": "invoice_line_id",
    "invoice_shipment": "invoice_id, shipment_id", "payment": "payment_id", "payment_allocation": "allocation_id",
    "dispute": "dispute_id", "ar_ledger_entry": "entry_id", "status_event": "event_id",
}

GROUND_TRUTH_FIELDS = ("gt_id", "issue_type", "expected_label", "scenario", "rule_id", "source_entity", "primary_id",
                       "related_ids", "expected_behavior", "observed_behavior", "causal_explanation", "impact_type",
                       "expected_impact_paise", "label_source")


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [row["name"] for row in conn.execute(f"PRAGMA table_info({table})")]


def build_database(dataset: Dataset, path: Path, scale_name: str, inject: bool) -> None:
    path.unlink(missing_ok=True)
    conn = connect(path)
    conn.executescript(cfg.SCHEMA_SQL.read_text(encoding="utf-8"))
    conn.executescript(cfg.ANALYTICS_SQL.read_text(encoding="utf-8"))
    metadata = {"cutoff_date": dataset.cutoff.isoformat(), "seed": str(dataset.seed), "scale": scale_name,
                "generator_version": cfg.GENERATOR_VERSION, "anomalies_injected": str(inject).lower()}
    conn.executemany("INSERT INTO run_metadata VALUES (?, ?)", sorted(metadata.items()))
    # Foreign keys are checked at COMMIT, so self-references inside a table load in any order.
    conn.execute("PRAGMA defer_foreign_keys = ON")
    for table in TABLE_ORDER:
        columns = table_columns(conn, table)
        placeholders = ", ".join("?" for _ in columns)
        rows = ([row[c] for c in columns] for row in dataset.tables[table])
        conn.executemany(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})", rows)
    conn.commit()
    conn.close()


def _sorted_rows(conn: sqlite3.Connection, table: str) -> tuple[list[str], list[tuple]]:
    columns = table_columns(conn, table)
    rows = [tuple(r) for r in conn.execute(f"SELECT * FROM {table} ORDER BY {PRIMARY_KEYS[table]}")]
    return columns, rows


def _write_csv(path: Path, columns: list[str], rows: list) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(columns)
        writer.writerows(rows)


def _sql_literal(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, int):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def export_all(db_path: Path, directory: Path) -> dict:
    """Write every table as CSV and JSON plus one SQL seed file. Returns per-table counts and checksums."""
    csv_dir = directory / "csv"
    json_dir = directory / "json"
    csv_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    tables = {}
    with (directory / "seed.sql").open("w", newline="", encoding="utf-8") as seed:
        seed.write("-- Load after sql/schema.sql. Generated file: do not edit.\n")
        seed.write("PRAGMA defer_foreign_keys = ON;\nBEGIN;\n")
        for table in TABLE_ORDER:
            columns, rows = _sorted_rows(conn, table)
            csv_path = csv_dir / f"{table}.csv"
            _write_csv(csv_path, columns, rows)
            with (json_dir / f"{table}.json").open("w", newline="", encoding="utf-8") as handle:
                json.dump([dict(zip(columns, r)) for r in rows], handle, separators=(",", ":"))
            for row in rows:
                values = ", ".join(_sql_literal(v) for v in row)
                seed.write(f"INSERT INTO {table} VALUES ({values});\n")
            tables[table] = {"rows": len(rows), "sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest()}
        seed.write("COMMIT;\n")
    conn.close()
    return tables


def write_ground_truth(dataset: Dataset, path: Path) -> None:
    labels = sorted(dataset.ground_truth, key=lambda g: (g["rule_id"], g["primary_id"]))
    rows = [[f"GT-2026-{i:06d}"] + [label[field] for field in GROUND_TRUTH_FIELDS[1:]]
            for i, label in enumerate(labels, start=1)]
    _write_csv(path, list(GROUND_TRUTH_FIELDS), rows)


def write_manifest(directory: Path, scale_name: str, seed: int, inject: bool, tables: dict) -> dict:
    combined = hashlib.sha256("".join(tables[t]["sha256"] for t in sorted(tables)).encode()).hexdigest()
    ground_truth = directory / "ground_truth.csv"
    manifest = {
        "generator_command": f"python run.py generate --scale {scale_name} --seed {seed}",
        "generator_version": cfg.GENERATOR_VERSION,
        "seed": seed,
        "scale": scale_name,
        "anomalies_injected": inject,
        "cutoff_date": cfg.CUTOFF.isoformat(),
        "currency": "INR, integer paise",
        "data_provenance": "Fully synthetic. No external, personal or confidential data was used; "
                           "account and product names are invented by src/generator.py.",
        "tables": tables,
        "combined_sha256": combined,
        "ground_truth": {
            "file": "ground_truth.csv",
            "rows": sum(1 for _ in ground_truth.open(encoding="utf-8")) - 1,
            "sha256": hashlib.sha256(ground_truth.read_bytes()).hexdigest(),
        },
    }
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def cutoff_of(conn: sqlite3.Connection) -> date:
    row = conn.execute("SELECT value FROM run_metadata WHERE key = 'cutoff_date'").fetchone()
    return date.fromisoformat(row["value"])
