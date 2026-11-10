#pragma once
#include <algorithm>
#include <cstdint>
#include <exception>
#include <functional>
#include <limits>
#include <string>
#include <utility>
#include <vector>

// Host-only executable specification. Include the VM before this header.
// Not a production entry point, durable transaction, or external-I/O rollback.
namespace guest_trial_ref {
enum class Outcome { Completed, InvalidInput, BudgetExhausted, WorkCapacity,
                     TreeCapacity, Exception, RevisionOverflow };
struct Result {
    Outcome outcome = Outcome::InvalidInput;
    bool committed = false;
    bool versioned_change = false;
    int attempted_steps = 0;
    float charged_hp = 0;
    bool observed_stop = false;
    std::vector<bool> read_trace;
    std::string error;
};

template<class Host, class Registry> class Trial {
    Host& h;
    Registry& registry;
    uint64_t& revision;

    // D-005: versioned guest state. Other Host fields are restored on rejection,
    // but caches, counters and traces are not themselves revision changes.
    static bool guest_changed(const Host& a, const Host& b) {
        return a.memory != b.memory || a.val_reg != b.val_reg ||
            a.hp != b.hp || a.ptr != b.ptr || a.secondary_ptr != b.secondary_ptr ||
            a.output_ptr != b.output_ptr || a.val_ptr != b.val_ptr ||
            a.pro_1 != b.pro_1 || a.pro_2 != b.pro_2 ||
            a.segment_pages != b.segment_pages || a.segment_used != b.segment_used;
    }
    Result execute(const std::function<void()>& after_guest) {
        Result result;
        const long long width = static_cast<long long>(h.params.op_order) + h.params.op_lvl;
        if (width <= 0 || h.params.unit_cost_per <= 0 || h.step_limit < 0 ||
            h.pro_1 < h.params.layout.program_start || h.pro_2 < h.pro_1 ||
            h.pro_2 >= static_cast<long long>(h.memory.size()) ||
            (h.pro_1 - h.params.layout.program_start) % width ||
            (static_cast<long long>(h.pro_2) - h.pro_1 + 1) % width)
            return result; // no execution, mutation, or charge

        Host saved = h;
        auto generations = registry.generation;
        const auto lineage = registry.lineage;
        const auto old_revision = revision;
        const int cost_per = h.params.unit_cost_per;
        auto rollback = [&] {
            h = std::move(saved);
            registry.generation = std::move(generations);
            registry.lineage = lineage;
            revision = old_revision;
        };
        h.stop = false;
        h.executed_steps = 0;
        h.budget_exhausted = h.work_insert_blocked = h.tree_capacity_blocked = false;
        try {
            simulate_spiral_program(h);
            result.attempted_steps = std::max(0, h.executed_steps);
            result.observed_stop = h.stop;
            result.read_trace = h.read_seen;
            // Capture cost before the optional HOST-ONLY fault injection hook.
            if (after_guest) after_guest();
            if (h.budget_exhausted) result.outcome = Outcome::BudgetExhausted;
            else if (h.work_insert_blocked) result.outcome = Outcome::WorkCapacity;
            else if (h.tree_capacity_blocked) result.outcome = Outcome::TreeCapacity;
            else {
                result.versioned_change = guest_changed(h, saved) ||
                    registry.generation != generations || registry.lineage != lineage;
                if (result.versioned_change && revision == std::numeric_limits<uint64_t>::max())
                    result.outcome = Outcome::RevisionOverflow;
                else {
                    if (result.versioned_change) ++revision;
                    result.outcome = Outcome::Completed;
                    result.committed = true;
                }
            }
        } catch (const std::exception& e) {
            result.attempted_steps = std::max(result.attempted_steps, std::max(0, h.executed_steps));
            result.observed_stop = h.stop;
            result.read_trace = h.read_seen;
            result.outcome = Outcome::Exception;
            result.error = e.what();
        } catch (...) {
            result.attempted_steps = std::max(result.attempted_steps, std::max(0, h.executed_steps));
            result.outcome = Outcome::Exception;
            result.error = "non-standard exception";
        }
        if (!result.committed) rollback();
        // D-003: settle once, after commit/rollback. Do not call use_hp() again.
        // This debit is intentionally outside the guest revision (D-005).
        result.charged_hp = static_cast<float>(result.attempted_steps) / cost_per;
        h.hp -= result.charged_hp;
        return result;
    }
public:
    Trial(Host& host, Registry& reg, uint64_t& rev) : h(host), registry(reg), revision(rev) {}
    Result run() { return execute({}); }
    Result run_with_host_fault_for_test(const std::function<void()>& hook) { return execute(hook); }
};
} // namespace guest_trial_ref
