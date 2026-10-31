# HP-BRIGHT: untested physical brightness trial

This changes only the NootedGreenHP kext (version 1.0.14) and adds
`-ngreenhpbacklight`. The existing upstream AppleIntelPanel::setDisplay hook
is registered only when this argument is present. Existing build, GPU and board
guards remain. HP-FIX is the baseline; do not claim this fixes brightness yet.

Apply these two files over a copy of `source/`, run its prepare/build commands,
and use the hp-bright-trial config on a separate bootable USB profile.
Build, ad-hoc signature and OpenCore config checks passed on 2026-10-31.
Physical brightness response, panel range and sleep/wake are unverified.
No arbitrary PWM register values or Dell-specific brightness values were added.
The graphics upstream license and notices apply to this derivative.
