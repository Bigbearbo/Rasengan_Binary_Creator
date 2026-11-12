#pragma once
#include <stdexcept>
#include <vector>

// Given one pending slot, compare its category/operator against the current
// question and choose a surviving hypothesis. output+25 is validity and
// output+26 is the candidate ID (0=COPY, 1=FLIP). No masks are changed.
inline std::vector<int> tree_candidate_choice_program(int slot){
    if(slot!=57&&slot!=70)throw std::invalid_argument("pending slot");
    const int present=slot==57?47:60, raw=present+2;
    const int category=slot==57?72:75, category_valid=slot==57?78:79;
    const int mask=slot==57?55:68;
    std::vector<int> w;
    auto e=[&](int op,int arg){int i=int(w.size()/2);w.push_back(op);w.push_back(arg);return i;};
    auto move=[&](int d){while(d>=15){e(14,31);d-=15;}if(d)e(14,16+d);};
    auto at=[&](int area,int offset){e(0,area);move(offset);};
    auto require=[&](int offset){at(3,offset);e(4,1);e(18,20);e(15,0);};
    auto compare=[&](int saved,int incoming){
        at(3,saved);e(4,3);at(2,20);e(9,3);
        at(0,incoming);e(4,3);at(2,20);e(5,3);
        for(int bit=0;bit<3;++bit){
            at(2,20+bit);e(4,1);e(24,2);e(26,2);e(15,0);
        }
    };
    e(16,1);
    at(2,25);e(3,2); // clear valid and previous candidate
    require(present);require(category_valid);require(present+1);
    at(3,slot);e(4,1);e(24,2);e(26,2);e(15,0); // confirmed already
    compare(category,2);compare(raw,6);
    at(3,mask);e(4,1);
    const int choose_copy=e(24,0);
    at(3,mask+1);e(4,1);e(18,20);e(15,0);
    at(2,26);e(2,1); // FLIP
    at(2,25);e(2,1);e(15,0);
    const int copy=int(w.size()/2);
    at(2,25);e(2,1);e(15,0); // COPY, candidate bit remains zero
    const int delta=copy-choose_copy;
    if(delta<=0||delta>31)throw std::logic_error("choice branch range");
    w[2*choose_copy+1]=delta;
    return w;
}

