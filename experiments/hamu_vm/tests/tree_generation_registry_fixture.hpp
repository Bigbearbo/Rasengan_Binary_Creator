#define main previous_reject_main
#include "test_tree_reject_mask.cpp"
#undef main
static HamsterParams extended(){auto p=cfg(true,3);p.tree_confirm_three_bits_enabled=true;return p;}
static bool recycle_leaf(Hamster& h,int id){if(id<1||id>h.params.tree_capacity || !(h.segment_row(id)&1u))return false;for(int other=1;other<=h.params.tree_capacity;++other){uint32_t row=h.segment_row(other);if(other!=id && (row&1u) && (row>>7)==unsigned(id))return false;}h.segment_row_ref(id)=0;h.invalidate_segment_index();h.rebuild_segment_first_free_id();return true;}
#include <sstream>
#include <unordered_set>
#include <limits>
#include <stdexcept>
// Host-only snapshot prototype: persist generations with tree rows as one logical unit.
struct DurableRegistry {
 Hamster& h;
 std::vector<uint64_t> generation;
 uint64_t lineage;
 explicit DurableRegistry(Hamster& host,uint64_t domain=1):h(host),generation(host.params.tree_capacity+1,1),lineage(domain){if(!domain)throw std::invalid_argument("domain");}
 struct Ref {uint32_t id;uint64_t generation;uint64_t lineage;};
 Ref acquire(uint32_t id)const{return {id,generation.at(id),lineage};}
 bool valid(Ref r)const{return r.lineage==lineage&&r.id>0&&r.id<generation.size()&&r.generation==generation[r.id]&&(h.segment_row(r.id)&1u);}
 bool erase(Ref r){if(!valid(r)||generation[r.id]==UINT64_MAX)return false;if(!recycle_leaf(h,r.id))return false;++generation[r.id];return true;}
 std::string snapshot()const{
  std::ostringstream s; s<<"HAMU-GEN-1 "<<lineage<<' '<<h.params.tree_capacity<<' '<<h.segment_used<<'\n';
  for(int id=1;id<=h.params.tree_capacity;++id)s<<generation[id]<<' '<<h.segment_row(id)<<'\n';
  return s.str();
 }
 bool restore(const std::string& data,bool allow_lineage_change=false){
  std::istringstream s(data);std::string magic;uint64_t domain=0;int capacity=0,used=0;
  if(!(s>>magic>>domain>>capacity>>used)||magic!="HAMU-GEN-1"||!domain||(capacity!=h.params.tree_capacity||used<0||used>capacity))return false;
  std::vector<uint64_t> gens(capacity+1,1);std::vector<uint32_t> rows(capacity+1);
  for(int id=1;id<=capacity;++id){uint64_t g=0,r=0;if(!(s>>g>>r)||!g||r>UINT32_MAX)return false;gens[id]=g;rows[id]=uint32_t(r);}
  std::string trailing;if(s>>trailing)return false;
  // Never roll back generation counters inside the same lineage: that can revive stale handles.
  if(domain!=lineage && !allow_lineage_change)return false;
  if(domain==lineage){for(int id=1;id<=capacity;++id)if(gens[id]<generation[id])return false;}
  // Validate canonical tree before committing any state.
  std::unordered_set<uint64_t> edges;
  for(int id=1;id<=capacity;++id){
   const uint32_t row=rows[id];
   if(id>used && row!=0)return false;
   if(!(row&1u)){if(row!=0)return false;continue;}
   const uint32_t parent=row>>7, key=(row>>4)&7u;
   if(parent>uint32_t(used)||parent==uint32_t(id))return false;
   if(parent && !(rows[parent]&1u))return false;
   if(!edges.insert((uint64_t(parent)<<3)|key).second)return false;
  }
  // Functional parent graph: each node is visited at most twice, O(N).
  std::vector<uint8_t> color(capacity+1,0);
  for(int id=1;id<=used;++id)if((rows[id]&1u)&&color[id]==0){
   std::vector<int> chain;
   int node=id;
   while(node && color[node]==0){
    color[node]=1;chain.push_back(node);
    node=int(rows[node]>>7);
   }
   if(node && color[node]==1)return false;
   for(int n:chain)color[n]=2;
  }

  // All parsing/validation before modifying live tree. In this trial rows are trusted
  // as a complete host snapshot; no disk crash-atomicity or checksum yet.
  for(int id=1;id<=capacity;++id)h.segment_row_ref(id)=rows[id];
  h.segment_used=used;generation=std::move(gens);lineage=domain;
  h.invalidate_segment_index();h.rebuild_segment_first_free_id();return true;
 }
 // Host-only atomic logical import: commit snapshot only after validation, then bind to child lineage.
 bool clone_into_new_lineage(const std::string& data,uint64_t child_domain){
  if(!child_domain || child_domain==lineage)return false;
  std::istringstream in(data);std::string magic;uint64_t source=0;
  if(!(in>>magic>>source)||magic!="HAMU-GEN-1"||!source||source==child_domain)return false;
  // The existing restore validates the complete payload before committing.
  if(!restore(data,true))return false;
  lineage=child_domain;return true;
 }
};
int prior_generation_main(){
 Hamster h(7101,extended());DurableRegistry d(h,99);
 set_id_candidate(h,0,0);execute(h,{28,1,15,0});auto old=d.acquire(1);
 require(d.erase(old),"erase old");set_id_candidate(h,0,0);execute(h,{28,1,15,0});auto fresh=d.acquire(1);
 auto bytes=d.snapshot();Hamster loaded(7102,extended());DurableRegistry recovered(loaded,99);
 require(recovered.restore(bytes),"restore failed");
 require(!recovered.valid(old)&&recovered.valid(fresh),"ABA after reload");
 require(!recovered.erase(old)&&recovered.valid(fresh),"stale erase after reload");
 // Foreign lineage cannot silently overwrite a live registry.
 Hamster foreign_h(7201,extended());DurableRegistry foreign(foreign_h,777);
 set_id_candidate(foreign_h,0,0);execute(foreign_h,{28,1,15,0});
 auto foreign_bytes=foreign.snapshot();
 auto local_before=recovered.snapshot();
 require(!recovered.restore(foreign_bytes),"foreign lineage overwrote live registry");
 require(recovered.snapshot()==local_before,"foreign lineage rejection changed state");
 auto before=recovered.snapshot();
 auto reject_bad=[&](std::string bad,const char* why){require(!recovered.restore(bad),why);require(recovered.snapshot()==before,"bad structure changed live state");};
 {auto bad=bytes;auto pos=bad.find('\n');auto next=bad.find('\n',pos+1);bad.replace(pos+1,next-pos-1,"2 129");reject_bad(bad,"accepted dangling parent");}
 {auto bad=bytes;auto pos=bad.find('\n');auto next=bad.find('\n',pos+1);bad.replace(pos+1,next-pos-1,"2 145");reject_bad(bad,"accepted self parent");}
 // Forge two active nodes with identical (parent,key), and a two-node cycle.
 {auto bad=bytes;auto header=bad.find('\n');bad.replace(0,header,"HAMU-GEN-1 99 3 2");auto pos=bad.find('\n');bad=bad.substr(0,pos+1)+"2 1\n1 1\n1 0\n";reject_bad(bad,"accepted duplicate edges");}
 {auto bad=bytes;auto header=bad.find('\n');bad.replace(0,header,"HAMU-GEN-1 99 3 2");auto pos=bad.find('\n');bad=bad.substr(0,pos+1)+"2 257\n1 129\n1 0\n";reject_bad(bad,"accepted two-node cycle");}
 // A previously valid snapshot must not rewind a live lineage after a later deletion.
 auto stale_snapshot=recovered.snapshot();
 require(recovered.erase(fresh),"delete fresh for rollback attack");
 auto after_delete=recovered.snapshot();
 require(!recovered.restore(stale_snapshot),"accepted generation rollback / stale handle resurrection");
 require(recovered.snapshot()==after_delete,"generation rollback mutated live state");
 require(!recovered.valid(fresh),"stale handle resurrected");
 require(recovered.restore(bytes)==false,"accepted old generation from same lineage");
 // Rehydrate the test's live state using an isolated new registry (restart scenario).
 Hamster reloaded(7110,extended());DurableRegistry new_session(reloaded,99);
 require(new_session.restore(bytes),"fresh session cannot load valid snapshot");
 require(!new_session.restore(bytes+" CORRUPT"),"accepted trailing corruption");require(new_session.snapshot()==before,"corrupt snapshot mutated state");
 require(!new_session.restore("HAMU-GEN-1 99 3\n"),"accepted truncated snapshot");require(new_session.snapshot()==before,"truncation mutated state");
 Hamster offspring(7103,extended());DurableRegistry inherited(offspring,100);
 require(!inherited.restore(bytes),"cross-lineage restore unexpectedly accepted");
 require(inherited.restore(bytes,true),"explicit offspring import failed");
 // Copying identical lineage identifiers across independent agents would permit cross-agent aliases.
 // Assign new lineage at birth and invalidate references from the parent.
 inherited.lineage=100;
 require(!inherited.valid(fresh),"parent handle leaked into child lineage");
 auto child=inherited.acquire(1);require(inherited.valid(child),"child handle invalid");
 // New API must reject invalid child lineage and corrupt input without modifying destination.
 Hamster child_h(7301,extended());DurableRegistry child_reg(child_h,500);
 auto child_before=child_reg.snapshot();
 require(!child_reg.clone_into_new_lineage(bytes,0),"accepted zero child lineage");
 require(!child_reg.clone_into_new_lineage(bytes,99),"accepted source lineage as child");
 require(!child_reg.clone_into_new_lineage(bytes+" BAD",501),"accepted corrupt child snapshot");
 require(child_reg.snapshot()==child_before,"failed child import changed state");
 require(child_reg.clone_into_new_lineage(bytes,501),"atomic child import failed");
 require(child_reg.lineage==501,"child lineage not bound");
 require(!child_reg.valid(fresh),"parent reference valid in child");
 require(child_reg.valid(child_reg.acquire(1)),"child reference invalid");
 require(d.valid(fresh),"parent corrupted by child");
 std::cout<<"PASS durable host registry reload, stale refs, corrupt rollback, offspring isolation\n";
}
