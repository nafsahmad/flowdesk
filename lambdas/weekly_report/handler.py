"""flowdesk-weekly-report: last week's leads + ad spend -> metrics -> email.

Runs every Monday at 08:00 Lagos. The spend comes from a SAMPLE file in S3,
and every report says so.
"""

import json
import os
from datetime import datetime, timedelta, timezone

import boto3

from shared.hubspot import search_contacts_created_since
from shared.report import build_report, format_email, read_spend_csv, write_summary

s3 = boto3.client("s3")
sns = boto3.client("sns")

BUCKET = os.environ["CONTENT_BUCKET"]
SPEND_KEY = os.environ.get("SPEND_KEY", "inputs/ad_spend_SAMPLE.csv")
DAYS = int(os.environ.get("REPORT_DAYS", "7"))
PROPERTIES = ["email", "fd_utm_source", "fd_utm_campaign", "fd_utm_content",
              "lifecyclestage", "fd_revenue", "fd_score"]


def log(**fields):
    """Write one line of JSON to CloudWatch Logs."""
    print(json.dumps(fields))


def lambda_handler(event, context):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=DAYS)

    contacts = search_contacts_created_since(start, PROPERTIES)
    spend_text = s3.get_object(Bucket=BUCKET, Key=SPEND_KEY)["Body"].read().decode("utf-8")
    spend_rows = read_spend_csv(spend_text, start.date().isoformat())

    report = build_report(contacts, spend_rows, start.date().isoformat(), end.date().isoformat())
    summary, unsupported = write_summary(report)
    if unsupported:
        report["summary"] = None
        report["summary_check"] = ("withheld, because it used numbers that aren't in the table: "
                                   + ", ".join(unsupported))
        report["withheld_summary"] = summary
    else:
        report["summary"] = summary
        report["summary_check"] = "pass"

    key = f"reports/{end.date().isoformat()}.json"
    s3.put_object(Bucket=BUCKET, Key=key,
                  Body=json.dumps(report, indent=2).encode("utf-8"),
                  ContentType="application/json")
    sns.publish(
        TopicArn=os.environ["SNS_TOPIC_ARN"],
        Subject=(f"FlowDesk weekly report (SAMPLE DATA) "
                 f"{report['period']['start']} to {report['period']['end']}"),
        Message=format_email(report),
    )
    log(step="report", leads=len(contacts), rows=len(report["rows"]),
        summary_check=report["summary_check"], saved=key)
    return {"leads": len(contacts), "summary_check": report["summary_check"]}