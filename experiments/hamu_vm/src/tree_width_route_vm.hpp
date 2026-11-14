#pragma once
#include <stdexcept>
#include <vector>

// The guest follows root/category/remembered-width/operator, then reads the
// data at input+9 (n=2) or input+10 (n=3). A missing or unbound leaf stops
// without writing output. The scaffold validates a new word before promotion.
inline std::vector<int> tree_width_route_program(bool four_candidates=false) {
    std::vector<int> w;
    auto e=[&](int op,int arg){int i=int(w.size()/2);w.push_back(op);w.push_back(arg);return i;};
    auto move=[&](int d){while(d>=15){e(14,31);d-=15;}if(d)e(14,16+d);};
    auto at=[&](int area,int offset){e(0,area);move(offset);};
    auto patch=[&](int i,int target){
        if(target-i<=0||target-i>31)throw std::logic_error("width route jump range");
        w[2*i+1]=target-i;
    };
    auto found=[&](){e(18,20);e(15,0);};
    e(16,1);
    // The root ID is zeroed independently of prior VM register contents.
    for(int bit=0;bit<5;++bit){at(0,0);e(4,1);if(bit<4)e(8,17);}
    e(8,17); // reg4 -> reg5
    at(0,2);e(8,17);e(4,3);
    e(29,0);e(8,1);found(); // root/category; val_ptr 6 -> 5
    at(0,0);e(8,17);e(4,2);
    at(3,96);e(8,18);e(4,1);
    e(29,0);e(8,3);found(); // category/width; val_ptr 8 -> 5
    at(3,96);e(4,1);
    const int n3=e(24,0);
    at(0,0);e(8,17);e(4,1);
    at(0,6);e(8,17);e(4,2);e(8,2); // val_ptr 7 -> 5
    const int after_key=e(26,0);
    const int key3=int(w.size()/2);
    at(0,6);e(8,17);e(4,3);e(8,1); // val_ptr 6 -> 5
    const int lookup=int(w.size()/2);
    patch(n3,key3);patch(after_key,lookup);
    e(29,0);found(); // width/operator
    e(30,0);found(); // the action must be committed
    // Loading data into registers 2..4 leaves the action in register 6.
    at(3,96);e(4,1);
    const int data3=e(24,0);
    at(0,9);e(8,3);e(4,3);
    const int after_data=e(26,0);
    const int load3=int(w.size()/2);
    at(0,10);e(8,3);e(4,3);
    const int action=int(w.size()/2);
    patch(data3,load3);patch(after_data,action);
    e(8,20); // register 2 -> register 6
    int constant=-1;
    if(four_candidates){e(8,17);constant=e(24,0);e(8,1);} // low bit selects constants
    const int flip=e(24,0);
    e(8,4);at(2,0);e(9,3);e(15,0);
    const int do_flip=int(w.size()/2);
    e(8,4);at(2,0);e(2,3);e(14,3);e(5,3);e(15,0);
    patch(flip,do_flip);
    if(four_candidates){
        const int constants=int(w.size()/2);
        e(8,1); // low-bit branch leaves val_ptr 7 -> 6 (high bit)
        const int one=e(24,0);
        at(2,0);e(3,3);e(15,0);
        const int ones=int(w.size()/2);
        at(2,0);e(2,3);e(15,0);
        patch(constant,constants);patch(one,ones);
    }
    return w;
}
