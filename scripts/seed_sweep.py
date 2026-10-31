"""Run the pipeline on other seeds to check the rules are not tuned to one dataset.

Usage:  python scripts/seed_sweep.py --scale full --seeds 1 2 3 4 5
Writes: outputs/<scale>/seed_sweep.json
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config as cfg  # noqa: E402
from src.database import build_database, connect, write_ground_truth  # noqa: E402
from src.detector import run_detection  # noqa: E402
from src.evaluation import evaluate, load_ground_truth  # noqa: E402
from src.generator import generate  # noqa: E402
from src.reconciliation import reconcile  # noqa: E402
from src.validation import validate  # noqa: E402


def run_seed(scale: cfg.Scale, seed: int, inject: bool, directory: Path) -> dict:
    dataset = generate(scale, seed, inject=inject)
    db_file = directory / f"seed_{seed}_{inject}.db"
    truth_file = directory / f"truth_{seed}_{inject}.csv"
    build_database(dataset, db_file, scale.name, inject)
    write_ground_truth(dataset, truth_file)
    conn = connect(db_file)
    run_detection(conn)
    checks = validate(conn, scale, truth_file)
    identities = reconcile(conn)
    report = evaluate(conn, load_ground_truth(truth_file))
    conn.close()
    return {"seed": seed, "anomalies": inject, **report["overall"],
            "impact_exact": f"{report['impact_accuracy']['exact']}/{report['impact_accuracy']['checked']}",
            "structural_failed": checks["structural_failed"], "business_failed": checks["business_failed"],
            "identities_failed": sum(1 for i in identities if i["status"] == "FAIL"),
            "false_positives": report["false_positive_sample"], "false_negatives": report["false_negative_sample"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", choices=sorted(cfg.SCALES), default="starter")
    parser.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3, 4, 5])
    args = parser.parse_args()
    scale = cfg.SCALES[args.scale]
    rows = []
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        for seed in args.seeds:
            for inject in (True, False):
                row = run_seed(scale, seed, inject, Path(temp))
                rows.append(row)
                print(f"seed {seed:>9} anomalies {str(inject):<5} TP {row['tp']:>5} FP {row['fp']:>3} FN {row['fn']:>3} "
                      f"impact {row['impact_exact']:<11} structural_failed {row['structural_failed']} "
                      f"business_failed {row['business_failed']} identities_failed {row['identities_failed']}")
                for item in row["false_positives"] + row["false_negatives"]:
                    print("    ", item)
    out = cfg.output_dir(args.scale) / "seed_sweep.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
