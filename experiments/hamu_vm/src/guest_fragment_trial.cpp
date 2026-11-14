#define INTEGRATED_ZERO_NO_MAIN
#include "integrated_zero_search.cpp"
#include "fragment_transaction.hpp"
#include "guest_fragment_request.hpp"
#include <memory>

int main() {
    const auto policy=fragment_request_policy();
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=140;
    p.layout.total_size=p.layout.program_start+int(policy.size())*6;
    Hamster controller(0,p);int at=p.layout.program_start;
    for(int w:policy)for(bool bit:SpiralToken(w,5,1).bits)controller.memory.at(at++)=bit;
    auto request=[&](bool feedback,bool passed) {
        Problem q;controller.write_prob(q);
        controller.memory[p.layout.input_start+1]=feedback;
        controller.memory[p.layout.input_start+2]=passed;
        controller.pro_1=p.layout.program_start;controller.pro_2=at-1;
        controller.step_limit=80;simulate_spiral_program(controller);
        if(controller.budget_exhausted)throw std::runtime_error("controller budget");
        return read_fragment_request(controller);
    };
    auto agent=integrated_zero_program(15);
    const auto original=agent.words;
    const std::vector<std::vector<int>> library={
        {0,2,14,17,2,4,15,0}, {0,2,14,17,3,4,15,0}};
    auto first=request(false,false);
    if(first.verb!=2||first.fragment!=0)return 1;
    {
        FragmentTransaction trial(agent,library.at(first.fragment));
        if(evaluate_program(agent,false).zero!=0)return 2;
    }
    if(agent.words!=original)return 3;
    std::cout<<"guest requested fragment 0; failed, rolled back\n"<<std::flush;
    auto second=request(true,false);
    if(second.verb!=2||second.fragment!=1)return 4;
    {
        FragmentTransaction trial(agent,library.at(second.fragment));
        const auto score=evaluate_program(agent,true);
        if(score.zero!=8||score.old!=23)return 5;
        auto decision=request(true,true);
        if(decision.verb!=1||decision.fragment!=second.fragment)return 6;
        trial.commit();
    }
    if(agent.words==original)return 7;
    std::cout<<"PASS guest VM request 0->1->COMMIT; ZERO=8/8 old=23/23;"
                " human-written controller, host installs and grades\n";
}
