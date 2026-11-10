#pragma once
#include <vector>

// The second prefix loop retains the last operator information bit in reg[1].
// The data loop combines each input bit with this flag using XOR_REG.
inline std::vector<int> flip_loop_program() {
    std::vector<int> code;
    auto emit=[&](int op,int param) {int at=int(code.size());code.push_back(op);code.push_back(param);return at;};
    auto skip=[&](bool capture_operator) {
        const int loop=int(code.size());
        emit(4,1);emit(18,20);
        const int done=emit(capture_operator?26:20,0);
        emit(14,17);emit(19,0);
        if(capture_operator) {emit(8,17);emit(4,1);emit(8,1);}
        emit(14,17);emit(19,0);
        const int back=emit(22,0);
        code[done+1]=capture_operator?(int(code.size())-done)/2:16+int(code.size())-done;
        code[back+1]=back-loop;
    };
    emit(0,2);emit(14,17);emit(21,0);
    emit(0,0);emit(14,17);emit(19,0);
    emit(0,3);emit(16,1);
    skip(false);emit(14,17);skip(true);
    emit(19,0);emit(14,17);emit(19,0);emit(14,17);
    static const int answer[]={
        4,1,24,19,19,0,4,1,18,24,21,0,3,1,15,0,
        19,0,2,1,19,0,21,0,9,1,14,17,21,0,14,17,
        4,1,21,0,9,1,15,0,
        14,17,19,0,4,1,25,1,21,0,9,1,14,17,
        21,0,14,17,19,0,23,30
    };
    code.insert(code.end(),std::begin(answer),std::end(answer));
    return code;
}
