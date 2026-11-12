#pragma once
#include <stdexcept>
#include <vector>

// Choose a candidate only for the matching category / width / padded key.
// output+25 is validity; output+26 is 0=COPY or 1=FLIP.
inline std::vector<int> tree_width_choice_guard_program(int slot){
    if(slot!=57&&slot!=70)throw std::invalid_argument("pending slot");
    const int present=slot==57?47:60,raw=present+2;
    const int category=slot==57?72:75,valid=slot==57?78:79;
    const int width=slot==57?100:101;
    std::vector<int> w;
    auto e=[&](int op,int arg){int i=int(w.size()/2);w.push_back(op);w.push_back(arg);return i;};
    auto move=[&](int d){while(d>=15){e(14,31);d-=15;}if(d)e(14,16+d);};
    auto at=[&](int area,int pos){e(0,area);move(pos);};
    auto require=[&](int offset){at(3,offset);e(4,1);e(18,20);e(15,0);};
    auto compare=[&](int saved,int area,int incoming,int bits){
        at(3,saved);e(4,bits);at(2,27);e(9,bits);
        at(area,incoming);e(4,bits);at(2,27);e(5,bits);
        for(int b=0;b<bits;++b){
            at(2,27+b);e(4,1);e(24,2);e(26,2);e(15,0);
        }
    };
    e(16,1);
    at(2,25);e(3,2);
    require(present);require(valid);require(present+1);
    at(3,slot);e(4,1);e(24,2);e(26,2);e(15,0);
    compare(category,0,2,3);compare(width,3,96,1);
    // Build a padded 3-bit numeric key in output+20..22.
    at(2,20);e(3,3);
    at(3,96);e(4,1);
    const int n3=e(24,0);
    at(0,6);e(8,17);e(4,2);
    at(2,21);e(9,2);e(8,1);
    const int done=e(26,0);
    const int load3=int(w.size()/2);
    at(0,6);e(4,3);at(2,20);e(9,3);
    const int ready=int(w.size()/2);
    if(load3-n3<=0||load3-n3>31||ready-done<=0||ready-done>31)
        throw std::logic_error("width choice jump");
    w[2*n3+1]=load3-n3;w[2*done+1]=ready-done;
    compare(raw,2,20,3);
    return w;
}

inline std::vector<int> tree_width_choice_program(int slot){
    auto w=tree_width_choice_guard_program(slot);
    const int mask=slot==57?55:68;
    auto e=[&](int op,int arg){int i=int(w.size()/2);w.push_back(op);w.push_back(arg);return i;};
    auto move=[&](int d){while(d>=15){e(14,31);d-=15;}if(d)e(14,16+d);};
    auto at=[&](int area,int pos){e(0,area);move(pos);};
    at(3,mask);e(4,1);
    const int choose_copy=e(24,0);
    at(3,mask+1);e(4,1);e(18,20);e(15,0);
    at(2,26);e(2,1);at(2,25);e(2,1);e(15,0);
    const int copy=int(w.size()/2);
    at(2,25);e(2,1);e(15,0);
    if(copy-choose_copy<=0||copy-choose_copy>31)
        throw std::logic_error("width choice candidate jump");
    w[2*choose_copy+1]=copy-choose_copy;
    return w;
}
