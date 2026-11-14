#define TREE_RESOURCE_POPULATION_NO_MAIN
#include "../src/tree_resource_population.cpp"
#include <iostream>
int main(){
    for(bool reverse:{false,true}){
        auto no_reward=run_tree_resource_population(0,true,reverse,true);
        auto control=run_tree_resource_population(12000,false,reverse,true);
        auto breeding=run_tree_resource_population(12000,true,reverse,true);
        population_check(control.rows.back().births==0,"varied-question no-birth control");
        population_check(breeding.rows.back().births>0,"varied-question earned births");
        for(const auto& r:breeding.rows)
            population_check(r.living<=8&&r.totals.balance==r.totals.initial+r.totals.rewarded-r.totals.spent,
                "varied-question conservation");
        population_check(no_reward.rows.back().totals.rewarded==0,"zero reward control");
        population_check(breeding.rows.back().totals.answers>0,"actual answers rewarded");
    }
    std::cout<<"PASS varied-question population: six scenarios, 72 censuses, reproduction and conservation\n";
}
