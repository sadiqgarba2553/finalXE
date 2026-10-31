#include "../overlay/kern_hp8bdf.hpp"
#include <cassert>
#include <cstdio>
#include <cstring>

int main() {
    using namespace HP8BDF;
    assert(kernelMatches(KernelVersion, sizeof(KernelVersion), KernelUUID, sizeof(KernelUUID)));
    assert(!kernelMatches(nullptr, sizeof(KernelVersion), KernelUUID, sizeof(KernelUUID)));
    for (size_t n = 0; n < sizeof(KernelVersion); ++n)
        assert(!kernelMatches(KernelVersion, n, KernelUUID, sizeof(KernelUUID)));
    for (size_t n = 0; n < sizeof(KernelUUID); ++n)
        assert(!kernelMatches(KernelVersion, sizeof(KernelVersion), KernelUUID, n));
    char version[sizeof(KernelVersion)], uuid[sizeof(KernelUUID)];
    memcpy(version, KernelVersion, sizeof(version));
    memcpy(uuid, KernelUUID, sizeof(uuid));
    for (size_t i = 0; i < sizeof(version); ++i) {
        version[i] ^= 1;
        assert(!kernelMatches(version, sizeof(version), uuid, sizeof(uuid)));
        version[i] ^= 1;
    }
    for (size_t i = 0; i < sizeof(uuid); ++i) {
        uuid[i] ^= 1;
        assert(!kernelMatches(version, sizeof(version), uuid, sizeof(uuid)));
        uuid[i] ^= 1;
    }
    const char original[] = "1291D44A-C0CD-3AC7-A9E4-CA2749B33959";
    assert(!kernelMatches(version, sizeof(version), original, sizeof(original)));
    puts("PASS: exact 25G332 identity, truncated fields, byte mutations, NUL mutations and the old kernel rejected.");
}
