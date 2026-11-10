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
int main(){
 Hamster h(8001,extended());DurableRegistry d(h,400);RevisionRegistry r(d);
 set_id_candidate(h,0,0);execute(h,{28,1,15,0});require(r.commit(),"first commit");
 auto first=r.snapshot();auto handle=d.acquire(1); auto old_row=h.segment_row(1);
 // Same generation, new confirmed answer: generation-only guard would accept first snapshot.
 h.segment_row_ref(1) ^= (1u<<1);require(h.segment_row(1)!=old_row,"answer write did not change row");require(r.commit(),"second commit");
 auto second=r.snapshot();require(first!=second,"revisions did not advance");
 require(!r.restore(first),"accepted same-generation stale snapshot");
 require(r.snapshot()==second,"stale snapshot changed state");
 require(d.valid(handle),"same-generation handle unexpectedly invalid");
 require(!r.restore("HAMU-REV-2 18446744073709551616\n"+d.snapshot()),"accepted revision overflow");
 require(r.snapshot()==second,"overflow mutated state");
 require(!r.restore("HAMU-REV-2 2 trailing\n"+d.snapshot()),"accepted trailing header");
 require(r.snapshot()==second,"trailing header mutated state");
 require(r.restore(second),"same revision reload failed");
 require(!r.restore("HAMU-REV-2 2\n"+first.substr(first.find('\n')+1)),"accepted same revision conflicting payload");
 // Fresh process with no trusted high-water mark CAN accept old snapshots.
 Hamster fresh(8002,extended());DurableRegistry fresh_d(fresh,400);RevisionRegistry fresh_r(fresh_d);
 require(fresh_r.restore(first),"fresh process rejected structurally valid old snapshot");
 require(fresh_r.revision==1,"fresh revision mismatch");
 std::cout<<"PASS revision guard same-generation stale restore, rollback, malformed header; restart limitation demonstrated\n";
}
