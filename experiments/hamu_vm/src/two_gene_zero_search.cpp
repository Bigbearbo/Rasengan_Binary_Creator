#define INTEGRATED_ZERO_NO_MAIN
#include "integrated_zero_search.cpp"
#include <set>

int main() {
    // Both single-bit neighbors are phenotype-neutral under the strict
    // whole-answer oracle. Keep equal-scoring descendants as separate paths.
    const auto initial=evaluate(2,false,5);
    const auto changed_opcode=evaluate(3,false,5);
    const auto changed_count=evaluate(2,false,4);
    if(initial.zero||changed_opcode.zero||changed_count.zero)return 1;
    std::set<std::pair<int,int>> frontier={{2,5}},seen=frontier;
    int evaluations=3,success_generation=-1;
    for(int generation=1;generation<=2;++generation) {
        std::set<std::pair<int,int>> next=frontier;
        for(auto [op,count]:frontier) {
            // Mutate one selected bit in either of two independent genes.
            for(auto child:{std::pair<int,int>{op^1,count},
                            std::pair<int,int>{op,count^1}}) {
                if(!seen.insert(child).second)continue;
                next.insert(child);
                const auto score=evaluate(child.first,false,child.second);
                ++evaluations;
                if(score.zero==8)success_generation=generation;
            }
        }
        frontier=std::move(next);
        if(success_generation>0)break;
    }
    if(success_generation!=2)return 2;
    const auto final=evaluate(3,true,4);
    if(final.old!=23||final.zero!=8)return 3;
    std::cout<<"PASS neutral lineage: (2,5)=0/8, (3,5)=0/8,"
                " (2,4)=0/8, (3,4)=8/8; generation="<<success_generation
             <<" evaluations="<<evaluations<<" old="<<final.old<<"/23\n";
}
