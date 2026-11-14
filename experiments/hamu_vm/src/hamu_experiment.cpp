// Experimental version derived from Bigbearbo Lin's Hamu_VM_v0.1.cpp.
// Goal: select a fixed-position COPY reader, not infer a full language protocol.
#include "hamu_vm_core.hpp"
#include <chrono>
#include <filesystem>
#include <numeric>
#include <regex>
#include <sstream>

struct Config {
    unsigned seed = 1;
    int population = 192, generations = 300, task_order = 2, vm_order = 5;
    int pairs = 6, steps = 32;
    double seconds = 15;
    bool rehearse_old = false;
    std::string mode = "raw", feedback = "exact", output = "results/run", initial_program;
};
using Genome = std::vector<bool>;
struct Evaluation {
    double fitness = 0, exact = 0, bit_accuracy = 0, mean_steps = 0;
    double mean_hp_change = 0;
    int read_hits = 0, timeouts = 0;
    std::vector<int> outputs;
};

static HamsterParams parameters(const Config& c) {
    HamsterParams p;
    p.op_order = c.vm_order;
    p.layout.val_reg_size = 16;
    p.layout.total_size = p.layout.program_start + (2 * c.pairs + 1) * (c.vm_order + 1);
    return p;
}

static void set_word(Genome& bits, int index, int value, int n) {
    const auto word = SpiralToken(value, n, 1);
    for (int j = 0; j < n + 1; ++j) bits[index * (n + 1) + j] = word.bits[j];
}

static void impose_structure(Genome& g, const Config& c) {
    const int width = c.vm_order + 1;
    if (c.mode != "raw") {
        for (int i = c.vm_order; i < static_cast<int>(g.size()); i += width) g[i] = false;
        set_word(g, c.pairs * 2, 15, c.vm_order);
    }
    if (c.mode == "scaffold" || c.mode == "open_read") {
        // Inject routing shape and output port, NOT source address or copy lengths.
        const int fixed[][2] = {{0,14},{2,4},{4,0},{5,2},{6,14},{7,(1 << (c.vm_order-1))+1},
                                {8,9},{10,15}};
        for (const auto& w : fixed)
            if (c.mode == "scaffold" || w[0] != 2) set_word(g, w[0], w[1], c.vm_order);
    }
}

static Genome random_genome(std::mt19937& rng, const Config& c) {
    Genome g((2*c.pairs+1)*(c.vm_order+1));
    for (size_t i=0; i<g.size(); ++i) g[i] = (rng() & 1) != 0;
    impose_structure(g,c);
    return g;
}

static Genome mutated(const Genome& parent, std::mt19937& rng, const Config& c) {
    Genome child = parent;
    // In the scaffold only source offset and read/write lengths are mutable.
    const int scaffold_words[] = {1,3,9};
    const int open_read_words[] = {1,2,3,9};
    const int changes = 1 + rng()%3;
    for (int i=0; i<changes; ++i) {
        int bit;
        if (c.mode == "scaffold")
            bit = scaffold_words[rng()%3]*(c.vm_order+1) + rng()%c.vm_order;
        else if (c.mode == "open_read")
            bit = open_read_words[rng()%4]*(c.vm_order+1) + rng()%c.vm_order;
        else
            bit = rng()%child.size();
        child[bit] = !child[bit];
    }
    impose_structure(child,c);
    return child;
}

static Problem copy_problem(int value, int n) {
    Problem p;
    p.type = ProblemType::EAZY;
    p.question = {SpiralToken(0,n,1), SpiralToken(value,n,1)};
    p.answer = SpiralToken(value,n,1);
    p.readable = "COPY " + std::to_string(value);
    return p;
}

static Evaluation evaluate(const Genome& g, const Config& c, bool reverse=false, bool inherited=false) {
    const auto params = parameters(c);
    const int cases = 1 << c.task_order;
    const int old_cases = c.rehearse_old && c.task_order>1 ? 1 << (c.task_order-1) : 0;
    int bit_total = 0;
    Evaluation e;
    for (int j=0; j<cases+old_cases; ++j) {
        const int n = j<cases ? c.task_order : c.task_order-1;
        const int local = j<cases ? j : j-cases;
        const int value = reverse ? (1<<n)-1-local : local;
        Hamster h(0,params);
        h.step_limit = c.steps;
        for (size_t b=0; b<g.size(); ++b) h.memory[params.layout.program_start+b] = g[b];
        if (inherited) {
            h.new_his(); Hamster archive(1,params), child(2,params);
            archive.copy_hamu(h); child.copy_hamu(archive); h.copy_hamu(child);
        }
        // Each case starts afresh: no previous answer or register survives.
        const auto problem = copy_problem(value,n);
        h.write_prob(problem);
        simulate_spiral_program(h);
        e.exact += Check_ans(h,problem);
        const int start = params.layout.output_start+1;
        int result = 0;
        for (int b=0; b<n+1; ++b) {
            e.bit_accuracy += h.written[start+b] && h.memory[start+b] == problem.answer.bits[b];
            if (b<n) result = (result<<1)|h.memory[start+b];
        }
        bit_total += n+1;
        e.outputs.push_back(result);
        // Count reads from the variable DATA bits, not the constant COPY opcode.
        for (int b=0; b<n; ++b) e.read_hits += h.read_seen[1+n+1+b];
        e.mean_steps += h.executed_steps;
        e.timeouts += h.budget_exhausted;
    }
    e.exact /= cases+old_cases;
    e.bit_accuracy /= bit_total;
    e.mean_steps /= cases+old_cases;
    e.mean_hp_change = 3*e.exact - basic_use - e.mean_steps/Op_cost;
    // Correct whole words dominate. Optional bit feedback is explicitly separate.
    e.fitness = 100*e.exact + (c.feedback=="bits" ? e.bit_accuracy : 0)
                - 0.0001*e.mean_steps;
    return e;
}

static std::string bits_text(const Genome& g) {
    std::string s; for(bool b:g) s += b?'1':'0'; return s;
}

static void save_run(const Config& c, const Genome& best, const Evaluation& e,
                     const Evaluation& initial, int first_success, int completed,
                     double elapsed, bool timed_out, const std::string& origin) {
    const std::filesystem::path dest(c.output);
    if (!dest.parent_path().empty()) std::filesystem::create_directories(dest.parent_path());
    const auto checked = evaluate(best,c,true);
    const auto inherited = evaluate(best,c,false,true);
    std::ofstream out(c.output+".json");
    if(!out) throw std::runtime_error("Cannot write result file");
    out << std::setprecision(12)
        << "{\n  \"seed\": "<<c.seed<<", \"mode\": \""<<c.mode<<"\", \"feedback\": \""<<c.feedback<<"\",\n"
        << "  \"task\": \"COPY\", \"task_order\": "<<c.task_order<<", \"vm_order\": "<<c.vm_order<<",\n"
        << "  \"population\": "<<c.population<<", \"generation_limit\": "<<c.generations<<",\n"
        << "  \"rehearse_old\": "<<(c.rehearse_old?"true":"false")<<", \"initial_program\": \""<<c.initial_program<<"\",\n"
        << "  \"generations_completed\": "<<completed<<", \"first_success_generation\": "<<first_success<<",\n"
        << "  \"initial_best_accuracy\": "<<initial.exact<<", \"final_accuracy\": "<<e.exact<<",\n"
        << "  \"snapshot_inheritance_accuracy\": "<<inherited.exact<<", \"best_origin\": \""<<origin<<"\",\n"
        << "  \"reverse_order_accuracy\": "<<checked.exact<<", \"correct_written_bits\": "<<e.bit_accuracy<<",\n"
        << "  \"input_data_read_hits\": "<<e.read_hits<<", \"mean_steps\": "<<e.mean_steps<<",\n"
        << "  \"expected_hp_change_per_question\": "<<e.mean_hp_change<<",\n"
        << "  \"instruction_budget_exhaustions\": "<<e.timeouts<<",\n"
        << "  \"wall_time_seconds\": "<<elapsed<<", \"run_time_limit_hit\": "<<(timed_out?"true":"false")<<",\n"
        << "  \"program_bits\": \""<<bits_text(best)<<"\", \"outputs\": [";
    for(size_t i=0;i<e.outputs.size();++i) out<<(i?",":"")<<e.outputs[i];
    out << "]\n}\n";
    std::ofstream listing(c.output+".program.txt");
    const int width=c.vm_order+1;
    listing << "mode="<<c.mode<<"; source offset and counts are evolved in scaffold mode\n";
    for(int i=0; i<static_cast<int>(best.size())/width; ++i) {
        std::vector<bool> word(best.begin()+i*width,best.begin()+(i+1)*width);
        listing<<i<<" "; for(bool b:word) listing<<(b?'1':'0');
        try { const auto t=decodeSpiral(word,c.vm_order,1); listing<<" value="<<t.value;
            if(i%2==0) listing<<" "<<op_to_string(decode_op(t));
        } catch(const std::invalid_argument&) { listing<<" non-instruction/data suffix"; }
        listing<<"\n";
    }
}

int main(int argc,char** argv) {
    try {
        Config c;
        for(int i=1;i<argc;++i) {
            const std::string key=argv[i];
            if(key=="--help") {
                std::cout<<"--mode raw|framed|scaffold|open_read --feedback exact|bits --seed N --population N "
                    "--generations N --task-order N --vm-order N --seconds N --steps N --output PATH "
                    "[--initial-program JSON] [--rehearse-old]\n";
                return 0;
            }
            if(key=="--rehearse-old") {c.rehearse_old=true;continue;}
            if(i+1>=argc) throw std::invalid_argument("Missing option value");
            const std::string value=argv[++i];
            if(key=="--mode") c.mode=value;
            else if(key=="--feedback") c.feedback=value;
            else if(key=="--seed") c.seed=std::stoul(value);
            else if(key=="--population") c.population=std::stoi(value);
            else if(key=="--generations") c.generations=std::stoi(value);
            else if(key=="--task-order") c.task_order=std::stoi(value);
            else if(key=="--vm-order") c.vm_order=std::stoi(value);
            else if(key=="--seconds") c.seconds=std::stod(value);
            else if(key=="--steps") c.steps=std::stoi(value);
            else if(key=="--output") c.output=value;
            else if(key=="--initial-program") c.initial_program=value;
            else throw std::invalid_argument("Unknown option: "+key);
        }
        if((c.mode!="raw"&&c.mode!="framed"&&c.mode!="scaffold"&&c.mode!="open_read") ||
           (c.feedback!="exact"&&c.feedback!="bits") || c.population<8 || c.population>4096 ||
           c.generations<1 || c.generations>100000 || c.task_order<1 || c.task_order>5 ||
           c.vm_order<4 || c.vm_order>8 || c.steps<1 || c.steps>1024 ||
           !std::isfinite(c.seconds) || c.seconds<=0 || c.seconds>300)
            throw std::invalid_argument("Option outside supported experiment range");
        std::mt19937 rng(c.seed);
        std::vector<Genome> population;
        std::vector<std::string> origins(c.population,"initial_random");
        for(int i=0;i<c.population;++i) population.push_back(random_genome(rng,c));
        if(!c.initial_program.empty()) {
            std::ifstream source(c.initial_program);
            if(!source) throw std::invalid_argument("Cannot open initial program");
            const std::string data((std::istreambuf_iterator<char>(source)),{});
            std::smatch match;
            if(!std::regex_search(data,match,std::regex("\\\"program_bits\\\"\\s*:\\s*\\\"([01]+)\\\"")) ||
               match[1].length()!=population[0].size())
                throw std::invalid_argument("Initial program needs matching program_bits length");
            for(size_t b=0;b<population[0].size();++b) population[0][b]=match[1].str()[b]=='1';
            impose_structure(population[0],c);
            origins[0]="transferred_program";
        }
        std::filesystem::path dest(c.output);
        if(!dest.parent_path().empty()) std::filesystem::create_directories(dest.parent_path());
        std::ofstream trace(c.output+".csv");
        if(!trace) throw std::runtime_error("Cannot write trace");
        trace<<"generation,best_accuracy,mean_accuracy,best_written_bit_accuracy,mean_best_steps\n";
        Genome best;
        std::string best_origin;
        Evaluation best_eval, initial;
        best_eval.fitness=-1e100;
        int first=-1, completed=0;
        bool limit_hit=false;
        const auto begin=std::chrono::steady_clock::now();
        for(int gen=0;gen<=c.generations;++gen) {
            std::vector<Evaluation> ev;
            double mean=0;
            for(const auto& genome:population) { ev.push_back(evaluate(genome,c)); mean+=ev.back().exact; }
            std::vector<int> rank(c.population); std::iota(rank.begin(),rank.end(),0);
            std::stable_sort(rank.begin(),rank.end(),[&](int a,int b){return ev[a].fitness>ev[b].fitness;});
            if(gen==0) initial=ev[rank[0]];
            if(ev[rank[0]].fitness>best_eval.fitness) { best=population[rank[0]]; best_eval=ev[rank[0]]; best_origin=origins[rank[0]]; }
            if(first<0 && best_eval.exact==1) first=gen;
            trace<<gen<<","<<best_eval.exact<<","<<mean/c.population<<","<<best_eval.bit_accuracy
                 <<","<<best_eval.mean_steps<<"\n";
            completed=gen;
            const double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count();
            if(first>=0 || gen==c.generations) break;
            if(seconds>=c.seconds) {limit_hit=true;break;}
            std::vector<Genome> next;
            std::vector<std::string> next_origins;
            const int elite=std::max(1,c.population/10), immigrants=c.population/5;
            for(int i=0;i<elite;++i) {next.push_back(population[rank[i]]);next_origins.push_back(origins[rank[i]]);}
            while(static_cast<int>(next.size())<c.population-immigrants) {
                int winner=rng()%c.population;
                for(int k=0;k<2;++k) {const int challenger=rng()%c.population;
                    if(ev[challenger].fitness>ev[winner].fitness) winner=challenger;}
                next.push_back(mutated(population[winner],rng,c));
                next_origins.push_back("mutated_offspring");
            }
            while(static_cast<int>(next.size())<c.population) {next.push_back(random_genome(rng,c));next_origins.push_back("random_immigrant");}
            population=std::move(next);
            origins=std::move(next_origins);
        }
        const double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count();
        save_run(c,best,best_eval,initial,first,completed,elapsed,limit_hit,best_origin);
        std::cout<<"mode="<<c.mode<<" seed="<<c.seed<<" initial="<<initial.exact
                 <<" final="<<best_eval.exact<<" success_generation="<<first
                 <<" seconds="<<elapsed<<"\n";
    } catch(const std::exception& e) {std::cerr<<e.what()<<"\n";return 2;}
    return 0;
}
