#include "../src/tree_observed_resources.hpp"
#include <iostream>
#include <stdexcept>
static void check(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
static HamsterParams params(){
    HamsterParams p;p.layout.status_start=45;p.layout.output_start=50;p.layout.work_start=80;
    p.layout.program_start=700;p.layout.total_size=24000;p.stable_work_bits=100;
    p.tree_start=600;p.tree_capacity=8;p.layout.val_reg_size=12;return p;
}
static void question(Hamster& h,int data){
    std::fill(h.memory.begin(),h.memory.begin()+45,false);h.memory[1]=true;
    for(int b=0;b<4;++b)h.memory[2+b]=SpiralToken(1,3,1).bits[b];
    for(int b=0;b<3;++b)h.memory[6+b]=SpiralToken(1,2,1).bits[b];
    for(int b=0;b<4;++b)h.memory[9+b]=SpiralToken(data,3,1).bits[b];
}
int main(){
    const auto p=params();const auto zero=tree_four_trial_program(2),copy=tree_four_trial_program(0),flip=tree_four_trial_program(1);
    const std::vector<int> loop={16,1,12,20,12,4};
    const std::array<std::vector<int>,4> table={loop,zero,copy,flip};
    { // No budget: no stale answer, no uncharged instruction or semantic update.
        TreeObservedLearner h(1,p,table);TreeResourceAccount a(0);question(h.hamster,5);
        for(int j=50;j<80;++j){h.hamster.memory[j]=true;h.hamster.written[j]=true;}
        const auto memory=h.hamster.memory;
        check(!run_tree_resource_learning_turn(h,a,{false,false,false},TreeResourcePolicy::Off),"zero budget rejected");
        check(!a.spent&&!a.rewarded&&!a.guest_steps&&!a.fragment_steps&&a.denied==1,"zero budget ledger");
        for(int j=80;j<700;++j)check(h.hamster.memory[j]==memory[j],"zero budget work unchanged");
        for(int j=50;j<80;++j)check(!h.hamster.written[j],"zero budget clears answers");
    }
    { // Observation setup is billable even when its requested fee is unaffordable.
        TreeObservedLearner h(2,p,table);TreeResourceRates rates;rates.observation_fee=100;
        TreeResourceAccount a(40,rates);auto observation=observe_tree_fragment(h.hamster,copy,TreeResourceRunner{h,a});
        check(!observation.valid&&a.spent==40&&a.balance==0&&a.observations==1&&!a.fragment_steps,"partial setup payment");
    }
    { // The guest combines its policy and the host resource sensor, and a child
      // inherits policy memory but receives a separately initialized account.
        TreeObservedLearner h(3,p,table);TreeResourceAccount a(50000);TreeResourceRunner run{h,a};
        initialize_tree_resource_policy(h,a,TreeResourcePolicy::On);
        h.hamster.memory[240]=false;run(h.hamster,tree_observed_resource_export_program(true));
        check(!h.hamster.memory[78]&&h.hamster.memory[79],"guest resource gate false");
        h.hamster.memory[240]=true;run(h.hamster,tree_observed_resource_export_program(true));
        check(h.hamster.memory[78]&&h.hamster.memory[79],"guest resource gate true");
        TreeObservedLearner child(h,4);TreeResourceAccount child_account(1234);
        check(child.hamster.memory[238]&&child_account.balance==1234&&a.balance!=1234,"no resource duplication by inheritance");
    }
    { // This is a real budget-exhausting loop, with distinct step and setup rates.
        TreeObservedLearner h(6,p,table);TreeResourceRates rates;
        rates.fragment_step=3;rates.guest_step=2;rates.observation_fee=1;
        TreeResourceAccount a(12001,rates);
        const auto o=observe_tree_fragment(h.hamster,loop,TreeResourceRunner{h,a});
        check(!o.valid&&o.steps==4000&&a.fragment_steps==4000&&a.setup_spent==1&&a.spent==12001&&a.balance==0&&a.exhausted==1,"real timeout accounting");
    }
    { // A fully funded real positive answer can bind; actual routed answers
      // receive reward only if their fresh three-bit output matches the teacher.
        TreeObservedLearner h(5,p,{zero,copy,flip,tree_four_trial_program(3)});
        TreeResourceAccount a(50000);initialize_tree_resource_policy(h,a,TreeResourcePolicy::Off);question(h.hamster,5);
        auto t=run_tree_resource_learning_turn(h,a,{false,false,false},TreeResourcePolicy::Off);
        check(t&&t->learning.confirmed&&t->learning.correct,"funded confirmation");
        const auto reward=a.rewarded;question(h.hamster,6);
        check(run_tree_resource_route(h,a,{false,false,false})&&a.rewarded==reward+a.rates.correct_reward,"funded route reward");
        question(h.hamster,6);const auto before=a.rewarded;
        check(!run_tree_resource_route(h,a,{true,true,true})&&a.rewarded==before,"wrong route cannot earn");
        check(a.balance==50000+a.rewarded-a.spent,"funded account conservation");
    }
    {TreeResourceRates r;r.guest_step=0;bool bad=false;try{TreeResourceAccount a(1,r);}catch(const std::invalid_argument&){bad=true;}
        check(bad,"reject zero step tariff");TreeResourceAccount a(TreeResourceAccount::capacity-1);a.reward();
        check(a.balance==TreeResourceAccount::capacity&&a.rewarded==1,"reward cap");}
    std::cout<<"initial,observation_fee,reward,policy,valid,correct,recovered,spent,rewarded,balance,guest_steps,fragment_steps,observations,denied,exhausted\n";
    for(int initial:{12000,50000})for(int fee:{0,200})for(int reward:{0,6000})for(int mode=0;mode<4;++mode){
        TreeResourceRates rates;rates.observation_fee=fee;rates.correct_reward=reward;rates.recovery_reserve=30000;
        TreeResourceAccount account(initial,rates);TreeObservedLearner h(10+mode,p,table);
        const auto policy=static_cast<TreeResourcePolicy>(mode);initialize_tree_resource_policy(h,account,policy);
        int valid=0,correct=0,recovered=0;
        for(int turn=0;turn<4;++turn){
            question(h.hamster,5);const auto t=run_tree_resource_learning_turn(h,account,{false,false,false},policy);
            if(t){valid+=t->learning.valid;correct+=t->learning.correct;recovered+=t->recovered;
                check(!t->learning.confirmed,"permanent unknown must block confirmation");}
            check(account.balance==initial+account.rewarded-account.spent&&account.balance>=0,"sweep conservation");
        }
        check(account.spent==account.guest_steps*rates.guest_step+account.fragment_steps*rates.fragment_step+
            account.setup_spent,"all attempted work charged");
        check(account.rewarded==int64_t(correct)*reward,"reward must follow actual correctness");
        if(initial==50000&&mode==1)check(correct==4&&recovered==4,"funded recovery coverage");
        if(mode==0)check(!correct&&!recovered,"off cannot bypass invalid first candidate");
        if(initial==12000&&mode==3)check(!recovered,"low resource guest declines recovery");
        std::cout<<initial<<','<<fee<<','<<reward<<','<<mode<<','<<valid<<','<<correct<<','<<recovered<<','<<account.spent<<','<<account.rewarded<<','<<account.balance<<','<<account.guest_steps<<','<<account.fragment_steps<<','<<account.observations<<','<<account.denied<<','<<account.exhausted<<'\n';
    }
    std::cout<<"PASS 32 resource scenarios: bounded execution, exact accounting, actual-answer rewards, guest gate, inheritance, unknown evidence\n";
}
