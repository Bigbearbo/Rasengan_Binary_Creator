#include "../src/operator_context_router_vm.hpp"
#include "../src/routed_context_choice_vm.hpp"
#include "../src/pending_operator_vm.hpp"
#include "../src/pending_choice_vm.hpp"
#include "../src/layer_packet.hpp"
#include <cassert>
#include <iostream>

int main() {
    const auto router=operator_context_router_program();
    const auto pending=pending_operator_program();
    const auto choose=routed_context_choice_program();
    const auto pending_choose=pending_choice_program();
    HamsterParams p;p.op_order=5;p.layout.status_start=45;
    p.layout.output_start=50;p.layout.work_start=80;
    p.layout.program_start=140;p.stable_work_bits=20;
    const int pending_start=140+int(router.size())*6;
    const int choice_start=pending_start+int(pending.size())*6;
    const int pending_choice_start=choice_start+int(choose.size())*6;
    p.layout.total_size=pending_choice_start+int(pending_choose.size())*6;
    Hamster h(0,p);
    int at=p.layout.program_start;
    for(const auto& program:{router,pending,choose,pending_choose})
        for(int word:program)for(bool bit:SpiralToken(word,5,1).bits)
            h.memory.at(at++)=bit;
    int cases=0,unseen=0;
    for(int operator_n:{2,3})for(int op=0;op<(1<<operator_n);++op)
        for(int data_n:{2,3})for(int data=0;data<(1<<data_n);++data) {
            Problem blank;h.write_prob(blank);
            const auto bits=encode_layer_packet(op,operator_n,data,data_n);
            for(size_t j=0;j<bits.size();++j)h.memory.at(1+j)=bits[j];
            h.memory[120]=1;h.memory[121]=0; // COPY selects local 0
            h.memory[122]=0;h.memory[123]=1; // FLIP selects local 1
            h.memory[101]=operator_n==3; // known-position width record
            for(int i=127;i<=134;++i)h.memory[i]=0;
            h.stop=false;h.executed_steps=0;h.written[124]=h.written[125]=false;
            h.pro_1=140;h.pro_2=pending_start-1;h.step_limit=80;
            simulate_spiral_program(h);
            const bool known=op<2;
            assert(!h.budget_exhausted&&h.written[124]&&h.written[125]);
            assert(h.memory[125]==known);
            if(known)assert(h.memory[124]==bool(op));
            h.stop=false;h.executed_steps=0;
            h.pro_1=pending_start;h.pro_2=choice_start-1;h.step_limit=120;
            simulate_spiral_program(h);
            assert(!h.budget_exhausted&&h.memory[127]==!known);
            if(!known) {
                assert(h.memory[128]==(operator_n==3));
                for(int j=0;j<3;++j)assert(h.memory[129+j]==h.memory[19+j]);
                for(int j=0;j<3;++j)
                    assert(h.memory[132+j]==bool(op&(1<<(2-j))));
            }
            h.stop=false;h.executed_steps=0;
            h.written[51]=h.written[52]=h.written[53]=false;
            h.pro_1=choice_start;h.pro_2=pending_choice_start-1;
            h.step_limit=65;simulate_spiral_program(h);
            assert(!h.budget_exhausted);
            if(known) {
                assert(h.written[51]&&h.written[52]&&h.written[53]);
                assert(!h.memory[51]&&h.memory[52]==bool(op)&&!h.memory[53]);
                ++cases;
            } else {
                assert(!h.written[51]&&!h.written[52]&&!h.written[53]);
                assert(h.memory[120]&&!h.memory[121]&&!h.memory[122]&&h.memory[123]);
                ++unseen;
            }
        }
    assert(cases==48&&unseen==96);
    Problem blank;h.write_prob(blank);
    const auto interrupted=encode_layer_packet(2,3,0,3);
    for(size_t j=0;j<interrupted.size();++j)h.memory[1+j]=interrupted[j];
    h.memory[101]=1;
    for(int i=127;i<=134;++i)h.memory[i]=0;
    h.stop=false;h.executed_steps=0;h.pro_1=140;h.pro_2=pending_start-1;
    h.step_limit=80;simulate_spiral_program(h);
    assert(!h.budget_exhausted&&!h.memory[125]);
    h.stop=false;h.executed_steps=0;h.budget_exhausted=false;
    h.pro_1=pending_start;h.pro_2=choice_start-1;h.step_limit=25;
    simulate_spiral_program(h);
    assert(h.budget_exhausted&&!h.memory[127]); // incomplete record is not committed
    h.stop=false;h.executed_steps=0;h.budget_exhausted=false;
    h.pro_1=pending_start;h.pro_2=choice_start-1;h.step_limit=120;
    simulate_spiral_program(h);
    assert(!h.budget_exhausted&&h.memory[127]&&!h.memory[132]&&h.memory[133]&&!h.memory[134]);
    auto ask_pending=[&](Hamster& guest,int op,int width,int data,bool expected,int id) {
        Problem q;guest.write_prob(q);
        const auto bits=encode_layer_packet(op,width,data,3);
        for(size_t j=0;j<bits.size();++j)guest.memory[1+j]=bits[j];
        guest.memory[101]=width==3;
        guest.stop=false;guest.executed_steps=0;
        guest.written[51]=guest.written[52]=guest.written[53]=false;
        guest.pro_1=pending_choice_start;guest.pro_2=p.layout.total_size-1;
        guest.step_limit=120;simulate_spiral_program(guest);
        assert(!guest.budget_exhausted&&guest.written[51]==expected);
        if(expected)assert(guest.written[52]&&guest.written[53]&&
                            !guest.memory[51]&&guest.memory[52]==bool(id)&&!guest.memory[53]);
    };
    h.memory[135]=h.memory[136]=1;
    ask_pending(h,2,3,0,true,0);
    ask_pending(h,3,3,0,false,-1); // another unseen word cannot share its slot
    ask_pending(h,2,2,0,false,-1); // equal number, different word width
    ask_pending(h,2,3,7,true,0);  // data does not identify the operator
    h.memory[135]=0;
    ask_pending(h,2,3,1,true,1);
    h.new_his();Hamster child(1,p);child.copy_hamu(h);
    assert(child.memory[127]&&!child.memory[135]&&child.memory[136]);
    ask_pending(child,2,3,2,true,1);
    h.memory[136]=0;
    ask_pending(h,2,3,1,false,-1);
    std::cout<<"PASS 48 known and 96 unseen routes; pending ID, interrupted write, exact-match choice and inheritance\n";
}
