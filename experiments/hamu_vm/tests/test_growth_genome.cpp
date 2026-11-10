#include "../src/growth_genome.hpp"
#include "../src/hamu_vm_core.hpp"
#include <cassert>
#include <iostream>

int main() {
    auto g=growth_genome(64);
    const auto fixed=layered_next_operator_growth_program();
    assert(std::equal(fixed.begin(),fixed.end(),g.words.begin()));
    assert(int(g.words.size())==2*(g.fixed_pairs+64));
    for(int i=0;i<64;++i)write_gene_pair(g,g.fixed_pairs+i,15,0);
    write_gene_pair(g,g.fixed_pairs+17,4,1);
    assert(g.words[2*(g.fixed_pairs+17)]==4);
    assert(std::equal(fixed.begin(),fixed.end(),g.words.begin()));
    bool blocked=false;
    try {write_gene_pair(g,g.fixed_pairs-1,4,1);}catch(const std::out_of_range&) {blocked=true;}
    assert(blocked);
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=140;
    p.layout.total_size=p.layout.program_start+int(g.words.size())*6;
    Hamster parent(0,p);int at=p.layout.program_start;
    for(int word:g.words)
        for(bool bit:SpiralToken(word,5,1).bits)parent.memory.at(at++)=bit;
    parent.new_his();Hamster child(1,p);child.copy_hamu(parent);
    assert(child.memory==parent.memory);
    const int gene_at=p.layout.program_start+2*(g.fixed_pairs+17)*6;
    child.pro_1=gene_at;child.pro_2=gene_at+11;child.step_limit=4;
    simulate_spiral_program(child);
    assert(child.read_seen[p.layout.input_start]); // reserved READ is executable
    std::cout<<"PASS 64 mutable pairs; fixed prefix intact, inheritance and reserved READ\n";
}
