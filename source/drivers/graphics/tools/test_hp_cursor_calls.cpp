#include "../overlay/kern_hp_cursor_calls.hpp"
#include "../overlay/kern_hp_linear_signatures.hpp"
#include <cassert>
#include <cstdio>
#include <cstring>
#include <map>
#include <vector>

using namespace HPCursorCalls;
static void put32(uint8_t *p, uint32_t v) { for (unsigned i=0;i<4;++i) p[i]=v>>(i*8); }

template<size_t N, size_t C>
static void verify(const uint8_t (&expected)[N], const Call (&calls)[C]) {
    const uint64_t base = 0xffffff7f90000000ULL;
    uint64_t targets[TargetCount] {};
    for (unsigned i=0;i<TargetCount;++i) targets[i]=base+0x100000+i*0x100;
    uint8_t code[N]; memcpy(code,expected,N);
    std::map<uint64_t,std::vector<uint8_t>> memory;
    auto read=[&](uint64_t at,size_t bytes,uint8_t *out) {
        auto i=memory.find(at);
        if(i==memory.end() || i->second.size()!=bytes)return false;
        memcpy(out,i->second.data(),bytes);return true;
    };
    for(const auto &call:calls)
        put32(code+call.offset,uint32_t(targets[call.target]-(base+call.offset+4)));
    assert(match(code,N,base,expected,calls,targets,read));
    assert(!match(code,N-1,base,expected,calls,targets,read));
    assert(!match(code,N,UINT64_MAX-N+1,expected,calls,targets,read));
    // Every unexpected instruction or operand mutation must be rejected.
    for(size_t i=0;i<N;++i) {
        code[i]^=1;
        assert(!match(code,N,base,expected,calls,targets,read));
        code[i]^=1;
    }
    // A legitimate linked import thunk is accepted only with the resolved target.
    for(const auto &call:calls) {
        const uint64_t thunk=base+0x200000+call.offset*32;
        const uint64_t slot=thunk+0x100;
        std::vector<uint8_t> jump(6),pointer(8);
        jump[0]=0xff;jump[1]=0x25;put32(jump.data()+2,uint32_t(slot-(thunk+6)));
        for(unsigned i=0;i<8;++i)pointer[i]=targets[call.target]>>(i*8);
        memory[thunk]=jump;memory[slot]=pointer;
        put32(code+call.offset,uint32_t(thunk-(base+call.offset+4)));
        assert(match(code,N,base,expected,calls,targets,read));
        memory[slot][0]^=1;assert(!match(code,N,base,expected,calls,targets,read));memory[slot][0]^=1;
        memory[thunk][1]=0x24;assert(!match(code,N,base,expected,calls,targets,read));memory[thunk][1]=0x25;
        memory.erase(slot);assert(!match(code,N,base,expected,calls,targets,read));memory[slot]=pointer;
        const uint64_t saved=targets[call.target];targets[call.target]=0;
        assert(!match(code,N,base,expected,calls,targets,read));targets[call.target]=saved;
    }
    assert(match(code,N,base,expected,calls,targets,read));
}

int main() {
    uint64_t out=0;
    assert(!relative(0,-1,out));assert(!relative(UINT64_MAX,1,out));
    assert(relative(0x100000000ULL,INT32_MIN,out)&&out==0x80000000ULL);
    verify(HPLinearSignatures::Image,Image);
    verify(HPLinearSignatures::State,State);
    puts("PASS: exact cursor bodies, relocated direct calls, verified import thunks, every-byte mutation and invalid/unmapped targets.");
}
