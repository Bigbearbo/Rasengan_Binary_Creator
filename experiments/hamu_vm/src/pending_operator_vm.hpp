#pragma once
#include <stdexcept>
#include <vector>

// One pending unseen operator, in the existing stable work tail:
// work+47 present, +48 width (0=n2,1=n3), +49..51 raw input+19..21,
// +52..54 left-padded numeric operator ID (three bits).
// This saves a bit pattern for later teaching; it does not assign meaning.
// A known word or a second unseen word leaves the first pending record intact.
inline std::vector<int> pending_operator_program() {
    std::vector<int> c;
    auto e=[&](int op,int param){int i=int(c.size()/2);c.push_back(op);c.push_back(param);return i;};
    auto gate=[&]() {e(24,2);e(26,2);e(15,0);};
    e(16,1); // immediate jumps
    e(0,3);e(14,31);e(14,31);e(14,31);e(4,1); // work+45 known?
    gate(); // known -> STOP
    e(0,3);e(14,31);e(14,31);e(14,31);e(14,18);e(4,1); // work+47 present?
    gate(); // already pending -> STOP
    e(0,3);e(14,31);e(14,22);e(4,1); // existing width work+21
    e(0,3);e(14,31);e(14,31);e(14,31);e(14,19);e(9,1); // work+48
    e(0,0);e(14,31);e(14,20);e(4,3); // original input+19..21
    e(0,3);e(14,31);e(14,31);e(14,31);e(14,20);e(9,3); // work+49..51
    e(0,3);e(14,31);e(14,31);e(14,31);e(14,19);e(4,1); // width work+48
    const int three=e(24,0);
    e(0,3);e(14,31);e(14,31);e(14,31);e(14,23);e(3,1); // n2: left zero work+52
    e(0,3);e(14,31);e(14,31);e(14,31);e(14,20);e(4,2); // raw high,low
    e(0,3);e(14,31);e(14,31);e(14,31);e(14,24);e(9,2); // work+53,+54
    e(0,3);e(14,31);e(14,31);e(14,31);e(14,18);e(2,1); // commit present=1 LAST
    e(15,0);
    const int three_start=int(c.size()/2);
    e(0,3);e(14,31);e(14,31);e(14,31);e(14,20);e(4,3); // n3: raw three bits
    e(0,3);e(14,31);e(14,31);e(14,31);e(14,23);e(9,3); // work+52..54
    e(0,3);e(14,31);e(14,31);e(14,31);e(14,18);e(2,1); // commit present=1 LAST
    e(15,0);
    if(three_start-three>31)throw std::logic_error("pending ID normalization jump range");
    c[2*three+1]=three_start-three;
    return c;
}
