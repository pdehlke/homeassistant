# Blueprint Studio installed but not used as the YAML-access workaround

Blueprint Studio (`ha-china/blueprint-studio`, HACS) is a genuine authenticated in-dashboard YAML
editor that would solve this instance's lack of file access to `configuration.yaml`. It wasn't
adopted for that purpose: unlike every other custom component here (card-mod/UIX, wall-clock-card,
kiosk-mode, sonos-card, music-flow), all of which are frontend-only, browser-side Lovelace code,
Blueprint Studio is a server-side integration with unsandboxed read/write access across the whole
`/config` directory — a different risk class, flagged to pde directly rather than used
unilaterally. See `docs/native-dashboards/native-dashboards-retired.md`.
