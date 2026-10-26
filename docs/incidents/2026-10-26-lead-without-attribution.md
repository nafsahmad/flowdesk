# Incident: lead saved with no attribution (drill)

**Date:** 2026-10-26
**Type:** Planned drill, simulating a shared link with the tracking stripped off

**What I noticed, and how:** Nothing alerted. No error, no alarm, and the Lambda reported success. I found it with the saved search "FlowDesk leads with no variant (7d)".

**Impact:** One lead (silent.drill@example.com) in HubSpot with no source, campaign or variant. In real life, that lead's cost and the A/B test result would be wrong, and nobody would know why.

**Where I looked:** HubSpot showed the contact with empty fd_utm fields. The lead-intake log line for the submission showed variant "none".

**Cause:** The form was opened from a link without UTM parameters, so the hidden fields stayed empty.

**Fix:** Nothing to fix in the code. This is a data quality problem, not a crash. The lead was kept on purpose (a lead without attribution is still a lead).

**How I verified:** Search 4 lists the lead. HubSpot shows the empty fields.

**How to stop it happening again:**
- Run "FlowDesk leads with no variant" in the weekly review.
- Stage 6's weekly report will flag any lead with no variant, so it can't hide in the totals.
- Always share tracked links, never the plain form link.
- Lesson: alarms only catch crashes. Data problems need their own checks.