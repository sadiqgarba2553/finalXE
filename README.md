# finalXE

Experimental Intel Iris Xe / macOS Tahoe configuration and driver source for
**HP Envy x360 15-fe0xxx, board 103C:8BDF, Intel Core i7-1355U, 16 GB RAM**.
Captured on **macOS 26.7.2, build 25G332**, OpenCore **1.0.8**.

This is a snapshot of one working machine, not universal Iris Xe support.
The physical GPU is **8086:A7A1 rev 04**, spoofed as 9A49 by this configuration.
Exact GPU, board, kernel and binary guards are intentional. Do not disable them
to make another machine load the driver.

## Current status

| Component | Status |
| --- | --- |
| Graphics / Metal | Experimental NootedGreenHP 1.0.14 + matching system runtime; Metal clients observed, earlier bounded render/compute checks; no universal performance claim |
| Sound | User reports sound works after HP-FIX boot; ALC245 codec (10EC:0245) and built-in output observed; speaker/headphone/microphone coverage not individually qualified |
| Native Intel AX211 Wi-Fi | Working baseline uses AirportItlwmHP 0.1.4 |
| Keyboard / trackpad / battery | Existing baseline configuration included; comprehensive testing pending |
| Brightness | Working on the original HP after HP-BRIGHT 1.0.14 boot; user confirmed 2026-10-31; panel brightness properties observed |
| Bluetooth / USB map | Drivers and board-specific USB map configured; pairing and every port not yet qualified |
| Sleep / wake | Unresolved; do not assume reliable system sleep |
| 3 GB graphics memory | No 3 GB reservation or cosmetic VRAM change applied; integrated GPU shares RAM |

## What is included

- Sanitized exact HP-FIX and separate HP-BRIGHT OpenCore configs.
- Driver versions, enabled order, kernel limits and SHA-256 inventories.
- Corresponding HP graphics, native Wi-Fi and other project source, pinned build
  dependencies, retained upstream licenses and build tools under `source/`.
- BrightnessKeys source and its license; the board-specific codeless USB map.
- A guarded local exporter and checksum verifier under `tools/`.
- Runtime inventory showing why copying EFI alone does not install this stack.

**This repository is not a complete bootable EFI or a macOS installer.**
Apple graphics/AppleHDA binaries, kernel collections, raw DSDT/firmware dumps,
serials, MLB, SystemUUID, ROM/MAC addresses, network reports and credentials
are not published. Acquire required third-party/Apple components from their
appropriate sources and review their terms. Existing local installations can
make a complete sanitized backup with the exporter below.

## Start here

1. Read [installation and adaptation](docs/INSTALL.md) and [component sources](docs/COMPONENTS.md).
2. Compare your actual hardware and macOS build. These tables and USB map are
   specific to HP 8BDF; another Iris Xe laptop needs its own ACPI, USB mapping,
   audio routing, panel and hardware qualification.
3. Use [source build instructions](source/docs/BUILD.md), with the
   [25G332 snapshot notes](docs/BUILD-25G332.md). Graphics source is a derivative
   of davghz, JulioNectar and sgiammori/NootedGreen work, not entirely original.
4. Generate your own SMBIOS identifiers before use. Reference configs deliberately
   have blank serial/MLB/UUID and a zero ROM value.
5. Test from a separate USB and keep a known-working boot profile.

For an existing installation matching this snapshot:

```sh
python3 tools/export-local.py --profile /Volumes/MACOS_BOOT/EFI/HP-BRIGHT --destination /path/to/local-backup
python3 tools/verify.py /path/to/local-backup
```

The exporter only copies to a new directory and sanitizes the copied config;
it does not modify the source EFI, system drivers, NVRAM or security settings.
Its local backup includes proprietary system runtime files for personal backup;
do not upload that backup or the raw diagnostics to GitHub.

## Attribution and licenses

Mixed licenses apply; there is no blanket MIT license for the drivers.
See [LICENSE](LICENSE), [component notices](THIRD_PARTY_NOTICES.md) and
[source provenance](source/licenses/README.md). The graphics license includes
noncommercial restrictions. This project offers no paid graphics downloads,
support or services. Apple/Intel/HP names identify hardware and software only.

## Brightness update — 2026-10-31

The owner confirmed physical brightness adjustment works after booting HP-BRIGHT.
The live display now exposes brightness and linear-brightness controls, which
were missing in HP-FIX. NootedGreenHP 1.0.14 opts into the existing upstream
AppleIntelPanel hook with `-ngreenhpbacklight`. PNLF and BrightnessKeys remain
configured. This confirms brightness on this machine; key combinations, full
panel range and sleep/wake have not been separately qualified.

`source/` now contains the 1.0.14 source; the profile remains at
`profiles/hp-bright-trial/` to preserve existing links. HP-FIX is retained as
the previous fallback. See [brightness verification](docs/BRIGHTNESS.md).
