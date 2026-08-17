# CP3N is mandatory if the MC2E fails any suitability test

The MC2E is retained as the lighting/XSIG processor only if it passes all seven documented
suitability conditions (available editable source, a reproducible compile, a free bidirectional
COM port for Apex, sufficient memory/signal/Ethernet headroom, a stable XSIG connection under
load, healthy existing Cresnet operation, and a programmer willing to support the modified
source). If any condition fails, the programmer must quote and implement the same interface on a
used CP3N instead, migrating the complete MC2E program rather than working around the gap. See
[docs/crestron/crestron-xsig-programmer-scope.md](../crestron/crestron-xsig-programmer-scope.md).
