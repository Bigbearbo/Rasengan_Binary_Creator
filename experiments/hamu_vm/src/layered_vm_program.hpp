#pragma once
#include "promoting_flip_program.hpp"
#include <stdexcept>

inline std::vector<int> layered_vm_program(int l1_order=0) {
    if(l1_order!=-1&&l1_order!=0&&l1_order!=2&&l1_order!=3)
        throw std::invalid_argument("unsupported L1 order");
    std::vector<int> code;
    auto emit=[&](int op,int param){code.push_back(op);code.push_back(param);};
    emit(0,2);emit(1,20);emit(14,21);emit(3,1); // clear reserved output control bit
    emit(16,1); // immediate jumps
    emit(0,0);emit(14,17); // input_start+1: first activation bit
    // 001 activation, MATH 00100, QUESTION 11000, END_L2 11100.
    for(int expected:{0,0,1, 0,0,1,0,0, 1,1,0,0,0, 1,1,1,0,0}) {
        emit(4,1);
        if(expected) {emit(24,2);emit(15,0);}
        else {emit(24,2);emit(26,2);emit(15,0);}
        emit(14,17);
    }
    if(l1_order==-1) {
        // The input pointer is just after the L2 prefix. Move the other
        // cursor to the two unary L1 records; each loop advances both.
        emit(19,0);emit(0,3);emit(1,19);emit(14,17); // work_start+19
        auto skip_record=[&]() {
            const int loop=int(code.size());
            emit(4,1);emit(18,20);
            const int done=int(code.size());emit(20,0);
            emit(14,17);emit(19,0);emit(14,17);emit(19,0);
            const int back=int(code.size());emit(22,0);
            code[done+1]=16+int(code.size())-done;
            code[back+1]=back-loop;
        };
        auto skip_tail=[&](bool next_record) {
            emit(19,0); // input at old expected tail
            emit(4,1);  // an unexpected 1 is the next information bit
            emit(24,2); // new bit: take the extra step
            emit(26,2); // old tail zero: go to common tail step
            emit(14,17); // additional information bit
            emit(14,17); // current tail zero
            if(next_record) {emit(19,0);emit(14,17);} // next unary marker
        };
        skip_record();
        skip_tail(true);
        skip_record();
        skip_tail(false); // ptr now at L1 period
    } else if(l1_order) {
        // After the L2 prefix, two n-bit L1 words each have one tail zero.
        emit(14,16+2*(l1_order+1));
    }
    if(l1_order) {
        for(int expected:{1,1,1,1,0}) {
            emit(4,1);
            if(expected) {emit(24,2);emit(15,0);}
            else {emit(24,2);emit(26,2);emit(15,0);}
            emit(14,17);
        }
    }
    // Reserved output-area control bit is not moved by work-area INSERT.
    emit(0,2);emit(1,20);emit(14,21);emit(2,1);
    auto body=promoting_flip_program(true);
    code.insert(code.end(),body.begin(),body.end());
    return code;
}
