#pragma once
#include "growth_genome.hpp"

struct IntegratedZero {
    std::vector<int> words;
    int mutation_pair;
    int reserve_start;
    int reserve_pairs;
};

// After the shared layer-prefix and period check, distinguish operator 0110
// (ZERO) by its two trailing information bits. Existing tasks enter the
// unchanged COPY/FLIP/NEXT code. ONE opcode in ZERO's write routine mutates.
inline IntegratedZero integrated_zero_program(int write_opcode,int write_count=4) {
    if(write_count<1||write_count>15)throw std::invalid_argument("ZERO write count");
    auto old=layered_next_operator_growth_program();
    auto prefix=layered_vm_program(-1);
    auto body=promoting_flip_program(true);
    const int n=int((prefix.size()-body.size())/2);
    IntegratedZero g{{old.begin(),old.begin()+2*n},-1,-1,64};
    auto e=[&](int op,int param) {
        int at=int(g.words.size()/2);g.words.push_back(op);g.words.push_back(param);return at;
    };
    auto patch=[&](int from,int to) {
        if(to<=from||to-from>31)throw std::logic_error("ZERO dispatch jump range");
        g.words[2*from+1]=to-from;
    };
    e(0,0);e(14,31);e(14,21);e(4,1); // input_start+20
    e(24,2);const int old_a=e(26,0);
    e(14,17);e(4,1); // input_start+21
    e(24,2);const int old_b=e(26,0);
    g.reserve_start=int(g.words.size()/2);
    // The reserve sits on the live dispatch path. ZERO enters its first
    // four pairs; old tasks bridge across without executing reserve genes.
    for(int i=0;i<g.reserve_pairs;++i){e(15,0);}
    auto set=[&](int index,int op,int param) {
        g.words[2*(g.reserve_start+index)]=op;
        g.words[2*(g.reserve_start+index)+1]=param;
    };
    set(0,0,2);set(1,14,17); // output_start+1
    g.mutation_pair=g.reserve_start+2;
    set(2,write_opcode,write_count); // opcode and count may mutate separately
    set(3,15,0);
    // Reserved bridges are protected structural words; the other reserved
    // positions can later become more program genes.
    for(int island:{16,38,60}) {
        set(island,26,2); // skip the bridge if reached sequentially
        set(island+1,26,0);
    }
    const int old_start=int(g.words.size()/2);
    g.words.insert(g.words.end(),old.begin()+2*n,old.end());
    patch(old_a,g.reserve_start+17);patch(old_b,g.reserve_start+17);
    patch(g.reserve_start+17,g.reserve_start+39);
    patch(g.reserve_start+39,g.reserve_start+61);
    patch(g.reserve_start+61,old_start);
    return g;
}
