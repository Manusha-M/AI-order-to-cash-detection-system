"""Command-line entry point. Run `python run.py --help` for the list of steps."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from src import config as cfg
from src.database import build_database, connect, export_all, table_columns, write_ground_truth, write_manifest
from src.detector import run_detection
from src.evaluation import evaluate, load_ground_truth
from src.generator import generate
from src.reconciliation import compute_metrics, reconcile
from src.reproducibility import verify_reproducibility
from src.validation import validate


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def db_path(scale: str) -> Path:
    path = cfg.data_dir(scale) / "o2c.db"
    if not path.exists() and sys.argv[1] != "generate":
        sys.exit(f"{path} not found. Run: python run.py generate --scale {scale}")
    return path


def step_generate(scale: str, seed: int, inject: bool = True) -> None:
    directory = cfg.data_dir(scale)
    directory.mkdir(parents=True, exist_ok=True)
    dataset = generate(cfg.SCALES[scale], seed, inject=inject)
    path = directory / "o2c.db"
    build_database(dataset, path, scale, inject)
    tables = export_all(path, directory)
    write_ground_truth(dataset, directory / "ground_truth.csv")
    manifest = write_manifest(directory, scale, seed, inject, tables)
    print(f"Generated {scale} dataset (seed {seed}, anomalies {'on' if inject else 'off'}) in {directory}")
    for table, info in tables.items():
        print(f"  {table:<20}{info['rows']:>8,}")
    print(f"  ground truth labels {manifest['ground_truth']['rows']:>7,}")
    print(f"  combined SHA-256    {manifest['combined_sha256']}")


def step_validate(scale: str) -> dict:
    conn = connect(db_path(scale))
    report = validate(conn, cfg.SCALES[scale], cfg.data_dir(scale) / "ground_truth.csv")
    conn.close()
    write_json(cfg.output_dir(scale) / "validation.json", report)
    print(f"Structural checks: {report['structural_checks'] - report['structural_failed']} of "
          f"{report['structural_checks']} passed")
    print(f"Business anomaly tie-outs: {report['business_checks'] - report['business_failed']} of "
          f"{report['business_checks']} match the ground truth")
    for result in report["results"]:
        if result["status"] == "FAIL":
            print(f"  FAIL {result['check_id']} {result['description']}: {result['problems']} {result['sample']}")
    return report


def step_detect(scale: str) -> list[dict]:
    conn = connect(db_path(scale))
    findings = run_detection(conn)
    conn.close()
    path = cfg.output_dir(scale) / "findings.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    if findings:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(findings[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(findings)
    counts: dict[str, int] = {}
    for item in findings:
        counts[item["issue_type"]] = counts.get(item["issue_type"], 0) + 1
    print(f"Detector raised {len(findings):,} findings")
    for issue_type in sorted(counts):
        print(f"  {issue_type:<24}{counts[issue_type]:>6,}")
    return findings


def step_reconcile(scale: str) -> dict:
    conn = connect(db_path(scale))
    report = {"metrics": compute_metrics(conn), "identities": reconcile(conn)}
    conn.close()
    write_json(cfg.output_dir(scale) / "reconciliation.json", report)
    for identity in report["identities"]:
        print(f"  {identity['status']} {identity['id']} {identity['description']} "
              f"(difference {identity['difference_paise']} paise)")
    return report


def step_evaluate(scale: str) -> dict:
    conn = connect(db_path(scale))
    report = evaluate(conn, load_ground_truth(cfg.data_dir(scale) / "ground_truth.csv"))
    conn.close()
    write_json(cfg.output_dir(scale) / "evaluation.json", report)
    overall = report["overall"]
    print(f"Overall: TP {overall['tp']:,}  FP {overall['fp']:,}  FN {overall['fn']:,}  "
          f"precision {overall['precision']}  recall {overall['recall']}  F1 {overall['f1']}")
    for source, row in report["by_label_source"].items():
        print(f"  {source:<9} labels {row['labels']:>5}  TP {row['tp']:>5}  FP {row['fp']:>3}  FN {row['fn']:>3}  "
              f"precision {row['precision']}  recall {row['recall']}")
    for issue_type, row in report["by_issue_type"].items():
        print(f"  {issue_type:<24}TP {row['tp']:>5}  FP {row['fp']:>4}  FN {row['fn']:>4}  F1 {row['f1']}")
    impact = report["impact_accuracy"]
    print(f"Impact amounts exact on {impact['exact']:,} of {impact['checked']:,} matched findings that carry money")
    return report


def step_negative_control(scale: str, seed: int) -> dict:
    """Run the detector on a world with nothing planted: every finding is a false positive."""
    import tempfile

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        dataset = generate(cfg.SCALES[scale], seed, inject=False)
        path = Path(temp) / "clean.db"
        build_database(dataset, path, scale, False)
        conn = connect(path)
        findings = run_detection(conn)
        checks = validate(conn, cfg.SCALES[scale], None)
        identities = reconcile(conn)
        conn.close()
    counts: dict[str, int] = {}
    for item in findings:
        counts[item["issue_type"]] = counts.get(item["issue_type"], 0) + 1
    report = {"scale": scale, "seed": seed, "findings_on_clean_data": len(findings), "by_issue_type": counts,
              "structural_failed": checks["structural_failed"], "business_failed": checks["business_failed"],
              "identities_failed": sum(1 for i in identities if i["status"] == "FAIL")}
    clean = not (findings or checks["structural_failed"] or checks["business_failed"] or report["identities_failed"])
    report["status"] = "PASS" if clean else "FAIL"
    write_json(cfg.output_dir(scale) / "negative_control.json", report)
    print(f"Negative control ({report['status']}): {len(findings)} findings on clean data {counts}")
    return report


def step_reproduce(scale: str, seed: int) -> dict:
    report = verify_reproducibility(scale, seed)
    write_json(cfg.output_dir(scale) / "reproducibility.json", report)
    print(f"Reproducibility {report['status']}: combined SHA-256 A {report['combined_sha256_a'][:16]}... "
          f"B {report['combined_sha256_b'][:16]}...; findings {report['findings_a']['rows']:,} vs "
          f"{report['findings_b']['rows']:,}")
    return report


def step_all(scale: str, seed: int) -> None:
    print("== 1. Generate ==")
    step_generate(scale, seed)
    print("\n== 2. Detect (reads the database only, never the labels) ==")
    step_detect(scale)
    print("\n== 3. Validate ==")
    step_validate(scale)
    print("\n== 4. Reconcile ==")
    step_reconcile(scale)
    print("\n== 5. Evaluate against ground truth ==")
    step_evaluate(scale)
    print("\n== 6. Negative control ==")
    step_negative_control(scale, seed)
    print("\n== 7. Reproducibility ==")
    step_reproduce(scale, seed)


def main() -> None:
    parser = argparse.ArgumentParser(description="Order-to-Cash revenue leakage and process delay analysis")
    parser.add_argument("step", choices=("generate", "detect", "validate", "reconcile", "evaluate",
                                         "negative-control", "reproduce", "all"))
    parser.add_argument("--scale", choices=sorted(cfg.SCALES), default="starter")
    parser.add_argument("--seed", type=int, default=cfg.DEFAULT_SEED)
    args = parser.parse_args()
    if args.step == "generate":
        step_generate(args.scale, args.seed)
    elif args.step == "detect":
        step_detect(args.scale)
    elif args.step == "validate":
        step_validate(args.scale)
    elif args.step == "reconcile":
        step_reconcile(args.scale)
    elif args.step == "evaluate":
        step_evaluate(args.scale)
    elif args.step == "negative-control":
        step_negative_control(args.scale, args.seed)
    elif args.step == "reproduce":
        step_reproduce(args.scale, args.seed)
    else:
        step_all(args.scale, args.seed)


if __name__ == "__main__":
    main()
