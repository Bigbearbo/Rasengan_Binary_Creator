#include "../src/layered_vm_program.hpp"
#include "../src/layer_packet.hpp"
#include "../src/math_questions.hpp"
#include "../src/feedback_capture_vm.hpp"
#include "../src/work_consistency_vm.hpp"
#include "../src/direct_mask_update_vm.hpp"
#include "../src/context_choice_vm.hpp"
#include "../src/context_feedback_choice_vm.hpp"
#include "../src/operator_context_router_vm.hpp"
#include "../src/routed_context_choice_vm.hpp"
#include "../src/pending_operator_vm.hpp"
#include <array>
#include <iostream>

int main() {
    const auto code=layered_vm_program(-1);
    const auto capture=feedback_capture_program();
    const auto route=operator_context_router_program();
    const auto copy_check=work_bitwise_consistency_program(false);
    const auto flip_check=work_bitwise_consistency_program(true);
    const int capture_start=140+int(code.size())*6;
    const int route_start=capture_start+int(capture.size())*6;
    const int copy_start=route_start+int(route.size())*6;
    const int flip_start=copy_start+int(copy_check.size())*6;
    std::array<std::vector<int>,4> feedback_choices;
    std::array<int,4> update_starts;
    int program_end=flip_start+int(flip_check.size())*6;
    for(int slot=0;slot<4;++slot) {
        update_starts[slot]=program_end;
        feedback_choices[slot]=context_feedback_choice_program(slot<2?0:2,slot%2);
        program_end+=int(feedback_choices[slot].size())*6;
    }
    const auto routed_choice=routed_context_choice_program();
    const auto pending=pending_operator_program();
    const int routed_start=program_end;
    program_end+=int(routed_choice.size())*6;
    const int pending_start=program_end;
    program_end+=int(pending.size())*6;
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=140;p.stable_work_bits=20;
    p.layout.total_size=program_end;
    Hamster h(0,p);int at=p.layout.program_start;
    for(int w:code)for(bool b:SpiralToken(w,5,1).bits)h.memory.at(at++)=b;
    for(int w:capture)for(bool b:SpiralToken(w,5,1).bits)h.memory.at(at++)=b;
    for(int w:route)for(bool b:SpiralToken(w,5,1).bits)h.memory.at(at++)=b;
    for(int w:copy_check)for(bool b:SpiralToken(w,5,1).bits)h.memory.at(at++)=b;
    for(int w:flip_check)for(bool b:SpiralToken(w,5,1).bits)h.memory.at(at++)=b;
    for(const auto& program:feedback_choices)
        for(int w:program)for(bool b:SpiralToken(w,5,1).bits)h.memory.at(at++)=b;
    for(int w:routed_choice)for(bool b:SpiralToken(w,5,1).bits)h.memory.at(at++)=b;
    for(int w:pending)for(bool b:SpiralToken(w,5,1).bits)h.memory.at(at++)=b;
    for(int slot=0;slot<4;++slot)h.memory[120+slot]=1;
    int pos=p.layout.work_start;
    for(int j=0;j<18;++j)h.memory[pos++]=1;
    h.memory[pos++]=0;
    for(int word=0;word<2;++word) {
        h.memory[pos++]=1;h.memory[pos++]=1;h.memory[pos++]=0;
    }
    auto solve=[&](ElementaryTask task,int op_n,int data_n,int value,bool alternate_target=false) {
        const int op=task==ElementaryTask::Flip?1:0;
        auto q=elementary_problem_with_operator_order(task,op_n,data_n,value);
        if(alternate_target)q.answer=SpiralToken(value,data_n,1); // COPY target for FLIP trial
        const auto bits=encode_layer_packet(op,op_n,value,data_n);
        h.write_prob(q);
        for(size_t j=0;j<bits.size();++j)h.memory[p.layout.input_start+1+j]=bits[j];
        h.pro_1=p.layout.program_start;h.pro_2=capture_start-1;h.step_limit=650;
        simulate_spiral_program(h);
        const bool correct=Check_ans(h,q);
        if(h.budget_exhausted||h.work_insert_blocked||correct==alternate_target) {
            std::cerr<<"FAIL op="<<op_n<<" data="<<data_n
                     <<" value="<<value<<" steps="<<h.executed_steps<<'\n';return false;
        }
        {
            h.memory[40]=correct; // teacher supplies only the grade
            h.stop=false;h.executed_steps=0;
            h.pro_1=capture_start;h.pro_2=route_start-1;h.step_limit=170;
            simulate_spiral_program(h);
            if(h.budget_exhausted||!h.written[114]||h.memory[114]!=correct){std::cerr<<"capture failed\n";return false;}
            for(int bit=2;bit>=0;--bit)
                if(h.memory[110-bit]!=bool((alternate_target?((1<<data_n)-1-value):q.answer.value)&(1<<bit))||
                   h.memory[113-bit]!=bool(value&(1<<bit))){std::cerr<<"capture bits failed\n";return false;}
            h.stop=false;h.executed_steps=0;h.written[124]=h.written[125]=false;
            h.read_seen[20]=h.read_seen[21]=false;
            h.pro_1=route_start;h.pro_2=copy_start-1;h.step_limit=80;
            simulate_spiral_program(h);
            if(h.budget_exhausted||!h.written[124]||!h.written[125]||!h.memory[125]||
               h.memory[124]!=(task==ElementaryTask::Flip)){
                std::cerr<<"guest operator context routing failed op="<<op_n<<" data="<<data_n
                         <<" task="<<op<<" record="<<h.memory[101]
                         <<" bit20="<<h.memory[20]<<" bit21="<<h.memory[21]
                         <<" written="<<h.written[124]<<" got="<<h.memory[124]
                         <<" read20="<<h.read_seen[20]<<" read21="<<h.read_seen[21]
                         <<" reg="<<h.val_reg[0]<<" vp="<<h.val_ptr
                         <<" p19="<<h.memory[19]<<" p22="<<h.memory[22]
                         <<" steps="<<h.executed_steps<<'\n';return false;
            }
            const int base=h.memory[124]?2:0;
            for(auto hypothesis:{ElementaryTask::Copy,ElementaryTask::Flip}) {
                h.stop=false;h.executed_steps=0;
                h.written[55]=false;
                h.pro_1=hypothesis==ElementaryTask::Copy?copy_start:flip_start;
                h.pro_2=hypothesis==ElementaryTask::Copy?flip_start-1:update_starts[0]-1;
                h.step_limit=110;
                simulate_spiral_program(h);
                if(h.budget_exhausted||!h.written[55]||
                   h.memory[55]!=((hypothesis==task)==correct)){std::cerr<<"check failed\n";return false;}
                const int slot=base+(hypothesis==ElementaryTask::Flip);
                const bool expected=h.memory[120+slot]&&((hypothesis==task)==correct);
                h.stop=false;h.executed_steps=0;h.written[120+slot]=false;
                h.written[51]=false;h.written[52]=false;h.written[53]=false;
                h.pro_1=update_starts[slot];
                h.pro_2=slot==3?routed_start-1:update_starts[slot+1]-1;
                h.step_limit=80;
                simulate_spiral_program(h);
                if(h.budget_exhausted||!h.written[120+slot]||
                   h.memory[120+slot]!=expected){
                    std::cerr<<"update failed slot="<<slot<<" written="<<h.written[120+slot]
                             <<" value="<<h.memory[120+slot]<<" check="<<h.memory[55]<<"\n";
                    return false;
                }
                const int next=h.memory[120+base]?0:h.memory[121+base]?1:-1;
                if(next<0) {
                    if(h.written[51])return false;
                } else if(!h.written[51]||!h.written[52]||!h.written[53]||
                          h.memory[51]||h.memory[52]!=bool(next)||h.memory[53])return false;
            }
        }
        return true;
    };
    if(!solve(ElementaryTask::Copy,2,2,2))return 1;
    if(!solve(ElementaryTask::Copy,2,3,1))return 2; // data old tail -> 1
    const int work=p.layout.work_start+19;
    if(h.memory[work+2]||!h.memory[work+3+2])return 3;
    if(!solve(ElementaryTask::Flip,3,3,5))return 4; // operator old tail -> 1
    if(!h.memory[p.layout.work_start-1]||
       !h.written[p.layout.work_start-1])return 7; // flag survived INSERT
    const int grown[]={1,1,1,0,1,1,1,0};
    for(int j=0;j<8;++j)if(h.memory[work+j]!=grown[j])return 5;
    if(!solve(ElementaryTask::Copy,3,3,0)||
       !solve(ElementaryTask::Flip,3,3,7))return 6;
    for(int slot=0;slot<4;++slot)
        if(h.memory[120+slot]!=(slot==0||slot==3))return 8;
    h.new_his();Hamster child(1,p);child.copy_hamu(h);
    for(int slot=0;slot<4;++slot)
        if(child.memory[120+slot]!=h.memory[120+slot])return 9;
    auto route_and_choose=[&](Hamster& guest,int op,bool expect_choice,int expected,
                              bool known=true) {
        Problem blank;guest.write_prob(blank);
        const auto bits=encode_layer_packet(op,3,0,3);
        for(size_t j=0;j<bits.size();++j)
            guest.memory[p.layout.input_start+1+j]=bits[j];
        guest.stop=false;guest.executed_steps=0;guest.written[124]=guest.written[125]=false;
        guest.pro_1=route_start;guest.pro_2=copy_start-1;
        guest.step_limit=120;simulate_spiral_program(guest);
        if(guest.budget_exhausted||!guest.written[124]||!guest.written[125]||
           guest.memory[125]!=known||(known&&guest.memory[124]!=bool(op))){
            std::cerr<<"route failed op="<<op<<" got="<<guest.memory[124]<<"\n";return false;
        }
        guest.stop=false;guest.executed_steps=0;
        guest.pro_1=pending_start;guest.pro_2=p.layout.total_size-1;
        guest.step_limit=120;simulate_spiral_program(guest);
        if(guest.budget_exhausted)return false;
        guest.stop=false;guest.executed_steps=0;
        guest.written[51]=guest.written[52]=guest.written[53]=false;
        guest.pro_1=routed_start;guest.pro_2=pending_start-1;
        guest.step_limit=65;simulate_spiral_program(guest);
        if(guest.budget_exhausted||guest.written[51]!=expect_choice){
            std::cerr<<"routed choice failed op="<<op<<" written="<<guest.written[51]
                     <<" got="<<guest.memory[52]<<" steps="<<guest.executed_steps<<"\n";return false;
        }
        return !expect_choice||
            (guest.written[52]&&guest.written[53]&&!guest.memory[51]&&
             guest.memory[52]==bool(expected)&&!guest.memory[53]);
    };
    for(int context:{0,2}) {
        if(!route_and_choose(child,context==2, true,context==2))return 10;
    }
    if(!solve(ElementaryTask::Flip,3,3,5,true))return 11;
    if(h.memory[122]||h.memory[123])return 12;
    if(!route_and_choose(h,1,false,-1))return 13;
    if(!h.memory[120]||h.memory[121])return 14; // other context untouched
    h.new_his();Hamster after_failure(2,p);after_failure.copy_hamu(h);
    const std::array<bool,4> before_unseen={after_failure.memory[120],after_failure.memory[121],
                                           after_failure.memory[122],after_failure.memory[123]};
    if(!route_and_choose(after_failure,2,false,-1,false))return 17; // a new word, not an error
    if(!after_failure.memory[127]||!after_failure.memory[128]||
       after_failure.memory[129]||!after_failure.memory[130]||after_failure.memory[131])return 19;
    if(after_failure.memory[132]||!after_failure.memory[133]||after_failure.memory[134])return 24;
    std::array<bool,8> first_pending;
    for(int i=0;i<8;++i)first_pending[i]=after_failure.memory[127+i];
    if(!route_and_choose(after_failure,3,false,-1,false))return 20; // preserve first unseen
    for(int i=0;i<8;++i)
        if(after_failure.memory[127+i]!=first_pending[i])return 21;
    for(int slot=0;slot<4;++slot)
        if(after_failure.memory[120+slot]!=before_unseen[slot])return 18;
    if(!route_and_choose(after_failure,0,true,0))return 15;
    if(!route_and_choose(after_failure,1,false,-1))return 16;
    for(int i=0;i<8;++i)
        if(after_failure.memory[127+i]!=first_pending[i])return 22;
    after_failure.new_his();Hamster pending_child(3,p);pending_child.copy_hamu(after_failure);
    for(int i=0;i<8;++i)
        if(pending_child.memory[127+i]!=first_pending[i])return 23;
    std::cout<<"PASS one layered VM: guest operator context and routed choice, actual answers, guest feedback+choice,"
                " growth, first unseen word saved and inherited, recovery, isolated contexts\n";
}
