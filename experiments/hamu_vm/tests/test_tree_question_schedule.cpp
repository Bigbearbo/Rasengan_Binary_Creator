#define TREE_RESOURCE_POPULATION_NO_MAIN
#include "../src/tree_resource_population.cpp"
#include <iostream>
int main(){
    for(auto schedule:{TreeQuestionSchedule::CleanSingle,TreeQuestionSchedule::CleanVaried})
        for(bool reverse:{false,true})for(bool breeding:{false,true}){
        const auto result=run_tree_resource_population(12000,breeding,reverse,schedule);
        const auto& last=result.rows.back();
        population_check(result.rows.size()==12&&last.totals.answers>0,"clean question schedule");
        population_check(last.confirmed>0&&last.route_answers>0,"confirmed and routed answers");
        population_check(last.totals.rewarded==12000*last.totals.answers,"actual answer credit");
        population_check(breeding||last.births==0,"no-breeding control");
        int previous_answers=0,previous_confirmed=0,previous_routes=0;
        for(const auto& row:result.rows){
            population_check(row.totals.answers>=previous_answers&&row.confirmed>=previous_confirmed&&
                row.route_answers>=previous_routes,"monotone cumulative outcomes");
            population_check(row.totals.balance==row.totals.initial+row.totals.rewarded-row.totals.spent,
                "closed question schedule balance");
            previous_answers=int(row.totals.answers);previous_confirmed=row.confirmed;previous_routes=row.route_answers;
        }
    }
    std::cout<<"PASS two matched-catalogue schedules, eight reward/birth/order controls, 96 censuses\n";
}
