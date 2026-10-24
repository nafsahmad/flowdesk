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
| 2026-10-24 | Lambda console test with sample Tally event | 200, Lead updated, received and written logs |  200, Lead updated, received and written logs |  |
| 2026-10-24 | POST sample payload to API URL from laptop | 200, Lead updated | 200, message "Lead updated". Kemi updated in HubSpot | Yes |
| 2026-10-24 | POST junk body to API URL | 400, Body must be JSON | 400 returned, shown in red by PowerShell. Nothing written to HubSpot | Yes |
| 2026-10-24 | Live Tally submission, UTM B (Bola, Marketing Lead) | Created in HubSpot, score 60, UTMs filled | Bola Live created within seconds. fd_score 60, fd_utm_source linkedin, fd_utm_campaign oct-launch, fd_utm_content B. received and written lines in CloudWatch | Yes |
| 2026-10-24 | Same email again, title changed to Head of Marketing | Same contact updated, score 100, no duplicate | One Bola Live in HubSpot, score now 100. Log shows action "updated" | Yes |