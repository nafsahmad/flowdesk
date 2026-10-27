"""Stage 6, local run: builds the weekly report on your laptop and prints the email.

Uses your laptop's HubSpot key and sample_data/ad_spend_SAMPLE.csv. Run it with
the fake model on, because your laptop has no AWS login:

    $env:FLOWDESK_FAKE_LLM = "1"
    python -m scripts.stage6_report_local
"""

from datetime import datetime, timedelta, timezone

from shared.hubspot import search_contacts_created_since
from shared.report import build_report, format_email, read_spend_csv, write_summary

DAYS = 7
PROPERTIES = ["email", "fd_utm_source", "fd_utm_campaign", "fd_utm_content",
              "lifecyclestage", "fd_revenue", "fd_score"]


def main():
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=DAYS)

    contacts = search_contacts_created_since(start, PROPERTIES)
    with open("sample_data/ad_spend_SAMPLE.csv", encoding="utf-8") as f:
        spend_rows = read_spend_csv(f.read(), start.date().isoformat(), end.date().isoformat())

    report = build_report(contacts, spend_rows, start.date().isoformat(), end.date().isoformat())
    summary, unsupported = write_summary(report)
    report["summary"] = None if unsupported else summary
    report["summary_check"] = ("pass" if not unsupported else
                               "withheld, because it used numbers that aren't in the table: "
                               + ", ".join(unsupported))
    print(format_email(report))


if __name__ == "__main__":
    main()