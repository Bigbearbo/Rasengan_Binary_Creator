#pragma once
#include <vector>

// The hand-written v0.31 VM program, factored out for the math baseline.
inline std::vector<int> copy_loop_program() {
    std::vector<int> code;
    auto emit=[&](int op,int param) {int at=int(code.size());code.push_back(op);code.push_back(param);return at;};
    auto skip=[&]() {
        const int loop=int(code.size());
        emit(4,1);emit(18,20);
        const int done=emit(20,0);
        emit(14,17);emit(19,0);emit(14,17);emit(19,0);
        const int back=emit(22,0);
        code[done+1]=16+int(code.size())-done;
        code[back+1]=back-loop;
    };
    emit(0,2);emit(14,17);emit(21,0);
    emit(0,0);emit(14,17);emit(19,0);
    emit(0,3);emit(16,1);
    skip();emit(14,17);skip();
    emit(19,0);emit(14,17);emit(19,0);emit(14,17);
    static const int answer[]={
        4,1,24,19,19,0,4,1,18,24,21,0,3,1,15,0,
        19,0,2,1,19,0,21,0,9,1,14,17,21,0,14,17,
        4,1,21,0,9,1,15,0,
        14,17,19,0,4,1,21,0,9,1,14,17,
        21,0,14,17,19,0,23,29
    };
    code.insert(code.end(),std::begin(answer),std::end(answer));
    return code;
}
