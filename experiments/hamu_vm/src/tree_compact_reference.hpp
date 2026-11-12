#pragma once
#include "tree_error_trial.hpp"

// Reference layout for the proposed design. TREE_ADD allocates only a
// question node. The twelve attached bits are persistent VM work memory:
// eight wrong flags, one success flag, three bits for the correct option.
// The guest decodes node ID into its own memory pointer for both reads and writes.
// 5+1 word layout only: the VM MOVE_PTR stride is six physical bits.
// Larger work offsets use six-bit word moves plus a small bit remainder.
// Reserve five scratch bits AFTER the maximum 31-node payload region.
// The former base-5 scratch overlaps TREE_ACTION slots for capacity=31.
// This position preserves existing 12-bit payload offsets, so a pure
// compact-only snapshot does not need relocation; the old scratch slots may
// already be damaged in mixed historical use and cannot be reconstructed.
inline int tree_compact_scratch_base(int base){return base+31*12;}
inline void tree_compact_guest_at_work(TreeFourCode& c,int pos){
    if(pos<0)throw std::invalid_argument("negative compact work offset");
    c.e(0,3);
    int words=pos/6;
    while(words>0){const int count=std::min(words,15);c.e(1,16+count);words-=count;}
    if(pos%6)c.e(14,16+pos%6);
}
inline void tree_compact_guest_address(TreeFourCode& c,int question,int base,int work_start){
    const int scratch=tree_compact_scratch_base(base);
    if(question<1||question>7||base-12<work_start||scratch<work_start)
        throw std::invalid_argument("compact payload layout");
    // Clear the parent ID in guest registers before every lookup. This
    // dedicated scratch space is AFTER the maximum payload allocation,
    // never inside TREE_ACTION's capacity-dependent action slots.
    tree_compact_guest_at_work(c,scratch-work_start);c.e(3,5);
    c.reset();tree_compact_guest_at_work(c,scratch-work_start);c.e(4,5);
    c.reset();c.e(28,question);
    tree_compact_guest_at_work(c,base-12-work_start);
    for(int bit=0;bit<5;++bit){
        c.reset();if(bit)c.e(8,16+bit);
        const int yes=c.e(24,0),skip=c.e(26,0);
        c.patch(yes,int(c.w.size()/2));
        // Each node weighs 12 bits. With the 5+1 Spiral word format,
        // MOVE_PTR advances six physical bits per unit. Prefer a few wide
        // movements to repeating +12 SMOVE_PTR for every unit of weight.
        // This guest instruction sequence remains the pointer computation:
        // the host does not derive the node address.
        int units=2*(16>>bit); // node weight * 12 / word width (6)
        while(units>0){const int chunk=std::min(units,15);c.e(1,16+chunk);units-=chunk;}
        c.patch(skip,int(c.w.size()/2));
    }
}
inline std::vector<int> tree_compact_guest_read_program(int question,int base,int work_start){
    TreeFourCode c;c.e(16,1);tree_compact_guest_address(c,question,base,work_start);
    c.reset();c.e(4,12);c.e(15,0);return c.w;
}
inline std::vector<int> tree_compact_guest_choice_program(int question,int base,int work_start,int first=0){
    if(first<0||first>=8)throw std::invalid_argument("compact first option");
    TreeFourCode c;c.e(16,1);tree_compact_guest_address(c,question,base,work_start);
    c.reset();c.e(4,12);
    auto emit=[&](int option){
        c.at(2,0);c.e(2,1);
        for(int bit=2;bit>=0;--bit)c.e(option&(1<<bit)?2:3,1);
        c.e(15,0);
    };
    c.reset();c.e(8,24); // success flag: register 8
    const int known=c.e(24,0),unknown=c.e(26,0);
    c.patch(known,int(c.w.size()/2));
    c.at(2,0);c.e(2,1); // write advances output pointer to bit 1
    c.reset();c.e(8,25);c.e(9,3);c.e(15,0);
    c.patch(unknown,int(c.w.size()/2));
    for(int index=0;index<8;++index){
        const int option=(first+index)%8;
        c.reset();if(option)c.e(8,16+option);
        const int wrong=c.e(24,0);emit(option);
        c.patch(wrong,int(c.w.size()/2));
    }
    c.e(15,0); // exhausted: no output presence
    return c.w;
}
inline std::vector<int> tree_compact_guest_write_program(int question,int option,bool right,int base,int work_start){
    if(option<0||option>=8)throw std::invalid_argument("option");
    TreeFourCode c;c.e(16,1);
    tree_compact_guest_address(c,question,base,work_start);
    if(right){
        c.e(14,25); // pointer at answer bit 9
        for(int b=2;b>=0;--b)c.e(option&(1<<b)?2:3,1);
        // WRITE advances the pointer to bit 12. Jump back to bit 8 and
        // publish the success flag only after all three answer bits.
        c.e(14,4);c.e(2,1);
    }else{
        if(option)c.e(14,16+option);
        c.e(2,1);
    }
    c.e(15,0);return c.w;
}
struct TreeCompactReference {
    Hamster& h;
    int base;
    template<class Runner> int node(int question,Runner run){
        if(question<1||question>7)throw std::invalid_argument("question");
        run(h,{16,1,8,11,28,question,15,0});
        int id=0;for(int b=0;b<5;++b)id=(id<<1)|int(h.val_reg[b]);
        if(!id||!h.stop||h.budget_exhausted)throw std::runtime_error("question tree full");
        if(base<h.params.tree_start+h.params.tree_capacity*12||
           base+h.params.tree_capacity*12>tree_compact_scratch_base(base)||
           tree_compact_scratch_base(base)+5>h.params.layout.program_start)
            throw std::invalid_argument("compact payload layout");
        return id;
    }
    template<class Runner> int next(int question,Runner run,int first=0){
        node(question,run); // validates existence and available payload layout
        const int out=h.params.layout.output_start;
        if(out+4>h.params.layout.work_start)throw std::invalid_argument("compact output layout");
        for(int i=0;i<4;++i){h.memory[out+i]=false;h.written[out+i]=false;}
        run(h,tree_compact_guest_choice_program(question,base,h.params.layout.work_start,first));
        if(!h.stop||h.budget_exhausted)throw std::runtime_error("compact choice interrupted");
        if(!h.written[out])return -1;
        for(int i=1;i<4;++i)if(!h.written[out+i])
            throw std::runtime_error("compact choice incomplete");
        return (int(h.memory[out+1])<<2)|(int(h.memory[out+2])<<1)|int(h.memory[out+3]);
    }
    template<class Runner> void record(int question,int option,bool right,Runner run){
        if(option<0||option>=8)throw std::invalid_argument("option");
        const int id=node(question,run); // host validates allocation and layout
        run(h,tree_compact_guest_write_program(question,option,right,base,h.params.layout.work_start));
        const int offset=base+(id-1)*12; // verification only
        if(!h.stop||h.budget_exhausted||
            !h.written[offset+(right?8:option)])
            throw std::runtime_error("compact VM write failed id="+std::to_string(id)+
                " option="+std::to_string(option)+" right="+std::to_string(right)+
                " stop="+std::to_string(h.stop)+" budget="+std::to_string(h.budget_exhausted)+
                " written="+std::to_string(h.written[offset+(right?8:option)])+
                " ptr="+std::to_string(h.ptr)+" pro="+std::to_string(h.pro_1)+
                " steps="+std::to_string(h.executed_steps));
    }
};
