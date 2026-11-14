#include "splice_operator.hpp"
#include "flip_vm_program.hpp"
#include "math_questions.hpp"
#include "task_upgrade.hpp"
#include <iostream>
#include <random>

struct Score {int old=0,trigger=0,copy=0,flip=0;};

static Score evaluate(const std::vector<int>& scaffold,int capture,int action,int opcode) {
    auto code=scaffold;
    code[capture]=4; // guaranteed ability: capture operator bit in the prefix loop
    code[action]=opcode;
    HamsterParams p;p.op_order=5;
    p.layout.total_size=p.layout.program_start+int(copy_loop_program().size())*6;
    Hamster donor(0,p);
    donor.extend_program_capacity(8); // grow 118 -> 126 whole words
    int at=p.layout.program_start;
    for(int word:code)for(bool b:SpiralToken(word,5,1).bits)donor.memory.at(at++)=b;
    for(int j=0;j<9;++j)donor.memory[p.layout.work_start+j]=(j%3!=2);
    donor.new_his();Hamster h(1,p);h.copy_hamu(donor);
    if(int(h.memory.size())<at)throw std::runtime_error("capacity not inherited");
    Score r;CopyUpgradeCurriculum curriculum(4,6);
    auto solve=[&](const Problem& q) {
        put_started_question(h,q);
        h.pro_1=p.layout.program_start;h.pro_2=at-1;h.step_limit=160;
        simulate_spiral_program(h);
        return int(!h.budget_exhausted&&Check_ans(h,q));
    };
    for(int i=0;i<4;++i)r.old+=solve(curriculum.next());
    for(int i=0;i<6;++i)r.trigger+=solve(curriculum.next());
    for(int v=0;v<8;++v)r.copy+=solve(elementary_problem(ElementaryTask::Copy,3,v));
    for(int v=0;v<8;++v)r.flip+=solve(elementary_problem(ElementaryTask::Flip,3,v));
    return r;
}

int main() {
    const auto code=splice_operator_from_copy();
    int capture=-1,action=-1;
    for(int i=0;i+5<int(code.size());i+=2) {
        if(code[i]==8&&code[i+1]==17&&code[i+2]==16&&
           code[i+3]==1&&code[i+4]==8&&code[i+5]==1)capture=i+2;
        if(code[i]==4&&code[i+1]==1&&code[i+2]==16&&
           code[i+3]==1&&code[i+4]==21&&code[i+5]==0)action=i+2;
    }
    if(capture<0||action<0)return 1;
    int preserved=0,full=0;
    for(int op=0;op<=26;++op) {
        const Score s=evaluate(code,capture,action,op);
        const bool old_ok=s.old==4&&s.trigger==6&&s.copy==8;
        preserved+=old_ok;
        if(old_ok&&s.flip==8) {
            ++full;
            std::cout<<"complete opcode="<<op<<" COPY="<<s.copy<<"/8 FLIP="<<s.flip<<"/8\n";
        }
    }
    std::cout<<"action opcode scan: old ability preserved="<<preserved
             <<"/27, complete COPY+FLIP="<<full<<"/27\n";
    if(full<1)return 2;
    for(unsigned seed=1;seed<=5;++seed) {
        std::mt19937 rng(seed);
        int attempts=0;
        for(;attempts<200;++attempts) {
            const int op=rng()%27;
            const auto s=evaluate(code,capture,action,op);
            if(s.old==4&&s.trigger==6&&s.copy==8&&s.flip==8)break;
        }
        std::cout<<"seed="<<seed<<" opcode_trials="<<attempts+1<<"\n";
        if(attempts==200)return 3;
    }
}
