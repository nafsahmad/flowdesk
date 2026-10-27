# FlowDesk smoke test

A full check that every part of FlowDesk works, end to end. Run it after any big change, before a demo, and before an interview. It takes about 35 minutes.

Tick each box as you go and note anything odd. A failed check here goes in `test-log.md`, and if it's a real problem, in `docs/incidents/` too.

Before starting: the AWS console region (top right) says **Stockholm** (eu-north-1).

---

## 1. Local tests (laptop, 2 minutes)

- [ ] `python -m scripts.run_all_tests` ends with **All 9 test files passed**

## 2. Laptop keys still work (2 minutes)

- [ ] `python -m scripts.stage1_score_contacts` fetches every contact, most say `SAME`, and it ends with `Verified N of N`

## 3. Nothing is in the wrong region (5 minutes)

- [ ] Tag Editor (all regions, all resource types): every resource with `flowdesk` in its name is in `eu-north-1`
- [ ] No leftover `/aws/lambda/flowdesk-*` log groups in other regions

## 4. Lead flow: form to HubSpot (5 minutes)

Open the Tally form with `?utm_source=smoke&utm_campaign=system-check&utm_content=A` on the end. Submit:

| Field | Value |
|---|---|
| First Name | Smoke |
| Last Name | Test (number it each run: Test 1, Test 2...) |
| Work email | smoke.test@example.com |
| Company | Smoke Test Co |
| Job title | Head of Operations |
| Company size | 20 |

- [ ] The contact appears in HubSpot within seconds, with `fd_score` **100**, `fd_utm_source` smoke, `fd_utm_campaign` system-check and `fd_utm_content` A
- [ ] lead-intake logs show `received` then `written`, with `variant` A

## 5. Content flow: brief form to record (5 minutes)

Open the **FlowDesk Content Brief** form in a private window. It asks for the password first. Submit:

| Field | Value |
|---|---|
| Topic | Smoke test N: one link for every client file (number it each run) |
| Audience | Owners of marketing agencies with 5 to 50 staff |
| Facts | Three lines: `FlowDesk sends clients one link where they share account access`, `The agency sees what's still missing on one page`, `FlowDesk reminds clients automatically when something is missing` |
| Your email | smoke.test@example.com |

- [ ] brief-intake logs show `received`, then `saved` with status `ok`
- [ ] A new file appears in `briefs/`, starting `smoke-test-n-`, with `"source": "brief-form"`. Note its `brief_id`
- [ ] Within about 2 minutes, `content/<brief_id>/draft.json` exists
- [ ] Its `model` is `eu.amazon.nova-2-lite-v1:0` (not `fake`) and `prompt_versions` match `shared/generator.py`
- [ ] Status is `checked` or `needs_review`. If it's `failed_checks`, read why, then repeat with the next number

## 6. Publishing and approval (10 minutes)

- [ ] Run `flowdesk-publisher` (Test tab, `manual-run`): the record moves to `in_wordpress` and a draft appears in WordPress
- [ ] Review it. Deal with any red box and delete it. Publish
- [ ] Run the publisher again: the record moves to `published`, with `wordpress.url`, `captions_ready` and `history`
- [ ] The live page loads, with no red box

## 7. The full loop: post to lead (3 minutes)

On the live post, click **Pick a time here**.

- [ ] The Tally form opens with `utm_source=blog&utm_campaign=<brief_id>&utm_content=blog` in the address bar

Submit as **Smoke Blog**, `smoke.blog@example.com`, Account Manager, Blog Test Ltd, 8 people.

- [ ] HubSpot shows Smoke Blog with `fd_score` **30**, `fd_utm_source` blog and `fd_utm_campaign` set to the brief_id

## 8. Credentials (1 minute)

- [ ] Run `flowdesk-credential-check` (Test tab): `{"checked": 4, "problems": 0}`, and no email

## 9. Monitoring (3 minutes)

- [ ] CloudWatch, then Alarms: all six `-errors` alarms are **OK**
- [ ] All three schedules are enabled: `flowdesk-publisher-hourly`, `flowdesk-credential-check-daily` and `flowdesk-weekly-report-monday` show as triggers on their Lambdas
- [ ] The publisher's logs show hourly runs you didn't start
- [ ] The credential check's logs show a 07:00 run (from the morning after it was set up)
- [ ] Saved search **FlowDesk errors (24h)** shows nothing unexpected from this smoke test
- [ ] Saved search **FlowDesk leads received vs written (7d)**: the counts match, apart from leads rejected on purpose
- [ ] Saved search **FlowDesk briefs rejected (7d)** shows nothing you didn't expect

## 10. Weekly report (3 minutes)

- [ ] Run `flowdesk-weekly-report` (Test tab, `manual-run`): it succeeds, and an email titled "FlowDesk weekly report (SAMPLE DATA)..." arrives
- [ ] A new file appears in `reports/` in S3, with `summary_check` of `pass`
- [ ] The smoke-test leads from sections 4 and 7 appear in the email (as "no spend data" rows)
- [ ] One number checked by hand with a calculator matches

## 11. Costs (2 minutes)

- [ ] Billing: month-to-date cost is what you'd expect (a few cents plus InstaWP)
- [ ] The $5 budget alert hasn't fired

---

## Clean up afterwards

- Leave the smoke-test contacts in HubSpot, or delete them. Either is fine, since they're fake.
- Leave the smoke-test post published, or move it to Trash. If you trash it, the next publisher run marks its record `removed_in_wordpress`, which is also correct.
- Leave the smoke-test brief files in `briefs/`. Each one has its own ID, so they never clash with real briefs.