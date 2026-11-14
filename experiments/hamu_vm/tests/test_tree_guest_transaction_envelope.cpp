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
int main(){
 Hamster h(8300,extended());DurableRegistry d(h,400);RevisionRegistry r(d);
 TransactionalRevision tx(r);GuestTreeEnvelope gate(tx);
 set_id_candidate(h,0,0);
 require(gate.run([&](){execute(h,{28,1,15,0});return true;}),"TREE_ADD failed");
 require(r.revision==1 && (h.segment_row(1)&1u),"TREE_ADD not committed");
 const auto stable=r.snapshot();
 require(gate.run([&](){return true;}),"noop failed");
 require(r.snapshot()==stable,"noop changed revision");
 require(!gate.run([&](){h.segment_row_ref(1)^=(1u<<1);return false;}),"failure accepted");
 require(r.snapshot()==stable,"failed mutation leaked");
 bool thrown=false;
 try{gate.run([&]()->bool{h.segment_row_ref(1)^=(1u<<2);throw std::runtime_error("injected");});}
 catch(const std::runtime_error&){thrown=true;}
 require(thrown&&r.snapshot()==stable,"exception leaked");
 r.revision=UINT64_MAX;
 const auto overflow_before=r.snapshot();
 require(!gate.run([&](){h.segment_row_ref(1)^=(1u<<3);return true;}),"overflow accepted");
 require(r.snapshot()==overflow_before,"overflow leaked");
 std::cout<<"PASS: guest TREE_ADD revision, noop, failure/exception rollback, overflow guard (canonical tree only)\n";
}
