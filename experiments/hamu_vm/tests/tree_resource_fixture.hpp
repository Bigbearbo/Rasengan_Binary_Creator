#pragma once
#include "../src/tree_resource_birth.hpp"
#include <stdexcept>
inline void require_resource(bool ok,const char* what){if(!ok)throw std::runtime_error(what);}
inline HamsterParams resource_fixture_params(){
    HamsterParams p;p.layout.status_start=45;p.layout.output_start=50;p.layout.work_start=80;
    p.layout.program_start=700;p.layout.total_size=24000;p.stable_work_bits=100;
    p.tree_start=600;p.tree_capacity=8;p.layout.val_reg_size=12;return p;
}
inline void resource_fixture_question(Hamster& h,int data){
    std::fill(h.memory.begin(),h.memory.begin()+45,false);h.memory[1]=true;
    for(int b=0;b<4;++b)h.memory[2+b]=SpiralToken(1,3,1).bits[b];
    for(int b=0;b<3;++b)h.memory[6+b]=SpiralToken(1,2,1).bits[b];
    for(int b=0;b<4;++b)h.memory[9+b]=SpiralToken(data,3,1).bits[b];
}
