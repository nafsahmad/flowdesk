# Test Log

| Date | Test | Expected | Actual | Pass? |
|---|---|---|---|---|
| 2026-10-24 | Fetch all contacts, page size 3 | All contacts, 7 pages | All contacts fetched over 7 pages | Yes |
| 2026-10-24 | Misspelled property name in GET (`jobtitel`) | An error, because the property doesn't exist | Status 200, no error. Every title came back empty | Experiment |
| 2026-10-24 | Empty-property warning | Warning for `fd_score` (nothing scored yet) | Warning printed for `fd_score` only | Yes |