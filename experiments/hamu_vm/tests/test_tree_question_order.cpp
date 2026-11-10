#define TREE_RESOURCE_POPULATION_NO_MAIN
#include "../src/tree_resource_population.cpp"
#include <algorithm>
#include <array>
#include <iostream>
int main(){
    int births_seen=0;
    auto keys=[](int seed){
        std::array<int,12> out{};
        for(int round=1;round<=12;++round){
            const auto q=tree_question_permuted(round,seed);
            population_check((round<=8)==(q.operator_width==2),"one-way width order");
            out[size_t(round-1)]=q.operator_width*1000+q.operator_id*100+q.data*10+int(q.kind);
        }
        std::sort(out.begin(),out.end());return out;
    };
    for(int seed=1;seed<=4;++seed){
        population_check(keys(seed)==keys(0),"identical question multiset");
        for(bool breeding:{false,true}){
            const auto result=run_tree_resource_population(12000,breeding,false,
                TreeQuestionSchedule::CleanPermuted,seed);
            const auto& last=result.rows.back();
            population_check(last.totals.rewarded==12000*last.totals.answers,"permuted reward identity");
            population_check(last.confirmed>0,"some meanings confirmed");
            population_check(breeding||last.births==0,"permuted no-birth control");
            if(breeding){
                births_seen+=last.births;
                population_check(last.births==(seed<=2?4:0),
                    "fixed question multiset has order-dependent births in this fixture");
            }
        }
    }
    population_check(births_seen>0,"some order permits earned births");
    bool rejected=false;try{(void)tree_question_permuted(1,5);}
    catch(const std::invalid_argument&){rejected=true;}
    population_check(rejected,"invalid permutation rejected");
    std::cout<<"PASS four exact-multiset permutations, eight sanitized populations, 96 censuses\n";
}
