#pragma once
#include "flip_vm_program.hpp"

// The operator and data use separate unary length records. A new operator
// word first changes its old tail bit from zero to one; promote only that
// record, inserting space before the following data record.
inline std::vector<int> promoting_flip_program(bool read_startup=false) {
    std::vector<int> code;
    auto emit=[&](int op,int param) {int at=int(code.size());code.push_back(op);code.push_back(param);return at;};
    auto skip=[&](bool capture_operator) {
        const bool read_prefix=read_startup && !capture_operator;
        const int loop=int(code.size());
        emit(4,1);emit(18,20);
        const int done=emit(capture_operator||read_prefix?26:20,0);
        emit(14,17);emit(19,0);
        if(capture_operator) {emit(8,17);emit(4,1);emit(8,1);}
        if(read_prefix)emit(4,1);
        emit(14,17);emit(19,0);
        const int back=emit(22,0);
        code[done+1]=capture_operator||read_prefix?(int(code.size())-done)/2:
                     16+int(code.size())-done;
        code[back+1]=back-loop;
    };
    emit(0,2);emit(14,17);emit(21,0);
    emit(0,0);emit(14,17);emit(19,0);
    emit(0,3);emit(16,1);
    skip(false);emit(14,17);skip(true);
    // ptr=operator marker's zero; secondary_ptr=old expected tail.
    emit(19,0);emit(4,1);emit(19,0); // read tail into reg[0]
    const int promote=emit(24,0);
    const int normal=emit(26,0);
    const int promotion=int(code.size());
    emit(19,0);    // input old tail (1)
    emit(8,17);    // reg[1]
    emit(4,1);     // FLIP flag = 1
    emit(8,1);     // reg[0]
    emit(14,17);   // input new tail
    emit(4,1);     // reg[0] = 0 for INSERT
    emit(19,0);    // work old marker zero
    emit(2,1);     // rewrite zero to one; ptr at next record
    emit(10,1);    // insert zero; shift data marker intact
    const int common=int(code.size());
    code[promote+1]=(promotion-promote)/2;
    code[normal+1]=(common-normal)/2;
    emit(19,0);emit(14,17);emit(19,0);emit(14,17); // tail then next marker
    static const int answer[]={
        4,1,24,20,19,0,4,1,18,24,21,0,3,1,15,0,
        19,0,2,1,19,0,21,0,25,1,9,1,14,17,21,0,14,17,
        4,1,21,0,9,1,15,0,
        14,17,19,0,4,1,25,1,21,0,9,1,14,17,
        21,0,14,17,19,0,23,31
    };
    code.insert(code.end(),std::begin(answer),std::end(answer));
    return code;
}
