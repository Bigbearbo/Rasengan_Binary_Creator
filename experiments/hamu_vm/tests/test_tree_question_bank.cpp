#include "../src/tree_question_experiment.hpp"
#include <iostream>
#include <stdexcept>
static void check_question(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
int main(){
    Hamster h(1,tree_question_params());
    for(int width:{2,3})for(int op=0;op<(1<<width);++op)for(int data=0;data<8;++data)
        for(auto kind:{TreeQuestionKind::Zero,TreeQuestionKind::Copy,TreeQuestionKind::Flip,
            TreeQuestionKind::ToggleLast,TreeQuestionKind::ToggleMiddle,TreeQuestionKind::ToggleFirst}){
            TreeQuestion q{width,op,data,kind};write_tree_question(h,q);
            const auto x=tree_question_answer(q);
            check_question(4*int(x[0])+2*int(x[1])+int(x[2])==tree_question_value(q),"oracle bits");
            check_question(h.memory[1]&&!h.memory[0]&&!h.memory[5],"startup/category format");
            const auto encoded=SpiralToken(op,width,1).bits;
            for(size_t i=0;i<encoded.size();++i)check_question(h.memory[6+i]==encoded[i],"operator encoding");
            const auto d=SpiralToken(data,3,1).bits;
            for(size_t i=0;i<d.size();++i)check_question(h.memory[7+width+i]==d[i],"data encoding");
            h.memory[40]=true; // next question must clear the teacher sensor
        }
    bool bad=false;try{write_tree_question(h,{2,4,0,TreeQuestionKind::Zero});}
    catch(const std::invalid_argument&){bad=true;}
    check_question(bad,"reject invalid fields");
    const auto summary=run_tree_question_curriculum();
    check_question(summary.attempted==12&&summary.confirmed==4,"all four meanings learned");
    check_question(summary.routed==32,"all data routed by both descendants");
    check_question(summary.correct>0&&summary.valid>=summary.correct&&summary.balance>0,"funded curriculum");
    // Swap the authored catalogue: a middle-bit toggle is genuinely different
    // from COPY, FLIP, ZERO and last-bit toggle, yet the observed learner does
    // not need a new hard-coded prediction formula.
    auto alternatives=tree_question_fragments();
    alternatives[3]=tree_question_toggle_program(1);
    TreeObservedLearner learner(5,tree_question_params(),alternatives);
    TreeResourceRates rates;rates.correct_reward=0;
    TreeResourceAccount account(1000000,rates);
    initialize_tree_resource_policy(learner,account,TreeResourcePolicy::Off);
    int alternative_confirms=0;
    for(const TreeQuestion q:std::array<TreeQuestion,4>{{
        {2,3,0,TreeQuestionKind::ToggleMiddle},{2,3,5,TreeQuestionKind::ToggleMiddle},
        {2,3,1,TreeQuestionKind::ToggleMiddle},{2,3,7,TreeQuestionKind::ToggleMiddle}}}){
        write_tree_question(learner.hamster,q);
        auto t=run_tree_resource_learning_turn(learner,account,tree_question_answer(q),TreeResourcePolicy::Off);
        check_question(t.has_value(),"middle-toggle learning turn");
        alternative_confirms+=t->learning.confirmed;
        if(t->learning.confirmed)break;
    }
    check_question(alternative_confirms==1,"middle-toggle confirmation");
    TreeObservedLearner descendant(learner,6);
    TreeResourceAccount child_account(1000000,rates);
    for(int data=0;data<8;++data){
        TreeQuestion q{2,3,data,TreeQuestionKind::ToggleMiddle};
        write_tree_question(descendant.hamster,q);
        check_question(run_tree_resource_route(descendant,child_account,tree_question_answer(q)),"middle-toggle route");
    }
    check_question(account.conserved()&&child_account.conserved(),"alternative ledger");
    std::cout<<"PASS 576 encoded questions, five tested meanings across two operator widths, 40 descendant routes; "
             <<"valid="<<summary.valid<<" correct="<<summary.correct
             <<" confirmed="<<summary.confirmed<<" spent="<<summary.spent<<'\n';
}
