#define TREE_RESOURCE_POPULATION_NO_MAIN
#include "../src/tree_resource_population.cpp"
#include <iostream>
int main(){
    for(int seed=0;seed<=4;++seed){
        std::vector<TreeQuestionTrace> trace;
        auto schedule=seed?TreeQuestionSchedule::CleanPermuted:TreeQuestionSchedule::CleanVaried;
        auto result=run_tree_resource_population(12000,false,false,schedule,seed,&trace);
        int answers=0,confirmations=0,routes=0;
        for(int round=1;round<=12;++round){
            for(const auto& e:trace)if(e.round==round){
                population_check(e.before_slots>=0&&e.before_slots<=2&&e.after_slots>=0&&e.after_slots<=2,
                    "pending slot occupancy");
                population_check(e.balance_after>=0&&e.balance_before>=0,"trace nonnegative balance");
                population_check(!e.route||!e.attempt,"one answer pathway per question");
                if(seed>=3&&e.id==0&&round>=9){
                    population_check(e.before_slots==2&&e.after_slots==2&&
                        !e.attempt&&!e.route,"late wide question blocked by both pending slots");
                }
                answers+=e.route||(e.attempt&&e.valid&&e.correct);
                confirmations+=e.confirmed;routes+=e.route;
            }
            const auto& row=result.rows[size_t(round-1)];
            population_check(row.totals.answers==answers&&row.confirmed==confirmations&&
                row.route_answers==routes,"trace to census reconciliation");
        }
        if(seed>=3)population_check(result.rows.back().totals.answers==4&&
            result.rows.back().route_answers==0,"late-slot blockage outcome");
    }
    std::cout<<"PASS five trace reconciliations, all 60 censuses and slot bounds\n";
}
