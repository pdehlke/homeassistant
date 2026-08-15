# Alarm/Apex integration does not go through Cresnet sniffing

Even though Cresnet bus-tapping is the chosen eventual path for lighting (Path B), the same
technique doesn't apply to the alarm system: Apex traffic runs over RS-232 between the AADS and
the Apex panel, and TSW-752 traffic runs over Ethernet to the AADS — neither touches the Cresnet
bus at all. Any alarm reverse-engineering has to observe the TSW-752-to-AADS Ethernet link and the
AADS-to-Apex RS-232 link instead. See `docs/crestron/crestron-apex-control-plane.md`.
