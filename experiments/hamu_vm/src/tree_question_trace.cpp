#define TREE_RESOURCE_POPULATION_NO_MAIN
#include "tree_resource_population.cpp"
int main(){
    std::cout<<"seed,round,id,width,op,data,before_slots,after_slots,candidate,route,attempt,valid,correct,confirmed,balance_before,balance_after\n";
    for(int seed=0;seed<=4;++seed){
        std::vector<TreeQuestionTrace> trace;
        const auto schedule=seed?TreeQuestionSchedule::CleanPermuted:TreeQuestionSchedule::CleanVaried;
        auto result=run_tree_resource_population(12000,false,false,schedule,seed,&trace);
        for(const auto& e:trace)
            std::cout<<e.seed<<','<<e.round<<','<<e.id<<','<<e.width<<','<<e.op<<','<<e.data
                <<','<<e.before_slots<<','<<e.after_slots<<','<<e.candidate<<','<<e.route
                <<','<<e.attempt<<','<<e.valid<<','<<e.correct<<','<<e.confirmed
                <<','<<e.balance_before<<','<<e.balance_after<<'\n';
        population_check(result.rows.size()==12,"trace schedule length");
    }
    std::cout<<"PASS five order traces, four founders each, actual VM outcomes\n";
}
