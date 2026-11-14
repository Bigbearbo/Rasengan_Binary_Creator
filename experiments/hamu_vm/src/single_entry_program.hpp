#pragma once
#include "guest_fragment_request.hpp"
#include "integrated_zero_program.hpp"

// Input area's last bit (offset 44 in this test layout) selects a declared
// control message versus a math packet. Both start at program_start.
inline IntegratedZero single_entry_program(int opcode,int failure_id=-1) {
    auto solver=integrated_zero_program(opcode);
    const auto policy=failure_id==-2?fragment_sequential_policy():
                      failure_id<0?fragment_request_policy(40):fragment_choice_policy(failure_id);
    std::vector<int> c={16,1,0,0,14,31,14,31,14,30,4,1,24,2,26,0};
    const int bypass=7;
    std::vector<int> relocated(policy.size()/2);
    std::vector<int> bridges;
    for(int i=0;i<int(policy.size()/2);++i) {
        if(i>0&&i%16==0) {
            c.insert(c.end(),{26,2,26,0});
            bridges.push_back(int(c.size()/2)-1);
        }
        relocated[i]=int(c.size()/2);
        c.push_back(policy[2*i]);c.push_back(policy[2*i+1]);
    }
    const int solver_start=int(c.size()/2);
    auto patch=[&](int from,int to) {
        if(to<=from||to-from>31)throw std::logic_error("single-entry bridge range");
        c.at(2*from+1)=to-from;
    };
    for(int i=0;i<int(policy.size()/2);++i) {
        const int op=policy[2*i];
        if(op==24||op==26) {
            const int target=i+policy[2*i+1];
            if(target>=int(relocated.size()))throw std::logic_error("policy target");
            patch(relocated[i],relocated[target]);
        }
    }
    int from=bypass;
    for(int bridge:bridges){patch(from,bridge);from=bridge;}
    patch(from,solver_start);
    c.insert(c.end(),solver.words.begin(),solver.words.end());
    solver.words=std::move(c);
    solver.reserve_start+=solver_start;solver.mutation_pair+=solver_start;
    return solver;
}
