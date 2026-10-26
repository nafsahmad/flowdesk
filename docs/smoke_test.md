# FlowDesk smoke test

A full check that every part of FlowDesk works, end to end. Run it after any big change, before a demo, and before an interview. It takes about 30 minutes.

Tick each box as you go and note anything odd. A failed check here goes in `test-log.md`, and if it's a real problem, in `docs/incidents/` too.

Before starting: the AWS console region (top right) says **Stockholm**.

---

## 1. Local tests (laptop, 2 minutes)

- [ ] `python -m scripts.run_all_tests` ends with **All 6 test files passed**

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

## 5. Content flow: brief to record (5 minutes)

Upload `sample_data/briefs/smoke-test-N.json` to `briefs/`. Use a **new number every run**, and change `brief_id` inside the file to match.

- [ ] Within about 2 minutes, `content/smoke-test-N/draft.json` exists
- [ ] Its `model` is `us.amazon.nova-2-lite-v1:0` (not `fake`) and `prompt_versions` match `shared/generator.py`
- [ ] Status is `checked` or `needs_review`. If it's `failed_checks`, read why, then repeat with the next number

## 6. Publishing and approval (10 minutes)

- [ ] Run `flowdesk-publisher` (Test tab, `manual-run`): the record moves to `in_wordpress` and a draft appears in WordPress
- [ ] Review it. Deal with any red box and delete it. Publish
- [ ] Run the publisher again: the record moves to `published`, with `wordpress.url`, `captions_ready` and `history`
- [ ] The live page loads, with no red box

## 7. The full loop: post to lead (3 minutes)

On the live post, click **Pick a time here**.

- [ ] The Tally form opens with `utm_source=blog&utm_campaign=smoke-test-N&utm_content=blog` in the address bar

Submit as **Smoke Blog**, `smoke.blog@example.com`, Account Manager, Blog Test Ltd, 8 people.

- [ ] HubSpot shows Smoke Blog with `fd_score` **30**, `fd_utm_source` blog and `fd_utm_campaign` smoke-test-N

## 8. Credentials (1 minute)

- [ ] Run `flowdesk-credential-check` (Test tab): `{"checked": 3, "problems": 0}`, and no email

## 9. Monitoring (3 minutes)

- [ ] CloudWatch, then Alarms: all four `-errors` alarms are **OK**
- [ ] Both schedules are enabled: `flowdesk-publisher-hourly` and `flowdesk-credential-check-daily` show as triggers on their Lambdas
- [ ] The publisher's logs show hourly runs you didn't start
- [ ] The credential check's logs show a 07:00 run (from the morning after it was set up)
- [ ] Saved search **FlowDesk errors (24h)** shows nothing unexpected from this smoke test
- [ ] Saved search **FlowDesk leads received vs written (7d)**: the counts match, apart from leads rejected on purpose

## 10. Costs (2 minutes)

- [ ] Billing: month-to-date cost is what you'd expect (a few cents plus InstaWP)
- [ ] The $5 budget alert hasn't fired

---

## Clean up afterwards

- Leave the smoke-test contacts in HubSpot, or delete them. Either is fine, since they're fake.
- Leave the smoke-test post published, or move it to Trash. If you trash it, the next publisher run marks its record `removed_in_wordpress`, which is also correct.