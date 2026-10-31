# Use and adaptation

The `profiles/hp-fix/config.example.plist` is a sanitized HP-FIX snapshot,
not the older generic config in the inherited source tree. Active audio entries
are Lilu -> AppleALC -> SimpleHDA; the layout is 13, which produced a visible
ALC245 built-in output on this machine. User-confirmed sound does not establish
all endpoints, amplifier cold-boot initialization or microphone operation.

This EFI depends on system-installed Apple TGL graphics bundles, HookCase,
the patched Metal driver and HP POSH adapter, plus matching caches. Compare
`manifest/system-runtime.json`; copying a kext alone is insufficient.
Do not mix this stack with WhateverXe enabled alongside NootedGreenHP.

The reference retains the current machine's boot arguments and security settings
so the configuration can be reviewed accurately. `amfi_get_out_of_my_way=1`
and a nonzero `csr-active-config` reduce macOS protections; they are part of this
experimental setup, not recommended general settings. No security change is
performed by the exporter. The build is guarded for 25G332.

Build or obtain the listed third-party dependencies under their own terms. Obtain
Apple components independently; no Apple driver payload is mirrored here.
Generate a unique matching SMBIOS identity with the normal OpenCore workflow;
never reuse another person's serial/MLB/UUID/ROM. The copied config has these
fields cleared and must be completed locally before booting.

Use ACPI/USB mapping collected and validated on your own board/BIOS. Raw patched
DSDTs from the original machine are intentionally local-only; filenames/hashes
are recorded for comparison. Inherited ACPI source is in source/tools/installer/acpi.

Validate a completed config with OpenCore 1.0.8 ocvalidate, check every enabled
kext/plist/executable and ACPI path, then test a separate USB. A boot USB also needs
the matching EFI/BOOT/BOOTx64.efi; the profile itself contains OpenCore.efi.
Record boot, rendering, sound endpoints, USB, brightness and sleep results
separately. Hardware support must not be inferred from an attached driver alone.
