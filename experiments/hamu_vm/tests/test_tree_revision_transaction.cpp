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
int main(){
 Hamster h(8100,extended());DurableRegistry d(h,400);RevisionRegistry r(d);TransactionalRevision tx(r);
 set_id_candidate(h,0,0);execute(h,{28,1,15,0});require(r.commit(),"initial");
 const auto base=r.snapshot();
 require(tx.apply([&](){h.segment_row_ref(1)^=(1u<<1);return true;}),"write");
 require(r.revision==2,"write did not advance revision");const auto updated=r.snapshot();
 require(!r.restore(base),"stale snapshot accepted");
 require(!tx.apply([&](){h.segment_row_ref(1)^=(1u<<2);return false;}),"failed write accepted");
 require(r.snapshot()==updated,"failed transaction leaked mutation");
 require(tx.apply([&](){return true;}),"noop failed");require(r.revision==2,"noop advanced revision");
 bool caught=false;try{tx.apply([&]()->bool{h.segment_row_ref(1)^=(1u<<3);throw std::runtime_error("injected");});}catch(const std::runtime_error&){caught=true;}
 require(caught&&r.snapshot()==updated,"exception rollback failed");
 // The host wrapper cannot detect raw writes made outside apply(). This is intentional limitation.
 h.segment_row_ref(1)^=(1u<<4);require(r.revision==2,"external write unexpectedly tracked");
 require(r.snapshot()!=updated,"external write not observed");
 std::cout<<"PASS transactional revision success/failure/noop/exception; external bypass demonstrated\n";
}
