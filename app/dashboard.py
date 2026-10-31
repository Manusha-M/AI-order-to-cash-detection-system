"""Streamlit dashboard. Run with: python -m streamlit run app/dashboard.py

Every number on screen is read from the SQLite database or from the JSON reports that
run.py writes. Nothing is typed in here, so a stale or missing report shows up as a
warning rather than as a believable figure.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config as cfg  # noqa: E402

BLUE = "#2a78d6"
ORANGE = "#eb6834"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
INK = "#52514e"
PAISE_PER_CRORE = 1_000_000_000

ISSUE_MEANING = {
    "UNDERBILLING": "Revenue earned but not billed. This is true leakage.",
    "OVERBILLING": "Customer billed beyond fulfilment. Refund or credit risk, not income.",
    "DUPLICATE_INVOICE": "Same goods billed twice. Inflates receivables.",
    "DUPLICATE_ALLOCATION": "Cash applied more than once. Receivables look lower than they are.",
    "CLOSED_ORDER_UNPAID": "Order closed while money is owed. Collection may stop.",
    "DISPUTE_NOT_IN_AR": "Disputed amount still shown as collectible.",
    "SHORT_PAYMENT": "Customer stopped paying with a balance open. Collection risk.",
    "LONG_OVERDUE": "More than 90 days past due. Collection risk.",
    "ILLEGAL_TRANSITION": "History skipped a required step. Process control failure.",
    "FULFILMENT_DELAY": "Order shipped later than the 21-day target.",
    "INVOICING_DELAY": "Invoice raised later than the 7-day target. Cash arrives later.",
}

st.set_page_config(page_title="Order-to-Cash Analysis", layout="wide", initial_sidebar_state="collapsed")
# Long rupee figures must wrap to the tile's width rather than be cut off with an ellipsis.
st.markdown("<style>[data-testid='stMetricValue'] {font-size: 1.5rem;} "
            "[data-testid='stMetricValue'] > div, [data-testid='stMetricLabel'] > div "
            "{white-space: normal; overflow: visible; text-overflow: clip;}</style>", unsafe_allow_html=True)


def inr(paise: int | float) -> str:
    """Format money the Indian way: crore, lakh, then plain rupees."""
    rupees = paise / 100
    if abs(rupees) >= 10_000_000:
        return f"₹{rupees / 10_000_000:,.2f} Cr"
    if abs(rupees) >= 100_000:
        return f"₹{rupees / 100_000:,.2f} L"
    return f"₹{rupees:,.0f}"


def available_scales() -> list[str]:
    return [name for name in ("full", "starter") if (cfg.data_dir(name) / "o2c.db").exists()]


@st.cache_data(show_spinner=False)
def query(db_file: str, stamp: float, sql: str, params: tuple = ()) -> pd.DataFrame:
    with sqlite3.connect(f"file:{db_file}?mode=ro", uri=True) as conn:
        return pd.read_sql_query(sql, conn, params=params)


def load_report(scale: str, name: str) -> dict | None:
    path = cfg.output_dir(scale) / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def styled(chart: alt.Chart) -> alt.Chart:
    return (chart.configure_view(stroke=None)
            .configure_axis(gridColor=GRID, domainColor=AXIS, tickColor=AXIS, labelColor=INK, titleColor=INK))


def bars(frame: pd.DataFrame, category: str, value: str, title: str, fmt: str,
         sort: list[str] | None = None) -> alt.Chart:
    chart = alt.Chart(frame).mark_bar(cornerRadiusEnd=4, size=20, color=BLUE).encode(
        y=alt.Y(f"{category}:N", sort=sort or "-x", title=None, axis=alt.Axis(labelLimit=240, ticks=False)),
        x=alt.X(f"{value}:Q", title=title, axis=alt.Axis(format=fmt)),
        tooltip=[alt.Tooltip(f"{category}:N", title=" "), alt.Tooltip(f"{value}:Q", title=title, format=",.2f")],
    )
    return styled(chart.properties(height=max(150, 34 * len(frame))))


def delay_histogram(frame: pd.DataFrame, sla: int, title: str) -> alt.Chart:
    frame = frame.assign(band=frame["days"].map(lambda d: "Over target" if d > sla else "Within target"))
    bars_layer = alt.Chart(frame).mark_bar(cornerRadiusEnd=2, size=7).encode(
        x=alt.X("days:Q", title=title, axis=alt.Axis(tickMinStep=5)),
        y=alt.Y("records:Q", title="Records (square-root scale)", scale=alt.Scale(type="sqrt")),
        color=alt.Color("band:N", title=None,
                        scale=alt.Scale(domain=["Within target", "Over target"], range=[BLUE, ORANGE]),
                        legend=alt.Legend(orient="top")),
        tooltip=[alt.Tooltip("days:Q", title="Days"), alt.Tooltip("records:Q", title="Records", format=",")],
    )
    return styled(bars_layer.properties(height=260))


def payment_histogram(frame: pd.DataFrame) -> alt.Chart:
    chart = alt.Chart(frame).mark_bar(cornerRadiusEnd=2, size=4, color=BLUE).encode(
        x=alt.X("days:Q", title="Days from invoice to final payment", axis=alt.Axis(tickMinStep=10)),
        y=alt.Y("records:Q", title="Paid invoices"),
        tooltip=[alt.Tooltip("days:Q", title="Days"), alt.Tooltip("records:Q", title="Paid invoices", format=",")],
    )
    return styled(chart.properties(height=240))


def tile_row(tiles: list[tuple[str, str]]) -> None:
    for column, (label, value) in zip(st.columns(len(tiles)), tiles):
        column.metric(label, value)


def table_view(frame: pd.DataFrame, label: str = "Table view") -> None:
    with st.expander(label):
        st.dataframe(frame, hide_index=True, width="stretch")


def overview_tab(scale: str, ask, recon: dict | None, counts: dict) -> None:
    st.subheader("Executive overview")
    if recon is None:
        st.warning(f"Run `python run.py reconcile --scale {scale}` to fill this tab.")
        return
    metrics = recon["metrics"]
    funnel = metrics["funnel_paise"]
    receivables = metrics["receivables_paise"]
    tile_row([("Quotes", f"{counts['quote']:,}"), ("Orders", f"{counts['sales_order']:,}"),
              ("Invoices", f"{counts['invoice']:,}"), ("Payments", f"{counts['payment']:,}"),
              ("Exceptions", f"{counts['finding']:,}")])
    tile_row([("Invoiced", inr(funnel["invoiced"])), ("Cash received", inr(funnel["cash_received"])),
              ("Outstanding receivables", inr(receivables["outstanding"])),
              ("Overdue, collectible", inr(receivables["overdue_collectible"])),
              ("On dispute hold", inr(receivables["disputed_on_hold"])),
              ("Underbilled revenue", inr(metrics["leakage_paise"]["underbilled_revenue"]))])

    left, right = st.columns(2)
    with left:
        st.markdown("**From quote to cash**")
        stages = ["Quoted", "Accepted", "Ordered", "Fulfilled", "Invoiced", "Cash received"]
        keys = ["quoted", "accepted", "ordered", "fulfilled", "invoiced", "cash_received"]
        frame = pd.DataFrame({"Stage": stages, "Value": [funnel[k] / PAISE_PER_CRORE for k in keys]})
        st.altair_chart(bars(frame, "Stage", "Value", "₹ crore", ",.0f", sort=stages), width="stretch")
        table_view(frame.assign(Value=[inr(funnel[k]) for k in keys]))
    with right:
        st.markdown("**Collectible receivables by age at the cutoff**")
        frame = pd.DataFrame(metrics["aging"])
        frame["Bucket"] = frame["aging_bucket"].str[2:]
        frame["Value"] = frame["collectible_paise"] / PAISE_PER_CRORE
        st.altair_chart(bars(frame, "Bucket", "Value", "₹ crore", ",.1f", sort=list(frame["Bucket"])), width="stretch")
        table_view(frame.assign(Collectible=frame["collectible_paise"].map(inr))[["Bucket", "invoices", "Collectible"]])

    st.markdown("**Where outstanding receivables sit** (each rupee counted once)")
    labels = {"not_due": "Not due", "other_overdue": "Overdue up to 90 days", "long_overdue": "Long overdue",
              "disputed_on_hold": "On dispute hold", "duplicate_billing": "Duplicate invoices, should not be collected",
              "short_paid": "Short paid, not yet long overdue"}
    classes = metrics["receivable_classes_paise"]
    frame = pd.DataFrame({"Class": [labels[k] for k in labels], "Value": [classes[k] / PAISE_PER_CRORE for k in labels]})
    st.altair_chart(bars(frame, "Class", "Value", "₹ crore", ",.1f", sort=list(frame["Class"])), width="stretch")
    st.caption(f"Analysis cutoff {cfg.CUTOFF.isoformat()}. Seed and scale are shown on the Data quality tab.")


def leakage_tab(scale: str, ask, recon: dict | None) -> None:
    st.subheader("Revenue leakage explorer")
    if recon is None:
        st.warning(f"Run `python run.py reconcile --scale {scale}` to fill this tab.")
        return
    leakage = recon["metrics"]["leakage_paise"]
    tile_row([("Underbilled revenue", inr(leakage["underbilled_revenue"])),
              ("Overbilled exposure", inr(leakage["overbilled_exposure"])),
              ("Duplicate billing exposure", inr(leakage["duplicate_billing_exposure"])),
              ("Allocation discrepancy", inr(leakage["payment_allocation_discrepancy"]))])
    st.info("These measure different things, so they are shown apart and never added up. Only underbilling is "
            "revenue actually lost. Overbilling and duplicates inflate what customers are asked to pay. "
            "Short payment and overdue amounts are collection risk: the money may still arrive.")
    frame = ask("""SELECT issue_type AS Issue, COUNT(*) AS Findings, SUM(impact_paise) AS impact_paise,
                          SUM(severity = 'HIGH') AS High
                   FROM finding WHERE impact_paise > 0 GROUP BY issue_type ORDER BY impact_paise DESC""")
    frame["Impact"] = frame["impact_paise"].map(inr)
    frame["What it means"] = frame["Issue"].map(ISSUE_MEANING)
    st.markdown("**Size of each exposure type**")
    frame["Value"] = frame["impact_paise"] / PAISE_PER_CRORE
    st.altair_chart(bars(frame, "Issue", "Value", "₹ crore", ",.1f"), width="stretch")
    st.dataframe(frame[["Issue", "Findings", "High", "Impact", "What it means"]], hide_index=True, width="stretch")
    top = ask("""SELECT f.source_id AS Record, f.issue_type AS Issue, f.severity AS Severity, f.impact_paise,
                        f.observed_behavior AS Observed
                 FROM finding f WHERE f.issue_type IN ('UNDERBILLING', 'OVERBILLING', 'DUPLICATE_INVOICE',
                                                       'DUPLICATE_ALLOCATION')
                 ORDER BY f.impact_paise DESC LIMIT 15""")
    top.insert(3, "Impact", top["impact_paise"].map(inr))
    st.markdown("**Largest billing and allocation findings**")
    st.dataframe(top.drop(columns="impact_paise"), hide_index=True, width="stretch")


def delays_tab(scale: str, ask, recon: dict | None) -> None:
    st.subheader("Process delays")
    if recon is None:
        st.warning(f"Run `python run.py reconcile --scale {scale}` to fill this tab.")
        return
    delays = recon["metrics"]["delays"]
    fulfil, invoice, payment = (delays[k] for k in ("order_to_fulfilment", "fulfilment_to_invoice",
                                                    "invoice_to_final_payment"))
    tile_row([("Order to full shipment, median", f"{fulfil['median_days']:g} days"),
              ("Shipment to invoice, median", f"{invoice['median_days']:g} days"),
              ("Invoice to final payment, median", f"{payment['median_days']:g} days"),
              ("Orders over target", f"{fulfil['over_sla']:,}"), ("Shipments billed late", f"{invoice['over_sla']:,}")])
    left, right = st.columns(2)
    with left:
        st.markdown(f"**Order to full shipment** (target {cfg.SLA_ORDER_TO_FULFILMENT_DAYS} days)")
        frame = ask("""SELECT CAST(julianday(last_shipped_date) - julianday(order_date) AS INTEGER) AS days,
                              COUNT(*) AS records
                       FROM v_order_timeline WHERE status IN ('FULFILLED', 'INVOICED', 'CLOSED')
                         AND last_shipped_date IS NOT NULL GROUP BY days""")
        st.altair_chart(delay_histogram(frame, cfg.SLA_ORDER_TO_FULFILMENT_DAYS, "Days"), width="stretch")
    with right:
        st.markdown(f"**Shipment to invoice** (target {cfg.SLA_SHIPMENT_TO_INVOICE_DAYS} days)")
        frame = ask("""SELECT lag_days AS days, COUNT(*) AS records FROM v_shipment_billing
                       WHERE lag_days IS NOT NULL GROUP BY lag_days""")
        st.altair_chart(delay_histogram(frame, cfg.SLA_SHIPMENT_TO_INVOICE_DAYS, "Days"), width="stretch")
    left, right = st.columns(2)
    with left:
        st.markdown("**Invoice to final payment**")
        frame = ask("""SELECT days, COUNT(*) AS records FROM (
                           SELECT CAST(julianday(MAX(a.allocated_date)) - julianday(i.invoice_date) AS INTEGER) AS days
                           FROM invoice i JOIN payment_allocation a ON a.invoice_id = i.invoice_id
                           WHERE i.status = 'PAID' GROUP BY i.invoice_id) GROUP BY days""")
        st.altair_chart(payment_histogram(frame), width="stretch")
    with right:
        st.markdown("**Unpaid invoices by age at the cutoff**")
        aging = pd.DataFrame(recon["metrics"]["aging"])
        aging["Bucket"] = aging["aging_bucket"].str[2:]
        st.altair_chart(bars(aging, "Bucket", "invoices", "Invoices", ",.0f", sort=list(aging["Bucket"])), width="stretch")
    st.markdown("**Most delayed records**")
    worst = ask("""SELECT source_id AS Record, issue_type AS Issue, severity AS Severity, delay_days AS Days,
                          observed_behavior AS Observed
                   FROM finding WHERE issue_type IN ('FULFILMENT_DELAY', 'INVOICING_DELAY')
                   ORDER BY delay_days DESC, source_id LIMIT 15""")
    st.dataframe(worst, hide_index=True, width="stretch")


def exceptions_tab(ask) -> None:
    st.subheader("Exception details")
    findings = ask("""SELECT finding_id, rule_id, issue_type, severity, source_entity, source_id, impact_type,
                             impact_paise, delay_days, observed_behavior FROM finding ORDER BY finding_id""")
    first, second, third = st.columns([2, 1, 2])
    issue_types = first.multiselect("Issue type", sorted(findings["issue_type"].unique()))
    severities = second.multiselect("Severity", ["HIGH", "MEDIUM", "LOW"])
    search = third.text_input("Find a record ID", placeholder="for example INV-2026-000033")
    shown = findings
    if issue_types:
        shown = shown[shown["issue_type"].isin(issue_types)]
    if severities:
        shown = shown[shown["severity"].isin(severities)]
    if search.strip():
        shown = shown[shown["source_id"].str.contains(search.strip(), case=False, regex=False)
                      | shown["observed_behavior"].str.contains(search.strip(), case=False, regex=False)]
    st.caption(f"{len(shown):,} of {len(findings):,} findings")
    view = shown.assign(impact=shown["impact_paise"].map(inr))
    st.dataframe(view[["finding_id", "issue_type", "severity", "source_id", "impact", "delay_days", "observed_behavior"]],
                 hide_index=True, width="stretch", height=280)
    if shown.empty:
        return

    chosen = st.selectbox("Open a finding", list(shown["finding_id"]))
    row = ask("SELECT * FROM finding WHERE finding_id = ?", (chosen,)).iloc[0]
    st.markdown(f"#### {row['finding_id']}: {row['issue_type']}")
    left, right = st.columns(2)
    with left:
        st.markdown(f"**Rule {row['rule_id']}.** {row['rule_description']}")
        st.markdown(f"**Expected:** {row['expected_behavior']}")
        st.markdown(f"**Observed:** {row['observed_behavior']}")
        st.markdown(f"**Severity:** {row['severity']}  \n**Source:** {row['source_entity']} {row['source_id']}")
        impact_line = f"{inr(row['impact_paise'])} ({row['impact_type']})" if row["impact_paise"] else "No direct money impact"
        st.markdown(f"**Impact:** {impact_line}")
        st.markdown(f"**Related records:** {', '.join(json.loads(row['related_ids'])) or 'none'}")
    with right:
        st.markdown("**Evidence**")
        st.json(json.loads(row["evidence"]))

    entities = [row["source_id"]] + json.loads(row["related_ids"])
    marks = ", ".join("?" for _ in entities)
    history = ask(f"""SELECT event_id, entity_type, entity_id, from_status, to_status, event_time, actor_role
                      FROM status_event WHERE entity_id IN ({marks}) ORDER BY event_time, event_id""", tuple(entities))
    st.markdown("**Status history of the records involved**")
    st.dataframe(history, hide_index=True, width="stretch")


def quality_tab(scale: str, ask, recon: dict | None, counts: dict) -> None:
    st.subheader("Data quality")
    metadata = dict(ask("SELECT key, value FROM run_metadata").values.tolist())
    st.caption(f"Scale {metadata.get('scale')}, seed {metadata.get('seed')}, cutoff {metadata.get('cutoff_date')}, "
               f"anomalies injected: {metadata.get('anomalies_injected')}.")
    validation = load_report(scale, "validation")
    evaluation = load_report(scale, "evaluation")
    negative = load_report(scale, "negative_control")
    repro = load_report(scale, "reproducibility")
    if not all((validation, evaluation, negative, repro, recon)):
        st.warning(f"Some reports are missing. Run `python run.py all --scale {scale}`.")
        return

    passed = validation["structural_checks"] - validation["structural_failed"]
    planted = evaluation["by_label_source"]["injected"]
    identities_ok = sum(1 for i in recon["identities"] if i["status"] == "PASS")
    tile_row([("Structural checks passed", f"{passed} of {validation['structural_checks']}"),
              ("Reconciliation identities", f"{identities_ok} of {len(recon['identities'])}"),
              ("Precision, injected anomalies", f"{planted['precision']:.3f}"),
              ("Recall, injected anomalies", f"{planted['recall']:.3f}"),
              ("Findings on clean data", f"{negative['findings_on_clean_data']:,}"), ("Reproducibility", repro["status"])])
    st.info("Precision and recall are measured against anomalies this same project planted, so they show that the "
            "rules work as designed. They are not an estimate of performance on real company data. Labels marked "
            "'rule' below re-apply the same rule, so a perfect score there proves little.")
    st.markdown("**Detection results by where the label came from**")
    sources = pd.DataFrame(evaluation["by_label_source"]).T.reset_index(names="Label source")
    st.dataframe(sources[["Label source", "labels", "tp", "fp", "fn", "precision", "recall"]], hide_index=True,
                 width="stretch")

    left, right = st.columns(2)
    with left:
        st.markdown("**Detection results by issue type**")
        frame = pd.DataFrame(evaluation["by_issue_type"]).T.reset_index(names="Issue")
        st.dataframe(frame, hide_index=True, width="stretch")
        st.markdown("**Reconciliation identities**")
        identity = pd.DataFrame(recon["identities"])[["id", "description", "difference_paise", "status"]]
        st.dataframe(identity, hide_index=True, width="stretch")
    with right:
        st.markdown("**Record counts**")
        frame = pd.DataFrame({"Table": list(counts), "Rows": list(counts.values())})
        st.dataframe(frame[frame["Table"] != "finding"], hide_index=True, width="stretch", height=350)
        st.markdown("**Reproducibility**")
        st.write(f"Combined checksum, run A: `{repro['combined_sha256_a'][:24]}...`")
        st.write(f"Combined checksum, run B: `{repro['combined_sha256_b'][:24]}...`")

    st.markdown("**Validation checks**")
    frame = pd.DataFrame(validation["results"])[["check_id", "category", "description", "problems", "status"]]
    st.dataframe(frame, hide_index=True, width="stretch", height=320)
    st.caption("BUSINESS rows count deliberate rule breaks, which must equal what the ground truth planted. "
               "STRUCTURAL rows must find zero problems.")


def main() -> None:
    st.title("Order-to-Cash revenue leakage and delay analysis")
    scales = available_scales()
    if not scales:
        st.error("No dataset found. Run `python run.py all --scale starter` first, then reload this page.")
        st.stop()
    scale = st.selectbox("Dataset", scales, format_func=lambda s: f"{s.title()} dataset")
    db_file = cfg.data_dir(scale) / "o2c.db"
    stamp = db_file.stat().st_mtime

    def ask(sql: str, params: tuple = ()) -> pd.DataFrame:
        return query(str(db_file), stamp, sql, params)

    tables = ("account", "quote", "quote_line", "sales_order", "order_line", "shipment", "shipment_line", "invoice",
              "invoice_line", "invoice_shipment", "payment", "payment_allocation", "dispute", "ar_ledger_entry",
              "status_event", "finding")
    counts = {t: int(ask(f"SELECT COUNT(*) AS n FROM {t}")["n"][0]) for t in tables}
    if counts["finding"] == 0:
        st.warning(f"The detector has not run on this dataset. Run `python run.py all --scale {scale}`.")
    recon = load_report(scale, "reconciliation")

    overview, leakage, delays, exceptions, quality = st.tabs(
        ["Overview", "Revenue leakage", "Process delays", "Exceptions", "Data quality"])
    with overview:
        overview_tab(scale, ask, recon, counts)
    with leakage:
        leakage_tab(scale, ask, recon)
    with delays:
        delays_tab(scale, ask, recon)
    with exceptions:
        exceptions_tab(ask)
    with quality:
        quality_tab(scale, ask, recon, counts)


main()
