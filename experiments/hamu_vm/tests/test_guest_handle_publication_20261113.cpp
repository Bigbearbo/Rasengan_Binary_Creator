// Window-GPT (ChatGPT conversation), 2026-11-13.
// Independent host-only regression; intentionally does not modify VM core.
#include "tree_generation_registry_fixture.hpp"
#include <stdexcept>
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

#include <unordered_map>

// A capability-only public interface: no raw generation handle is accepted.
// This is a host API prototype; private DurableRegistry remains reachable to the host.
class PublishedRefs {
 public:
  struct Token { uint64_t ticket; };
  explicit PublishedRefs(DurableRegistry& d): d_(d) {}
  template<class Fn> bool run(FullStateEnvelope& tx, Fn fn){
   require(!in_tx_, "nested published ref transaction");
   in_tx_=true;
   try{bool ok=tx.run(fn);in_tx_=false;return ok;}
   catch(...){in_tx_=false;throw;}
  }
  Token publish(uint32_t id){
   if(in_tx_)throw std::logic_error("cannot publish uncommitted reference");
   auto raw=d_.acquire(id);
   if(!d_.valid(raw) || next_ticket_==UINT64_MAX)
    throw std::logic_error("cannot publish invalid reference");
   const auto ticket=next_ticket_++;
   published_.emplace(ticket,raw);
   return {ticket};
  }
  bool valid(Token t) const {
   auto it=published_.find(t.ticket);
   return it!=published_.end() && d_.valid(it->second);
  }
 private:
  DurableRegistry& d_;
  bool in_tx_=false;
  uint64_t next_ticket_=1;
  std::unordered_map<uint64_t,DurableRegistry::Ref> published_;
};

int main(){
 Hamster h(8501,extended());DurableRegistry d(h,8501);RevisionRegistry rev(d);
 FullStateEnvelope tx{h,d,rev};PublishedRefs pub(d);
 set_id_candidate(h,0,0);
 DurableRegistry::Ref leaked{};
 // Negative control: raw references can escape a rejected host transaction.
 require(!tx.run([&](){execute(h,{28,1,15,0});leaked=d.acquire(1);return false;}),"abort expected");
 require(!d.valid(leaked),"reference unexpectedly valid directly after abort");
 require(tx.run([&](){execute(h,{28,1,15,0});return true;}),"reallocation failed");
 require(d.valid(leaked),"expected raw ABA alias not reproduced");
 // New guarded API rejects publication during a tentative transaction.
 bool blocked=false;
 require(!pub.run(tx,[&](){
   try{(void)pub.publish(1);}catch(const std::logic_error&){blocked=true;}
   return false;
 }),"controlled rejection expected");
 require(blocked,"provisional handle was publicly minted");
 auto committed=pub.publish(1);
 require(pub.valid(committed),"committed handle was not valid");
 // Abort a deletion; previously published committed handles must survive.
 require(!pub.run(tx,[&](){require(d.erase(d.acquire(1)),"erase in rejected transaction");return false;}),"abort expected");
 require(pub.valid(committed),"abort invalidated old committed handle");
 // A committed erase and reallocation invalidates old published handle.
 require(pub.run(tx,[&](){require(d.erase(d.acquire(1)),"committed erase");return true;}),"erase failed");
 set_id_candidate(h,0,0);
 require(pub.run(tx,[&](){execute(h,{28,1,15,0});return true;}),"new allocation failed");
 require(!pub.valid(committed),"published handle ABA after committed recycle");
 auto next=pub.publish(1);
 require(pub.valid(next) && next.ticket!=committed.ticket,"new minted handle mismatch");
 require(!pub.valid(PublishedRefs::Token{UINT64_MAX}),"unissued ticket valid");
 std::cout << "PASS raw aborted-handle ABA reproduced; publication-gated host token tests passed\n";
}
