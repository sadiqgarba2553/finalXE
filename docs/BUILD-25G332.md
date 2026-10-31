# 25G332 source snapshot

The inherited source README and some historical manifests describe the earlier
25G241 / GPU 1.0.12 development state. The current source overlay/build.py is
GPU **1.0.13**, explicitly guarded for **25G332**. The native Wi-Fi overlay is
the 0.1.4 build used by HP-DAILY/HP-FIX. Root README and manifest/ describe
this captured deployment; historical docs are retained for provenance.

From `source/`, run tools/prepare-build.py and drivers/graphics/build.py.
Preparation fetches pinned source/dependencies and applies the overlays. The
output is drivers/graphics/build-v1.0.13/NootedGreenHP.kext. This does not install
the system-side graphics runtime. The historical-build-and-install.py and
historical-install-port.py record that local integration procedure, including
the separate native donor revision, HookCase and HP POSH linkage. They refer
to the original USB kit and are reference recipes, not portable one-click installers.
Do not run them unchanged on someone else's machine.

The original full native donor checkout is pinned to
sgiammori/NootedGreen 95f81898be65cb9f7b3d370ca78054be4cc8a62d.
Apple binaries and caches are not included. A successful source compilation
alone is not a complete graphics stack or hardware qualification.

The isolated brightness experiment is optional and separate. Its only functional
change registers the existing panel hook with -ngreenhpbacklight; physical
testing is pending. Do not replace the baseline or claim brightness is fixed.
