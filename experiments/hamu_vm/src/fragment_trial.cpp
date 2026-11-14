#define INTEGRATED_ZERO_NO_MAIN
#include "integrated_zero_search.cpp"
#include "fragment_transaction.hpp"
#include <cassert>

int main() {
    auto agent=integrated_zero_program(15); // current ZERO slot halts, no answer
    const auto original=agent.words;
    bool rejected=false;
    try {FragmentTransaction invalid(agent,std::vector<int>(34,0));}
    catch(const std::invalid_argument&){rejected=true;}
    assert(rejected&&agent.words==original);
    // Library candidates are human-written. The host tries them in order.
    const std::vector<int> wrong={0,2,14,17,2,4,15,0};
    const std::vector<int> useful={0,2,14,17,3,4,15,0};
    {
        FragmentTransaction trial(agent,wrong);
        auto score=evaluate_program(agent,false);
        if(score.zero!=0)return 1;
    }
    if(agent.words!=original)return 2;
    std::cout<<"wrong candidate ZERO=0/8; full program rollback exact\n"<<std::flush;
    {
        FragmentTransaction trial(agent,useful);
        auto score=evaluate_program(agent,true);
        if(score.zero!=8||score.old!=23)return 3;
        trial.commit();
    }
    const int start=2*agent.reserve_start;
    for(int i=0;i<int(agent.words.size());++i)
        if((i<start||i>=start+32)&&agent.words[i]!=original[i])return 4;
    auto retained=agent.words;
    {
        FragmentTransaction trial(agent,wrong);
        // Explicit rejection without changing the committed installed version.
    }
    if(agent.words!=retained)return 5;
    std::cout<<"PASS host fragment trial: useful ZERO=8/8 old=23/23,"
                " commit retained, later rejected replacement restored; slot=16 pairs\n";
}
