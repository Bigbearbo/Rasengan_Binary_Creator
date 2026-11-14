#include "flip_vm_program.hpp"
#include "loop_vm_program.hpp"
#include "splice_operator.hpp"
#include "math_questions.hpp"
#include "task_upgrade.hpp"
#include <iostream>
#include <random>

struct Genes {bool capture=false,xor_bit=false;};
struct Score {int old=0,trigger=0,copy=0,flip=0,operator_reads=0;};

static Score evaluate(const std::vector<int>& prototype,int capture_at,int xor_at,
                      int old_words,Genes genes) {
    auto code=prototype;
    code[capture_at]=genes.capture?4:16;
    code[xor_at]=genes.xor_bit?25:16;
    HamsterParams p;p.op_order=5;
    p.layout.total_size=p.layout.program_start+old_words*6;
    Hamster donor(0,p);
    const int added=int(code.size())-old_words;
    if(added<=0)throw std::runtime_error("missing growth budget");
    if(donor.memory.size()>=size_t(p.layout.program_start+int(code.size())*6))
        throw std::runtime_error("capacity test cannot detect insufficient memory");
    donor.extend_program_capacity(added); // explicit host-provided capacity
    int at=p.layout.program_start;
    for(int word:code)for(bool b:SpiralToken(word,5,1).bits)donor.memory.at(at++)=b;
    for(int j=0;j<9;++j)donor.memory[p.layout.work_start+j]=(j%3!=2);
    donor.new_his();
    Hamster h(1,p);h.copy_hamu(donor);
    if(int(h.memory.size())<at||h.memory[p.layout.work_start+8])
        throw std::runtime_error("program or state not inherited");
    Score s;
    auto solve=[&](const Problem& q,bool measure_read) {
        put_started_question(h,q);
        h.pro_1=p.layout.program_start;h.pro_2=at-1;h.step_limit=160;
        simulate_spiral_program(h);
        if(h.budget_exhausted)throw std::runtime_error("VM step limit");
        if(measure_read)s.operator_reads+=h.read_seen[p.layout.input_start+1+2+1];
        return int(Check_ans(h,q));
    };
    CopyUpgradeCurriculum curriculum(4,6);
    for(int i=0;i<4;++i)s.old+=solve(curriculum.next(),false);
    for(int i=0;i<6;++i)s.trigger+=solve(curriculum.next(),false);
    for(int v=0;v<8;++v)s.copy+=solve(elementary_problem(ElementaryTask::Copy,3,v),false);
    for(int v=0;v<8;++v)s.flip+=solve(elementary_problem(ElementaryTask::Flip,3,v),true);
    return s;
}

int main() {
    const auto old=copy_loop_program(),prototype=splice_operator_from_copy();
    const int old_words=int(old.size()),new_words=int(prototype.size());
    if(old_words>=new_words)return 1;
    int capture=-1,xor_at=-1;
    for(int i=0;i+5<int(prototype.size());i+=2) {
        if(prototype[i]==8&&prototype[i+1]==17&&prototype[i+2]==16&&
           prototype[i+3]==1&&prototype[i+4]==8&&prototype[i+5]==1)capture=i+2;
        if(prototype[i]==4&&prototype[i+1]==1&&prototype[i+2]==16&&
           prototype[i+3]==1&&prototype[i+4]==21&&prototype[i+5]==0)xor_at=i+2;
    }
    if(capture<0||xor_at<0)return 2;
    const auto baseline=evaluate(prototype,capture,xor_at,old_words,{});
    if(baseline.old!=4||baseline.trigger!=6||baseline.copy!=8||baseline.flip!=0)return 3;
    for(unsigned seed=1;seed<=5;++seed) {
        std::mt19937 rng(seed);Genes best;Score result=baseline;
        int success_step=-1;
        for(int step=1;step<=30;++step) {
            Genes child=best;
            if(rng()%2)child.capture=!child.capture;
            else child.xor_bit=!child.xor_bit;
            const Score test=evaluate(prototype,capture,xor_at,old_words,child);
            if(test.old!=4||test.trigger!=6||test.copy!=8)return 4;
            if(test.flip*100+test.operator_reads>result.flip*100+result.operator_reads) {
                best=child;result=test;
            }
            if(result.flip==8) {success_step=step;break;}
        }
        std::cout<<"seed="<<seed<<" mutation_step="<<success_step<<" COPY="<<result.copy
                 <<"/8 FLIP="<<result.flip<<"/8 operator_reads="<<result.operator_reads
                 <<"/8\n";
        if(success_step<0||!best.capture||!best.xor_bit)return 5;
    }
    std::cout<<"capacity: old="<<old_words<<" words, expanded="<<new_words
             <<" words (additional "<<new_words-old_words<<" words, "
             <<6*(new_words-old_words)<<" bits)\n";
}
