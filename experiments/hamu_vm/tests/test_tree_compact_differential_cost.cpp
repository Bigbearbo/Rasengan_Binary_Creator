#include "../src/tree_compact_reference.hpp"
#include <iostream>
#include <stdexcept>
#include <string>

// A controlled replay: both layouts receive exactly the same questions,
// feedback and number of revisits.  VM instruction steps, not wall time, are
// counted.  Host orchestration is included; core ISA is unchanged.
struct ReplayCost {
    long long steps = 0, calls = 0, choice_steps = 0, record_steps = 0, read_steps = 0;
    int peak_steps = 0;
};
struct ReplayVM {
    Hamster h;
    ReplayCost cost;
    std::string phase;
    explicit ReplayVM(int id, const HamsterParams& p) : h(id, p) {
        h.memory[1] = true;
    }
    void run(Hamster& who, const std::vector<int>& words) {
        int at = who.params.layout.program_start;
        for (int word : words)
            for (bool bit : SpiralToken(word, 5, 1).bits)
                who.memory.at(at++) = bit;
        std::fill(who.val_reg.begin(), who.val_reg.end(), false);
        who.val_ptr = 0;
        who.stop = false;
        who.budget_exhausted = false;
        who.executed_steps = 0;
        who.step_limit = 4000;
        who.pro_1 = who.params.layout.program_start;
        who.pro_2 = at - 1;
        simulate_spiral_program(who);
        if (!who.stop || who.budget_exhausted)
            throw std::runtime_error("replay VM interrupted in " + phase);
        cost.steps += who.executed_steps;
        ++cost.calls;
        cost.peak_steps = std::max(cost.peak_steps, who.executed_steps);
        if (phase == "choice") cost.choice_steps += who.executed_steps;
        else if (phase == "record") cost.record_steps += who.executed_steps;
        else if (phase == "read") cost.read_steps += who.executed_steps;
        else throw std::logic_error("unclassified replay operation");
    }
};
static int used_nodes(const Hamster& h) {
    int used = 0;
    for (int i = 0; i < h.params.tree_capacity; ++i)
        used += h.memory[h.params.tree_start + 9 * i];
    return used;
}
int main() {
    HamsterParams p;
    p.layout.status_start = 45;
    p.layout.output_start = 50;
    p.layout.work_start = 80;
    p.layout.program_start = 1100;
    p.layout.total_size = 24000;
    p.stable_work_bits = 800;
    p.tree_start = 300;
    p.tree_capacity = 31;
    p.layout.val_reg_size = 12;
    ReplayVM old_vm(100, p), compact_vm(101, p);
    TreeCompactReference compact{compact_vm.h, 672};
    auto old_run = [&](Hamster& h, const std::vector<int>& words) { old_vm.run(h, words); };
    auto compact_run = [&](Hamster& h, const std::vector<int>& words) { compact_vm.run(h, words); };
    int events = 0, fresh = 0, learned = 0;
    // The last four episodes are deliberately repeated mastered questions.
    for (int question : {1, 2, 1, 2, 1, 2}) {
        const int answer = question == 1 ? 6 : 3;
        for (int attempt = 0; attempt < 8; ++attempt) {
            old_vm.phase = "choice";
            const int old_option = tree_error_next(old_vm.h, question, 0, old_run);
            compact_vm.phase = "choice";
            const int compact_option = compact.next(question, compact_run);
            if (old_option != compact_option || old_option < 0 || old_option > 7)
                throw std::runtime_error("layouts disagreed on next answer");
            ++events;
            const bool right = old_option == answer;
            old_vm.phase = "read";
            const bool old_known = tree_error_probe(old_vm.h, question, old_option, old_run).correct;
            compact_vm.phase = "read";
            compact_run(compact_vm.h, tree_compact_guest_read_program(question, 672, p.layout.work_start));
            const bool compact_known = compact_vm.h.val_reg[8];
            if (old_known != compact_known)
                throw std::runtime_error("layouts disagreed on mastery");
            if (old_known) {
                if (!right) throw std::runtime_error("mastered wrong option");
                ++learned;
            } else {
                ++fresh;
                old_vm.phase = "record";
                tree_error_record_from_input(old_vm.h, old_option, right, old_run);
                compact_vm.phase = "record";
                compact.record(question, old_option, right, compact_run);
            }
            if (right) break;
            if (attempt == 7) throw std::runtime_error("no success within eight answers");
        }
    }
    if (events != 15 || fresh != 11 || learned != 4 ||
        used_nodes(old_vm.h) != 13 || used_nodes(compact_vm.h) != 2)
        throw std::runtime_error("wrong replay history or node count");
    for (auto [name, v] : {std::pair<const char*, ReplayVM&>{"legacy", old_vm}, {"compact", compact_vm}}) {
        const int nodes = used_nodes(v.h);
        const int used_bits = nodes * (9 + (std::string(name) == "compact" ? 12 : 0));
        const int reserved_bits = p.tree_capacity * (9 + (std::string(name) == "compact" ? 12 : 0));
        std::cout << name << ",events=" << events << ",fresh=" << fresh
                  << ",learned=" << learned << ",vm_calls=" << v.cost.calls
                  << ",vm_steps=" << v.cost.steps << ",peak_steps=" << v.cost.peak_steps
                  << ",choice_steps=" << v.cost.choice_steps
                  << ",record_steps=" << v.cost.record_steps
                  << ",read_steps=" << v.cost.read_steps
                  << ",used_nodes=" << nodes << ",used_data_bits=" << used_bits
                  << ",reserved_data_bits=" << reserved_bits << '\n';
    }
    std::cout << "PASS same-question same-feedback same-revisit differential replay\n";
}
