// 25G332 port: qualify native cursor bodies across kernel-cache branch relocations.
#pragma once
#include <stddef.h>
#include <stdint.h>

namespace HPCursorCalls {
enum Target { Lock, TryLock, Unlock, Sleep, CompareSwap, Zero, TargetCount };
struct Call { size_t offset; Target target; }; // offset points at the rel32 operand
constexpr Call Image[] = {{0x167, Lock}, {0x1d8, Unlock}, {0x3fe, Zero}, {0x4b5, CompareSwap}};
constexpr Call State[] = {{0x404, Lock}, {0x473, Unlock}, {0x491, CompareSwap},
    {0x582, TryLock}, {0x590, Sleep}, {0x5e9, Unlock}, {0x9b2, Lock},
    {0xa1b, Unlock}, {0xa39, CompareSwap}, {0xa8c, CompareSwap}, {0xb24, Unlock}};
constexpr const char *Names[] = {"_IORecursiveLockLock", "_IORecursiveLockTryLock",
    "_IORecursiveLockUnlock", "_IOSleep", "_OSCompareAndSwap", "_bzero"};

inline uint32_t u32(const uint8_t *p) {
    return uint32_t(p[0]) | (uint32_t(p[1]) << 8) | (uint32_t(p[2]) << 16) | (uint32_t(p[3]) << 24);
}
inline bool relative(uint64_t next, int32_t delta, uint64_t &out) {
    const uint64_t magnitude = delta < 0 ? uint64_t(-int64_t(delta)) : uint64_t(delta);
    if ((delta < 0 && next < magnitude) || (delta >= 0 && next > UINT64_MAX - magnitude)) return false;
    out = delta < 0 ? next - magnitude : next + magnitude;
    return true;
}

// Read must refuse unmapped memory. Accept only a direct resolved call or an
// x86_64 kernel-cache FF25 RIP-relative import thunk whose pointer equals it.
template<size_t N, size_t C, typename Read>
bool match(const uint8_t *actual, size_t available, uint64_t base,
           const uint8_t (&expected)[N], const Call (&calls)[C],
           const uint64_t (&targets)[TargetCount], Read read) {
    if (!actual || available < N || base > UINT64_MAX - N) return false;
    for (size_t i = 0; i < N; ++i) {
        bool operand = false;
        for (const auto &call : calls) {
            if (!call.offset || call.offset > N || 4 > N - call.offset ||
                call.target >= TargetCount || expected[call.offset - 1] != 0xe8) return false;
            if (i >= call.offset && i - call.offset < 4) operand = true;
        }
        if (!operand && actual[i] != expected[i]) return false;
    }
    for (const auto &call : calls) {
        const uint64_t wanted = targets[call.target];
        uint64_t destination = 0;
        if (!wanted || !relative(base + call.offset + 4, int32_t(u32(actual + call.offset)), destination)) return false;
        if (destination == wanted) continue;
        uint8_t thunk[6] {};
        if (!read(destination, sizeof(thunk), thunk) || thunk[0] != 0xff || thunk[1] != 0x25 || destination > UINT64_MAX - 6) return false;
        uint64_t slot = 0;
        if (!relative(destination + 6, int32_t(u32(thunk + 2)), slot)) return false;
        uint8_t pointer[8] {};
        if (!read(slot, sizeof(pointer), pointer)) return false;
        uint64_t resolved = 0;
        for (size_t i = 0; i < 8; ++i) resolved |= uint64_t(pointer[i]) << (8 * i);
        if (resolved != wanted) return false;
    }
    return true;
}
}
