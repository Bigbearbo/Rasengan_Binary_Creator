#pragma once
#include <stdexcept>
#include <vector>

// The host grades an actual candidate trial. These guest programs bind that
// observation to category, operator width/key, data and emitted answer.
inline std::vector<int> tree_width_snapshot_program(){
    std::vector<int> w;
    auto e=[&](int op,int arg){int i=int(w.size()/2);w.push_back(op);w.push_back(arg);return i;};
    auto move=[&](int d){while(d>=15){e(14,31);d-=15;}if(d)e(14,16+d);};
    auto at=[&](int area,int pos){e(0,area);move(pos);};
    auto copy=[&](int area,int source,int destination,int bits){
        at(area,source);e(4,bits);at(3,destination);e(9,bits);
    };
    auto patch=[&](int from,int to){
        if(to-from<=0||to-from>31)throw std::logic_error("width snapshot branch");
        w[2*from+1]=to-from;
    };
    e(16,1);
    at(3,92);e(3,1); // invalidate old snapshot before writing fields
    copy(0,2,80,3);
    at(3,83);e(3,3); // pad the n=2 operator with a leading zero
    at(3,96);e(4,1);
    const int n3=e(24,0);
    copy(0,6,84,2);
    const int after_key=e(26,0);
    const int key3=int(w.size()/2);
    copy(0,6,83,3);
    const int data=int(w.size()/2);
    patch(n3,key3);patch(after_key,data);
    at(3,96);e(4,1);
    const int data3=e(24,0);
    copy(0,9,86,3);
    const int after_data=e(26,0);
    const int load3=int(w.size()/2);
    copy(0,10,86,3);
    const int attempt=int(w.size()/2);
    patch(data3,load3);patch(after_data,attempt);
    copy(2,0,89,3);
    copy(3,96,102,1);
    copy(0,40,34,1);
    at(3,92);e(2,1); // publish last
    e(15,0);
    return w;
}

// Fall-through guard. On a mismatch the VM stops before any mask mutation.
inline std::vector<int> tree_width_grade_guard_program(int slot){
    if(slot!=57&&slot!=70)throw std::invalid_argument("pending slot");
    const int present=slot==57?47:60, raw=present+2;
    const int category=slot==57?72:75,valid=slot==57?78:79;
    const int width=slot==57?100:101;
    std::vector<int> w;
    auto e=[&](int op,int arg){int i=int(w.size()/2);w.push_back(op);w.push_back(arg);return i;};
    auto move=[&](int d){while(d>=15){e(14,31);d-=15;}if(d)e(14,16+d);};
    auto at=[&](int area,int pos){e(0,area);move(pos);};
    auto require=[&](int pos){at(3,pos);e(4,1);e(18,20);e(15,0);};
    auto compare=[&](int saved,int area,int incoming,int bits){
        at(3,saved);e(4,bits);at(2,27);e(9,bits);
        at(area,incoming);e(4,bits);at(2,27);e(5,bits);
        for(int b=0;b<bits;++b){
            at(2,27+b);e(4,1);e(24,2);e(26,2);e(15,0);
        }
    };
    auto patch=[&](int from,int to){
        if(to-from<=0||to-from>31)throw std::logic_error("width guard branch");
        w[2*from+1]=to-from;
    };
    e(16,1);
    require(present);require(valid);require(present+1);
    at(3,slot);e(4,1);e(24,2);e(26,2);e(15,0);
    require(93);require(92);
    compare(width,3,96,1);compare(102,3,96,1);
    compare(category,0,2,3);compare(80,0,2,3);
    // Construct the current padded operator in output+20..22.
    at(2,20);e(3,3);at(3,96);e(4,1);
    const int key3=e(24,0);
    at(0,6);e(8,17);e(4,2);at(2,21);e(9,2);e(8,1);
    const int after_key=e(26,0);
    const int load3=int(w.size()/2);
    at(0,6);e(4,3);at(2,20);e(9,3);
    const int check_key=int(w.size()/2);
    patch(key3,load3);patch(after_key,check_key);
    compare(raw,2,20,3);compare(83,2,20,3);
    // Construct current data in output+24..26.
    at(3,96);e(4,1);
    const int data3=e(24,0);
    at(0,9);e(4,3);at(2,24);e(9,3);
    const int after_data=e(26,0);
    const int load_data3=int(w.size()/2);
    at(0,10);e(4,3);at(2,24);e(9,3);
    const int check_data=int(w.size()/2);
    patch(data3,load_data3);patch(after_data,check_data);
    compare(86,2,24,3);compare(89,2,0,3);
    return w;
}
