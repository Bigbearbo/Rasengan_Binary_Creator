#pragma once
#include "hamu_vm_core.hpp"

// The COPY operator remains the known n=2 word. Only its data word grows.
// This makes the old expected tail position well-defined during teaching.
struct CopyUpgradeCurriculum {
    int old_left, trigger_left, stable_index=0, trigger_index=0;
    explicit CopyUpgradeCurriculum(int old_questions,int trigger_questions)
        : old_left(old_questions),trigger_left(trigger_questions) {
        if(old_questions<0 || trigger_questions<1)
            throw std::invalid_argument("Invalid upgrade curriculum length");
    }
    Problem next() {
        const bool old=old_left>0;
        const bool teaching=!old && trigger_left>0;
        const int order=old?2:3;
        int value;
        if(old) {value=(old_left-1)%4;--old_left;}
        else if(teaching) {value=1+2*(trigger_index++%4);--trigger_left;}
        else value=stable_index++%8;
        Problem p;p.type=ProblemType::EAZY;
        p.question={SpiralToken(0,2,1),SpiralToken(value,order,1)};
        p.answer=SpiralToken(value,order,1);
        p.readable="COPY " + std::to_string(value);
        return p;
    }
};
