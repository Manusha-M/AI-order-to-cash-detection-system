"""Score detector findings against the separate ground truth.

Matching is exact on (issue_type, primary record ID), so one anomaly can match one finding
only. The primary record is the natural grain of each rule: order line for billing, invoice
for duplicates and aging, payment for allocation, order for closure and fulfilment delay,
status event for lifecycle breaks, dispute for receivables treatment.

Labels differ in how much they prove, so scores are also split by label_source:

* injected: a valid record was deliberately changed. This is the independent test.
* plan: the generator planned the outcome (a customer who stops paying), then labelled it.
* rule: the label re-applies the documented rule to the data. A perfect score here is
  close to guaranteed and only shows that two implementations of one rule agree.
"""
from __future__ import annotations

import csv
import sqlite3
from collections import defaultdict
from pathlib import Path


def load_ground_truth(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _scores(tp: int, fp: int, fn: int) -> dict:
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * precision * recall / (precision + recall) if precision and recall else 0.0 if tp + fp + fn else None
    rounded = {k: None if v is None else round(v, 4) for k, v in (("precision", precision), ("recall", recall), ("f1", f1))}
    return {"tp": tp, "fp": fp, "fn": fn, **rounded}


def evaluate(conn: sqlite3.Connection, ground_truth: list[dict]) -> dict:
    expected = {(g["issue_type"], g["primary_id"]): g for g in ground_truth}
    if len(expected) != len(ground_truth):
        raise ValueError("ground truth holds two labels for the same (issue_type, primary_id)")
    rows = [dict(r) for r in conn.execute("SELECT * FROM finding")]
    detected = {(r["issue_type"], r["source_id"]): r for r in rows}
    if len(detected) != len(rows):
        raise ValueError("two findings share one (issue_type, source_id), so one anomaly would count twice")

    matched = expected.keys() & detected.keys()
    false_positives = sorted(detected.keys() - expected.keys())
    false_negatives = sorted(expected.keys() - detected.keys())

    impact_checked = impact_equal = 0
    impact_misses = []
    for key in sorted(matched):
        wanted = int(expected[key]["expected_impact_paise"])
        got = detected[key]["impact_paise"]
        if wanted == 0 and got == 0:
            continue  # nothing to compare: 0 equals 0 proves nothing
        impact_checked += 1
        if wanted == got:
            impact_equal += 1
        else:
            impact_misses.append({"key": list(key), "expected": wanted, "detected": got})

    counts = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    for issue_type, _ in matched:
        counts[issue_type]["tp"] += 1
    for issue_type, _ in false_positives:
        counts[issue_type]["fp"] += 1
    for issue_type, _ in false_negatives:
        counts[issue_type]["fn"] += 1

    by_type = {issue_type: _scores(**counts[issue_type]) for issue_type in sorted(counts)}

    source_of = {g["issue_type"]: g.get("label_source", "unknown") for g in ground_truth}
    by_source = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "labels": 0})
    for issue_type, row in counts.items():
        bucket = by_source[source_of.get(issue_type, "unlabelled")]
        for key in ("tp", "fp", "fn"):
            bucket[key] += row[key]
        bucket["labels"] += row["tp"] + row["fn"]
    source_scores = {source: {**_scores(row["tp"], row["fp"], row["fn"]), "labels": row["labels"]}
                     for source, row in sorted(by_source.items())}
    tp, fp, fn = len(matched), len(false_positives), len(false_negatives)
    macro_f1 = [v["f1"] for v in by_type.values() if v["f1"] is not None]
    return {
        "matching_rule": "Exact match on (issue_type, primary record ID); one finding per anomaly.",
        "ground_truth_labels": len(expected),
        "findings": len(detected),
        "overall": _scores(tp, fp, fn),
        "macro_f1": round(sum(macro_f1) / len(macro_f1), 4) if macro_f1 else None,
        "by_label_source": source_scores,
        "by_issue_type": by_type,
        "impact_accuracy": {"checked": impact_checked, "exact": impact_equal, "misses": impact_misses[:20]},
        "false_positive_sample": [list(k) for k in false_positives[:25]],
        "false_negative_sample": [list(k) for k in false_negatives[:25]],
    }
