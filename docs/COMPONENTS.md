# Component sources

Exact installed versions/order/hashes are in manifest/kexts.json. These are
upstream acquisition locations, not a request to install their newest releases.

| Components | Source |
| --- | --- |
| OpenCore 1.0.8, OpenRuntime, OpenHfsPlus | https://github.com/acidanthera/OpenCorePkg |
| Lilu | https://github.com/acidanthera/Lilu |
| NootedGreenHP + HP POSH adapter | source/drivers/graphics; https://github.com/davghz/hackintosh; https://github.com/JulioNectar/Hackintosh-XPS13Plus-IrisXe-Tahoe; https://github.com/sgiammori/NootedGreen |
| AirportItlwmHP / itlwm | source/drivers/wifi; https://github.com/laobamac/itlwm |
| IntelBluetoothFirmware, IntelBTPatcher | https://github.com/OpenIntelWireless/IntelBluetoothFirmware |
| BlueToolFixup | https://github.com/acidanthera/BrcmPatchRAM |
| AppleALC | https://github.com/acidanthera/AppleALC |
| SimpleHDA | https://github.com/laobamac/SimpleHDA |
| BrightnessKeys | third-party/BrightnessKeys; https://github.com/acidanthera/BrightnessKeys |
| VirtualSMC, SMCBatteryManager | https://github.com/acidanthera/VirtualSMC |
| NVMeFix | https://github.com/acidanthera/NVMeFix |
| RestrictEvents | https://github.com/acidanthera/RestrictEvents |
| VoodooPS2Controller | https://github.com/acidanthera/VoodooPS2 |
| VoodooI2C, VoodooI2CHID | https://github.com/VoodooI2C/VoodooI2C |
| HookCase | pinned XPS dependency/build-hookcase.sh; retain upstream MIT notices |

AMFIPass, WhateverXe and itlwm are present but disabled in this snapshot.
No CirrusAudioFixup driver is installed in HP-FIX. Sound has been reported
working without adding it; do not enable an unrelated board's amplifier profile.

AppleALC's original universal binary failed current codesign on its i386 object
slice. The local preparation thinned the staging copy to x86_64 and then signed
and strictly verified it. The public acquisition archive hash and installed
binary hash therefore differ intentionally; see source/historical-install-fix.py.
