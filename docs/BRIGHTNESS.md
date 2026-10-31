# Brightness verification — 2026-10-31

Hardware: HP Envy x360 15-fe0xxx, 103C:8BDF, i7-1355U, Iris Xe A7A1 rev04.
System: macOS 26.7.2 / 25G332, OpenCore 1.0.8.

The owner booted HP-BRIGHT and confirmed brightness works. Live NVRAM contains
`-ngreenhpbacklight`. AppleBacklightDisplay now publishes both `brightness`
(range 0–1024) and `linear-brightness` (0–65403), alongside existing backlight
parameters. Previously the normal brightness controls were absent.

The NootedGreenHP 1.0.14 source registers its existing upstream AppleBacklight
callback only with this opt-in argument. That makes the existing
AppleIntelPanel::setDisplay route and panel-data patch reachable. No new PWM
constants, Dell-specific brightness values or 3 GB VRAM change were added.
All original board, GPU and kernel guards remain.

The source and sanitized config are included. This result is limited to the
original machine; full brightness range, individual hotkeys and sleep/wake are
not independently qualified. HP-FIX remains the earlier fallback profile.
