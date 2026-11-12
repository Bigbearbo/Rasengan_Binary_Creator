#pragma once
#include <stdexcept>
#include <vector>

// Read the category from a three-bit-category / three-bit-operator question:
// input 01 | category(3+0) | operator(3+0) | data(3+0).
// The pending operator must already be present, n=3 and match the current
// question. A separate context commit bit is set only after all three bits.
// The output area (+20..22) is temporary XOR comparison scratch.
inline std::vector<int> tree_category_capture_program(int commit_offset) {
    if(commit_offset!=57&&commit_offset!=70)
        throw std::invalid_argument("Only the two pending slots are supported");
    const int present=commit_offset==57?47:60;
    const int width=present+1, raw=present+2;
    const int category=commit_offset==57?72:75;
    const int valid=commit_offset==57?78:79;
    std::vector<int> w;
    auto e=[&](int op,int param){w.push_back(op);w.push_back(param);};
    auto move=[&](int d){while(d>=15){e(14,31);d-=15;}if(d)e(14,16+d);};
    auto read_work=[&](int off,int count){e(0,3);move(off);e(4,count);};
    auto require_one=[&](int off){read_work(off,1);e(18,20);e(15,0);};
    e(16,1);
    // A previous completed capture cannot be silently relabeled.
    read_work(valid,1);e(24,2);e(26,2);e(15,0);
    require_one(present);require_one(width);
    read_work(raw,3);e(0,2);move(20);e(9,3);
    e(0,0);move(6);e(4,3);e(0,2);move(20);e(5,3);
    for(int bit=0;bit<3;++bit){
        e(0,2);move(20+bit);e(4,1);
        e(24,2);e(26,2);e(15,0); // mismatch -> stop
    }
    e(0,0);move(2);e(4,3);
    e(0,3);move(category);e(9,3);
    e(0,3);move(valid);e(2,1);
    e(15,0);
    return w;
}
