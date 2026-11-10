#pragma once
#include <stdexcept>
#include <vector>

// Read back the saved leaf's committed action before releasing the record.
// Presence is cleared last, so interrupted records remain retryable.
inline std::vector<int> tree_width_reclaim_program(int slot){
    if(slot!=57&&slot!=70)throw std::invalid_argument("pending slot");
    const int present=slot==57?47:60,category=slot==57?72:75;
    const int valid=slot==57?78:79,width=slot==57?100:101;
    std::vector<int> w;
    auto e=[&](int op,int arg){w.push_back(op);w.push_back(arg);};
    auto at=[&](int area,int pos){e(0,area);while(pos>=15){e(14,31);pos-=15;}if(pos)e(14,16+pos);};
    auto found=[&](){e(18,20);e(15,0);};
    auto zero=[&](){e(24,2);e(26,2);e(15,0);};
    auto require=[&](int pos){at(3,pos);e(4,1);found();};
    e(16,1);require(present);require(valid);require(present+1);require(slot);
    for(int b=0;b<5;++b){at(0,0);e(4,1);if(b<4)e(8,17);}
    e(8,17);
    at(3,category);e(8,17);e(4,3);e(29,0);e(8,1);found();
    at(0,0);e(8,17);e(4,2);
    at(3,width);e(8,18);e(4,1);e(29,0);e(8,3);found();
    at(3,present+2);e(8,17);e(4,3);e(29,0);e(8,1);found();
    e(30,0);found(); // action committed; reg6..7 contain action bits
    e(8,18);zero(); // COPY=00, FLIP=10: low bit must be zero
    e(8,1);at(2,24);e(9,1);
    at(3,slot+1);e(4,1);at(2,24);e(5,1);e(4,1);zero();
    at(3,92);e(3,3); // invalidate old snapshot/grade before reuse
    at(3,present);e(3,1); // logical release, final persistent write
    e(15,0);
    return w;
}
