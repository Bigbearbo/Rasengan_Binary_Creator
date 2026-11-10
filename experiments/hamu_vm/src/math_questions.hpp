#pragma once
#include "hamu_vm_core.hpp"
#include <stdexcept>

enum class ElementaryTask { Copy, Flip, Next };

inline Problem elementary_problem(ElementaryTask task,int n,int value) {
    if(n<2 || n>3 || value<0 || value>=(1<<n))
        throw std::invalid_argument("out of range for elementary task");
    if(task==ElementaryTask::Next && value+1 >= (1<<n))
        throw std::invalid_argument("successor needs a wider number word");
    Problem q;q.type=ProblemType::EAZY;
    // n=2,k=1: COPY 000, FLIP 010, NEXT 100.
    const int op=task==ElementaryTask::Copy?0:task==ElementaryTask::Flip?1:2;
    q.question={SpiralToken(op,2,1),
                SpiralToken(value,n,1)};
    const int answer=task==ElementaryTask::Copy?value:
                     task==ElementaryTask::Flip?((1<<n)-1-value):value+1;
    q.answer=SpiralToken(answer,n,1);
    q.readable=(task==ElementaryTask::Copy?"COPY ":
                task==ElementaryTask::Flip?"FLIP ":"NEXT ")+std::to_string(value);
    return q;
}

inline Problem elementary_problem_with_operator_order(ElementaryTask task,int op_n,int data_n,int value) {
    if(op_n<2||op_n>3)throw std::invalid_argument("operator order out of range");
    auto q=elementary_problem(task,data_n,value);
    q.question[0]=SpiralToken(task==ElementaryTask::Copy?0:
                              task==ElementaryTask::Flip?1:2,op_n,1);
    return q;
}

inline void put_started_question(Hamster& h,const Problem& q) {
    h.write_prob(q);
    const int payload=h.params.layout.input_start+1;
    const int count=int(q.question[0].bits.size()+q.question[1].bits.size());
    for(int j=count-1;j>=0;--j)h.memory.at(payload+j+2)=h.memory.at(payload+j);
    h.memory.at(payload)=0;h.memory.at(payload+1)=1; // 01 startup
}
