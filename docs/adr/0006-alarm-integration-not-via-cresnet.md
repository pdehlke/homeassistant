# Alarm integration does not go through Cresnet sniffing

Even though Cresnet bus-tapping is the chosen eventual path for lighting (Path B), the same
technique doesn't apply to the alarm system: alarm traffic runs over RS-232 between the AADS and
the DSC PC1864 panel, and TSW-752 traffic runs over Ethernet to the AADS — neither touches the
Cresnet bus at all. Any alarm reverse-engineering has to observe the TSW-752-to-AADS Ethernet link
and the AADS-to-panel RS-232 link instead. See
[docs/crestron/crestron-alarm-integration-paths.md](../crestron/crestron-alarm-integration-paths.md)
(this ADR originally cited `crestron-apex-control-plane.md`, since superseded; the panel it named,
"Apex," was a misidentification, but the RS-232-not-Cresnet reasoning here was always about the
transport, not the brand, and is unaffected).
