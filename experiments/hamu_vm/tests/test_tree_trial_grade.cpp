#include "../src/tree_trial_grade.hpp"
#include <cassert>
#include <iostream>

int main(){
    HamsterParams p;p.op_order=5;p.layout.status_start=45;
    p.layout.output_start=50;p.layout.work_start=80;
    p.layout.program_start=400;p.layout.total_size=2000;
    Hamster h(1,p);
    auto run=[&](std::vector<int> words,int budget=100){
        int at=p.layout.program_start;
        for(int word:words)for(bool bit:SpiralToken(word,5,1).bits)
            h.memory.at(at++)=bit;
        h.ptr=h.secondary_ptr=h.output_ptr=h.val_ptr=0;
        std::fill(h.val_reg.begin(),h.val_reg.end(),false);
        h.step_limit=budget;h.pro_1=p.layout.program_start;h.pro_2=at-1;
        simulate_spiral_program(h);
    };
    const std::array<bool,3> zero{false,false,false};
    h.memory[40]=h.memory[114]=h.memory[172]=true;
    for(int i=50;i<53;++i)h.written[i]=true;
    assert(!run_tree_graded_trial(h,zero,[&]{run({15,0});}));
    assert(!h.memory[40]&&!h.memory[114]&&!h.memory[172]);
    // Matching zeroes without a fresh WRITE are not an answer.
    assert(!run_tree_graded_trial(h,zero,[&]{run({0,2,3,2,15,0});}));
    assert(!run_tree_graded_trial(h,zero,[&]{run({0,2,3,3,15,0},2);}));
    assert(h.budget_exhausted);
    assert(!run_tree_graded_trial(h,zero,[&]{run({0,2,3,4,15,0});}));
    assert(run_tree_graded_trial(h,zero,[&]{run({0,2,3,3,15,0});}));
    // Exhaustive data coverage for the two candidate programs.
    for(int value=0;value<8;++value)for(int flip=0;flip<2;++flip){
        for(int b=0;b<3;++b)h.memory[10+b]=(value>>(2-b))&1;
        std::array<bool,3> expected{};
        for(int b=0;b<3;++b)expected[b]=((value^(flip?7:0))>>(2-b))&1;
        std::vector<int> candidate={16,1,0,0,14,26,4,3,0,2};
        if(flip)candidate.insert(candidate.end(),{2,3,14,3,5,3});
        else candidate.insert(candidate.end(),{9,3});
        candidate.insert(candidate.end(),{15,0});
        assert(run_tree_graded_trial(h,expected,[&]{run(candidate);}));
        expected[0]=!expected[0];
        assert(!run_tree_graded_trial(h,expected,[&]{run(candidate);}));
    }
    // Correct writes followed by budget exhaustion do not earn confirmation.
    assert(!run_tree_graded_trial(h,zero,[&]{run({0,2,3,3,22,0},3);}));
    // Candidate attempts to publish the confirmation work bits are invalidated.
    assert(run_tree_graded_trial(h,zero,[&]{
        run({0,2,3,3,15,0});h.memory[114]=h.memory[172]=true;
    }));
    assert(!h.memory[114]&&!h.memory[172]);
    std::cout<<"PASS fresh VM tree trial grading: coverage, timeout, stale output and 16 candidates\n";
}
