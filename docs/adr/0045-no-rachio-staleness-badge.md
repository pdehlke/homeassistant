# No standalone "as of HH:MM" staleness badge for Rachio

A general staleness indicator for Rachio data was considered and rejected, not because it's
unneeded but because the periodic config-entry reload already provides the same safety property for
free: every Rachio entity gets refreshed at worst once per reload cycle regardless of whether the
webhook is working, since a config-entry reload re-fetches everything, not just the zone list. The
reload cadence is treated as the staleness bound itself; a separate badge showing it explicitly
would be redundant. See `docs/rachio/rachio-webhook-responsiveness-plan.md`.
