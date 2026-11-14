#pragma once
#include "tree_confirm_bridge.hpp"

// Two pending records reserve work+72..74 and +75..77 for their category keys.
// Start from the implicit root, then use the saved category as the parent of
// the saved operator word. Both lookups are guest VM instructions.
inline std::vector<int> tree_context_confirm_program(int commit_offset) {
    if(commit_offset!=57&&commit_offset!=70)
        throw std::invalid_argument("Only the two pending slots are supported");
    const int category=commit_offset==57?72:75;
    const int valid=commit_offset==57?78:79;
    std::vector<int> w;
    auto e=[&](int op,int param){w.push_back(op);w.push_back(param);};
    auto move=[&](int distance){
        while(distance>=15){e(14,31);distance-=15;}
        if(distance)e(14,16+distance);
    };
    e(16,1);
    e(0,3);move(valid);e(4,1);e(18,20);e(15,0); // complete category capture only
    e(0,0); // the frame starts with input[0]=0
    for(int b=0;b<5;++b){e(4,1);e(8,17);} // clear root ID registers 0..4
    e(8,11); // restore val_ptr 0
    e(0,3);move(category);e(8,22);e(4,3); // saved category -> reg6..8
    e(29,0);e(8,1);e(18,20);e(15,0); // find under root, or stop
    e(8,5); // reset val_ptr 5 -> 0; node ID remains in reg0..4
    auto child=tree_confirm_bridge_program(commit_offset);
    w.insert(w.end(),child.begin()+2,child.end()); // already in immediate mode
    return w;
}
