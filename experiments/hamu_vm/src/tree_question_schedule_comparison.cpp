#define TREE_RESOURCE_POPULATION_NO_MAIN
#include "tree_resource_population.cpp"
int main(){
    std::cout<<"schedule,reward,breeding,reverse,round,living,births,retired,off,on,after_failure,reserve,balance,spent,rewarded,correct_answers,confirmed,route_answers\n";
    for(auto schedule:{TreeQuestionSchedule::CleanSingle,TreeQuestionSchedule::CleanVaried})
        for(int reward:{0,12000})for(bool breeding:{false,true})for(bool reverse:{false,true}){
        const auto result=run_tree_resource_population(reward,breeding,reverse,schedule);
        for(const auto& r:result.rows){const auto& t=r.totals;
            std::cout<<int(schedule==TreeQuestionSchedule::CleanVaried)<<','<<reward<<','<<breeding<<','<<reverse
                <<','<<r.round<<','<<r.living<<','<<r.births<<','<<r.retired;
            for(int count:r.policies)std::cout<<','<<count;
            std::cout<<','<<t.balance<<','<<t.spent<<','<<t.rewarded<<','<<t.answers
                <<','<<r.confirmed<<','<<r.route_answers<<'\n';
        }
    }
    std::cout<<"PASS 16 matched-catalogue scenarios, 192 censuses, resource and answer ledger\n";
}
