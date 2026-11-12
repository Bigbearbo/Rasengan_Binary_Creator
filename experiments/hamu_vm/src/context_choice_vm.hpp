#pragma once
#include <stdexcept>
#include <vector>

// Human-assigned two-candidate context at work+40+base; emit local 0/1.
inline std::vector<int> context_choice_program(int base) {
    if(base!=0&&base!=2)throw std::invalid_argument("context base");
    std::vector<int> c;
    auto e=[&](int op,int param){int i=int(c.size()/2);c.push_back(op);c.push_back(param);return i;};
    e(16,1);e(0,3);e(14,31);e(14,31);e(14,26+base);
    e(4,1);const int first=e(24,0);
    e(14,17);e(4,1);const int second=e(24,0);
    e(15,0);
    const int zero=int(c.size()/2);e(0,2);e(14,17);e(3,3);e(15,0);
    const int one=int(c.size()/2);e(0,2);e(14,17);e(3,1);e(2,1);e(3,1);e(15,0);
    c[2*first+1]=zero-first;c[2*second+1]=one-second;
    return c;
}
