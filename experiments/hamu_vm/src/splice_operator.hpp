#pragma once
#include "loop_vm_program.hpp"
#include <stdexcept>

// Host-side word-aligned splice. The VM cannot alter its protected program
// area, so this is an explicit reproduction/mutation operator.
inline std::vector<int> splice_operator_from_copy() {
    auto code=copy_loop_program();
    int second_loop=-1,seen=0;
    for(int i=0;i+5<int(code.size());i+=2)
        if(code[i]==4&&code[i+1]==1&&code[i+2]==18&&code[i+3]==20&&
           code[i+4]==20) {
            if(++seen==2)second_loop=i;
        }
    if(second_loop<0)throw std::runtime_error("second prefix loop missing");
    const int done=second_loop+4;
    int insertion=-1;
    for(int i=second_loop+6;i+7<int(code.size());i+=2)
        if(code[i]==19&&code[i+1]==0&&code[i+2]==14&&code[i+3]==17&&
           code[i+4]==19&&code[i+5]==0&&code[i+6]==22) {insertion=i+2;break;}
    if(insertion<0)throw std::runtime_error("operator loop insertion missing");
    code.insert(code.begin()+insertion,{8,17,16,1,8,1});
    code[done]=26; // short jump no longer reaches across the expanded loop
    int back=-1;
    for(int i=insertion+6;i+1<int(code.size());i+=2)
        if(code[i]==22) {back=i;break;}
    if(back<0)throw std::runtime_error("operator loop back jump missing");
    code[done+1]=(back+2-done)/2;
    code[back+1]=back-second_loop;

    int answer_read=-1;
    for(int i=back+2;i+5<int(code.size());i+=2)
        if(code[i]==4&&code[i+1]==1&&code[i+2]==21&&code[i+3]==0&&
           code[i+4]==9&&code[i+5]==1) answer_read=i;
    if(answer_read<0)throw std::runtime_error("answer loop insertion missing");
    code.insert(code.begin()+answer_read+2,{16,1});
    if(code.size()<2||code[code.size()-2]!=23)
        throw std::runtime_error("answer loop back jump missing");
    code.back()=30;
    return code;
}
