# Test Log

| Date | Test | Expected | Actual | Pass? |
|---|---|---|---|---|
| 2026-10-24 | Fetch all contacts, page size 3 | All contacts, 7 pages | All contacts fetched over 7 pages | Yes |
| 2026-10-24 | Misspelled property name in GET (`jobtitel`) | An error, because the property doesn't exist | Status 200, no error. Every title came back empty | Experiment |
| 2026-10-24 | Empty-property warning | Warning for `fd_score` (nothing scored yet) | Warning printed for `fd_score` only | Yes |
| 2026-10-24 | Dry run before first write | About 21 contacts, fake ones match answer key | 21 contacts. Fake ones matched 7 of 7. Found 2 HubSpot sample contacts and duplicate family records | Yes, and cleanup needed |
| 2026-10-24 | Tally webhook with UTM link, sent to Webhook.site | All 3 hidden fields filled | utm_source=test, utm_campaign=oct-launch, utm_content=A. Type HIDDEN_FIELDS | Yes |
| 2026-10-24 | Upsert from sample Tally payload, first run | New contact created, all properties verified | Created contact ID. Verified all 10 properties. Score 100, UTM fields filled | Yes |
| 2026-10-24 | Same payload run again (duplicate check) | Same contact updated, no duplicate | Updated contact same ID. Only one Kemi Test in HubSpot | Yes |
| 2026-10-24 | Lambda console test with sample Tally event | 200, Lead updated, received and written logs |  200, Lead updated, received and written logs | Yes |
| 2026-10-24 | POST sample payload to API URL from laptop | 200, Lead updated | 200, message "Lead updated". Kemi updated in HubSpot | Yes |
| 2026-10-24 | POST junk body to API URL | 400, Body must be JSON | 400 returned, shown in red by PowerShell. Nothing written to HubSpot | Yes |
| 2026-10-24 | Live Tally submission, UTM B (Bola, Marketing Lead) | Created in HubSpot, score 60, UTMs filled | Bola Live created within seconds. fd_score 60, fd_utm_source linkedin, fd_utm_campaign oct-launch, fd_utm_content B. received and written lines in CloudWatch | Yes |
| 2026-10-24 | Same email again, title changed to Head of Marketing | Same contact updated, score 100, no duplicate | One Bola Live in HubSpot, score now 100. Log shows action "updated" | Yes |
| 2026-10-24 | D1: Unsigned POST from laptop after signature check deployed | 401, nothing written | 401 returned (red in PowerShell). No change in HubSpot. CloudWatch: step "signature", status "rejected" | Yes |
| 2026-10-24 | D2: Lambda console test event (no signature header) | Function succeeds but returns 401 | Green "succeeded" box, response statusCode 401, "Invalid signature" | Yes |
| 2026-10-24 | D3: Signed live Tally submission (Chioma, Founder, 5 people, UTM A) | Created in HubSpot, score 70 | Chioma Signed created. fd_score 70, UTMs filled. received and written lines in CloudWatch | Yes |
| 2026-10-24 | D4: Wrong secret in Lambda, then fixed | Rejected, then recovered by Tally's retry | Submission rejected (signature mismatch in logs), nothing in HubSpot. After restoring the secret, Tally's retry delivered it and the lead appeared | Yes |
| 2026-10-25 | Rule checks on good and broken captions | 11 of 11 | 11 of 11 | Yes |
| 2026-10-25 | Generator tests with fake model | 8 of 8 | 8 of 8 | Yes |
| 2026-10-25 | Fake run, onboarding-checklist brief | status checked | No maid up claims | Yes |
| 2026-10-25 | Fake run, results-promise (trap) brief | failed_checks, judge flags made-up claim | failed_check, flags made-up claim | Yes |
| 2026-10-25 | Upload good brief to S3 (fake model) | Draft saved, status checked | content/onboarding-checklist/draft.json created within seconds. status "checked", model "fake", prompt versions v1, judge 5/5/4 with no made-up claims. Logs show received then saved | Yes |
| 2026-10-25 | Upload trap brief to S3 (fake model) | Draft saved, failed_checks, made-up claim flagged | content/results-promise/draft.json created. status "failed_checks". Judge flagged "onboard clients 3x faster" on the blog and caption A | Yes |
| 2026-10-25 | Upload broken brief | Rejected in logs, nothing written | Logs: step "validate", status "rejected", reason "missing audience, offer, facts". Nothing created in content/ | Yes |
| 2026-10-25 | First real Nova run (onboarding-checklist) | Draft saved with model us.amazon.nova-2-lite-v1:0 | status checked | Yes |
| 2026-10-25 | WordPress formatting and link tests | 6 of 6 | 6 of 6 passed | Yes |
| 2026-10-25 | Local: checked record -> WordPress draft | Draft created and verified (status, title, link, category) | Draft created in the FlowDesk category. Script printed "Verified: it's a draft, with the right title, tracked link and category" | Yes |
| 2026-10-25 | Preview link opens Tally with UTMs | utm_source=blog, utm_campaign=onboarding-checklist, utm_content=blog | Clicked "Pick a time here" in preview. Tally opened with all three UTM values in the address bar | Yes |
| 2026-10-25 | Revoked application password | 401 from WordPress, then fixed with a new password | 401 after revoking. New application password created, WP_APP_PASSWORD updated, script worked again | Yes |
| 2026-10-25 | Nova, prompts v2 | Status checked | failed_checks. Questions and em dashes fixed. Only length failed: blog 160 words, captions 36 and 37 | No |
| 2026-10-25 | Nova, prompts v3 + repair loop, run 1 of 3 | Status checked | checked. Repairs and judge scores not recorded (record overwritten by later runs) | Yes |
| 2026-10-25 | Nova, prompts v3 + repair loop, run 2 of 3 | Status checked | checked. Repairs and judge scores not recorded (record overwritten by later runs) | Yes |
| 2026-10-25 | Nova, prompts v3 + repair loop, run 3 of 3 | Status checked | checked. Repairs: blog 1, captions 0. Judge: blog 5/5/5, caption A 5/5/5, caption B 5/5/5, no made-up claims | Yes |
| 2026-10-26 | Trap brief (results-promise), Nova, judge v1 | failed_checks, made-up claims flagged | failed_checks. Repairs: blog 1, captions 1. Judge flagged 4 promised results in the blog and 2 in caption B. Missed: invented features ("connect it to your CRM", "set it up in minutes"), the same claim in caption A (5/5/5), and the CTA not matching the trial offer | Partly |
| 2026-10-26 | Access requests, new generator | needs_review with review_notes | needs_review. review_notes listed 6 flagged sentences from the judge | Yes |
| 2026-10-26 | Publisher sends needs_review draft | WordPress draft with red review box | Draft created in the FlowDesk category with the red FLOWDESK REVIEW NOTES box at the top, listing each flagged sentence. Record moved to in_wordpress | Yes |
| 2026-10-26 | Published with the box still in | Run fails, record stays in_wordpress | Run failed: "published with the review notes box still in it. Edit the post and delete the box". Record stayed in_wordpress. Box was visible on the public page | Yes |
| 2026-10-26 | Box deleted, flags reviewed (2 kept / 2 rewritten / 1 deleted), published | Record published, live page verified, captions_ready | Run succeeded. Record moved to published, with the live URL, captions_ready (A and B with utm_content=A and B) and history showing in_wordpress then published. Live page has no box | Yes |
| 2026-10-26 | Onboarding post approved and published | Record published | Promised results edited out during review. Published. Record moved to published, live page verified | Yes |
| 2026-10-26 | Hourly schedule | Rule added, automatic run not yet confirmed | EventBridge rule flowdesk-publisher-hourly added (rate(1 hour)). Automatic run seen in CloudWatch logs | Pending |
| 2026-10-26 | SNS topic flowdesk-alerts, test message | Email arrives | Topic created in eu-north-1, email subscription confirmed. Test message "FlowDesk test alert" arrived in the inbox | Yes |
| 2026-10-26 | Errors alarms on lead-intake, content-generator and publisher | All three created, OK state |    | Yes |
| 2026-10-26 | Drill 1: wrong HUBSPOT_KEY on lead-intake | Alarm email, 401 in logs, lead recovered by Tally retry after fix, OK email |    | Yes |
| 2026-10-26 | Credential check, all healthy | 3 checked, 0 problems, no email | 3 checked, 0 problems, no email | Pass |
| 2026-10-26 | Drill 2: revoked WordPress password | Email naming the WordPress password (401), then 0 problems after rotation |  |  |
| 2026-10-26 | Saved Logs Insights searches (errors 24h, errors by Lambda, received vs written, never written, no variant) | All run and return sensible results |  |  |
| 2026-10-26 | Drill 3: submission from the plain link (no UTMs) | No alarm. Lead in HubSpot with empty UTM fields. Caught by the "no variant" search |  |  |
| F1 | 2026-10-27 | `python -m scripts.run_all_tests` with the two new test files | All 9 test files pass, 103 checks | Pass |
| F2 | 2026-10-27 | Lambda Test tab, unsigned request | 401, log shows `step: signature, status: rejected`, nothing in `briefs/` | Pass |
| F3 | 2026-10-27 | Opened the brief form in a private window | Asks for the password before showing the form | Pass |
| F4 | 2026-10-27 | Submitted a real brief through the form | Logs show `received` then `saved ok`. New file in `briefs/` with `"source": "brief-form"` | Pass |
| F5 | 2026-10-27 | Waited for the generator | `content/<brief_id>/draft.json` within 2 minutes, real model, status `checked` or `needs_review` | Pass |
| F6 | 2026-10-27 | Ran the publisher | WordPress draft with the brief's topic | Pass |
| F7 | 2026-10-27 | Drill: renamed `BRIEF_FORM_SIGNING_SECRET`, submitted a brief, put the name back | Alarm email, then Tally's retry delivers the brief within about 5 minutes, then OK email | Pass |