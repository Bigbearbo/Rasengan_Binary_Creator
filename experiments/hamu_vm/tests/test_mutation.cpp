#define main experiment_entry_for_testing
#include "../src/hamu_experiment.cpp"
#undef main
#include <cassert>
#include <iostream>
int main() {
    for(const auto& mode: {std::string("scaffold"),std::string("open_read")}) {
        Config c;c.mode=mode;std::mt19937 rng(17);
        const auto parent=random_genome(rng,c);
        int saw_change=0;
        for(int trial=0;trial<10000;++trial) {
            const auto child=mutated(parent,rng,c);
            for(size_t bit=0;bit<child.size();++bit) if(child[bit]!=parent[bit]) {
                const int word=bit/(c.vm_order+1), offset=bit%(c.vm_order+1);
                const bool allowed=mode=="scaffold" ? (word==1||word==3||word==9) :
                                                        (word==1||word==2||word==3||word==9);
                assert(allowed && offset<c.vm_order);
                ++saw_change;
            }
        }
        assert(saw_change>0);
    }
    std::cout<<"PASS: 20000 offspring only mutate authorized word bits\n";
}
