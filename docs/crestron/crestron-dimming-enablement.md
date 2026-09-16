# Why most lights do not dim on a press-and-hold

Most of the house's lighting loads sit on Crestron dimmer modules, yet holding their keypad or
touch panel button does nothing. A few loads, notably the Kitchen Island and the Living Room
pathway, cycle dim to bright to dim exactly the way a dimmer-controlled light should. Pde
confirmed the split with a multimeter: the loads that dim show a changing voltage, and the loads
that do not sit steady at 117 to 120 volts.

This document answers why, and where the behavior is decided.

**The answer is that press-and-hold dimming is a per-button setting in the D3 Pro project that
generated the MC2E's program.** It is chosen button by button, so two buttons driving the same
dimmer channel can behave differently. The AADS plays no part in it.

Everything below was established by static analysis of the program dumps already committed under
[dumps/](dumps) plus Crestron's own published documentation. No light was turned on, no join was
written, and no live command was sent, per the constraint pde set when he asked the question.

## The dimmer hardware has no concept of a button, a hold, or a ramp

A CLX module's entire control interface is a level per channel. Crestron's device library
documentation for the [CLX dimming modules](https://help.crestron.com/cds/symbols/Device_Library/Lighting/CLX_Dimming_Modules.htm)
gives each channel an analog input, `dim1` through `dim8`, described as "Sets the light level of
the corresponding controlled circuit", alongside per-channel override inputs and a per-channel
`curve_type` parameter. There is no Raise input, no Lower input, and no ramp input of any kind.
The same page says the dimming inputs "should be driven by symbols that generate smoothly varying
outputs, such as the Analog Ramp or Analog Preset, and not by symbols that generate discrete
values."

The live capture recorded in [cresnet-frame-decode.md](cresnet-frame-decode.md) shows the same
thing from the wire side. Cresnet opcode `1D` carries a list of (channel, level) pairs, and the
observed levels span `1C` at roughly 11 percent, `C3` at roughly 76 percent, and `FF` at full. The
MC2E computes the level and sends it; the module obeys.

A fade is therefore the MC2E sending a stream of levels. If the program does not generate that
stream, no amount of holding a button will produce one, and the load will sit at whatever discrete
level its last command set. A load parked at `FF` is a load reading 117 to 120 volts on a meter.

## The MC2E program is D3 Pro output, and the behavior is a per-button model

The program header in [dumps/mc2e-gale-favela-11-14-08.strings.txt](dumps/mc2e-gale-favela-11-14-08.strings.txt)
identifies the toolchain:

```
Programmer:   D3 Pro 2.8.29
Compiled On:  8/23/2011 3:07 PM
Source File:  C:\ASI\Client Folders\Favela\Crestron\D3Pro\Gale Favela 11-14-08\...
```

D3 Pro is Crestron's lighting-specific configurator rather than a general SIMPL editor. The
installer defines loads, keypads, buttons and scenes in a GUI, and D3 Pro generates the SIMPL
logic. Every button gets a *button model*, and that model decides what a tap does and what a
press-and-hold does.

The [release notes for D3 Pro v2.8.29](https://www.crestron.com/release_notes/d3-pro_2.08.029.00_release_notes.pdf),
the exact build that compiled this program, name the models in use across its revision history:
`Toggle`, `Toggle + Dim`, `Single Press`, `Single Press + Dim`, `Timeout`, `Master Raise` and
`Master Lower`, `Tap and DblTap`, and `Tap, Hold, and DblTap`.

Only the `+ Dim` variants ramp on a hold. The release notes call the behavior "cycle dim", which is
precisely the dim to bright to dim cycling pde observes:

> Fixed bug introduced in v2.1.0 where the "cycle dim" action of the Toggle+Dim and Single
> Press+Dim button models was broken.

The hold threshold is a project-wide setting rather than a per-button one, but it only applies to
buttons that have a hold action at all:

> Use the Global Tap/Hold time for the holding-time value for both SinglePress+Dim and Toggle+Dim
> button models. The old holding-time is fixed 0.5 sec.

A button left on plain `Toggle` or `Single Press` has no hold action whatsoever. That is the
explicit enablement the question was about, and it is per button. It is not per system, not per
room, and not per load.

D3 Pro also treats dimmability as a property of the load itself, separately from the button. The
release notes describe the programming dialog refusing to mix kinds in one step: "You also cannot
select dimmable and non-dimmable loads together."

## The program dump corroborates that the tap-versus-hold split is in generated logic

The only named signals in the entire compiled MC2E program are 243 `pressN` digital inputs and 9
`Backlight_Enabled_fb` outputs:

| Interface | Count | Press signals each | Total |
|---|---:|---:|---:|
| CNX-B8 wall keypads | 9 | 8 | 72 |
| EISC virtual keypads (Dining, Living, Kitchen, Master Suite, Entry, Patio, Modes, Others) | 8 | 12 | 96 |
| `101-Kitchen, XPanel` | 1 | 75 | 75 |

There is one bare press signal per button, and no `hold`, `tap`, `dbl`, `raise`, `lower` or `dim`
signal name appears anywhere in the dump. The CNX-B8 predates the keypads that emit built-in Tap,
DblTap and Hold events, which the release notes describe D3 Pro adopting for "most new keypads", so
D3 Pro must time the hold itself inside generated logic, per button.

The limit of this evidence matters. The compiled dump preserves only those names; all feedback
signals and all internal logic are unnamed. So this establishes that the input side of every button
is a single undifferentiated press, and it does not and cannot establish which buttons carry which
model. The compiled program will not answer that question.

## The AADS is not involved

Its device list in [dumps/aads-favela-v4.dsc.txt](dumps/aads-favela-v4.dsc.txt) is an ST-IO, two
stale `CHV-TSTAT` definitions, the EISC to the MC2E, four TSW-752 panels, two Crestron App slots,
and a CEN-IDOC. No keypads and no CLX modules. It forwards panel joins to the MC2E over the EISC
and nothing more.

The TSW-752 project at [dumps/tsw752-favela-v3-environment.xml](dumps/tsw752-favela-v3-environment.xml)
also contains no raise, lower, ramp or dim control of any kind, so the panels never offered a
dimming affordance in their own right. Any ramp a panel button produces is generated on the MC2E
side of the EISC.

There is consequently nothing to enable on the AADS. This corrects an assumption worth naming
explicitly, because "the panels drive the lights" is an easy reading of the control path and it
points at the wrong processor.

## Three independent reasons a load will not dim

These are indistinguishable at the fixture. All three produce a steady 117 to 120 volts.

| Cause | Where it lives | Scope |
|---|---|---|
| Button model is `Toggle` or `Single Press` rather than a `+ Dim` variant | D3 Pro project, per button | The only cause that plausibly explains most of the house |
| Channel `curve_type` set to a non-dim curve | D3 Pro project, per channel | Any channel on a dimmer module |
| Load is on the CLX-4HSW4 at Cresnet `0x74` | Physical hardware | Four channels only |

On the second cause, Crestron's device library page describes a non-dim curve as one where "a value
of 0% is Off, and anything greater than 0% is On". D3 Pro offers Dim and Non-Dim variants of every
load type it supports, and the [CLX-1DIM8 spec sheet](https://www.crestron.com/getmedia/4b579869-a6d7-436f-a0ed-f86ac140d08b/ss_clx-1dim8_1)
lists those types as incandescent, magnetic low voltage, neon or cold cathode, and dimmable 2-wire
fluorescent. A channel configured non-dim will snap between off and full regardless of what the
program sends it.

On the third, `0x74` is the house's single CLX-4HSW4, a four-channel high-inrush switching module
with no dimming capability at all. House Perimeter is the one load known to sit on it, as recorded
in [crestron-ha-bridge.md](crestron-ha-bridge.md). Four channels cannot account for a
whole-house pattern.

## Holding a scene button saves the scene rather than dimming it

Many of the buttons in this house are scene buttons, and the program marks them "(Learnable)". The
strings dump lists A-Welcome, B-Good Bye, C-House On, D-House Off, E-Good Morning, F-Good Night and
H-Entertain, plus the five Patio scenes (Night, Club, Pool Party, Fiesta, Path), all carrying that
suffix. G-Security is the only one of the eight lettered house scenes that does not.

D3 Pro's release notes describe what learnable means:

> Buttons can now be marked for "Learnable Lighting" (user can store new lighting levels by holding
> button for 5s)

So on a learnable button, a five second hold overwrites the scene with the current levels. Holding
one will never dim, by design, and it can silently destroy a scene. This is worth knowing before
experimenting with press-and-hold across the house to find out which buttons ramp.

That G-Security alone is not learnable is a small data point for
[issue #19](https://github.com/pdehlke/homeassistant/issues/19), which is stalled on the Modes
page's four scene buttons producing no visible effect. It is not an explanation on its own.

## What this means for the Phase 2 brightness pass

The brightness picture differs between the two links, and an earlier reading of it as uniformly
absent was wrong.

On the AADS link, [crestron-ha-bridge.md](crestron-ha-bridge.md) records that the panel slot
carries no per-load analog level join, so the bridge cannot command or read a level for any of its
twenty-six loads.

On the MC2E link it is better than that. [crestron-xpanel-control-path.md](crestron-xpanel-control-path.md)
records two analog joins carrying real levels, `a21` for the channel shared with Living Pathway and
`a22` for Island, each the 8-bit dimmer level scaled to 16 bits and directly usable as a Home
Assistant brightness value. The same document's Kitchen join map already lists dedicated raise and
lower digital joins: 22 and 23 for `0x71` ch3, and 27, 28 and 29 for `0x72` ch2 as raise, lower and
off.

Read against the D3 Pro finding, those joins are what a raise button and a lower button look like
from outside. That is a direct, if partial, answer to the question
[crestron-xpanel-control-path.md](crestron-xpanel-control-path.md#kitchen-identification-resolved-2026-09-03)
left open, namely whether a brief tap of join 27 recalls a fixed preset level or whether the level
reached is proportional to how long 27 is held. A D3 Pro raise button ramps for as long as it is
held, which favors the second reading. It is not proof, because the model assigned to that specific
button is not recoverable from the compiled program, and the single live sample recorded there is
consistent with either theory.

The practical consequence is that Home Assistant brightness control may be reachable on some loads
with no Crestron reprogramming at all. The bridge currently pulses joins. Holding a raise or lower
join high, or holding a join whose button carries a `+ Dim` model, should ramp for the duration of
the hold. Island and the Living Room pathway are the obvious first candidates. The model is set per
button, so the XPanel button the bridge presses may not share the behavior of the physical keypad
button pde holds, and each join needs testing on its own.

## Settling which buttons and which channels

The compiled program cannot answer it, so there are two routes.

The clean one is the D3 Pro project file from ASI, the original integrator. It shows every button's
model and every load's type directly, with no inference. That retrieval is already an open action
in [crestron-xsig-programmer-scope.md](crestron-xsig-programmer-scope.md), which also records that
D3 Pro reached [end of feature life](https://www.crestron.com/News/Blog/January-2025/Transitioning-D3-Pro-Software-to-Crestron-Home),
so obtaining the tool as well as the file is part of that task.

The other is observation, and it distinguishes the first two causes from each other. During a
press-and-hold, a Cresnet capture that shows `1D` frames streaming with changing level bytes means
the button does carry a ramping model and the channel's curve is the remaining suspect. No stream
at all means the button model is the cause. This needs the Cresnet tap physically connected, it
means pressing buttons and changing lights, and so it needs pde at the machine and his go-ahead
first.

A cheaper variant runs over the existing CIP bridge rather than the tap: hold one of the MC2E
XPanel's known raise joins high and watch `a21` or `a22` move. That reads the level directly from
the processor with no bus tap involved. It still turns a light on, so it carries the same
precondition.

## Sources

- [CLX Dimming Modules](https://help.crestron.com/cds/symbols/Device_Library/Lighting/CLX_Dimming_Modules.htm),
  Crestron device library, for the per-channel analog inputs, the absence of ramp inputs, and the
  non-dim curve type.
- [D3 Pro v2.8.29 release notes](https://www.crestron.com/release_notes/d3-pro_2.08.029.00_release_notes.pdf),
  the exact build that compiled this program, for the button model names, "cycle dim", the global
  tap/hold time, and learnable lighting's five second save.
- [CLX-1DIM8 spec sheet](https://www.crestron.com/getmedia/4b579869-a6d7-436f-a0ed-f86ac140d08b/ss_clx-1dim8_1),
  for the supported load types.
- [D3 Pro Reference Guide](https://www.crestron.com/getmedia/e9c54f3f-3363-4831-8bf6-a3f22ecfd94c/mg_d3pro_1),
  retrieved and checked but not usable as a citation here: it is a scanned document with no text
  layer.
