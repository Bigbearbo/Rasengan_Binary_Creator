#include "../src/task_upgrade.hpp"
#include <iostream>
#include <vector>

static std::vector<int> code;
static int emit(int op,int param) {const int at=int(code.size());code.push_back(op);code.push_back(param);return at;}
static void skip_unary() {
    const int loop=int(code.size());
    emit(4,1);                            // read unary bit
    emit(18,20);                          // if one, jump four words to body
    const int done=emit(20,0);            // if zero, leave loop
    emit(14,17);emit(19,0);emit(14,17);emit(19,0);
    const int back=emit(22,0);
    code[done+1]=16+int(code.size())-done;
    code[back+1]=back-loop;
}
static std::vector<int> make_program() {
    code.clear();
    emit(0,2);emit(14,17);emit(21,0); // output cursor = output+1
    emit(0,0);emit(14,17);emit(19,0); // input cursor = input+1
    emit(0,3);emit(16,1);             // unary cursor = work; immediate jumps
    skip_unary();                      // skip 01 by its 110 marker
    emit(14,17);                       // next unary marker
    skip_unary();                      // skip COPY information bits
    emit(19,0);emit(14,17);emit(19,0); // skip COPY's one tail bit
    emit(14,17);                       // next unary marker is data word
    const int start=int(code.size());
    // Same answer / growth VM instruction sequence as v0.30, from its word 18.
    static const int answer[]={
        4,1,24,19,19,0,4,1,18,24,21,0,3,1,15,0,
        19,0,2,1,19,0,21,0,9,1,14,17,21,0,14,17,
        4,1,21,0,9,1,15,0,
        14,17,19,0,4,1,21,0,9,1,14,17,
        21,0,14,17,19,0,23,29
    };
    code.insert(code.end(),std::begin(answer),std::end(answer));
    if(code.size()!=size_t(start+60))throw std::runtime_error("answer length mismatch");
    return code;
}

int main() {
    const auto words=make_program();
    HamsterParams p;p.op_order=5;p.layout.total_size=p.layout.program_start+int(words.size())*6;
    Hamster h(0,p);int at=p.layout.program_start;
    for(int word:words)for(bool b:SpiralToken(word,5,1).bits)h.memory.at(at++)=b;
    const int work=p.layout.work_start;
    for(int j=0;j<9;++j)h.memory[work+j]=(j%3!=2); // 110 110 110
    CopyUpgradeCurriculum teacher(4,6);
    int promotions=0,even_stable=0;
    for(int i=0;i<26;++i) {
        Problem q=teacher.next();h.write_prob(q);
        const int payload=p.layout.input_start+1;
        const int count=3+int(q.question[1].bits.size());
        for(int j=count-1;j>=0;--j)h.memory.at(payload+j+2)=h.memory.at(payload+j);
        h.memory.at(payload)=0;h.memory.at(payload+1)=1;
        const bool before=h.memory[work+8];
        h.pro_1=p.layout.program_start;h.pro_2=at-1;h.step_limit=130;
        simulate_spiral_program(h);
        promotions+=before!=h.memory[work+8];
        if(i>=10 && !h.memory[payload+2+3+2])++even_stable;
        if(!Check_ans(h,q)||h.budget_exhausted||h.memory[work+8]!=(i>=4)||
           h.written[work+8]!=(i==4)) {
            std::cerr<<"FAIL question="<<i<<" steps="<<h.executed_steps
                     <<" ptr="<<h.ptr<<" marker="<<h.memory[work+8]<<"\n";return 1;
        }
        if(i==10) {
            h.new_his();Hamster child(1,p);child.copy_hamu(h);
            if(!child.memory[work+8])return 2;
            h=std::move(child);
        }
    }
    if(promotions!=1||even_stable==0)return 3;
    // Changing the operator width moves the data start; the program stays identical.
    Hamster shifted(2,p);at=p.layout.program_start;
    for(int word:words)for(bool b:SpiralToken(word,5,1).bits)shifted.memory.at(at++)=b;
    const int marker[]={1,1,0,1,1,1,0,1,1,0}; // 110 1110 110
    for(int j=0;j<10;++j)shifted.memory[work+j]=marker[j];
    Problem q;q.type=ProblemType::EAZY;
    q.question={SpiralToken(0,3,1),SpiralToken(2,2,1)};
    q.answer=SpiralToken(2,2,1);
    shifted.write_prob(q);
    const int payload=p.layout.input_start+1;
    for(int j=6;j>=0;--j)shifted.memory[payload+j+2]=shifted.memory[payload+j];
    shifted.memory[payload]=0;shifted.memory[payload+1]=1;
    shifted.pro_1=p.layout.program_start;shifted.pro_2=at-1;shifted.step_limit=130;
    simulate_spiral_program(shifted);
    if(!Check_ans(shifted,q)||!shifted.read_seen[payload+2+4]||
       shifted.memory[work+9]||shifted.budget_exhausted)return 4;
    std::cout<<"PASS: one VM program skips startup/operator by unary loops,"
                " promotes data once, answers 26 COPY questions, inherits marker;"
                " operator width may shift data start\n";
}
