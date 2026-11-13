// [視窗GPT] Host reference ticket issuer epoch regression, 2026-11-13.
#define HAMU_PUBLICATION_NO_MAIN
#include "test_guest_handle_publication_20261113.cpp"
#undef HAMU_PUBLICATION_NO_MAIN

// This is an independent host-side issuance-epoch experiment.
// Non-cryptographic reference IDs: no claim of adversarial unforgeability.
struct IssuerHighwater {
 uint64_t last_epoch=0;
 explicit IssuerHighwater(uint64_t previous):last_epoch(previous){}
 bool issue(uint64_t& out){
  if(last_epoch==UINT64_MAX)return false;
  out=++last_epoch;
  return true;
 }
};
class SessionPublishedRefs {
 public:
  struct Token {uint64_t issuer_epoch, serial;};
  SessionPublishedRefs(DurableRegistry& d,IssuerHighwater& authority): d_(d) {
   if(!authority.issue(epoch_))throw std::overflow_error("epoch highwater exhausted");
  }
  Token publish(uint32_t id){
   auto raw=d_.acquire(id);
   if(!d_.valid(raw)||serial_==UINT64_MAX)
    throw std::logic_error("invalid node or ticket overflow");
   uint64_t s=serial_++;
   refs_.emplace(s,raw);
   return {epoch_,s};
  }
  bool valid(Token t)const{
   if(t.issuer_epoch!=epoch_)return false;
   auto it=refs_.find(t.serial);
   return it!=refs_.end() && d_.valid(it->second);
  }
 private:
  DurableRegistry& d_;
  uint64_t epoch_=0,serial_=1;
  std::unordered_map<uint64_t,DurableRegistry::Ref> refs_;
};

#ifndef HAMU_SESSION_EPOCH_NO_MAIN
int main(){
 Hamster h(9601,extended());DurableRegistry d(h,9601);
 set_id_candidate(h,0,0);execute(h,{28,1,15,0});
 require(d.valid(d.acquire(1)),"fixture node1 missing");
 set_id_candidate(h,0,0);execute(h,{28,2,15,0});
 require(d.valid(d.acquire(2)),"fixture node2 missing");
 // Baseline: two independent issuers reset next_ticket=1.
 PublishedRefs::Token stale{};
 {
  PublishedRefs before(d);
  stale=before.publish(1);
  require(before.valid(stale),"original token should refer to node1");
 }
 PublishedRefs after(d);
 auto another=after.publish(2);
 require(stale.ticket==another.ticket,"expected reused initial ticket counter");
 require(after.valid(stale),"expected baseline cross-session token confusion");
 require(d.erase(d.acquire(1)),"erase original node1");
 require(!d.valid(d.acquire(1)),"original node still live");
 require(after.valid(stale),"old ticket not spuriously rebound to second node");
 // Remedy model: issuer identity is separately versioned; serial may restart safely.
 IssuerHighwater highwater(700);
 SessionPublishedRefs::Token old{};
 {
  SessionPublishedRefs a(d,highwater);
  old=a.publish(2);
  require(a.valid(old),"old session token initially invalid");
 }
 auto durable_highwater=highwater.last_epoch; // Simulated checkpoint, not disk durability.
 // Negative control: restoring a STALE issuer high-water would revive a token
 // even with (issuer_epoch, serial). No persistence guarantee is asserted.
 set_id_candidate(h,0,0);execute(h,{28,3,15,0});
 require(d.valid(d.acquire(1)),"recycled fixture node1 missing");
 IssuerHighwater stale_checkpoint(700);
 SessionPublishedRefs restarted_unsafely(d,stale_checkpoint);
 auto reused=restarted_unsafely.publish(1);
 require(reused.issuer_epoch==old.issuer_epoch && reused.serial==old.serial &&
         restarted_unsafely.valid(old),"stale epoch checkpoint hazard not reproduced");
 IssuerHighwater restarted(durable_highwater);
 SessionPublishedRefs b(d,restarted);
 auto fresh=b.publish(2);
 require(old.serial==fresh.serial,"test must reuse within-session serial");
 require(old.issuer_epoch!=fresh.issuer_epoch,"new session reused epoch");
 require(b.valid(fresh) && !b.valid(old),"issuer-epoch guard failed across restart");
 require(!b.valid({0,fresh.serial}),"invalid epoch accepted");
 // A committed deletion still invalidates an otherwise current token.
 require(d.erase(d.acquire(2)),"delete second node failed");
 require(!b.valid(fresh),"deleted-node ticket remained live");
 // Overflow must fail closed, not repeat the initial issuer ID.
 IssuerHighwater exhausted(UINT64_MAX);
 bool refused=false;
 try{SessionPublishedRefs forbidden(d,exhausted);}catch(const std::overflow_error&){refused=true;}
 require(refused,"issuer epoch overflow accepted");
 std::cout << "PASS: baseline ticket reuse alias reproduced; issuer epoch, deletion, overflow guards pass (host-only)\n";
}

#endif // HAMU_SESSION_EPOCH_NO_MAIN
