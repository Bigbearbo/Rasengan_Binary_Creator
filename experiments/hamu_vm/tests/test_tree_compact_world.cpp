#define TREE_COMPACT_WORLD_NO_MAIN
#include "../src/tree_compact_world.cpp"
int main(){
    const auto r=run_compact_world();
    if(r.promotion_round!=6||r.laggards!=1||r.rows.back().question!=2||
       r.rows.back().mastered!=4||r.rows.back().resource!=3600||
       r.rows[5].mastered!=3||r.rows[6].resource!=2800||
       r.used_question_nodes!=8||r.reserved_tree_bits!=1116||
       r.reserved_payload_bits!=1488||r.vm_steps<=0||r.vm_calls<=0||
       r.peak_vm_steps<=0||r.peak_vm_steps>=4000||
       r.vm_steps>10000||r.vm_calls>230)
        throw std::runtime_error("compact world majority or resource accounting");
    const auto small=run_compact_world(1);
    if(small.promotion_round!=6||small.rows.size()!=16||
       small.rows[6].resource!=2900||small.rows.back().resource!=2900||
       small.rows.back().question!=2||small.rows.back().mastered!=0||
       small.used_question_nodes!=4||small.reserved_tree_bits!=36||
       small.reserved_payload_bits!=48)
        throw std::runtime_error("compact world full tree refusal");
    std::cout<<"PASS compact four-agent world promotion, resource accounting, capacity refusal\n";
}
