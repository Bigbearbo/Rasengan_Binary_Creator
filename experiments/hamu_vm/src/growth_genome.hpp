#pragma once
#include "layered_next_operator_growth.hpp"

struct GrowthGenome {
    std::vector<int> words;
    int fixed_pairs;
    int mutable_pairs;
};

// Reserve complete opcode/parameter pairs in the inheritable program area.
// Each reserved pair initially halts. Evolution may replace only these pairs
// and must preserve each token's trailing zero and the fixed prefix.
inline GrowthGenome growth_genome(int mutable_pairs=64) {
    if(mutable_pairs<1||mutable_pairs>512)
        throw std::invalid_argument("invalid mutable gene capacity");
    auto fixed=layered_next_operator_growth_program();
    GrowthGenome g{fixed,int(fixed.size()/2),mutable_pairs};
    for(int i=0;i<mutable_pairs;++i) {
        g.words.push_back(15); // OUT_AREA: safe default for entry into reserve
        g.words.push_back(0);
    }
    return g;
}

inline void write_gene_pair(GrowthGenome& g,int pair,int opcode,int parameter) {
    if(pair<g.fixed_pairs||pair>=g.fixed_pairs+g.mutable_pairs||
       opcode<0||opcode>26||parameter<0||parameter>31)
        throw std::out_of_range("gene mutation outside reserved program pairs");
    g.words.at(2*pair)=opcode;
    g.words.at(2*pair+1)=parameter;
}
