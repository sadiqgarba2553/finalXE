// HP 8BDF/A7A1 bring-up policy. No IOKit dependency: tested on the host.
#pragma once
#include <stdint.h>
#include <stddef.h>

namespace HP8BDF {
// Measured running kernel and on-disk LC_UUID on this HP's captured 25G332 installation.
constexpr char KernelUUID[] = "28267FD5-3E1E-3686-8A1C-E73E2466FCFB";
constexpr char KernelVersion[] = "Darwin Kernel Version 25.6.0: Mon Oct 12 00:33:09 PDT 2026; root:xnu-12377.161.15.701.48~2/RELEASE_X86_64";
// Require the complete kernel strings, including their terminating NULs.
inline bool kernelMatches(const char *version, size_t versionBytes,
                          const char *uuid, size_t uuidBytes) {
    if (!version || !uuid || versionBytes < sizeof(KernelVersion) || uuidBytes < sizeof(KernelUUID)) return false;
    for (size_t i = 0; i < sizeof(KernelVersion); ++i) if (version[i] != KernelVersion[i]) return false;
    for (size_t i = 0; i < sizeof(KernelUUID); ++i) if (uuid[i] != KernelUUID[i]) return false;
    return true;
}
constexpr uint32_t MiB = 1024U * 1024U;
// Captured from i915_frequency_info on this exact board/revision.
constexpr uint32_t MaxGpuMHz = 1300;
constexpr uint32_t NominalGpuMHz = 300;

constexpr bool matches(uint16_t vendor, uint16_t device, uint16_t subsystemVendor,
                       uint16_t subsystemDevice, uint8_t revision) {
    return vendor == 0x8086 && device == 0xA7A1 && subsystemVendor == 0x103C &&
           subsystemDevice == 0x8BDF && revision == 0x04;
}

// GGC[15:8]. The 0xF0..0xFE encoding is 4..60 MiB, not gms * 32 MiB.
// Source reference: WhateverXe kern_dvmt.cpp and its Intel datasheet reference.
constexpr uint32_t stolenBytes(uint8_t gms) {
    return gms <= 0x10 ? uint32_t(gms) * 32U * MiB :
           (gms == 0x20 || gms == 0x30 || gms == 0x40) ? uint32_t(gms) * 32U * MiB :
           (gms >= 0xF0 && gms <= 0xFE) ? uint32_t((gms & 15) + 1) * 4U * MiB : 0;
}

// Bound the reference driver's optional floor to this device's observed RP0.
constexpr uint32_t floorMHz(int requested) {
    return requested <= 0 ? 0 : uint32_t(requested) > MaxGpuMHz ? MaxGpuMHz : uint32_t(requested);
}
constexpr uint32_t limitFrequencyRequest(uint32_t request, int floor) {
    const uint32_t shift = (request & 15U) ? 14 : 23;
    const uint32_t mask = 0x1FFU << shift;
    uint32_t ratio = (request >> shift) & 0x1FFU;
    const uint32_t low = floorMHz(floor) * 3U / 50U;
    const uint32_t high = MaxGpuMHz * 3U / 50U;
    if (ratio < low) ratio = low;
    if (ratio > high) ratio = high;
    return (request & ~mask) | (ratio << shift);
}
}
