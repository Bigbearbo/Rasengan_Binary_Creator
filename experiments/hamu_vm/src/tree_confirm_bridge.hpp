#pragma once
#include <stdexcept>
#include <vector>

// Caller supplies the parent node ID in registers 0..4. The guest reads the
// saved word's numeric key and finds its child, rather than trusting a target
// node ID supplied by the caller. Slots are the existing two pending records.
inline std::vector<int> tree_confirm_bridge_program(int commit_offset) {
    if(commit_offset!=57&&commit_offset!=70)
        throw std::invalid_argument("Only the two confirmed candidate slots are supported");
    std::vector<int> w;
    auto e=[&](int op,int param){w.push_back(op);w.push_back(param);};
    auto move=[&](int distance){
        while(distance>=15){e(14,31);distance-=15;}
        if(distance)e(14,16+distance);
    };
    const int present=commit_offset==57?47:60;
    const int width=commit_offset==57?48:61;
    const int key=commit_offset==57?52:65;
    e(16,1); // immediate branch
    e(0,3);move(present);e(8,21);e(4,1); // presence -> reg5
    e(18,20);e(15,0); // no record
    e(0,3);move(width);e(4,1);e(18,20);e(15,0); // only n=3
    e(0,3);move(key);e(8,17);e(4,3); // saved numeric key -> reg6..8
    e(29,0);e(8,1);e(18,20);e(15,0); // find under parent; missing child -> stop
    e(0,3);move(commit_offset);e(4,1); // confirmation -> reg5
    e(18,20);e(15,0); // no confirmation: leave the node untouched
    e(0,3);move(commit_offset+1);e(8,17);e(4,1); // local ID -> action high bit reg6
    e(0,0);e(8,17);e(4,1); // input[0] is zero; clear action low bit reg7
    e(30,1);e(15,0); // local COPY 0 -> action 0, FLIP 1 -> action 2
    return w;
}
