#define main prior_reject_main
#include "test_tree_reject_mask.cpp"
#undef main
static HamsterParams extended(){auto p=cfg(true,3);p.tree_confirm_three_bits_enabled=true;return p;}
static bool recycle_leaf(Hamster& h,int id){if(id<1||id>h.params.tree_capacity || !(h.segment_row(id)&1u))return false;for(int other=1;other<=h.params.tree_capacity;++other){uint32_t row=h.segment_row(other);if(other!=id && (row&1u) && (row>>7)==unsigned(id))return false;}h.segment_row_ref(id)=0;h.invalidate_segment_index();h.rebuild_segment_first_free_id();return true;}
#include <vector>
#include <cstdint>
struct Handle {uint32_t id; uint64_t generation;};
struct Registry {
 Hamster& h; std::vector<uint64_t> gen;
 explicit Registry(Hamster& x):h(x),gen(x.params.tree_capacity+1,1){}
 Handle acquire(int id) const {return {uint32_t(id),gen.at(id)};}
 bool valid(Handle a) const {return a.id>0&&a.id<gen.size()&&gen[a.id]==a.generation&&(h.segment_row(a.id)&1u);}
 bool erase(Handle a){if(!valid(a))return false;if(!recycle_leaf(h,a.id))return false;++gen[a.id];return true;}
};
int main(){
 Hamster h(7001,extended());Registry registry(h);
 set_id_candidate(h,0,0);execute(h,{28,1,15,0});
 auto old=registry.acquire(1);require(registry.valid(old),"initial handle invalid");
 set_id_candidate(h,1,1);execute(h,{28,1,15,0});auto child=registry.acquire(2);
 require(!registry.erase(old),"nonleaf deletion incorrectly allowed");require(registry.valid(old),"failed delete invalidated handle");
 require(registry.erase(child),"leaf deletion failed");require(!registry.valid(child),"deleted handle remained valid");
 require(registry.erase(old),"parent deletion failed");require(!registry.valid(old),"deleted parent handle valid");
 set_id_candidate(h,0,0);execute(h,{28,1,15,0});auto fresh=registry.acquire(1);
 require(fresh.id==old.id&&fresh.generation!=old.generation,"reuse not distinguished");
 require(!registry.valid(old)&&registry.valid(fresh),"ABA alias survived");
 require(!registry.erase(old)&&registry.valid(fresh),"stale handle erased new record");
 // A raw integer ID is still unsafe; the registry is a host-only prototype.
 std::cout<<"PASS generation handle prevents stale ID reuse alias; failed delete preserves handle\n";
}
