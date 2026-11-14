#pragma once
#include <stdexcept>
#include <vector>
#include "tree_four_layout.hpp"

// Width-aware pending capture for the controlled n=2 -> n=3 operator.
// Existing slots retain their category and padded three-bit key layout;
// work+100/101 stores the actual width flag for each slot.
inline std::vector<int> tree_width_pending_program(int slot,bool four_candidates=false,bool observed=false) {
    if(slot!=57&&slot!=70)throw std::invalid_argument("pending slot");
    if(observed&&!four_candidates)throw std::invalid_argument("observed candidates require four masks");
    const int present=slot==57?47:60, raw=present+2;
    const int category=slot==57?72:75, valid=slot==57?78:79;
    const int width_bit=slot==57?100:101;
    const int other_present=slot==57?60:47;
    const int other_raw=slot==57?62:49;
    const int other_category=slot==57?75:72;
    const int other_width=slot==57?101:100;
    std::vector<int> w;
    auto e=[&](int op,int arg){int i=int(w.size()/2);w.push_back(op);w.push_back(arg);return i;};
    auto move=[&](int d){while(d>=15){e(14,31);d-=15;}if(d)e(14,16+d);};
    auto at=[&](int area,int offset){e(0,area);move(offset);};
    auto patch=[&](int from,int to){
        if(to-from<=0||to-from>31)throw std::logic_error("width pending jump");
        w[2*from+1]=to-from; // wide jumps encode two token ordinals per word
    };
    auto mismatch=[&](int saved,int incoming_area,int incoming,int bits){
        at(3,saved);e(4,bits);at(2,20);e(9,bits);
        at(incoming_area,incoming);e(4,bits);at(2,20);e(5,bits);
        for(int bit=0;bit<bits;++bit){
            at(2,20+bit);e(4,1);at(2,23);e(7,1);
        }
    };
    e(16,1);
    at(3,present);e(4,1);e(24,2);e(26,2);e(15,0);
    at(3,valid);e(3,1);
    at(3,slot);e(3,2); // reclaimed slots cannot retain confirmation/ID
    at(3,tree_four_format(slot));e(3,1);
    at(3,tree_observed_format(slot));e(3,1);
    // Caller has already run the width scaffold and validated the packet.
    at(3,96);e(8,22);e(4,1);at(2,28);e(9,1);e(8,11);
    // Freeze width without changing the root parent ID in reg0..4.
    at(0,2);e(8,22);e(4,3);e(29,0);e(8,1);e(18,20);e(15,0);
    at(0,0);e(8,17);e(4,2);
    at(3,96);e(8,18);e(4,1); // width key 010 or 011
    e(29,0);e(8,3);e(18,20);e(15,0);
    at(2,28);e(4,1);
    const int n3=e(24,0);
    at(0,0);e(8,17);e(4,1);
    at(0,6);e(8,17);e(4,2);
    const int done=e(26,0);
    const int load3=int(w.size()/2);
    at(0,6);e(8,17);e(4,3);
    const int find=int(w.size()/2);
    patch(n3,load3);patch(done,find);
    e(29,0);e(8,11);e(8,21);e(18,20);e(15,0);
    // TREE_ACTION overwrites reg6..7 even for an unbound leaf. Freeze the
    // complete padded key first, otherwise keys 010..111 lose upper bits.
    e(8,17);at(3,raw);e(9,3);e(8,1);
    e(30,0);e(24,2);e(26,2);e(15,0); // already bound
    // Never let a second slot describe the same category/width/key.
    at(3,other_present);e(4,1);
    at(2,24);e(9,1); // save presence before comparing
    e(8,11); // reg5 -> reg0 for comparisons
    at(2,23);e(3,1);
    mismatch(other_category,0,2,3);
    mismatch(other_width,2,28,1);
    mismatch(other_raw,3,raw,3);
    at(2,23);e(4,1);
    at(0,1);e(8,17);e(4,1);e(8,1);e(25,1); // no mismatches
    at(2,24);e(6,1);e(4,1);
    e(24,2);e(26,2);e(15,0); // same and present: stop
    at(0,2);e(4,3);at(3,category);e(9,3);
    at(2,28);e(4,1);at(3,width_bit);e(9,1);
    at(3,raw);e(4,3);at(3,present+5);e(9,3);
    at(3,present+1);e(2,1); // legacy present-width marker
    at(3,slot==57?55:68);e(2,2);
    at(3,valid);e(2,1);
    if(four_candidates){
        at(3,tree_four_mask(slot));e(2,4);
        at(3,tree_four_action(slot));e(3,2);
        at(3,tree_four_format(slot));e(2,1);
        if(observed){at(3,tree_observed_format(slot));e(2,1);}
    }
    at(3,present);e(2,1); // publish last
    e(15,0);
    return w;
}
