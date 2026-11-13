// Research: Window-GPT (ChatGPT conversation), 2026-11-13.
// Negative regression: issuer-epoch guard must not drop transaction-publish guard.
// Build on the unmodified prior published prototypes; no VM core edits.
#define HAMU_SESSION_EPOCH_NO_MAIN
#include "test_guest_handle_session_epoch_20261113.cpp"
#undef HAMU_SESSION_EPOCH_NO_MAIN

class TransactionAwareEpochRefs {
 public:
  using Token=SessionPublishedRefs::Token;
  TransactionAwareEpochRefs(DurableRegistry& registry,IssuerHighwater& authority)
      : issuer_(registry,authority) {}
  template<class F> bool run(FullStateEnvelope& tx,F body){
    if(active_) throw std::logic_error("nested publication transaction");
    active_=true;
    try {bool committed=tx.run(body);active_=false;return committed;}
    catch(...){active_=false;throw;}
  }
  Token publish(uint32_t id){
    if(active_)throw std::logic_error("uncommitted reference publication");
    return issuer_.publish(id);
  }
  bool valid(Token t)const{return issuer_.valid(t);}
 private:
  SessionPublishedRefs issuer_;
  bool active_=false;
};

int main(){
  // Negative control: the previous epoch/serial issuer has NO transaction guard.
  {
    Hamster h(9801,extended());DurableRegistry d(h,9801);
    RevisionRegistry r(d);FullStateEnvelope tx{h,d,r};
    IssuerHighwater authority(40);SessionPublishedRefs old(d,authority);
    set_id_candidate(h,0,0);
    SessionPublishedRefs::Token provisional{};
    require(!tx.run([&]{
      execute(h,{28,1,15,0});
      provisional=old.publish(1); // unexpectedly accepted before commit
      require(old.valid(provisional),"provisional token absent during transaction");
      return false;
    }),"abort must fail");
    require(!old.valid(provisional),"rollback should temporarily invalidate token");
    require(tx.run([&]{execute(h,{28,1,15,0});return true;}),"second add must commit");
    require(old.valid(provisional),"missing cross-transaction ABA after abort/reuse");
    require(r.revision==1,"only committed add should increase revision");
  }
  // Positive prototype: same epoch/serial mechanism WITH an explicit tx gate.
  {
    Hamster h(9802,extended());DurableRegistry d(h,9802);
    RevisionRegistry r(d);FullStateEnvelope tx{h,d,r};
    IssuerHighwater authority(100);TransactionAwareEpochRefs safe(d,authority);
    set_id_candidate(h,0,0);
    bool blocked=false;
    require(!safe.run(tx,[&]{
      execute(h,{28,1,15,0});
      try{(void)safe.publish(1);}catch(const std::logic_error&){blocked=true;}
      return false;
    }),"intentional abort must not commit");
    require(blocked,"missing transaction issuance guard");
    require(r.revision==0 && !(h.segment_row(1)&1u),"rejected add leaked canonical tree");
    bool refused=false;
    try{(void)safe.publish(1);}catch(const std::logic_error&){refused=true;}
    require(refused,"issuer minted non-existent node outside aborted transaction");
    require(safe.run(tx,[&]{execute(h,{28,1,15,0});return true;}),"valid add failed");
    auto committed=safe.publish(1);
    require(safe.valid(committed),"post-commit publication failed");
    // A rejected deletion must not invalidate a previously published token.
    require(!safe.run(tx,[&]{require(d.erase(d.acquire(1)),"delete setup");return false;}),
            "abort failed");
    require(safe.valid(committed),"aborted delete invalidated committed token");
    require(safe.run(tx,[&]{require(d.erase(d.acquire(1)),"committed erase");return true;}),
            "committed erase failed");
    set_id_candidate(h,0,0);
    require(safe.run(tx,[&]{execute(h,{28,1,15,0});return true;}),"recycle failed");
    require(!safe.valid(committed),"committed delete/reuse failed to revoke prior ticket");
    auto replacement=safe.publish(1);
    require(safe.valid(replacement) && replacement.serial!=committed.serial,
            "replacement token must have fresh serial");
  }
  std::cout<<"PASS: epoch issuer lost transaction guard (ABA reproduced); composed host guard blocks provisional publication\n";
}
