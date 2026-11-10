#pragma once
#include <stdexcept>
#include <vector>

// Fall-through guard; failures stop before any persistent candidate update.
inline std::vector<int> tree_grade_guard_program(int commit_offset) {
    if(commit_offset!=57&&commit_offset!=70)
        throw std::invalid_argument("Only the two pending slots are supported");
    const int present=commit_offset==57?47:60;
    const int width=present+1,raw=present+2;
    const int category=commit_offset==57?72:75;
    const int valid=commit_offset==57?78:79;
    std::vector<int> w;
    auto e=[&](int op,int arg){int i=int(w.size()/2);w.push_back(op);w.push_back(arg);return i;};
    auto move=[&](int distance){
        while(distance>=15){e(14,31);distance-=15;}
        if(distance)e(14,16+distance);
    };
    auto at_work=[&](int offset){e(0,3);move(offset);};
    auto require_one=[&](int offset){
        at_work(offset);e(4,1);e(18,20);e(15,0);
    };
    auto reject_mismatch=[&](){
        for(int bit=0;bit<3;++bit){
            e(0,2);move(20+bit);e(4,1);
            e(24,2);e(26,2);e(15,0);
        }
    };
    auto compare=[&](int saved,int area,int incoming){
        at_work(saved);e(4,3);
        e(0,2);move(20);e(9,3);
        e(0,area);move(incoming);e(4,3);
        e(0,2);move(20);e(5,3);
        reject_mismatch();
    };
    e(16,1);
    require_one(present);require_one(valid);require_one(width);
    at_work(commit_offset);e(4,1);e(24,2);e(26,2);e(15,0);
    // A learned word cannot be relabeled by later trials or mask changes.
    require_one(93); // host verified complete execution and fresh output
    require_one(92); // the grade has a completed guest snapshot
    compare(category,0,2);compare(raw,0,6);
    compare(80,0,2);compare(83,0,6);compare(86,0,10);
    compare(89,2,0); // attempted answer has not been swapped since grading
    return w;
}
