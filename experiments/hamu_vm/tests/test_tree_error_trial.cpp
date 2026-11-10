#include "../src/tree_error_trial.hpp"
#include <iostream>
#include <set>
static void check_error(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
int main(){
    HamsterParams p;p.layout.status_start=45;p.layout.output_start=50;p.layout.work_start=80;
    p.layout.program_start=700;p.layout.total_size=24000;p.stable_work_bits=400;
    p.tree_start=300;p.tree_capacity=31;p.layout.val_reg_size=12;
    Hamster h(1,p);h.memory[1]=true;
    auto run=[&](Hamster& who,const std::vector<int>& words){
        int at=p.layout.program_start;
        for(int word:words)for(bool bit:SpiralToken(word,5,1).bits)who.memory.at(at++)=bit;
        std::fill(who.val_reg.begin(),who.val_reg.end(),false);who.val_ptr=0;
        who.stop=false;who.budget_exhausted=false;who.executed_steps=0;who.step_limit=4000;
        who.pro_1=p.layout.program_start;who.pro_2=at-1;simulate_spiral_program(who);
        check_error(who.stop&&!who.budget_exhausted,"tree instruction finishes");
    };
    for(auto [question,answer]:{std::pair<int,int>{1,6},{2,3}}){
        std::set<int> tried;
        for(int step=0;step<8;++step){
            const int option=tree_error_next(h,question,0,run);
            check_error(option>=0&&option<8&&tried.insert(option).second,"never repeat wrong answer");
            const bool correct=option==answer;
            tree_error_record(h,question,option,correct,run);
            auto mark=tree_error_probe(h,question,option,run);
            check_error(mark.exists&&mark.correct==correct,"VM tree feedback persisted");
            if(correct)break;
        }
        check_error(tree_error_next(h,question,0,run)==answer,"correct answer reused");
    }
    check_error(tree_error_probe(h,1,3,run).exists&&!tree_error_probe(h,1,3,run).correct,
        "wrong answer remains question-specific");
    check_error(tree_error_probe(h,2,3,run).correct,"separate question remembers success");
    const auto fixed_guest_code=tree_error_guest_choice_program(0);
    tree_error_write_question(h,1);
    check_error(tree_error_next_from_input(h,0,run)==6,"input key routes to question one");
    tree_error_write_question(h,2);
    check_error(tree_error_next_from_input(h,0,run)==3,"same guest code routes to question two");
    tree_error_write_question(h,3);
    check_error(tree_error_next_from_input(h,0,run)==0,"new input key is a new question");
    check_error(fixed_guest_code==tree_error_guest_choice_program(0),
        "guest instruction sequence independent of question key");
    check_error(!h.memory[p.layout.input_start+5],"question token tail remains zero");
    Hamster input_record(55,p);input_record.memory[1]=true;
    tree_error_write_question(input_record,1);
    tree_error_record_from_input(input_record,0,false,run);
    tree_error_write_question(input_record,2);
    tree_error_record_from_input(input_record,0,true,run);
    check_error(tree_error_next_from_input(input_record,0,run)==0,
        "input feedback remembers the second question's correct answer");
    tree_error_write_question(input_record,1);
    check_error(tree_error_next_from_input(input_record,0,run)==1,
        "input feedback keeps first question's wrong answer separate");
    Hamster snapshot=h;snapshot.new_his();Hamster child(2,p);child.copy_hamu(snapshot);child.memory[1]=true;
    check_error(tree_error_next(child,1,0,run)==6&&tree_error_next(child,2,0,run)==3,
        "descendant inherits error tree");
    for(int pattern=0;pattern<16;++pattern){
        Hamster sample(100+pattern,p);sample.memory[1]=true;
        for(int candidate=0;candidate<8;++candidate){
            if((pattern>>(candidate%4))&1)
                tree_error_record(sample,3,candidate,false,run);
        }
        if(pattern%3==0)tree_error_record(sample,3,7,true,run);
        for(int start=0;start<=8;++start){
            const int baseline=tree_error_next_host(sample,3,start,run);
            check_error(tree_error_next(sample,3,start,run)==baseline,
                "guest option traversal matches recursive baseline");
        }
    }
    Hamster exhausted(300,p);exhausted.memory[1]=true;
    for(int candidate=0;candidate<8;++candidate)
        tree_error_record(exhausted,4,candidate,false,run);
    check_error(tree_error_next(exhausted,4,0,run)==-1,"exhausted question has no repeat");
    HamsterParams small=p;small.tree_capacity=4;
    Hamster limited(400,small);limited.memory[1]=true;
    for(int candidate=0;candidate<3;++candidate)
        tree_error_record(limited,5,candidate,false,run);
    check_error(!tree_error_has_free_node(limited),"full tree detected before paid attempt");
    bool full=false;
    try{tree_error_record(limited,5,3,false,run);}catch(const std::runtime_error&){full=true;}
    check_error(full&&!tree_error_probe(limited,5,3,run).exists,
        "full tree rejects a new memory rather than falsely recording it");
    check_error(tree_error_next(limited,5,0,run)==3,
        "without capacity the next guess cannot be remembered");
    tree_error_record(limited,5,2,true,run);
    check_error(tree_error_next(limited,5,0,run)==2,
        "existing node can become a correct answer when tree is full");
    std::cout<<"PASS input-token search and feedback, recursion, inheritance and full-tree refusal\n";
}
