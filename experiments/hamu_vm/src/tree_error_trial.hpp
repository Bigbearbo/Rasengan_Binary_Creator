#pragma once
#include "hamu_vm_core.hpp"
#include "tree_four_vm.hpp"

inline std::vector<int> tree_error_program(int question,int option,bool add,bool correct=false){
    if(question!=-1&&(question<1||question>7))throw std::invalid_argument("error tree key");
    if(option<0||option>7||(!add&&correct))
        throw std::invalid_argument("error tree key");
    TreeFourCode c;c.e(16,1);c.reset();
    if(question==-1){
        c.at(0,2);c.e(8,22);c.e(4,3);c.reset();
        c.e(31,0); // input token key in registers 6..8
    }else c.e(28,question); // legacy immediate key, recursive reference
    c.e(add?28:27,option); // answer node under that question
    if(correct){
        c.e(8,22);c.at(0,1);c.e(4,1); // reg6 = startup 1
        c.e(8,17);c.at(0,1);c.e(4,1); // reg7 = startup 1
        c.reset();c.e(30,1); // committed 11 marks a correct answer
    }else c.e(30,0); // uncommitted answer node means previously wrong
    c.e(15,0);return c.w;
}
struct TreeErrorProbe {bool exists=false,correct=false;};
template<class Runner>
TreeErrorProbe tree_error_probe(Hamster& h,int question,int option,Runner run){
    run(h,tree_error_program(question,option,false));
    if(!h.stop||h.budget_exhausted)throw std::runtime_error("error tree probe interrupted");
    return {bool(h.val_reg[0]||h.val_reg[1]||h.val_reg[2]||h.val_reg[3]||h.val_reg[4]),
        bool(h.val_reg[5]&&h.val_reg[6]&&h.val_reg[7])};
}
template<class Runner>
void tree_error_record(Hamster& h,int question,int option,bool correct,Runner run){
    run(h,tree_error_program(question,option,true,correct));
    bool node=false;for(int b=0;b<5;++b)node=node||h.val_reg[b];
    if(!h.stop||h.budget_exhausted||!node||(correct&&!h.val_reg[5]))
        throw std::runtime_error("error tree record failed");
}
template<class Runner>
void tree_error_record_from_input(Hamster& h,int option,bool correct,Runner run){
    run(h,tree_error_program(-1,option,true,correct));
    bool node=false;for(int b=0;b<5;++b)node=node||h.val_reg[b];
    if(!h.stop||h.budget_exhausted||!node||(correct&&!h.val_reg[5]))
        throw std::runtime_error("error input record failed");
}
// Host-side resource gate: a new answer needs a free physical tree row.
inline bool tree_error_has_free_node(const Hamster& h){
    for(int id=0;id<h.params.tree_capacity;++id)
        if(!h.memory[h.params.tree_start+id*9])return true;
    return false;
}
// Retain the host recursion as a reference for differential guest testing.
struct TreeErrorChoice {int known=-1,untried=-1;};
template<class Runner>
TreeErrorChoice tree_error_search(Hamster& h,int question,int option,Runner run){
    if(option==8)return {};
    const auto found=tree_error_probe(h,question,option,run);
    const auto tail=tree_error_search(h,question,option+1,run);
    if(found.correct)return {option,tail.untried};
    return {tail.known,!found.exists?option:tail.untried};
}
template<class Runner>
int tree_error_next_host(Hamster& h,int question,int option,Runner run){
    if(option<0||option>8)throw std::invalid_argument("error search option");
    const auto choice=tree_error_search(h,question,option,run);
    return choice.known>=0?choice.known:choice.untried;
}

// Generate a bounded guest traversal. The question's three information bits
// are read from the input token at input+2; the host supplies only the start.
// A selected option is written as a presence bit plus three bits at output.
inline std::vector<int> tree_error_guest_choice_program(int first){
    if(first<0||first>8)
        throw std::invalid_argument("error guest choice key");
    TreeFourCode c;c.e(16,1); // jumps take effect immediately
    auto find=[&](int option){
        c.reset();c.at(0,2);c.e(8,22);c.e(4,3); // input token -> regs 6..8
        c.reset();c.at(2,0);c.e(4,5); // cleared output resets root id
        c.e(31,0);c.e(27,option);c.e(30,0);
        c.e(8,21); // val_ptr 5: TREE_ACTION's committed bit
    };
    auto emit=[&](int option){
        c.at(2,0);c.e(2,1);
        for(int bit=2;bit>=0;--bit)c.e(option&(1<<bit)?2:3,1);
        c.e(15,0);
    };
    for(int option=first;option<8;++option){
        find(option);
        const int yes=c.e(24,0),skip=c.e(26,0);
        c.patch(yes,int(c.w.size()/2));emit(option);
        c.patch(skip,int(c.w.size()/2));
    }
    for(int option=first;option<8;++option){
        c.reset();c.at(0,2);c.e(8,22);c.e(4,3);
        c.reset();c.at(2,0);c.e(4,5);
        c.e(31,0);c.e(27,option);
        c.e(8,21); // val_ptr 5: found node skips, absent emits
        const int skip=c.e(24,0);emit(option);
        c.patch(skip,int(c.w.size()/2));
    }
    c.e(15,0);return c.w;
}
inline void tree_error_write_question(Hamster& h,int question){
    if(question<1||question>7||h.params.layout.input_start+6>h.params.layout.status_start)
        throw std::invalid_argument("error input question key");
    const auto bits=SpiralToken(question,3,1).bits;
    for(int i=0;i<4;++i)h.memory[h.params.layout.input_start+2+i]=bits[size_t(i)];
}
template<class Runner>
int tree_error_next_from_input(Hamster& h,int option,Runner run){
    const int out=h.params.layout.output_start;
    if(h.params.layout.input_start+6>h.params.layout.status_start||
        out+5>h.params.layout.work_start)throw std::invalid_argument("error choice space");
    for(int i=0;i<5;++i){h.memory[out+i]=false;h.written[out+i]=false;}
    run(h,tree_error_guest_choice_program(option));
    if(!h.stop||h.budget_exhausted)throw std::runtime_error("error guest choice interrupted");
    if(!h.written[out])return -1;
    if(!h.memory[out]||!h.written[out+1]||!h.written[out+2]||!h.written[out+3])
        throw std::runtime_error("error guest choice incomplete");
    return (int(h.memory[out+1])<<2)|(int(h.memory[out+2])<<1)|int(h.memory[out+3]);
}
template<class Runner>
int tree_error_next(Hamster& h,int question,int option,Runner run){
    tree_error_write_question(h,question);
    return tree_error_next_from_input(h,option,run);
}
