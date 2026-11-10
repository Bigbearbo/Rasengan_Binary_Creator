#pragma once
#include "hamu_vm_core.hpp"

// Host-side trial state. Construct after the resident controller has emitted
// its request. On rejection, restore the whole guest including registers,
// HP, pointers, output, program bytes and inherited snapshots. External
// effects and the host's separate program-word vector are outside this scope.
class GuestTrialCheckpoint {
    Hamster& guest;
    Hamster before;
    bool retained=false;
public:
    explicit GuestTrialCheckpoint(Hamster& h):guest(h),before(h) {}
    GuestTrialCheckpoint(const GuestTrialCheckpoint&)=delete;
    GuestTrialCheckpoint& operator=(const GuestTrialCheckpoint&)=delete;
    ~GuestTrialCheckpoint(){if(!retained)guest=std::move(before);}
    void commit(){retained=true;}
};
