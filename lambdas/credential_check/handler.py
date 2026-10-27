"""flowdesk-credential-check: tests every key FlowDesk relies on, once a day.

It reads each key from the Lambda that actually uses it, so it tests the real
thing, not a copy. If anything is wrong, it sends one email to flowdesk-alerts.
"""

import json
import os

import boto3
import requests

from shared import llm

lambda_client = boto3.client("lambda")
sns = boto3.client("sns")
TIMEOUT_SECONDS = 10


def log(**fields):
    """Write one line of JSON to CloudWatch Logs."""
    print(json.dumps(fields))


def env_of(function_name):
    """The environment variables of another FlowDesk Lambda."""
    config = lambda_client.get_function_configuration(FunctionName=function_name)
    return config.get("Environment", {}).get("Variables", {})


def explain(status):
    """What a failed status code means, and what to do about it."""
    if status == 401:
        return "rejected (401): the key is wrong, expired or revoked. Issue a new one and update the Lambda"
    if status == 403:
        return "accepted, but missing a permission (403). Check the key's scopes"
    return f"unexpected status {status}"


def check_hubspot(env):
    r = requests.get("https://api.hubapi.com/crm/v3/objects/contacts",
                     headers={"Authorization": f"Bearer {env['HUBSPOT_KEY']}"},
                     params={"limit": 1}, timeout=TIMEOUT_SECONDS)
    return None if r.ok else explain(r.status_code)


def check_wordpress(env):
    r = requests.get(env["WP_SITE"].rstrip("/") + "/wp-json/wp/v2/users/me",
                     auth=(env["WP_USER"], env["WP_APP_PASSWORD"]),
                     timeout=TIMEOUT_SECONDS)
    return None if r.ok else explain(r.status_code)


def check_bedrock(_env):
    reply = llm.ask("You are a health check.", "Reply with the word OK.",
                    max_tokens=10, temperature=0)
    return None if reply.strip() else "Bedrock replied with nothing"


# (what it is, which Lambda holds the key, how to test it)
CHECKS = [
    ("HubSpot key used by flowdesk-lead-intake", "flowdesk-lead-intake", check_hubspot),
    ("WordPress password used by flowdesk-publisher", "flowdesk-publisher", check_wordpress),
    ("Bedrock access for flowdesk-content-generator", None, check_bedrock),
    ("HubSpot key used by flowdesk-weekly-report", "flowdesk-weekly-report", check_hubspot),
]


def lambda_handler(event, context):
    problems = []
    for name, function_name, check in CHECKS:
        try:
            env = env_of(function_name) if function_name else {}
            problem = check(env)
        except Exception as e:  # a check that crashes is a problem worth reporting too
            problem = f"the check itself failed: {str(e)[:200]}"
        log(step="credential", name=name,
            status="ok" if problem is None else "problem", detail=problem)
        if problem:
            problems.append(f"- {name}: {problem}")

    if problems:
        sns.publish(
            TopicArn=os.environ["SNS_TOPIC_ARN"],
            Subject=f"FlowDesk credential check: {len(problems)} problem(s)",
            Message=("These credentials need attention:\n\n" + "\n".join(problems)
                     + "\n\nSee the credentials table in docs/decisions.md and docs/runbook.md."),
        )
    log(step="summary", checked=len(CHECKS), problems=len(problems))
    return {"checked": len(CHECKS), "problems": len(problems)}