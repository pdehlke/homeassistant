# Keep the CLX-* lighting modules

The CLX-1DIM8 and CLX-4HSW4 modules stay in place rather than being replaced with a non-Cresnet
lighting system (Lutron Caseta/RA3, Z-Wave, etc.), which would eliminate the Cresnet bus
dependency entirely. A full rip-and-replace only makes sense if the CLX hardware itself becomes a
liability (failure, unavailable parts); while it's functioning, the cost of replacing working
hardware just to escape a bus protocol isn't justified. See [docs/crestron/crestron-strategy.md](../crestron/crestron-strategy.md).
