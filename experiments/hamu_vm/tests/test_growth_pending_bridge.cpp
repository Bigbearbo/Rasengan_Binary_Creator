#include "../src/integrated_zero_program.hpp"
#include "../src/layer_packet.hpp"
#include "../src/math_questions.hpp"
#include "../src/operator_context_router_vm.hpp"
#include "../src/pending_operator_vm.hpp"
#include <cassert>
#include <iostream>

int main() {
    const auto genome=integrated_zero_program(15);
    const auto route=operator_context_router_program();
    const auto pending=pending_operator_program();
    const int program=140;
    const int route_start=program+int(genome.words.size())*6;
    const int pending_start=route_start+int(route.size())*6;
    const int end=pending_start+int(pending.size())*6;
    HamsterParams p;p.op_order=5;p.layout.status_start=45;
    p.layout.output_start=50;p.layout.work_start=80;p.layout.program_start=program;
    p.layout.total_size=end;p.stable_work_bits=20;
    Hamster h(31,p);int at=program;
    for(const auto& words:{genome.words,route,pending})
        for(int word:words)for(bool bit:SpiralToken(word,5,1).bits)h.memory.at(at++)=bit;
    assert(at==end);
    for(int i=80;i<98;++i)h.memory[i]=1;
    h.memory[98]=0; // fixed L2 -> L1 prefix
    h.memory[99]=h.memory[100]=1;h.memory[101]=0; // operator n=2: 110
    h.memory[102]=h.memory[103]=1;h.memory[104]=0; // data n=2: 110
    auto ask=[&](int op,int op_n,int value,ElementaryTask meaning,bool score) {
        auto q=elementary_problem(meaning,2,value);
        q.question[0]=SpiralToken(op,op_n,1);
        h.write_prob(q);
        const auto bits=encode_layer_packet(op,op_n,value,2);
        for(size_t j=0;j<bits.size();++j)h.memory[1+j]=bits[j];
        h.pro_1=program;h.pro_2=route_start-1;h.step_limit=900;
        simulate_spiral_program(h);
        assert(!h.budget_exhausted&&!h.work_insert_blocked);
        if(score)assert(Check_ans(h,q));
    };
    ask(1,2,1,ElementaryTask::Flip,true);
    assert(!h.memory[101]);
    ask(1,3,1,ElementaryTask::Flip,true); // old tail 0 becomes information 1
    assert(h.memory[101]); // guest grew the operator position by one bit
    // New word ID 3 arrives after the width transition. Its meaning is
    // deliberately not supplied to the guest at this recording stage.
    h.write_prob(elementary_problem_with_operator_order(ElementaryTask::Flip,3,2,1));
    const auto bits=encode_layer_packet(3,3,1,2);
    for(size_t j=0;j<bits.size();++j)h.memory[1+j]=bits[j];
    auto run=[&](int first,int last,int limit) {
        h.stop=false;h.executed_steps=0;h.pro_1=first;h.pro_2=last-1;
        h.step_limit=limit;simulate_spiral_program(h);
        assert(!h.budget_exhausted&&!h.work_insert_blocked);
    };
    run(route_start,pending_start,80);
    assert(!h.memory[125]); // unseen operator, not malformed input
    run(pending_start,end,120);
    assert(h.memory[127]&&h.memory[128]); // pending and n=3
    for(int i=0;i<3;++i)assert(h.memory[129+i]==h.memory[19+i]);
    assert(!h.memory[132]&&h.memory[133]&&h.memory[134]); // numeric ID 3
    std::cout<<"PASS n2 -> n3 operator growth then pending ID 3 recording\n";
}
