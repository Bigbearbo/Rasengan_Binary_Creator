#define TREE_ERROR_WORLD_NO_MAIN
#include "../src/tree_error_world.cpp"
int main(){
    auto r=run_error_world();
    if(r.promotion_round<=0||r.laggards!=1||r.rows.back().question!=2||
        r.rows.back().mastered!=4||r.rows.back().resource<0)
        throw std::runtime_error("majority-gated question world");
    for(const auto& row:r.rows)if(row.mastered<0||row.mastered>4||row.correct>4)
        throw std::runtime_error("error world counters");
    auto limited=run_error_world(4);
    if(limited.promotion_round!=0||limited.rows.size()!=16||
        limited.rows[2].resource!=2800||limited.rows.back().resource!=2800||
        limited.rows.back().question!=1)
        throw std::runtime_error("full tree must refuse trials without losing resources");
    std::cout<<"PASS majority gate and full-tree refusal without repeated paid attempts\n";
}
