#include "../src/tree_observed_learner.hpp"
#include <iostream>
#include <stdexcept>

static void check(bool ok,const char* what){if(!ok)throw std::runtime_error(what);}
struct Counts {long long guest=0,request=0,recovery=0,fragment=0,policy=0,observations=0,failed=0;};
struct Outcome {Counts learning;int confirmed_at=0,valid=0,correct=0,recovered=0;};

// Failure schedule belongs to (question index, fragment code), not the number
// of previous probes. Both policies face the same two exhausted executions.
Outcome experiment(int mode,bool failing_is_correct){
    const bool recover=mode==1,guest_policy=mode==2;
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=700;p.layout.total_size=24000;
    p.stable_work_bits=100;p.tree_start=600;p.tree_capacity=8;p.layout.val_reg_size=12;
    auto xor1=tree_width_trial_program(false);xor1.resize(xor1.size()-2);
    const std::vector<int> toggle={0,0,14,17,4,1,0,2,14,18,5,1,15,0};
    xor1.insert(xor1.end(),toggle.begin(),toggle.end());
    const auto copy=tree_four_trial_program(0),zero=tree_four_trial_program(2),flip=tree_four_trial_program(1);
    const std::array<std::vector<int>,4> table=failing_is_correct?
        std::array<std::vector<int>,4>{copy,zero,flip,xor1}:
        std::array<std::vector<int>,4>{zero,xor1,copy,flip};
    TreeObservedLearner learner(1,p,table);Hamster* active=&learner.hamster;
    const auto request0=tree_observed_request_program(57),request1=tree_observed_request_program(70);
    const auto recover0=tree_observed_recover_choice_program(57),recover1=tree_observed_recover_choice_program(70);
    Counts counts;Outcome result;int question_index=0;bool inject=true;
    auto run=[&](Hamster& h,const std::vector<int>& code){
        const bool probe=&h!=active;
        const bool fail=probe&&inject&&question_index<2&&code==table[0];
        int at=p.layout.program_start;
        for(int word:code)for(bool b:SpiralToken(word,5,1).bits)h.memory.at(at++)=b;
        std::fill(h.val_reg.begin(),h.val_reg.end(),false);h.val_ptr=0;
        h.stop=false;h.budget_exhausted=false;h.executed_steps=0;h.step_limit=fail?0:4000;
        h.pro_1=p.layout.program_start;h.pro_2=at-1;simulate_spiral_program(h);
        check(h.stop&&h.budget_exhausted==fail,"execution budget");
        if(probe){counts.fragment+=h.executed_steps;++counts.observations;counts.failed+=fail;}
        else if(code==request0||code==request1)counts.request+=h.executed_steps;
        else if(code==recover0||code==recover1)counts.recovery+=h.executed_steps;
        else if(code==tree_observed_policy_export_program()||code==tree_observed_policy_react_program())counts.policy+=h.executed_steps;
        else counts.guest+=h.executed_steps;
    };
    auto question=[&](Hamster& h,int data){
        std::fill(h.memory.begin(),h.memory.begin()+45,false);h.memory[1]=true;
        for(int b=0;b<4;++b)h.memory[2+b]=SpiralToken(1,3,1).bits[b];
        for(int b=0;b<3;++b)h.memory[6+b]=SpiralToken(1,2,1).bits[b];
        for(int b=0;b<4;++b)h.memory[9+b]=SpiralToken(data,3,1).bits[b];
    };
    const std::array<bool,3> expected={true,false,true};
    const int correct_id=failing_is_correct?0:2;
    if(guest_policy){run(learner.hamster,tree_observed_policy_set_program(false));counts={};}
    for(question_index=0;question_index<6;++question_index){
        question(learner.hamster,5);
        if(result.confirmed_at){
            const auto id=run_tree_observed_route(learner,run);
            check(id&&*id==correct_id,"post-learning route");
            ++result.valid;++result.correct;continue;
        }
        const auto t=guest_policy?run_tree_observed_policy_turn(learner,expected,run):
            run_tree_observed_learning_turn(learner,expected,run,recover);
        check(bool(t),"learning turn");result.valid+=t->learning.valid;
        result.correct+=t->learning.correct;result.recovered+=t->recovered;
        if(question_index<2){
            check(!t->learning.confirmed,"cannot confirm with unknown alternative");
            check(learner.hamster.memory[80+tree_four_mask(57)],"failure must remain unknown");
            check(t->initially_invalid,"initial failure sensor");
            if(guest_policy)check(learner.hamster.memory[238],"guest enables after failure");
            check(t->learning.valid==(recover||(guest_policy&&question_index==1)),"recovery must yield a valid alternate");
        }
        if(t->learning.confirmed){
            check(t->learning.candidate==correct_id,"confirmed wrong fragment");
            result.confirmed_at=question_index+1;result.learning=counts;
            check(!learner.hamster.memory[127],"confirmed pending slot reclaimed");
        }
    }
    check(result.confirmed_at>0,"transient failure did not finish");
    inject=false;
    TreeObservedLearner child(learner,2);
    if(guest_policy){
        check(child.hamster.memory[238],"inherited policy");active=&child.hamster;
        run(child.hamster,tree_observed_policy_set_program(false));
        check(!child.hamster.memory[238]&&learner.hamster.memory[238],"independent child policy");
    }
    for(auto* who:{&learner,&child}){
        active=&who->hamster;
        for(int data=0;data<8;++data){
            question(*active,data);const auto id=run_tree_observed_route(*who,run);
            check(id&&*id==correct_id,"parent/child fragment index");
            for(int b=0;b<3;++b)check(active->written[50+b]&&active->memory[50+b]==bool(data&(4>>b)),"parent/child answer");
        }
    }
    return result;
}

int main(){
    { // A partial policy export cannot start learning or leave stale answers.
        HamsterParams p;p.layout.status_start=45;p.layout.output_start=50;
        p.layout.work_start=80;p.layout.program_start=700;p.layout.total_size=24000;
        p.stable_work_bits=100;p.tree_start=600;p.tree_capacity=8;p.layout.val_reg_size=12;
        const auto copy=tree_four_trial_program(0);
        TreeObservedLearner interrupted(9,p,{copy,copy,copy,copy});
        for(int i=50;i<80;++i){interrupted.hamster.memory[i]=true;interrupted.hamster.written[i]=true;}
        const auto before=interrupted.hamster.memory;
        auto short_run=[&](Hamster& h,const std::vector<int>& code){
            int at=700;for(int word:code)for(bool b:SpiralToken(word,5,1).bits)h.memory.at(at++)=b;
            h.stop=false;h.budget_exhausted=false;h.executed_steps=0;h.step_limit=2;
            h.pro_1=700;h.pro_2=at-1;simulate_spiral_program(h);
        };
        check(!run_tree_observed_policy_turn(interrupted,{true,false,true},short_run),"partial policy rejected");
        for(int i=80;i<700;++i)check(interrupted.hamster.memory[i]==before[i],"no learning before policy commit");
        for(int i=50;i<80;++i)check(!interrupted.hamster.written[i],"clear stale policy and answer");
    }
    std::cout<<"failing_fragment,recovery,confirmed_turn,valid_of_6,correct_of_6,recovered,learning_guest,learning_request,learning_recovery,learning_fragment,learning_policy,learning_observations,failed_observations\n";
    for(bool correct:{false,true}){
        Outcome outcomes[3];
        for(int enabled=0;enabled<3;++enabled){
            const auto r=experiment(enabled,correct);outcomes[enabled]=r;const auto c=r.learning;
            std::cout<<(correct?"COPY":"ZERO")<<','<<enabled<<','<<r.confirmed_at<<','<<r.valid<<','<<r.correct<<','<<r.recovered<<','<<c.guest<<','<<c.request<<','<<c.recovery<<','<<c.fragment<<','<<c.policy<<','<<c.observations<<','<<c.failed<<'\n';
        }
        check(outcomes[0].learning.failed==2&&outcomes[1].learning.failed==2,"unequal failure schedule");
        check(outcomes[1].valid==6&&outcomes[0].valid==4,"valid-answer coverage");
        check(outcomes[1].recovered==2,"recovery count");
        check(outcomes[0].confirmed_at==(correct?3:5),"baseline confirmation timing");
        check(outcomes[1].confirmed_at==(correct?3:4),"recovery confirmation timing");
        check(outcomes[2].confirmed_at==(correct?3:4)&&outcomes[2].valid==5&&outcomes[2].recovered==1,"adaptive timing and coverage");
        check(outcomes[2].learning.policy>0&&outcomes[0].learning.policy==0&&outcomes[1].learning.policy==0,"policy costs");
    }
    std::cout<<"PASS transient failures: identical schedule, no semantic elimination from failure, confirmation, binding, reclamation, 96 parent/child routes, guest policy inheritance and independent rewrite\n";
}
