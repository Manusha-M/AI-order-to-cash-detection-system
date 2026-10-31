"""Write the measured documents from the JSON reports, so no result is typed by hand.

Usage:  python scripts/write_reports.py --tests "145 passed in 90s"
Writes: docs/validation_report.md, docs/reproducibility.md, and the measured block in README.md
"""
from __future__ import annotations

import argparse
import json
import platform
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import config as cfg  # noqa: E402

CORE_TABLES = ("account", "product", "quote", "quote_line", "sales_order", "order_line", "shipment", "shipment_line",
               "invoice", "invoice_line", "invoice_shipment", "payment", "payment_allocation", "dispute",
               "ar_ledger_entry", "status_event")


def load(scale: str, name: str) -> dict | list:
    return json.loads((cfg.output_dir(scale) / f"{name}.json").read_text(encoding="utf-8"))


def manifest(scale: str) -> dict:
    return json.loads((cfg.data_dir(scale) / "manifest.json").read_text(encoding="utf-8"))


def rupees(paise: int) -> str:
    return f"Rs {paise / 100:,.2f}"


def crore(paise: int) -> str:
    return f"Rs {paise / 1_000_000_000:,.2f} Cr"


def row_count_table() -> list[str]:
    starter, full = manifest("starter"), manifest("full")
    lines = ["| Table | Starter | Full |", "|---|---:|---:|"]
    for table in CORE_TABLES:
        lines.append(f"| {table} | {starter['tables'][table]['rows']:,} | {full['tables'][table]['rows']:,} |")
    lines.append(f"| ground truth labels | {starter['ground_truth']['rows']:,} | {full['ground_truth']['rows']:,} |")
    return lines


def evaluation_table(scale: str) -> list[str]:
    report = load(scale, "evaluation")
    lines = ["| Issue type | TP | FP | FN | Precision | Recall | F1 |", "|---|---:|---:|---:|---:|---:|---:|"]
    for issue_type, row in report["by_issue_type"].items():
        lines.append(f"| {issue_type} | {row['tp']:,} | {row['fp']} | {row['fn']} | {row['precision']} | "
                     f"{row['recall']} | {row['f1']} |")
    overall = report["overall"]
    lines.append(f"| **Overall** | **{overall['tp']:,}** | **{overall['fp']}** | **{overall['fn']}** | "
                 f"**{overall['precision']}** | **{overall['recall']}** | **{overall['f1']}** |")
    return lines


def source_table(scale: str) -> list[str]:
    notes = {"injected": "A valid record was deliberately changed. The independent test",
             "plan": "The generator planned the outcome, then labelled it",
             "rule": "The label re-applies the rule. Close to guaranteed; proves little"}
    report = load(scale, "evaluation")
    lines = ["| Label source | Labels | TP | FP | FN | Precision | Recall | What it means |", "|---|---:|---:|---:|---:|---:|---:|---|"]
    for source, row in report["by_label_source"].items():
        lines.append(f"| {source} | {row['labels']:,} | {row['tp']:,} | {row['fp']} | {row['fn']} | {row['precision']} | "
                     f"{row['recall']} | {notes.get(source, '')} |")
    return lines


def identities_table(scale: str) -> list[str]:
    lines = ["| ID | Identity | Left | Right | Difference | Result |", "|---|---|---:|---:|---:|---|"]
    for item in load(scale, "reconciliation")["identities"]:
        lines.append(f"| {item['id']} | {item['description']} | {item['left_paise']:,} | {item['right_paise']:,} | "
                     f"{item['difference_paise']} | {item['status']} |")
    return lines


def metrics_table(scale: str) -> list[str]:
    metrics = load(scale, "reconciliation")["metrics"]
    funnel, cash, receivables, leakage = (metrics[k] for k in ("funnel_paise", "cash_paise", "receivables_paise",
                                                               "leakage_paise"))
    rows = [("Quoted value", funnel["quoted"]), ("Accepted value", funnel["accepted"]), ("Ordered value", funnel["ordered"]),
            ("Fulfilled value", funnel["fulfilled"]), ("Invoiced value", funnel["invoiced"]),
            ("Cash received", cash["cash_received"]), ("Unapplied cash", cash["unapplied_cash"]),
            ("Credits issued", cash["credits_issued"]), ("Outstanding receivables", receivables["outstanding"]),
            ("On dispute hold", receivables["disputed_on_hold"]), ("Overdue, collectible", receivables["overdue_collectible"]),
            ("Underbilled revenue (leakage)", leakage["underbilled_revenue"]),
            ("Overbilled exposure", leakage["overbilled_exposure"]),
            ("Duplicate-billing exposure", leakage["duplicate_billing_exposure"]),
            ("Payment allocation discrepancy", leakage["payment_allocation_discrepancy"])]
    return ["| Measure | Value |", "|---|---:|"] + [f"| {name} | {crore(value)} |" for name, value in rows]


def delay_table(scale: str) -> list[str]:
    delays = load(scale, "reconciliation")["metrics"]["delays"]
    lines = ["| Stage | Records | Mean days | Median | P90 | Max | Over target |", "|---|---:|---:|---:|---:|---:|---:|"]
    for key, label in (("order_to_fulfilment", "Order to full shipment"), ("fulfilment_to_invoice", "Shipment to invoice"),
                       ("invoice_to_final_payment", "Invoice to final payment")):
        row = delays[key]
        lines.append(f"| {label} | {row['count']:,} | {row['mean_days']} | {row['median_days']:g} | {row['p90_days']} | "
                     f"{row['max_days']} | {row.get('over_sla', 'n/a')} |")
    return lines


def validation_lines(scale: str) -> list[str]:
    report = load(scale, "validation")
    groups = {"S01": "Primary keys unique", "S02": "Foreign keys and event references", "S03": "Required values",
              "S04": "Allowed enums", "S05": "ID format and contiguity", "S06": "Relationship consistency",
              "S07": "Date ordering", "S08": "Monetary arithmetic", "S09": "Status agrees with the facts",
              "S10": "Status history", "S11": "Row counts", "S12": "Ground-truth references", "S13": "Data types"}
    lines = ["| Group | Checks | Failed |", "|---|---:|---:|"]
    for prefix, label in groups.items():
        rows = [r for r in report["results"] if r["check_id"].startswith(prefix)]
        lines.append(f"| {prefix} {label} | {len(rows)} | {sum(r['status'] == 'FAIL' for r in rows)} |")
    lines.append(f"| **All structural** | **{report['structural_checks']}** | **{report['structural_failed']}** |")
    lines += ["", "Deliberate rule breaks, counted directly in the data and compared with what was planted:", "",
              "| Anomaly | Found in data | Planted | Result |", "|---|---:|---:|---|"]
    for row in report["results"]:
        if row["category"] == "BUSINESS":
            lines.append(f"| {row['check_id'][2:]} | {row['problems']} | {row['planted']} | {row['status']} |")
    return lines


def volume_split(scale: str) -> list[str]:
    conn = sqlite3.connect(cfg.data_dir(scale) / "o2c.db")
    payments = conn.execute("SELECT status, COUNT(*) FROM payment GROUP BY status ORDER BY status").fetchall()
    events = conn.execute("SELECT entity_type, COUNT(*) FROM status_event GROUP BY entity_type ORDER BY 2 DESC").fetchall()
    conn.close()
    lines = ["\"15,000 payments/events\" is read as 15,000 rows in `payment`, with status events counted on top.", "",
             "| Payment status | Meaning | Rows |", "|---|---|---:|"]
    meaning = {"ALLOCATED": "Applied to invoices", "RECEIVED": "Received, not yet applied", "REVERSED": "Bounced or returned"}
    lines += [f"| {status} | {meaning[status]} | {count:,} |" for status, count in payments]
    lines += ["", "| Status events for | Rows |", "|---|---:|"]
    lines += [f"| {entity} | {count:,} |" for entity, count in events]
    return lines


def sweep_lines(scale: str) -> list[str]:
    path = cfg.output_dir(scale) / "seed_sweep.json"
    if not path.exists():
        return [f"Seed sweep has not been run at {scale} scale."]
    rows = json.loads(path.read_text(encoding="utf-8"))
    lines = ["| Seed | Anomalies | TP | FP | FN | Structural failures | Identity failures |", "|---:|---|---:|---:|---:|---:|---:|"]
    for row in rows:
        lines.append(f"| {row['seed']} | {'yes' if row['anomalies'] else 'no (clean control)'} | {row['tp']:,} | {row['fp']} | "
                     f"{row['fn']} | {row['structural_failed']} | {row['identities_failed']} |")
    return lines


def write_validation_report(tests: str) -> None:
    negative_full = load("full", "negative_control")
    negative_starter = load("starter", "negative_control")
    full_eval = load("full", "evaluation")
    impact = full_eval["impact_accuracy"]
    parts = [
        "# Validation Report", "",
        "Generated by `scripts/write_reports.py` from executed results. Do not edit by hand.", "",
        f"Environment: Python {platform.python_version()} on {platform.system()} {platform.release()}.", "",
        "These results were produced by Claude Code on the development machine. "
        "They do not show that the candidate has run anything.", "",
        "## Automated tests", "", f"`python -m pytest -q`: **{tests}**", "",
        "## Row counts", "", *row_count_table(), "",
        "## Payments and events (full scale)", "", *volume_split("full"), "",
        "## Structural validation (full scale)", "", *validation_lines("full"), "",
        "## Reconciliation (full scale)", "", "All differences are in paise.", "", *identities_table("full"), "",
        "## Detector evaluation (full scale)", "",
        "Matching is exact on issue type and primary record ID. Evaluation is at record level.", "",
        *source_table("full"), "", *evaluation_table("full"), "",
        f"Money impact matched the label exactly on {impact['exact']:,} of {impact['checked']:,} matched findings that "
        "carry money.", "",
        "## Detector evaluation (starter scale)", "", *evaluation_table("starter"), "",
        "## Negative control", "",
        "The same generator with nothing planted. Any finding here is a false positive.", "",
        f"- Full scale: **{negative_full['findings_on_clean_data']} findings**, status {negative_full['status']}.",
        f"- Starter scale: **{negative_starter['findings_on_clean_data']} findings**, status {negative_starter['status']}.", "",
        "## Other seeds", "",
        "The rules were not tuned to one dataset. Each seed is a different world, with and without anomalies.", "",
        "### Full scale", "", *sweep_lines("full"), "", "### Starter scale", "", *sweep_lines("starter"), "",
        "## How much weight to give these numbers", "",
        "The labels, the data and the rules share one author, so a perfect score shows the rules match their own "
        "specification. It is not an estimate of performance on real data. An independent review found 27 issues in a "
        "version that already scored 1.0.", "",
        "The more useful evidence is that the checks can fail. The test suite corrupts data on purpose and confirms "
        "the validators catch it, and it moves money between invoices to prove reconciliation notices. "
        "18 structural checks (S01, S03, S04) repeat rules the schema already enforces, so they can only fail for data "
        "loaded by another route. The bugs found along the way are listed in `decisions.md`.", "",
    ]
    (ROOT / "docs" / "validation_report.md").write_text("\n".join(parts), encoding="utf-8", newline="\n")


def write_reproducibility_report() -> None:
    parts = ["# Reproducibility Report", "",
             "Generated by `scripts/write_reports.py` from `outputs/<scale>/reproducibility.json`. Do not edit by hand.", "",
             "## Method", "",
             "1. Generate dataset A in a fresh Python process with `PYTHONHASHSEED=1`.",
             "2. Generate dataset B in a second fresh process with `PYTHONHASHSEED=2`.",
             "3. Export each table as CSV, sorted by primary key, with fixed line endings.",
             "4. Compare row counts and SHA-256 per table, the ground truth, and the detector's findings.", "",
             "SQLite file bytes are not compared, because they can differ with identical contents.", "",
             "Run it yourself: `python run.py reproduce --scale full`", ""]
    for scale in ("full", "starter"):
        report = load(scale, "reproducibility")
        parts += [f"## {scale.title()} scale: {report['status']}", "",
                  f"Seed {report['seed']}.", "",
                  f"- Combined SHA-256, run A: `{report['combined_sha256_a']}`",
                  f"- Combined SHA-256, run B: `{report['combined_sha256_b']}`",
                  f"- Ground truth SHA-256, run A: `{report['ground_truth_sha256_a']}`",
                  f"- Ground truth SHA-256, run B: `{report['ground_truth_sha256_b']}`",
                  f"- Findings: {report['findings_a']['rows']:,} and {report['findings_b']['rows']:,}, "
                  f"SHA-256 `{report['findings_a']['sha256'][:32]}...` and `{report['findings_b']['sha256'][:32]}...`", "",
                  "| Table | Rows A | Rows B | SHA-256 A (first 16) | SHA-256 B (first 16) | Match |",
                  "|---|---:|---:|---|---|---|"]
        for row in report["tables"]:
            parts.append(f"| {row['table']} | {row['rows_a']:,} | {row['rows_b']:,} | `{row['sha256_a'][:16]}` | "
                         f"`{row['sha256_b'][:16]}` | {'yes' if row['match'] else 'NO'} |")
        parts.append("")
    parts += ["## Limit", "",
              f"These checksums were measured on Python {platform.python_version()}. Python keeps `random.random()` stable "
              "between versions but does not promise it for every helper function, so another version could produce "
              "different, equally valid data. `run.py reproduce` proves determinism on whichever version you use.", ""]
    (ROOT / "docs" / "reproducibility.md").write_text("\n".join(parts), encoding="utf-8", newline="\n")


def update_readme(tests: str) -> None:
    path = ROOT / "README.md"
    text = path.read_text(encoding="utf-8")
    start, end = "<!-- MEASURED:START -->", "<!-- MEASURED:END -->"
    negative = load("full", "negative_control")
    validation = load("full", "validation")
    repro = load("full", "reproducibility")
    identities = load("full", "reconciliation")["identities"]
    block = [start, "", f"Measured on Python {platform.python_version()}, seed {cfg.DEFAULT_SEED}, cutoff {cfg.CUTOFF}.", "",
             "**Row counts**", "", *row_count_table(), "",
             f"**Checks:** {validation['structural_checks'] - validation['structural_failed']} of "
             f"{validation['structural_checks']} structural checks passed; "
             f"{sum(i['status'] == 'PASS' for i in identities)} of {len(identities)} reconciliation identities closed to "
             f"0 paise; {negative['findings_on_clean_data']} findings on clean data; reproducibility {repro['status']}; "
             f"tests: {tests}.", "",
             "**Business picture (full dataset)**", "", *metrics_table("full"), "",
             "**Process delays (full dataset)**", "", *delay_table("full"), "",
             "**Detector evaluation (full dataset)**", "", *source_table("full"), "", *evaluation_table("full"), "", end]
    before = text[: text.index(start)]
    after = text[text.index(end) + len(end):]
    path.write_text(before + "\n".join(block) + after, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tests", required=True, help="pytest summary line from a run you actually did")
    args = parser.parse_args()
    write_validation_report(args.tests)
    write_reproducibility_report()
    update_readme(args.tests)
    print("Wrote docs/validation_report.md, docs/reproducibility.md and the README measured block")


if __name__ == "__main__":
    main()
