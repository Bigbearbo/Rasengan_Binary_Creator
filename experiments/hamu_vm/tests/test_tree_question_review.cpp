#define TREE_RESOURCE_POPULATION_NO_MAIN
#include "../src/tree_resource_population.cpp"
#include <iostream>
int main(){
    for(bool reverse:{false,true})for(bool breeding:{false,true}){
        std::vector<TreeQuestionTrace> idle_trace,review_trace;
        auto idle=run_tree_resource_population(12000,breeding,reverse,TreeQuestionSchedule::CleanDelay,0,&idle_trace);
        auto review=run_tree_resource_population(12000,breeding,reverse,TreeQuestionSchedule::CleanReview,0,&review_trace);
        population_check(idle.rows.size()==16&&review.rows.size()==16,"extended schedule length");
        for(int round=1;round<=8;++round){
            const auto& a=idle.rows[size_t(round-1)];const auto& b=review.rows[size_t(round-1)];
            population_check(a.totals.balance==b.totals.balance&&a.totals.answers==b.totals.answers&&
                a.living==b.living,"identical first eight rounds");
        }
        for(const auto& e:idle_trace)population_check(e.round<9||e.round>12,"idle rounds do not execute questions");
        for(const auto& r:review.rows)population_check(r.totals.balance==200000+r.totals.rewarded-r.totals.spent,
            "review resource conservation");
        population_check(review.rows.back().totals.answers>idle.rows.back().totals.answers,
            "review unlocks actual answers");
    }
    std::cout<<"PASS matched 16-round delay/review, eight sanitized populations, 128 censuses\n";
}
