#pragma once
#include <stdexcept>
#include <vector>

// The fixed category is n=3. The operator starts at input+6 and grows from
// n=2 to n=3 when its former tail (input+8) becomes 1. work+96 remembers the
// promotion; subsequent n=3 words may have either value at that position.
// Path: root / category / width(2 or 3) / operator numeric key.
inline std::vector<int> tree_width_scaffold_program(){
    std::vector<int> w;
    auto e=[&](int op,int arg){int i=int(w.size()/2);w.push_back(op);w.push_back(arg);return i;};
    auto move=[&](int d){while(d>=15){e(14,31);d-=15;}if(d)e(14,16+d);};
    auto at=[&](int area,int offset){e(0,area);move(offset);};
    auto require_zero=[&](){e(24,2);e(26,2);e(15,0);};
    e(16,1);
    at(0,0);e(4,1);require_zero();
    at(0,1);e(4,1);e(18,20);e(15,0);
    at(0,5);e(4,1);require_zero(); // category tail
    at(0,8);e(4,1);at(2,20);e(9,1); // tentative width in scratch
    at(3,96);e(4,1);at(2,20);e(7,1); // old width OR observed trigger
    at(2,20);e(4,1);e(24,2); // if n=3, validate new tail
    const int skip_tail=e(26,0);
    at(0,9);e(4,1);require_zero();
    const int commit_width=int(w.size()/2);
    at(2,20);e(4,1);at(3,96);e(9,1); // commit only after all checks
    if(commit_width-skip_tail<=0||commit_width-skip_tail>31)
        throw std::logic_error("tree width tail branch out of range");
    w[2*skip_tail+1]=commit_width-skip_tail;
    at(2,20);e(3,5);at(2,20);e(4,5); // clear root parent ID reg0..4
    at(0,2);e(8,22);e(4,3);e(31,0); // root/category
    e(8,1);e(18,20);e(15,0);       // stop if category could not be added
    at(0,0);e(8,17);e(4,2);          // reg6..7 = opening 01
    at(3,96);e(8,18);e(4,1);        // reg8 = promoted flag
    e(31,0);                        // category/width 010 or 011
    e(8,3);e(18,20);e(15,0);        // check success at reg5
    at(3,96);e(4,1);                // branch on persistent width
    const int three=e(24,0);
    // n=2: reg6=0, reg7..8 = input+6..7.
    at(0,0);e(8,17);e(4,1);
    at(0,6);e(8,17);e(4,2);
    const int done=e(26,0);
    const int three_at=int(w.size()/2);
    at(0,6);e(8,17);e(4,3); // n=3: reg6..8 = input+6..8
    const int add_at=int(w.size()/2);
    e(31,0);e(15,0);
    if(three_at-three<=0||three_at-three>31||add_at-done<=0||add_at-done>31)
        throw std::logic_error("tree width branch out of range");
    w[2*three+1]=three_at-three;
    w[2*done+1]=add_at-done;
    return w;
}
