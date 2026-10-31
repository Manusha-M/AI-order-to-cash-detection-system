"""Prove determinism by generating the dataset twice in separate processes.

Each run is a fresh Python process with a different PYTHONHASHSEED, so accidental reliance
on dict/set hash ordering would show up. Comparison uses logical exports (sorted CSV plus
findings), never the SQLite file bytes, which legitimately differ between builds.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from . import config as cfg
from .database import connect, export_all, table_columns


def build_once(scale_name: str, seed: int, directory: Path) -> dict:
    """Used by the child process: generate, detect, then return a logical fingerprint."""
    from .database import build_database, write_ground_truth, write_manifest
    from .detector import run_detection
    from .generator import generate

    dataset = generate(cfg.SCALES[scale_name], seed)
    db_path = directory / "o2c.db"
    build_database(dataset, db_path, scale_name, True)
    tables = export_all(db_path, directory)
    write_ground_truth(dataset, directory / "ground_truth.csv")
    manifest = write_manifest(directory, scale_name, seed, True, tables)
    conn = connect(db_path)
    run_detection(conn)
    rows = conn.execute("SELECT * FROM finding ORDER BY finding_id").fetchall()
    columns = table_columns(conn, "finding")
    conn.close()
    payload = "\n".join(json.dumps(dict(zip(columns, tuple(r))), sort_keys=True) for r in rows)
    return {"tables": tables, "combined_sha256": manifest["combined_sha256"],
            "ground_truth_sha256": manifest["ground_truth"]["sha256"],
            "findings": {"rows": len(rows), "sha256": hashlib.sha256(payload.encode()).hexdigest()}}


def _child_run(scale_name: str, seed: int, directory: Path, hash_seed: str) -> dict:
    env = dict(os.environ, PYTHONHASHSEED=hash_seed)
    code = ("import json, sys; from pathlib import Path; from src.reproducibility import build_once; "
            "print(json.dumps(build_once(sys.argv[1], int(sys.argv[2]), Path(sys.argv[3]))))")
    done = subprocess.run([sys.executable, "-c", code, scale_name, str(seed), str(directory)],
                          cwd=cfg.ROOT, env=env, capture_output=True, text=True, check=True)
    return json.loads(done.stdout.strip().splitlines()[-1])


def verify_reproducibility(scale_name: str, seed: int = cfg.DEFAULT_SEED) -> dict:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        run_a = Path(temp) / "run_a"
        run_b = Path(temp) / "run_b"
        run_a.mkdir()
        run_b.mkdir()
        a = _child_run(scale_name, seed, run_a, "1")
        b = _child_run(scale_name, seed, run_b, "2")

    comparison = []
    for table in a["tables"]:
        left, right = a["tables"][table], b["tables"][table]
        comparison.append({"table": table, "rows_a": left["rows"], "rows_b": right["rows"],
                           "sha256_a": left["sha256"], "sha256_b": right["sha256"],
                           "match": left == right})
    same = (all(c["match"] for c in comparison) and a["ground_truth_sha256"] == b["ground_truth_sha256"]
            and a["findings"] == b["findings"])
    return {"scale": scale_name, "seed": seed, "status": "PASS" if same else "FAIL",
            "method": "Two independent processes with PYTHONHASHSEED 1 and 2; SHA-256 of sorted logical CSV exports.",
            "combined_sha256_a": a["combined_sha256"], "combined_sha256_b": b["combined_sha256"],
            "ground_truth_sha256_a": a["ground_truth_sha256"], "ground_truth_sha256_b": b["ground_truth_sha256"],
            "findings_a": a["findings"], "findings_b": b["findings"], "tables": comparison}
