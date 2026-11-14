#pragma once
#include <stdexcept>
#include <vector>

// Resolve the saved category/width/key entirely in the guest. No host node ID.
inline std::vector<int> tree_width_confirm_bridge_program(int slot){
    if(slot!=57&&slot!=70)throw std::invalid_argument("pending slot");
    const int present=slot==57?47:60,category=slot==57?72:75;
    const int valid=slot==57?78:79,width=slot==57?100:101;
    std::vector<int> w;
    auto e=[&](int op,int arg){w.push_back(op);w.push_back(arg);};
    auto at=[&](int area,int pos){e(0,area);while(pos>=15){e(14,31);pos-=15;}if(pos)e(14,16+pos);};
    auto found=[&](){e(18,20);e(15,0);};
    auto require=[&](int pos){at(3,pos);e(4,1);found();};
    e(16,1);require(present);require(valid);require(slot);
    for(int b=0;b<5;++b){at(0,0);e(4,1);if(b<4)e(8,17);}
    e(8,17); // reg4 -> reg5
    at(3,category);e(8,17);e(4,3);e(29,0);e(8,1);found();
    at(0,0);e(8,17);e(4,2);
    at(3,width);e(8,18);e(4,1);e(29,0);e(8,3);found();
    at(3,present+2);e(8,17);e(4,3);e(29,0);e(8,1);found();
    // An already committed leaf is immutable through this bridge.
    e(30,0);e(24,2);e(26,2);e(15,0);
    at(3,slot+1);e(8,17);e(4,1);
    at(0,0);e(8,17);e(4,1);
    e(30,1);e(15,0);
    return w;
}
