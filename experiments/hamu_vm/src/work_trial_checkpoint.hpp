#pragma once
#include "hamu_vm_core.hpp"

// Host-side isolation of a candidate trial's writable work state. The
// controller request is made before this checkpoint, so its choice persists.
class WorkTrialCheckpoint {
    Hamster& guest;
    int begin,end;
    std::vector<bool> before,written_before;
    bool retained=false;
public:
    explicit WorkTrialCheckpoint(Hamster& h):guest(h),begin(h.params.layout.work_start),
        end(h.params.layout.program_start) {
        if(begin<0||end<begin||size_t(end)>h.memory.size()||
           size_t(end)>h.written.size())throw std::invalid_argument("work trial bounds");
        before.assign(h.memory.begin()+begin,h.memory.begin()+end);
        written_before.assign(h.written.begin()+begin,h.written.begin()+end);
    }
    WorkTrialCheckpoint(const WorkTrialCheckpoint&)=delete;
    WorkTrialCheckpoint& operator=(const WorkTrialCheckpoint&)=delete;
    ~WorkTrialCheckpoint() {
        if(!retained) {
            std::copy(before.begin(),before.end(),guest.memory.begin()+begin);
            std::copy(written_before.begin(),written_before.end(),guest.written.begin()+begin);
        }
    }
    void commit(){retained=true;}
};
