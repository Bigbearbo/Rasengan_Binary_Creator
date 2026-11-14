#include "../src/tree_compact_reference.hpp"
#include <iostream>
#include <stdexcept>
#include <vector>

struct GrowthRun {
    int calls=0;
    long long vm_steps=0;
    int peak_steps=0;
    void operator()(Hamster& h,const std::vector<int>& code){
        int at=h.params.layout.program_start;
        for(int word:code) for(bool bit:SpiralToken(word,5,1).bits)
            h.memory.at(at++)=bit;
        std::fill(h.val_reg.begin(),h.val_reg.end(),false);
        h.val_ptr=0;h.stop=false;h.budget_exhausted=false;
        h.executed_steps=0;h.step_limit=4000;
        h.pro_1=h.params.layout.program_start;h.pro_2=at-1;
        simulate_spiral_program(h);
        if(!h.stop||h.budget_exhausted)
            throw std::runtime_error("growth VM interrupted");
        ++calls;vm_steps+=h.executed_steps;
        peak_steps=std::max(peak_steps,h.executed_steps);
    }
};

int main(){
    std::cout<<"capacity,used_nodes,first_lookup_rows,guest_choice_rows,guest_choice_steps,"
                "guest_total_steps,guest_vm_calls,reserved_tree_bits,reserved_payload_bits\n";
    for(int capacity : {1,2,4,8,16,24,31}){
        HamsterParams p;
        p.layout.status_start=45;p.layout.output_start=50;
        p.layout.work_start=80;p.layout.program_start=1100;
        p.layout.total_size=24000;p.layout.val_reg_size=12;
        p.stable_work_bits=800;p.tree_start=300;p.tree_capacity=capacity;
        Hamster h(1,p);h.memory[1]=true;
        GrowthRun run;
        // Fill IDs 1..capacity-1 with a deep chain, then create a final
        // independent root under key 7, forcing a last-row lookup.
        if(capacity>1){
            std::vector<int> chain={16,1,8,11};
            for(int j=0;j<capacity-1;++j){chain.push_back(28);chain.push_back(0);}
            chain.push_back(15);chain.push_back(0);
            run(h,chain);
        }
        run(h,{16,1,8,11,28,7,15,0});
        int id=0;for(int bit=0;bit<5;++bit)id=(id<<1)|int(h.val_reg[bit]);
        if(id!=capacity)throw std::runtime_error("unexpected dense allocation ID");
        TreeCompactReference compact{h,672};
        auto runner=[&](Hamster& who,const std::vector<int>& words){run(who,words);};
        const auto before=h.tree_lookup_rows_examined;
        const auto old_steps=run.vm_steps;
        if(compact.node(7,runner)!=capacity)throw std::runtime_error("lost last-row node");
        const auto first_lookup=h.tree_lookup_rows_examined-before;
        if(first_lookup!=static_cast<unsigned>(capacity))
            throw std::runtime_error("native TREE_ADD scan count wrong");
        // TREE_ACTION's final slot is at tree_start+capacity*12-3.
        // Compact address scratch must not touch any of those legacy bits.
        const int last_action=p.tree_start+capacity*12-3;
        for(int bit=0;bit<3;++bit)h.memory[last_action+bit]=true;
        runner(h,{16,1,8,11,27,7,30,0,15,0});
        if(!h.val_reg[5]||!h.val_reg[6]||!h.val_reg[7])
            throw std::runtime_error("action slot initialization failed");
        const auto before_choice=h.tree_lookup_rows_examined;
        const auto before_steps=run.vm_steps;
        if(compact.next(7,runner)!=0||h.val_reg[8])
            throw std::runtime_error("unlearned choice incorrect");
        const auto choice_rows=h.tree_lookup_rows_examined-before_choice;
        const auto choice_steps=run.vm_steps-before_steps;
        if(choice_steps<=0||run.calls<3)throw std::runtime_error("guest accounting missing");
        if(choice_rows!=static_cast<unsigned>(2*capacity))
            throw std::runtime_error("choice must make two native node lookups");
        for(int bit=0;bit<3;++bit)
            if(!h.memory[last_action+bit])
                throw std::runtime_error("compact scratch corrupted TREE_ACTION slot");
        compact.record(7,0,false,runner);
        if(compact.next(7,runner)!=1||h.val_reg[8])
            throw std::runtime_error("wrong answer not excluded");
        compact.record(7,1,true,runner);
        if(compact.next(7,runner)!=1||!h.val_reg[8])
            throw std::runtime_error("correct answer lost");
        Hamster snapshot=h;snapshot.new_his();
        Hamster child(2,p);child.copy_hamu(snapshot);
        GrowthRun after;
        TreeCompactReference inherited{child,672};
        auto after_runner=[&](Hamster& who,const std::vector<int>& words){after(who,words);};
        if(inherited.next(7,after_runner)!=1||!child.val_reg[8])
            throw std::runtime_error("knowledge lost in same-layout inheritance");
        // A changed tree_start/capacity may reinterpret stored node rows and
        // move TREE_ACTION slots: refusing implicit conversion is essential.
        HamsterParams wrong=p;wrong.tree_start=301;
        bool rejected=false;
        try{Hamster alien(3,wrong);alien.copy_hamu(snapshot);}
        catch(const std::invalid_argument&){rejected=true;}
        if(!rejected)throw std::runtime_error("silently accepted relocated tree");
        if(capacity<31){
            wrong=p;wrong.tree_capacity=capacity+1;rejected=false;
            try{Hamster alien(4,wrong);alien.copy_hamu(snapshot);}
            catch(const std::invalid_argument&){rejected=true;}
            if(!rejected)throw std::runtime_error("silently accepted resized tree");
        }
        std::cout<<capacity<<','<<capacity<<','<<first_lookup<<','<<choice_rows
                 <<','<<choice_steps<<','<<run.vm_steps-old_steps<<','<<run.calls
                 <<','<<9*capacity<<','<<12*capacity<<'\n';
    }
    std::cout<<"PASS: full-density growth, last-row guest payload, wrong-answer exclusion,"
                " inheritance, incompatible-layout refusal\n";
}
