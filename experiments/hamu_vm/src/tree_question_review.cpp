#define TREE_RESOURCE_POPULATION_NO_MAIN
#include "tree_resource_population.cpp"
int main(){
    std::cout<<"review,reward,breeding,reverse,round,living,births,retired,balance,spent,rewarded,correct_answers,confirmed,route_answers\n";
    for(bool review:{false,true})for(int reward:{0,12000})for(bool breeding:{false,true})
        for(bool reverse:{false,true}){
        const auto schedule=review?TreeQuestionSchedule::CleanReview:TreeQuestionSchedule::CleanDelay;
        auto result=run_tree_resource_population(reward,breeding,reverse,schedule);
        for(const auto& r:result.rows){const auto& t=r.totals;
            std::cout<<review<<','<<reward<<','<<breeding<<','<<reverse<<','<<r.round<<','<<r.living
                <<','<<r.births<<','<<r.retired<<','<<t.balance<<','<<t.spent<<','<<t.rewarded
                <<','<<t.answers<<','<<r.confirmed<<','<<r.route_answers<<'\n';
        }
    }
    std::cout<<"PASS sixteen matched delay/review scenarios, 256 censuses\n";
}
