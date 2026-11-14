#include "loop_vm_program.hpp"
#include "math_questions.hpp"
#include "task_upgrade.hpp"
#include <iostream>
#include <random>

struct Counts {int old=0,trigger=0,new_copy=0;};
static Counts evaluate(const std::vector<int>& code,int base_words) {
    HamsterParams p;p.op_order=5;
    p.layout.total_size=p.layout.program_start+base_words*6;
    Hamster h(0,p);
    const int extra=int(code.size())-base_words;
    if(extra<0||extra%2)throw std::runtime_error("unaligned growth");
    if(extra)h.extend_program_capacity(extra);
    int at=p.layout.program_start;
    for(int word:code)for(bool bit:SpiralToken(word,5,1).bits)h.memory.at(at++)=bit;
    for(int j=0;j<9;++j)h.memory[p.layout.work_start+j]=(j%3!=2);
    Counts r;CopyUpgradeCurriculum curriculum(4,6);
    auto solve=[&](const Problem& q) {
        put_started_question(h,q);
        h.pro_1=p.layout.program_start;h.pro_2=at-1;h.step_limit=160;
        simulate_spiral_program(h);
        return int(!h.budget_exhausted&&Check_ans(h,q));
    };
    for(int i=0;i<4;++i)r.old+=solve(curriculum.next());
    for(int i=0;i<6;++i)r.trigger+=solve(curriculum.next());
    for(int v=0;v<8;++v)r.new_copy+=solve(elementary_problem(ElementaryTask::Copy,3,v));
    return r;
}
static bool survives(const Counts& r) {return r.old==4&&r.trigger==6&&r.new_copy==8;}

int main() {
    const auto parent=copy_loop_program();
    const int base=int(parent.size());
    if(base!=118||!survives(evaluate(parent,base)))return 1;
    int one_survives=0,one_old=0;
    std::vector<int> safe_slots;
    for(int slot=0;slot<=base;slot+=2) {
        auto candidate=parent;
        candidate.insert(candidate.begin()+slot,{16,31}); // neutral pair, no jump repair
        const auto result=evaluate(candidate,base);
        one_old+=result.old==4;
        if(survives(result)) {++one_survives;safe_slots.push_back(slot);}
    }
    int four_survives=0,four_old=0;
    std::mt19937 rng(37);
    for(int trial=0;trial<200;++trial) {
        auto candidate=parent;
        for(int insert=0;insert<4;++insert) {
            const int slot=2*(rng()%(candidate.size()/2+1));
            candidate.insert(candidate.begin()+slot,{16,31});
        }
        const auto result=evaluate(candidate,base);
        four_old+=result.old==4;
        four_survives+=survives(result);
    }
    std::cout<<"selected one-pair insertions (four accepted pairs):";
    for(unsigned seed=1;seed<=5;++seed) {
        std::mt19937 select_rng(seed);
        auto selected=parent;
        int attempts=0;
        for(int accepted=0;accepted<4;) {
            if(++attempts>500)return 3;
            auto child=selected;
            const int slot=2*(select_rng()%(child.size()/2+1));
            child.insert(child.begin()+slot,{16,31});
            if(survives(evaluate(child,base))) {selected=std::move(child);++accepted;}
        }
        std::cout<<" seed"<<seed<<"="<<attempts;
    }
    std::cout<<"\n";
    std::cout<<"one neutral pair: preserve old="<<one_old<<"/60,"
             <<" full COPY growth="<<one_survives<<"/60\n"
             <<"four neutral pairs (8 words / 48 bits), 200 seeded trials: preserve old="
             <<four_old<<"/200, full COPY growth="<<four_survives<<"/200\n";
    std::cout<<"single-pair surviving word offsets:";
    for(int slot:safe_slots)std::cout<<" "<<slot;
    std::cout<<"\n";
    if(one_survives>=60||four_survives>=200||one_survives==0)return 2;
}
