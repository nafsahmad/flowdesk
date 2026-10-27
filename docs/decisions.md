# Decisions
## 2026-10-24: Lead scoring rules (v1)

**What:** Every contact gets a score from 0 to 100, saved in `fd_score`.

| Signal | Points | How it's checked |
|---|---|---|
| Senior job title | +40 | Job title contains "head", "director" or "founder", ignoring capital letters |
| Company of 10 or more people | +30 | `fd_company_size` is 10 or higher |
| Company name filled in | +15 | Company name isn't blank |
| Came from a campaign | +15 | `fd_utm_campaign` isn't blank |

**Edge cases**
- A blank field scores 0 for that rule. A completely blank contact scores 0, and the script must not crash.
- A company size of exactly 10 counts.
- "Manager" doesn't count as senior in v1, because Managers often recommend but don’t sign off on purchases.

**Why these rules:** FlowDesk sells to B2B teams, so decision-makers at real companies are the best leads. A campaign source means they came in through our marketing.

**What I'd change with real data:** Check which scores actually became customers, then adjust the points.


## 2026-10-24: HubSpot key for local scripts

| Key name | Stored in | Scopes | Created | Rotate by |
|---|---|---|---|---|
| flowdesk-local | Windows environment variable `HUBSPOT_KEY` | crm.objects.contacts.read, crm.objects.contacts.write | 2026-10-24 | 2027-04-24 |
| flowdesk-lead-intake | Lambda environment variable on flowdesk-lead-intake | crm.objects.contacts.read, crm.objects.contacts.write | 2026-10-24 | 2027-04-24 |
| flowdesk-weekly-report | HUBSPOT_KEY env var on flowdesk-weekly-report (eu-north-1) | crm.objects.contacts.read (read only) | 2026-10-26 | 2027-04-26 |

**Why only two scopes:** my scripts only read and update contacts. A key limited to that can't do much damage if it leaks.


## 2026-10-24: Reading Tally submissions

- Questions are matched by **label**, ignoring capitals, because Tally's keys are random strings. Risk: renaming a question in Tally silently drops that field (there's a test proving it). Rule: never rename form questions without updating `LABEL_TO_PROPERTY`.
- Blank answers aren't sent to HubSpot, so a returning lead's existing details are never wiped.
- A submission with no email, or an obviously broken one, is rejected as an invalid lead.
- Error messages name the submission ID, never the email, so logs hold no personal data.

## 2026-10-24: Upserting leads

- Look up by email with `idProperty=email` (a direct read), then PATCH if found or POST if not.
- Webhook code raises errors instead of returning None, so a failed run makes Tally retry.
- Known limitation: if the same email is submitted twice within the same second, both runs could try to create it. HubSpot would reject the second with a 409. Handling that is a later improvement.
| TALLY_SIGNING_SECRET | Tally webhook settings + Lambda env var on flowdesk-lead-intake | Signs and checks webhook requests | 2026-10-24 | 2027-04-24 |


## 2026-10-24: Checking Tally signatures

- Every request must carry a valid Tally-Signature (HMAC-SHA256 of the raw body, base64). Anything else gets a 401 and nothing is written.
- The signature is checked on the raw body, before parsing, because re-saving the JSON could change it.
- If the secret isn't configured, the Lambda returns 500 and rejects everything (fails closed), so Tally keeps retrying until it's fixed.
- Rollout order: secret in Lambda, then in Tally, then deploy the code. That way no real submission is rejected during the change.


## 2026-10-25: Building against a fake model while Bedrock is blocked

- Bedrock returned "too many tokens per day" on the first request (new-account quota). Quota increase requested, and support case opened.
- All model calls go through `shared/llm.py`. With FLOWDESK_FAKE_LLM=1 it returns ready-made replies in Bedrock's JSON shape, so everything else can be built and tested now.
- Every draft records `"model": "fake"` when the fake was used, so fake output can never be mistaken for real output.
- When the quota arrives: remove FLOWDESK_FAKE_LLM and rerun. No other code changes.

## 2026-10-25: Content generator in AWS

- Briefs go in `briefs/`, drafts come out in `content/<brief_id>/draft.json`. The Lambda is triggered by new .json files in `briefs/` only.
- Three guards against the Lambda triggering itself: the code skips anything outside `briefs/`, the trigger only watches `briefs/`, and the IAM policy only allows writing to `content/`.
- Least privilege: the Lambda can read `briefs/`, write `content/` and call Nova 2 Lite. Nothing else.
- Broken briefs are rejected before any model call. Model failures raise, so AWS retries the run.

| WP_APP_PASSWORD (flowdesk-publisher) | Windows env var, later Lambda env var | WordPress application password for the InstaWP lab | 2026-10-25 | 2027-04-25 |

| WP_APP_PASSWORD (flowdesk-publisher-lambda) | Lambda env var on flowdesk-publisher | WordPress application password for the InstaWP lab | 2026-10-26 | 2027-04-26 |

## 2026-10-25: WordPress lab

- Self-hosted WordPress on an InstaWP Sandbox site ($2 a month, billed daily, permanent site). It's the same kind of WordPress most companies run.
- API login uses an application password over HTTPS. It can be revoked without touching the admin login.
- Search engines discouraged, so test posts stay out of Google.
- Cost control: delete the site after interviews. A paused site is still billed.

## 2026-10-25: Repair loop

- If a draft breaks a rule, it's sent back to the model once, with its own draft and the exact failed checks. Then it's checked again.
- Capped at one repair, so a stubborn model can't loop and run up costs.
- Each record saves how many repairs were needed, so we can still measure how often the prompt works on its own.

## 2026-10-26: Three layers against made-up claims

- Writer prompts say what may and may not be claimed. Hard rules beat the marketer's notes.
- Code checks a list of made-up claims seen in real runs (CLAIM_PHRASES). It's certain and free, and the list grows after each review.
- The AI judge (v2) looks for new ones. It's stricter than v1 but over-flags a little and still misses some, so it's a filter, not the final word.
- The human approval in WordPress is the final gate.
- Prompt tuning is time-boxed: after v4, we move on unless results get worse.

## 2026-10-26: Daily credential check

- Runs at 7am Lagos (cron(0 6 * * ? *) in UTC). It tests the HubSpot key on lead-intake, the WordPress password on publisher, and Bedrock access.
- It reads each key from the Lambda that uses it, so it tests the real key, not a copy. Its permission to read Lambda settings is limited to those two functions.
- One email when anything fails, naming the key and what to do. If the checker itself crashes, its own Errors alarm fires instead.
- Known limits: the HubSpot check only proves read access, not write. The Tally signing secret can't be tested from here. If the checker stopped running altogether, nothing would notice yet (fix later: an alarm when it hasn't run for a day). Long term, keys belong in Secrets Manager.

## 2026-10-26: Saved log searches

- Five saved Logs Insights searches in the FlowDesk folder: errors (24h), errors by Lambda (24h), leads received vs written (7d), leads never written (7d), leads with no variant (7d).
- Lost-lead checks count distinct submission IDs, so Tally's retries don't look like lost leads.
- lead-intake logs each lead's variant (or "none"), so leads without attribution can be found.
- Alarms only catch crashes. Silent data problems, like missing attribution, are caught by the searches and the weekly report.


## 2026-10-26: Weekly report

**What it does:** every Monday, it pulls the last 7 days of new HubSpot contacts, joins them with ad spend by campaign and variant, works out the metrics, gets a written summary from Bedrock, saves the report to S3 and emails it.

**How it runs**
- Lambda `flowdesk-weekly-report` in eu-north-1, Python 3.12, timeout 2 minutes.
- Schedule: EventBridge rule `flowdesk-weekly-report-monday`, `cron(0 7 ? * MON *)`. That's 07:00 UTC, which is 08:00 Lagos.
- Environment variables: `HUBSPOT_KEY` (read-only key `flowdesk-weekly-report`), `CONTENT_BUCKET`, `SNS_TOPIC_ARN` (the eu-north-1 `flowdesk-alerts` topic).
- Permissions (`flowdesk-weekly-report-access`): read `inputs/`, write `reports/`, publish to `flowdesk-alerts`, call Nova 2 Lite through the EU profile. Nothing else.
- Alarm: `flowdesk-weekly-report-errors`.
- The credential check tests its HubSpot key every morning.

**Data**
- Leads: HubSpot search for contacts created in the last 7 days (`createdate` GTE the start of the period).
- Spend: `inputs/ad_spend_SAMPLE.csv` in S3. It's made-up data, labelled SAMPLE in the file name, the email subject and the email body. Only rows with `week_start` inside the period are counted.
- Customers and revenue come from HubSpot's lifecycle stage (`customer`) and `fd_revenue`.

**How the numbers are worked out**
- Both tables are loaded into an in-memory SQLite database. Each side is totalled before joining, because joining first would count each week's spend once per lead and inflate every cost.
- Rows are by campaign and variant. A UNION of keys keeps leads that have no spend, and `IS` in the join lets leads with no campaign match their own group.
- Python works out CTR, CPC, CPM, CVR, CPA, CAC and ROAS, rounded to 2 places. Cost metrics only appear where there was spend: no spend means "no cost metrics", not $0. Dividing by zero gives "n/a", not a crash.
- Totals cover paid rows only.
- Data notes flag leads with no campaign, leads with a campaign but no variant, and leads from campaigns with no spend data.

**The summary**
- Bedrock (`eu.amazon.nova-2-lite-v1:0`, prompt `weekly_summary_v1.txt`, temperature 0.3) writes four parts: what happened, what worked, what failed, what should happen next.
- Python does all the maths. The model only writes words.
- Every number in the summary is checked against the table, allowing for normal rounding. If any number isn't in the table, the summary is withheld from the email and kept in the saved report as `withheld_summary` for review.

**Output**
- Saved to `reports/<date>.json` in S3.
- Emailed through `flowdesk-alerts`, subject "FlowDesk weekly report (SAMPLE DATA) <start> to <end>".

**Known limits and next steps**
- Reports and alerts share one SNS topic. A separate reports topic would be cleaner.
- If Bedrock fails, the whole report fails, even though the numbers were worked out fine. Next improvement: still email the numbers with "Summary unavailable", then fail the run so the alarm fires.
- LTV, contribution margin and payback period aren't calculated, because there's no data on how long customers stay.