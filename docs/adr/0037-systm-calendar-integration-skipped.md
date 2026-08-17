# SYSTM workout calendar integration skipped entirely

Wahoo's SYSTM has no built-in calendar export for planned workouts, and its Authorized Apps
integrations only push completed sessions after the fact. Unofficial routes exist (a
reverse-engineered GraphQL client, a credential-based scraper) that could pull the planned
calendar into Google Calendar via intervals.icu, but both were rejected: Wahoo's API Agreement
explicitly prohibits reverse engineering its platform, and the whole chain is a lot of fragile,
small-project infrastructure to build on a ToS violation. If specific planned sessions are wanted
on Overview C, the lowest-effort ToS-clean path is logging them onto a Google Calendar by hand.
See [docs/homie-dashboard/overview-c-calendar-google-sync.md](../homie-dashboard/overview-c-calendar-google-sync.md).
