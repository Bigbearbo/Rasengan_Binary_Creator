#pragma once
#include <stdexcept>
#include <vector>

// Record one previously unbound leaf from a fixed n=3 question:
// input 01 | category(3+0) | operator(3+0) | data(3+0).
// The tree structure is installed separately; no meaning is assigned here.
// The selected pending slot is a caller choice. The guest checks both tree
// keys, the leaf's absent action, and the other slot's category/operator path
// before saving the paired record.
inline std::vector<int> tree_pending_context_program(int commit_offset) {
    if(commit_offset!=57&&commit_offset!=70)
        throw std::invalid_argument("Only the two pending slots are supported");
    const int present=commit_offset==57?47:60;
    const int width=present+1, raw=present+2, numeric=present+5;
    const int category=commit_offset==57?72:75;
    const int valid=commit_offset==57?78:79;
    const int other_present=commit_offset==57?60:47;
    const int other_raw=commit_offset==57?62:49;
    const int other_category=commit_offset==57?75:72;
    std::vector<int> w;
    auto e=[&](int op,int arg){w.push_back(op);w.push_back(arg);};
    auto move=[&](int distance){
        while(distance>=15){e(14,31);distance-=15;}
        if(distance)e(14,16+distance);
    };
    auto at_work=[&](int offset){e(0,3);move(offset);};
    e(16,1);
    at_work(present);e(4,1);e(24,2);e(26,2);e(15,0);
    // Clear an old half-written context before trying a new capture.
    at_work(valid);e(3,1);
    e(0,0);move(2);e(8,22);e(4,3); // category -> reg6..8, root ID 0
    e(29,0);e(8,1);e(18,20);e(15,0); // unknown category -> stop
    e(8,11); // reg5 -> reg0
    e(0,0);move(6);e(8,22);e(4,3); // operator -> reg6..8, parent retained
    e(29,0);e(8,1);e(18,20);e(15,0); // no scaffolded leaf -> stop
    e(30,0);e(24,2);e(26,2);e(15,0); // learned leaf -> stop
    e(8,11); // reg5 -> reg0
    // Compare the other committed slot's six-bit path with this question.
    // output+23 accumulates mismatches; output+24 holds "same AND present".
    e(0,2);move(23);e(3,1);
    auto mismatch=[&](int saved,int incoming){
        at_work(saved);e(4,3);
        e(0,2);move(20);e(9,3);
        e(0,0);move(incoming);e(4,3);
        e(0,2);move(20);e(5,3);
        for(int bit=0;bit<3;++bit){
            e(0,2);move(20+bit);e(4,1);
            e(0,2);move(23);e(7,1);
        }
    };
    mismatch(other_category,2);mismatch(other_raw,6);
    e(0,2);move(23);e(4,1); // mismatch -> reg0
    e(0,0);move(1);e(8,17);e(4,1);e(8,1); // frame 01 -> reg1=1
    e(25,1); // reg0 = !mismatch
    e(0,2);move(24);e(9,1);
    at_work(other_present);e(4,1);
    e(0,2);move(24);e(6,1);e(4,1);
    e(24,2);e(26,2);e(15,0); // already pending under that path -> stop
    e(0,0);move(6);e(4,3);
    at_work(raw);e(9,3);
    at_work(numeric);e(9,3); // n=3, so original bits are the numeric key
    at_work(width);e(2,1);
    e(0,0);move(2);e(4,3);
    at_work(category);e(9,3);
    at_work(commit_offset==57?55:68);e(2,2); // both hypotheses start alive
    at_work(valid);e(2,1);
    at_work(present);e(2,1); // publish the paired record last
    e(15,0);
    return w;
}
