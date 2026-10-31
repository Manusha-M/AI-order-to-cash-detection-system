"""Headless dashboard test: the page runs, and its numbers match the database."""
from __future__ import annotations

import json

import pytest

from src import config as cfg
from src.database import connect

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(cfg.ROOT / "app" / "dashboard.py")


@pytest.fixture(scope="module")
def page():
    if not (cfg.data_dir("starter") / "o2c.db").exists() or not (cfg.output_dir("starter") / "reconciliation.json").exists():
        pytest.skip("Run `python run.py all --scale starter` first.")
    app = AppTest.from_file(APP, default_timeout=60)
    app.run()
    if len(app.selectbox[0].options) > 1:
        app.selectbox[0].set_value("starter").run()
    return app


def metric(app, label: str) -> str:
    return next(m.value for m in app.metric if m.label == label)


def test_page_renders_without_errors(page):
    assert not page.exception
    assert [t.label for t in page.tabs] == ["Overview", "Revenue leakage", "Process delays", "Exceptions", "Data quality"]


def test_counts_match_the_database(page):
    conn = connect(cfg.data_dir("starter") / "o2c.db")
    for label, table in (("Quotes", "quote"), ("Orders", "sales_order"), ("Invoices", "invoice"), ("Exceptions", "finding")):
        assert metric(page, label) == f"{conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]:,}"
    conn.close()


def test_overview_shows_potential_leakage(page):
    assert metric(page, "Underbilled revenue").startswith("₹")


def test_quality_tab_shows_measured_results(page):
    evaluation = json.loads((cfg.output_dir("starter") / "evaluation.json").read_text(encoding="utf-8"))
    planted = evaluation["by_label_source"]["injected"]
    assert metric(page, "Precision, injected anomalies") == f"{planted['precision']:.3f}"
    assert metric(page, "Recall, injected anomalies") == f"{planted['recall']:.3f}"


def test_exception_filter_narrows_the_list(page):
    page.multiselect[0].set_value(["OVERBILLING"]).run()
    assert not page.exception
    assert any("6 of" in c.value for c in page.caption)
    page.multiselect[0].set_value([]).run()
