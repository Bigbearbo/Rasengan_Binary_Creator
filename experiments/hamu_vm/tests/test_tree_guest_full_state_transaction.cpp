#include "tree_generation_registry_fixture.hpp"
// Host-only V2 envelope. Caller MUST call commit() after every mutation.
// A separate durable high-water revision is required across process restarts.
struct RevisionRegistry {
 DurableRegistry& inner;
 uint64_t revision=0;
 explicit RevisionRegistry(DurableRegistry& d):inner(d){}
 bool commit(){if(revision==UINT64_MAX)return false;++revision;return true;}
 std::string snapshot() const {return "HAMU-REV-2 "+std::to_string(revision)+"\n"+inner.snapshot();}
 bool restore(const std::string& data){
  const auto nl=data.find('\n');if(nl==std::string::npos)return false;
  std::istringstream header(data.substr(0,nl));std::string magic,extra;uint64_t incoming=0;
  if(!(header>>magic>>incoming)||magic!="HAMU-REV-2"||(header>>extra)||incoming<revision || (incoming==revision && revision>0 && data!=snapshot()))return false;
  // The underlying restore validates and commits atomically in memory.
  if(!inner.restore(data.substr(nl+1)))return false;
  revision=incoming;return true;
 }
};

#include <stdexcept>
// Host-only controlled mutation boundary. Not a VM-wide write interceptor.
struct TransactionalRevision {
 RevisionRegistry& r;
 explicit TransactionalRevision(RevisionRegistry& x):r(x){}
 template<class Fn> bool apply(Fn fn){
  const auto before=r.snapshot();
  const auto old_revision=r.revision;
  try {
   if(!fn()) {require(r.inner.restore(before.substr(before.find('\n')+1)),"rollback restore failed");return false;}
   // Compare canonical inner snapshots, not only a reported success flag.
   if(r.inner.snapshot()==before.substr(before.find('\n')+1))return true;
   if(!r.commit()) {require(r.inner.restore(before.substr(before.find('\n')+1)),"overflow rollback failed");return false;}
   return true;
  } catch(...) {
   require(r.inner.restore(before.substr(before.find('\n')+1)),"exception rollback failed");
   require(r.revision==old_revision,"revision changed after exception");
   throw;
  }
 }
};

// Host-only guest execution boundary for canonical tree mutations.
// It does not promise rollback of work/status/output or external side effects.
struct GuestTreeEnvelope {
 TransactionalRevision& tx;
 explicit GuestTreeEnvelope(TransactionalRevision& t):tx(t){}
 template<class Fn> bool run(Fn fn){return tx.apply(fn);}
};

// Isolated host-side experiment: complete in-memory checkpoint, not a guest API.
struct FullStateEnvelope {
 Hamster& h; DurableRegistry& d; RevisionRegistry& r;
 template<class Fn> bool run(Fn fn) {
  Hamster saved=h;
  auto saved_generations=d.generation;
  auto saved_lineage=d.lineage;
  auto saved_revision=r.revision;
  const auto before=d.snapshot();
  auto rollback=[&](){h=saved;d.generation=saved_generations;d.lineage=saved_lineage;r.revision=saved_revision;};
  try {
   if(!fn()){rollback();return false;}
   if(d.snapshot()==before && h.memory==saved.memory && h.hp==saved.hp && h.val_reg==saved.val_reg) return true;
   if(r.revision==UINT64_MAX){rollback();return false;}
   ++r.revision;return true;
  }catch(...){rollback();throw;}
 }
};
int main(){
 Hamster h(8301,extended());DurableRegistry d(h,401);RevisionRegistry r(d);
 FullStateEnvelope tx{h,d,r};
 set_id_candidate(h,0,0);
 require(tx.run([&](){execute(h,{28,1,15,0});return true;}),"add");
 require(r.revision==1,"revision");
 auto handle=d.acquire(1);
 bool work_before=h.memory[h.params.layout.work_start];
 require(tx.run([&](){h.memory[h.params.layout.work_start]=!work_before;return true;}),"work commit");
 require(r.revision==2 && h.memory[h.params.layout.work_start]!=work_before,"work-only mutation not versioned");
 auto before_h=h.memory;auto before_tree=d.snapshot();auto before_rev=r.revision;
 require(!tx.run([&](){
   h.memory[h.params.layout.work_start]=!h.memory[h.params.layout.work_start];
   require(d.erase(handle),"erase");return false;
 }),"rejected transaction accepted");
 require(h.memory==before_h && d.snapshot()==before_tree && r.revision==before_rev,"rollback leaked work/tree/generation");
 require(d.valid(handle),"failed transaction invalidated handle");
 const auto saved_hp=h.hp;
 bool thrown=false;
 try{tx.run([&]()->bool{h.hp-=10;require(d.erase(handle),"erase exception");throw std::runtime_error("injected");});}
 catch(const std::runtime_error&){thrown=true;}
 require(thrown && d.valid(handle) && d.snapshot()==before_tree && h.hp==saved_hp,"exception rollback leaked");
 r.revision=UINT64_MAX;
 auto high=d.snapshot();
 require(!tx.run([&](){require(d.erase(handle),"erase overflow");return true;}),"overflow accepted");
 require(d.snapshot()==high && d.valid(handle) && r.revision==UINT64_MAX,"overflow rollback leaked");
 std::cout<<"PASS: full-state host checkpoint rolls back work, generation, HP, exception and revision overflow\n";
 return 0;
}
