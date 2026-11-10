#pragma once
#include <stdexcept>
#include <vector>

// Fixed L2 -> L1 grammar and operator IDs 0=COPY, 1=FLIP.
// The two possible positions for operator ID 1's only set bit are input+20
// (n=2) and input+21 (n=3). XOR them into stable work+44. Also use the existing
// guest width record at work+21 to recognize only IDs 0 and 1: input+19
// must be zero, and for n=3 input+20 must also be zero. stable work+45 is the
// recognized flag. The packet's fixed layer prefix and token tails remain
// the responsibility of the existing solver/parser, not this small router.
inline std::vector<int> operator_context_router_program() {
    std::vector<int> c;
    auto e=[&](int op,int param){int i=int(c.size()/2);c.push_back(op);c.push_back(param);return i;};
    e(16,1); // immediate jumps
    e(0,0);e(14,31);e(14,21);e(4,2); // input+20,+21
    e(25,1); // XOR the two possible operator information bits
    e(0,3);e(14,31);e(14,31);e(14,30);e(9,1); // work+44
    e(0,0);e(14,31);e(14,20);e(4,1); // input+19: high bit
    e(0,3);e(14,31);e(14,31);e(14,31);e(9,1); // work+45: unknown so far
    e(0,3);e(14,31);e(14,22);e(4,1); // work+21: width n=3?
    const int three=e(24,0);
    const int skip=e(26,0);
    const int three_start=int(c.size()/2);
    e(0,0);e(14,31);e(14,21);e(4,1); // input+20: high bit when n=3
    e(0,3);e(14,31);e(14,31);e(14,31);e(7,1); // OR unknown into work+45
    const int invert=int(c.size()/2);
    e(0,3);e(14,31);e(14,31);e(14,31);e(14,17);e(2,1); // work+46=1
    e(0,3);e(14,31);e(14,31);e(14,31);e(4,2); // unknown, 1
    e(25,1);e(9,1); // XOR_REG: known = !unknown, work+45
    e(15,0);
    if(three_start-three>31||invert-skip>31)
        throw std::logic_error("operator router jump range");
    c[2*three+1]=three_start-three;
    c[2*skip+1]=invert-skip;
    return c;
}
