# Alarm user codes never leave the Crestron program

The Apex alarm system's user code lives only inside the Crestron program's nonvolatile
configuration — never on an XSIG join, in the signal schedule, in debug logs, or supplied to Home
Assistant. A dedicated automation credential is used instead of the household's normal keypad
code where the panel supports that separation. Disarm and other security-sensitive commands are
edge-triggered, not maintained signals, and must not be replayed automatically after a reconnect
or processor restart. See [docs/crestron/crestron-xsig-programmer-scope.md](../crestron/crestron-xsig-programmer-scope.md).
