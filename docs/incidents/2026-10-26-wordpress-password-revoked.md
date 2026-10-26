# Incident: WordPress application password revoked (drill)

**Date:** 2026-10-26
**Type:** Planned drill, simulating an expired or revoked credential

**What I noticed, and how:** The credential check emailed "FlowDesk credential check: 1 problem(s)" naming the WordPress password used by flowdesk-publisher, rejected with a 401.

**Impact:** None. The problem was caught by the scheduled check before the publisher needed WordPress. Without the check, the next draft would have failed to reach WordPress, and the publisher alarm would have fired then.

**Where I looked:** The email said which key and which Lambda. The credential check's logs confirmed HubSpot and Bedrock were fine and only WordPress failed.

**Cause:** The flowdesk-publisher-lambda application password was revoked (on purpose).

**Fix:** Created a new application password and updated WP_APP_PASSWORD on flowdesk-publisher.

**How I verified the fix:** Ran the credential check again: 3 checked, 0 problems.

**How to stop it happening again:**
- The daily check catches dead keys before real work hits them.
- Rotation dates are in the credentials table.
- Each place has its own key, so revoking one broke nothing else.