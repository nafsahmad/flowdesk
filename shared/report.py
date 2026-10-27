"""The weekly report: HubSpot leads + ad spend -> metrics -> a checked summary.

Everything here is plain Python and SQLite, so it can be tested without AWS.
Python does the maths. The model only writes words, and every number it
writes is checked against the table.
"""

import csv
import io
import json
import re
import sqlite3

from shared import llm
from shared.prompts import fill, load
from datetime import date, timedelta

SUMMARY_PROMPT = "weekly_summary_v1.txt"
NUMBER = re.compile(r"\d+(?:\.\d+)?")

# Total each side first, then join. Joining first would count each week's
# spend once per lead, and every cost would come out too high.
AGGREGATE_SQL = """
WITH spend_totals AS (
    SELECT utm_campaign, utm_content,
           SUM(spend_usd) AS spend, SUM(impressions) AS impressions, SUM(clicks) AS clicks
    FROM ad_spend
    GROUP BY utm_campaign, utm_content
),
lead_totals AS (
    SELECT utm_campaign, utm_content,
           COUNT(*) AS leads,
           SUM(CASE WHEN lifecyclestage = 'customer' THEN 1 ELSE 0 END) AS customers,
           SUM(COALESCE(revenue, 0)) AS revenue
    FROM contacts
    GROUP BY utm_campaign, utm_content
),
all_keys AS (
    SELECT utm_campaign, utm_content FROM spend_totals
    UNION
    SELECT utm_campaign, utm_content FROM lead_totals
)
SELECT k.utm_campaign, k.utm_content,
       s.spend IS NOT NULL AS has_spend,
       COALESCE(s.spend, 0), COALESCE(s.impressions, 0), COALESCE(s.clicks, 0),
       COALESCE(l.leads, 0), COALESCE(l.customers, 0), COALESCE(l.revenue, 0)
FROM all_keys k
LEFT JOIN spend_totals s
       ON s.utm_campaign IS k.utm_campaign AND s.utm_content IS k.utm_content
LEFT JOIN lead_totals l
       ON l.utm_campaign IS k.utm_campaign AND l.utm_content IS k.utm_content
ORDER BY has_spend DESC, k.utm_campaign, k.utm_content
"""


def _number(value):
    """HubSpot sends numbers as text. Blank or junk becomes None."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _ratio(top, bottom, scale=1):
    """top / bottom * scale, rounded to 2 places, or None if bottom is 0."""
    return round(top / bottom * scale, 2) if bottom else None


def read_spend_csv(text, start, end):
    """Rows from the spend file whose week overlaps the report period.

    Each row covers 7 days from week_start, so a week that began before the
    period but ends inside it still counts. Dates are YYYY-MM-DD.
    """
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    rows = []
    for row in csv.DictReader(io.StringIO(text)):
        week_start = date.fromisoformat(row["week_start"])
        week_end = week_start + timedelta(days=6)
        if week_start <= last and week_end >= first:
            rows.append(row)
    return rows


def add_metrics(row):
    """Work out the metrics. Cost metrics only make sense where there was spend."""
    paid = row["has_spend"]
    spend, impressions, clicks = row["spend"], row["impressions"], row["clicks"]
    leads, customers, revenue = row["leads"], row["customers"], row["revenue"]
    row.update({
        "ctr_pct": _ratio(clicks, impressions, 100) if paid else None,
        "cpc": _ratio(spend, clicks) if paid else None,
        "cpm": _ratio(spend, impressions, 1000) if paid else None,
        "cvr_pct": _ratio(leads, clicks, 100) if paid else None,
        "cpa": _ratio(spend, leads) if paid else None,
        "cac": _ratio(spend, customers) if paid else None,
        "roas": _ratio(revenue, spend) if paid else None,
    })
    return row


def build_report(contacts, spend_rows, start, end):
    """Put leads and spend into SQLite, total them with SQL, add metrics and notes."""
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE contacts (utm_campaign TEXT, utm_content TEXT, "
               "lifecyclestage TEXT, revenue REAL)")
    db.execute("CREATE TABLE ad_spend (utm_campaign TEXT, utm_content TEXT, "
               "spend_usd REAL, impressions INTEGER, clicks INTEGER)")
    db.executemany("INSERT INTO contacts VALUES (?, ?, ?, ?)", [
        (p.get("fd_utm_campaign") or None, p.get("fd_utm_content") or None,
         p.get("lifecyclestage") or None, _number(p.get("fd_revenue")))
        for p in (c["properties"] for c in contacts)
    ])
    db.executemany("INSERT INTO ad_spend VALUES (?, ?, ?, ?, ?)", [
        (r["utm_campaign"], r["utm_content"], float(r["spend_usd"]),
         int(r["impressions"]), int(r["clicks"]))
        for r in spend_rows
    ])

    columns = ["campaign", "variant", "has_spend", "spend", "impressions", "clicks",
               "leads", "customers", "revenue"]
    rows = []
    for values in db.execute(AGGREGATE_SQL):
        row = dict(zip(columns, values))
        row["has_spend"] = bool(row["has_spend"])
        rows.append(add_metrics(row))

    paid = [r for r in rows if r["has_spend"]]
    totals = add_metrics({
        "campaign": "TOTAL (paid)", "variant": None, "has_spend": bool(paid),
        **{k: round(sum(r[k] for r in paid), 2)
           for k in ("spend", "impressions", "clicks", "leads", "customers", "revenue")},
    })

    notes = []
    untracked = sum(r["leads"] for r in rows if r["campaign"] is None)
    no_variant = sum(r["leads"] for r in rows if r["campaign"] and r["variant"] is None)
    no_spend = sum(r["leads"] for r in rows
                   if r["campaign"] and r["variant"] and not r["has_spend"])
    if untracked:
        notes.append(f"{untracked} lead(s) had no campaign at all, so nobody knows where they came from.")
    if no_variant:
        notes.append(f"{no_variant} lead(s) had a campaign but no variant, so they can't count in the A/B test.")
    if no_spend:
        notes.append(f"{no_spend} lead(s) came from campaigns with no spend data, so they have no cost metrics.")

    return {
        "sample_data": True,
        "period": {"start": start, "end": end},
        "leads_total": len(contacts),
        "rows": rows,
        "totals": totals,
        "notes": notes,
    }


def unsupported_numbers(text, source):
    """Numbers in text that don't appear in source (allowing for rounding)."""
    allowed = [float(n) for n in NUMBER.findall(source.replace(",", ""))]
    bad = []
    for token in NUMBER.findall(text.replace(",", "")):
        x = float(token)
        if not any(abs(x - y) < 0.006 or round(y, 1) == x or round(y) == x for y in allowed):
            bad.append(token)
    return bad


def write_summary(report):
    """Ask the model for the four-part summary. Returns (summary, unsupported numbers)."""
    table = json.dumps({"period": report["period"], "rows": report["rows"],
                        "totals": report["totals"]}, indent=1)
    notes = "\n".join(f"- {n}" for n in report["notes"]) or "none"
    prompt = fill(load(SUMMARY_PROMPT), {"table": table, "notes": notes})
    summary = llm.ask("You are a careful marketing analyst.", prompt,
                      max_tokens=800, temperature=0.3).strip()
    return summary, unsupported_numbers(summary, table + "\n" + notes)


def _money(x):
    return "n/a" if x is None else f"${x:,.2f}"


def _plain(x, suffix=""):
    return "n/a" if x is None else f"{x:,}{suffix}"


def format_email(report):
    """The plain-text email."""
    p = report["period"]
    lines = [
        f"FlowDesk weekly report, {p['start']} to {p['end']}",
        "SAMPLE DATA: the ad spend is made up for testing. The leads are real test leads from HubSpot.",
        "",
        f"Leads this period: {report['leads_total']}",
        "",
        "BY CAMPAIGN AND VARIANT",
    ]
    for r in report["rows"] + [report["totals"]]:
        name = f"{r['campaign'] or '(no campaign)'} / {r['variant'] or '(no variant)'}"
        if r["campaign"] == "TOTAL (paid)":
            name = "TOTAL (paid)"
        lines.append(f"{name}: {r['leads']} leads, {r['customers']} customers, "
                     f"revenue {_money(r['revenue'])}")
        if r["has_spend"]:
            lines.append(f"    spend {_money(r['spend'])}, {_plain(r['impressions'])} impressions, "
                         f"{_plain(r['clicks'])} clicks")
            lines.append(f"    CTR {_plain(r['ctr_pct'], '%')}, CPC {_money(r['cpc'])}, "
                         f"CPM {_money(r['cpm'])}, CVR {_plain(r['cvr_pct'], '%')}")
            lines.append(f"    CPA {_money(r['cpa'])}, CAC {_money(r['cac'])}, "
                         f"ROAS {_plain(r['roas'])}")
        else:
            lines.append("    no spend data, so no cost metrics")
    lines += ["", "DATA NOTES"]
    lines += [f"- {n}" for n in report["notes"]] or ["- none"]
    lines += ["", "SUMMARY (written by Bedrock, every number checked against the table above)"]
    if report.get("summary"):
        lines.append(report["summary"])
    else:
        lines.append(f"Summary {report.get('summary_check', 'missing')}. Read the table instead.")
    return "\n".join(lines)
