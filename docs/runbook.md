# FlowDesk runbook

How FlowDesk runs, how to tell when it's broken, and how to fix it. Written from real incidents and drills, not guesses.

Everything lives in **AWS us-north-1 (Stockholm)**. If you can't find something in the console, check the region at the top right first.

---

## The system in one paragraph

A marketer uploads a brief to S3. `flowdesk-content-generator` writes a blog post and two captions with Amazon Bedrock, checks them, and saves a record in `content/`. Every hour, `flowdesk-publisher` sends checked drafts to WordPress, waits for a human to approve and publish them, then confirms the live page. Readers click tracked links to the Tally form, and `flowdesk-lead-intake` scores each lead and upserts it into HubSpot. Every morning, `flowdesk-credential-check` tests every key. Any Lambda that fails emails the `flowdesk-alerts` list.

---

## Where everything is

| Thing | Name | Notes |
|---|---|---|
| S3 bucket | `flowdesk-content-nafs-2026` | `briefs/` in, `content/` out. Versioning on |
| HTTP API | `flowdesk-api` | `POST /leads` goes to `flowdesk-lead-intake`. URL in the API Gateway console, kept out of this repo |
| Alert topic | SNS `flowdesk-alerts` | Email subscription to "my email" |
| WordPress lab | InstaWP Sandbox, permanent site | Category `flowdesk` (slug). $2 a month, billed daily |
| HubSpot | Free account | Custom properties `fd_score`, `fd_company_size`, `fd_utm_source`, `fd_utm_campaign`, `fd_utm_content`, |
| Tally form | FlowDesk Demo Request | Hidden fields `utm_source`, `utm_campaign`, `utm_content`. Webhook to the HTTP API, signed |
| Log retention | All FlowDesk log groups | 1 month |

---

## flowdesk-lead-intake

**What it does:** turns a Tally submission into a scored HubSpot contact, with its source, campaign and variant.

**Triggered by:** Tally's webhook, through API Gateway `POST /leads`.

**Settings:** Python 3.12, timeout 10 seconds.

**Environment variables:** `HUBSPOT_KEY` (service key `flowdesk-lead-intake`), `TALLY_SIGNING_SECRET`.

**What it replies, and why:**

| Situation | Reply | Logged as |
|---|---|---|
| Signature missing or wrong | 401, nothing written | `step: signature, status: rejected` |
| Body isn't JSON | 400 | `step: parse, status: rejected` |
| No email, or a broken one | 200, so Tally stops retrying | `step: parse, status: rejected` |
| Lead saved | 200 | `step: received`, then `step: written` with `action`, `score` and `variant` |
| HubSpot fails | Error (500), so Tally retries | Traceback, and the Errors alarm fires |
| `TALLY_SIGNING_SECRET` not set | 500, rejects everything (fails closed) | `step: config, status: error` |

**Tally retries** a failed delivery up to 5 times over about a day (roughly 5 minutes, 30 minutes, 1 hour, 6 hours, 1 day). A lead that failed because of a temporary problem usually arrives by itself once the problem is fixed.

**Errors seen so far:**

| Symptom | Cause | Fix |
|---|---|---|
| Alarm email, `HubSpot returned 401` in the logs | `HUBSPOT_KEY` wrong or expired (drill 1) | Fix the key. Tally's retry delivers the lead |
| 401 replies to real Tally submissions | Signing secret in the Lambda doesn't match Tally's | Make the two secrets match (see Rotation) |
| Lead in HubSpot with empty `fd_utm_` fields, no alarm | Form opened from a link without UTMs (drill 3) | Not a code fault. Find them with the "no variant" search |

**Safe to repeat:** yes. Contacts are upserted by email, so sending the same lead twice updates one contact instead of creating two.

---

## flowdesk-content-generator

**What it does:** brief in, checked and judged drafts out, saved as `content/<brief_id>/draft.json`.

**Triggered by:** a new `.json` file in `briefs/`.

**Settings:** Python 3.12, timeout 2 minutes.

**Environment variables:** none in normal use. `FLOWDESK_FAKE_LLM=1` switches to the fake model for testing only, so it must be **absent** in normal use. `FLOWDESK_MODEL_ID` can override the model (default `us.amazon.nova-2-lite-v1:0`).

**Permissions:** read `briefs/`, write `content/`, call Nova 2 Lite. Nothing else.

**What it does, in order:** check the brief. Write the blog and captions. Run the rule checks. Send anything that fails back once with the exact reasons (the repair loop). Judge only what passed. Save the record.

**Statuses it sets:**

| Status | Meaning | What happens next |
|---|---|---|
| `checked` | Rules pass and the judge found nothing | Publisher sends it to WordPress |
| `needs_review` | Rules pass, scores 3 or more, but the judge flagged sentences | Publisher sends it to WordPress with a red review box |
| `failed_checks` | A rule broke after one repair, or a score under 3 | Never reaches WordPress. Read `rule_checks` and `judge` in the record |

**Every record says how it was made:** `model`, `prompt_versions`, `repairs`, `rule_checks`, `judge`, `review_notes`, `created_at`.

**Changing a prompt:** add a new numbered file (for example `blog_v5.txt`), change `PROMPT_VERSIONS` in `shared/generator.py`, run the tests, rebuild, upload, then **open `shared/generator.py` in the Lambda console and check the version line**. Log the change in `prompts/changelog.md`.

**Errors seen so far:**

| Symptom | Cause | Fix |
|---|---|---|
| `AccessDeniedException: account being verified` | New AWS account under verification | Wait up to 2 hours, then contact AWS |
| `ThrottlingException: too many tokens per day` | New account's Bedrock quota at zero | Service Quotas increase request and a support case |
| `Task timed out after 3.00 seconds` | Default timeout too short for model calls | Timeout 2 minutes |
| Record says `v3` after shipping `v4` | Version line not changed before the build | Check the version in the console after every upload |
| `failed_checks`, blog too short | Nova writes short | Prompt v3 counts sentences, plus the repair loop |
| Nothing in `content/` after uploading | Brief rejected (missing fields, bad `brief_id`) | Logs show `step: validate, status: rejected` and the reason |

**Safe to repeat:** only with a **new `brief_id`**. Reusing one overwrites the record, including one already in WordPress (known gap).

---

## flowdesk-publisher

**What it does:** moves records along. `checked` or `needs_review` becomes a WordPress draft (`in_wordpress`). After a human publishes it and the live page checks out, it becomes `published`. A draft deleted or trashed in WordPress becomes `removed_in_wordpress`.

**Triggered by:** EventBridge rule `flowdesk-publisher-hourly`, `rate(1 hour)`.

**Settings:** Python 3.12, timeout 1 minute, reserved concurrency 1 (two runs can never overlap).

**Environment variables:** `CONTENT_BUCKET`, `WP_SITE` (**with** `https://`, no slash at the end), `WP_USER`, `WP_APP_PASSWORD` (application password `flowdesk-publisher-lambda`), `TALLY_FORM_URL`.

**Permissions:** list, read and write `content/`. No Bedrock, no briefs.

**The approval rule:** "published" only counts once the public page loads, is the right post, and has **no** "FLOWDESK REVIEW NOTES" box on it. If the box was left in, the run fails, so the alarm fires and the record stays `in_wordpress` until the box is deleted.

**Errors seen so far:**

| Symptom | Cause | Fix |
|---|---|---|
| `Invalid URL ... No scheme supplied` | `WP_SITE` missing `https://` | Add it |
| `WordPress returned 401` | Application password revoked or wrong | New application password, update `WP_APP_PASSWORD` |
| `published with the review notes box still in it` | Post published before the box was deleted | Edit the post, delete the box, update. The next run marks it published |

**Safe to repeat:** yes, any time. Run it by hand from the Test tab (`manual-run`, event `{}`). It only ever moves records forward.

---

## flowdesk-credential-check

**What it does:** tests the HubSpot key on lead-intake, the WordPress password on publisher, and Bedrock access. It reads each key from the Lambda that uses it, so it tests the real key.

**Triggered by:** EventBridge rule `flowdesk-credential-check-daily`, `cron(0 6 * * ? *)`. That's 06:00 UTC, which is **07:00 Lagos**.

**Settings:** Python 3.12, timeout 30 seconds.

**Environment variables:** `SNS_TOPIC_ARN`.

**Permissions:** read the settings of `flowdesk-lead-intake` and `flowdesk-publisher` only, publish to `flowdesk-alerts`, call Nova 2 Lite.

**Two kinds of email:**
- **"FlowDesk credential check: N problem(s)"** means a key is bad. The email says which key and what to do.
- **"ALARM: flowdesk-credential-check-errors"** means the checker itself crashed. Read its logs.

**Limits:** the HubSpot check proves read access, not write. The Tally signing secret can't be tested from here. If the checker stopped running altogether, nothing would notice yet.

---

## Alerts and searches

**Alarms** (all send In alarm and OK emails to `flowdesk-alerts`): `flowdesk-lead-intake-errors`, `flowdesk-content-generator-errors`, `flowdesk-publisher-errors`, `flowdesk-credential-check-errors`. Each fires on Errors of 1 or more in 5 minutes. Missing data counts as good.

**Saved searches** (CloudWatch Logs Insights, folder `FlowDesk`):

| Search | Use it when |
|---|---|
| FlowDesk errors (24h) | Any alarm email. Start here |
| FlowDesk errors by Lambda (24h) | You want to know which part is struggling |
| FlowDesk leads received vs written (7d) | Weekly, or when lead numbers look low |
| FlowDesk leads never written (7d) | The counts above don't match |
| FlowDesk leads with no variant (7d) | Weekly. Catches silent attribution loss |

**Alarms only catch crashes.** Data problems, like leads with no attribution, need the searches and the weekly review.

---

## When an alert arrives

1. Read the email. It names the Lambda (or the key).
2. Run **FlowDesk errors (24h)**. Find the first error line for that Lambda.
3. Read the status code and the error text. 401 means a bad key, 403 means a missing permission, 404 means the wrong address or a deleted item, and a timeout means it's too slow.
4. Reproduce it if you can (Postman, or the Lambda's Test tab).
5. Fix it, then **prove the outcome**: the lead is in HubSpot, the post is live, the credential check says 0 problems. "I redeployed" isn't proof.
6. Wait for the **OK** email.
7. Write an incident note in `docs/incidents/` while it's fresh.

---

## Rotating each credential

Make the new key **before** removing the old one, so nothing breaks in between.

**HubSpot service key (`flowdesk-lead-intake`):**
1. HubSpot: Development, then Keys, then Service keys, then the key, then **Rotate and expire later**. The old key keeps working for 7 days.
2. Copy the new key into `HUBSPOT_KEY` on `flowdesk-lead-intake` and save.
3. Run `flowdesk-credential-check`. You want 0 problems.
4. Back in HubSpot, **Expire now** on the old key.
5. Update the credentials table.

**WordPress application password (`flowdesk-publisher-lambda`):**
1. WordPress: Users, then Profile, then Application Passwords. Create a new one.
2. Paste it into `WP_APP_PASSWORD` on `flowdesk-publisher` and save.
3. Run `flowdesk-credential-check`. You want 0 problems.
4. Revoke the old password in WordPress.
5. Update the credentials table.

**Tally signing secret:**
1. Make a new secret: `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
2. Update `TALLY_SIGNING_SECRET` on `flowdesk-lead-intake`, then straight away update the secret in Tally's webhook settings.
3. Any submission in the gap gets a 401, but Tally retries, so it arrives after the second step.
4. Submit a test lead and check it reaches HubSpot.
5. Update the credentials table.

**Laptop keys** (`flowdesk-local` HubSpot key, `flowdesk-publisher` WordPress password): same steps, but update them with `setx` and restart VS Code.

The full list of keys, where each lives and when it's due for rotation is the credentials table in `docs/decisions.md`.

---

## Routine

**Daily:** read any alert emails. The credential check runs at 07:00 Lagos and emails only if something's wrong.

**When a draft appears in WordPress:** review it. For `needs_review` drafts, check each flagged sentence against the brief's facts, delete the red box, then publish.

**Weekly:**
- Run **leads received vs written** and **leads with no variant**.
- Check `content/` in S3 for `failed_checks` records, and read why they failed.
- Add any new made-up claims you spot to `CLAIM_PHRASES` in `shared/checks.py`.

---

## Known gaps

- Reusing a `brief_id` overwrites its record, even after the post is in WordPress.
- The judge over-flags some sentences and misses others, so the human approval is the real gate.
- Briefs fix the call to action as a demo, even when the offer is a trial.
- Captions are only available inside the record in S3.
- If WordPress creates a draft but saving the record fails, the next run could create a second draft.
- Keys are stored as Lambda environment variables. They belong in AWS Secrets Manager.
- Nothing alerts if the credential check stops running.
