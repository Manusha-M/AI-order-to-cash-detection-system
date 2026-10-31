"""Build the clean handover archive and refuse to finish if anything unsafe is inside.

Usage:  python scripts/make_handover_zip.py
Writes: yottaflex-o2c-handover.zip beside the project folder.
"""
from __future__ import annotations

import os
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT.parent / "yottaflex-o2c-handover.zip"

EXCLUDED_DIRECTORIES = {".venv", "__pycache__", ".pytest_cache", ".claude", ".git"}
EXCLUDED_SUFFIXES = {".db", ".pyc", ".key", ".pem", ".tmp", ".log"}
EXCLUDED_NAMES = {".env"}
EXCLUDED_PREFIXES = (("data", "full"),)

TEXT_SUFFIXES = {".py", ".md", ".txt", ".toml", ".ini", ".sql", ".json", ".csv", ".gitignore", ""}
# Scanned in everything except the prompt history, which must stay verbatim.
UNSAFE = [re.compile(p, re.IGNORECASE) for p in (
    r"C:\\Users\\",
    r"\bghp_[A-Za-z0-9]{20,}",
    r"\bgithub_pat_",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"\bsk-[A-Za-z0-9]{20,}",
)]
SCAN_EXEMPT = {"docs/prompt_history.md"}


def included(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if EXCLUDED_DIRECTORIES & set(relative.parts):
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES or path.name in EXCLUDED_NAMES:
        return False
    return not any(relative.parts[: len(prefix)] == prefix for prefix in EXCLUDED_PREFIXES)


def unsafe_lines(path: Path) -> list[str]:
    relative = path.relative_to(ROOT).as_posix()
    if relative in SCAN_EXEMPT or path.suffix.lower() not in TEXT_SUFFIXES or path.stat().st_size > 5_000_000:
        return []
    text = path.read_text(encoding="utf-8", errors="ignore")
    return [f"{relative}: {pattern.pattern}" for pattern in UNSAFE if pattern.search(text)]


def main() -> None:
    files = []
    for folder, subfolders, names in os.walk(ROOT):
        subfolders[:] = [s for s in subfolders if s not in EXCLUDED_DIRECTORIES]  # never walk into .venv
        files.extend(Path(folder) / name for name in names)
    files = sorted(p for p in files if included(p))
    problems = [issue for path in files for issue in unsafe_lines(path)]
    if problems:
        print("Refusing to build the archive. Fix these first:")
        print("\n".join(f"  {p}" for p in problems))
        sys.exit(1)

    with zipfile.ZipFile(TARGET, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            archive.write(path, Path(ROOT.name) / path.relative_to(ROOT))

    with zipfile.ZipFile(TARGET) as archive:
        names = archive.namelist()
        required = ["README.md", "HANDOFF.md", "run.py", "requirements.txt", "src/detector.py", "sql/schema.sql",
                    "docs/prompt_history.md", "docs/ai_usage.md", "data/starter/ground_truth.csv"]
        missing = [r for r in required if f"{ROOT.name}/{r}" not in names]
        leaked = [n for n in names if ".venv" in n or n.endswith(".db") or "/data/full/" in n]
    if missing or leaked:
        sys.exit(f"Archive check failed. Missing: {missing}. Should not be there: {leaked}.")
    print(f"Wrote {TARGET.name}: {len(names)} files, {TARGET.stat().st_size / 1_048_576:.1f} MB")


if __name__ == "__main__":
    main()
