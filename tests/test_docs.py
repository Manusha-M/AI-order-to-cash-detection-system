"""Documentation checks: docs that drift from the code are worse than none."""
from __future__ import annotations

import re

from src import config as cfg
from src.database import connect
from src.detector import RULES
from src.lifecycle import TRANSITIONS

DOCS = cfg.ROOT / "docs"


def section(text: str, table: str) -> str:
    match = re.search(rf"^## {table}\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    assert match, f"no section for {table}"
    return match.group(1)


def test_every_column_is_in_the_data_dictionary(starter_conn):
    dictionary = (DOCS / "data_dictionary.md").read_text(encoding="utf-8")
    tables = [r[0] for r in starter_conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")]
    for table in tables:
        body = section(dictionary, table)
        for row in starter_conn.execute(f"PRAGMA table_info({table})"):
            assert f"| {row['name']} |" in body, f"{table}.{row['name']} is not documented"


def test_every_enum_value_is_in_the_data_dictionary():
    dictionary = (DOCS / "data_dictionary.md").read_text(encoding="utf-8")
    for (table, column), allowed in cfg.ENUMS.items():
        body = section(dictionary, table)
        for value in allowed:
            assert value in body, f"{table}.{column} value {value} is not documented"


def test_every_rule_is_in_business_rules():
    rules = (DOCS / "business_rules.md").read_text(encoding="utf-8")
    for rule_id, (issue_type, _) in RULES.items():
        assert f"| {rule_id} | {issue_type} |" in rules


def test_every_lifecycle_state_is_in_business_rules():
    rules = (DOCS / "business_rules.md").read_text(encoding="utf-8")
    states = {s for machine in TRANSITIONS.values() for targets in machine.values() for s in targets}
    for state in states:
        assert state in rules, state


def test_thresholds_in_the_docs_match_the_code():
    rules = (DOCS / "business_rules.md").read_text(encoding="utf-8")
    assert f"| Order-to-fulfilment target | {cfg.SLA_ORDER_TO_FULFILMENT_DAYS} days |" in rules
    assert f"| Shipment-to-invoice target | {cfg.SLA_SHIPMENT_TO_INVOICE_DAYS} days |" in rules
    assert f"| Unbilled grace period | {cfg.UNBILLED_GRACE_DAYS} days |" in rules
    assert f"| Long overdue | More than {cfg.LONG_OVERDUE_DAYS} days past due |" in rules
    assert f"| Analysis cutoff | {cfg.CUTOFF.isoformat()} |" in rules


def test_required_documents_exist():
    for name in ("README.md", "HANDOFF.md", "docs/data_dictionary.md", "docs/architecture.md", "docs/business_rules.md",
                 "docs/decisions.md", "docs/validation_report.md", "docs/reproducibility.md", "docs/development_log.md",
                 "docs/ai_usage.md", "docs/prompt_history.md", "docs/requirements_matrix.md", "docs/final_audit.md"):
        assert (cfg.ROOT / name).exists(), name


def test_disclosure_keeps_the_individual_work_flag():
    disclosure = (DOCS / "ai_usage.md").read_text(encoding="utf-8")
    handoff = (cfg.ROOT / "HANDOFF.md").read_text(encoding="utf-8")
    assert "FAQ item 7" in disclosure
    assert "operated by the candidate" in disclosure
    assert "Prompt 1 describes a different arrangement" in disclosure
    assert "Not recorded at the time this was written" in disclosure
    assert "item 7" in handoff


def test_no_unfilled_placeholders_remain():
    for name in ("ai_usage.md", "prompt_history.md", "final_audit.md"):
        assert "CANDIDATE TO COMPLETE" not in (DOCS / name).read_text(encoding="utf-8").split("### Prompt 1:")[0], name


def test_prompt_history_keeps_every_prompt_unedited():
    history = (DOCS / "prompt_history.md").read_text(encoding="utf-8")
    assert "ABSOLUTE RESTRICTION" in history  # Prompt 1, as submitted
    assert "friend" in history
    assert history.index("### Prompt 1:") < history.index("### Prompt 4:") < history.index("### Prompt 5:")


def test_no_machine_specific_paths_in_code():
    for path in list((cfg.ROOT / "src").glob("*.py")) + [cfg.ROOT / "run.py", cfg.ROOT / "app" / "dashboard.py"]:
        text = path.read_text(encoding="utf-8")
        assert "C:\\Users" not in text and "/Users/" not in text, path


def test_clean_control_report_matches_a_real_run(clean_paths):
    conn = connect(clean_paths)
    assert conn.execute("SELECT value FROM run_metadata WHERE key = 'anomalies_injected'").fetchone()[0] == "false"
    conn.close()
