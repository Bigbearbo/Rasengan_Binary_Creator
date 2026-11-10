#define TREE_RESOURCE_POPULATION_NO_MAIN
#include "../src/tree_resource_population.cpp"
int main(){
    for(bool reverse:{false,true}){
        const auto no_reward=run_tree_resource_population(0,true,reverse);
        const auto control=run_tree_resource_population(12000,false,reverse);
        const auto growth=run_tree_resource_population(12000,true,reverse);
        population_check(no_reward.rows.back().living==0,"no external reward cannot sustain this population");
        population_check(control.rows.back().births==0,"breeding off control");
        population_check(growth.rows.back().births>0,"earned answers permit births");
        for(const auto& row:growth.rows)population_check(row.policies[0]<=1,"idle policy cannot reproduce");
        population_check(growth.rows.back().living>control.rows.back().living,"births replenish population");
    }
    std::cout<<"PASS population controls: extinction without reward, earned reproduction, idle lineage excluded, replenishment, both founder orders\n";
}
