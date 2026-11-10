// Verilator test bench for the m12-chipyard-018 fetch/data port split.
//
// It drives the *generated* `WumingCore` module directly (the same Verilog the
// SoC simulation uses) with two hand-written TileLink slaves:
//
//   * `imem`: answers every request with the beat from a flat program image.
//   * `dmem`: answers after `--latency` cycles (default 200).
//
// The program (`gen_probe.py`, layout `probe.json`) jumps far away and then
// issues one store, so the fetch queue holds a single beat when the data access
// starts.  The bench then checks the property m12-020 adds:
//
//   * while the data port has a request outstanding the fetch port issues no
//     new prefetch (data priority); at most the one prefetch admitted in the
//     same cycle as the store may still be on the bus,
//   * the data burst completes in exactly the configured latency (fetch
//     arbitration does not slow it down),
//   * execution resumes from the queue once the store completes.
//
// Everything is printed as `PROBE <name>=<value>` and the bench exits non-zero
// if any check fails.
//
// Build (see `run.sh`):
//   verilator --cc --exe --build -Wno-fatal --top-module WumingCore \
//       -Mdir <dir> <generated WumingCore.sv and friends> tb_fetch_probe.cpp
//
// Usage: ./VWumingCore --img probe.img --base 0xffffffff0000 --depth 8
//                      [--latency 200] [--max-cycles 5000]

#include "VWumingCore.h"
#include "verilated.h"

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <string>
#include <vector>

namespace {

struct Options {
  std::string img;
  uint64_t base = 0xffffffff0000ULL;
  int depth = 8;
  int latency = 200;
  int maxCycles = 5000;
  uint64_t target = 0;  // beat whose demand reply marks the queue start
};

struct Image {
  std::vector<uint8_t> bytes;
  uint64_t base = 0;
};

struct Pending {
  uint64_t addr;
  uint8_t source;
  uint64_t due;
  bool isGet;
};

Options opt;
Image img;
VWumingCore *dut = nullptr;

// The fetch port can have the demand request plus two prefetches outstanding;
// replies are returned in request order.
std::deque<Pending> imemQ;
std::deque<Pending> dmemQ;

uint64_t cycle = 0;
uint64_t bootCycle = 8;
uint64_t imemReqCount = 0;
uint64_t dmemReqCycle = 0;
uint64_t dmemRespCycle = 0;
uint64_t fetchDuringStall = 0;
uint64_t fetchAfterDataReq = 0;
uint64_t haltCycle = 0;
uint64_t targetRespCycle = 0;

uint8_t memByte(uint64_t addr) {
  if (addr < img.base) return 0;
  uint64_t off = addr - img.base;
  if (off >= img.bytes.size()) return 0;
  return img.bytes[off];
}

// TileLink beats are little-endian: byte k of the beat sits in bits [8k+7:8k].
uint64_t beatAt(uint64_t addr) {
  uint64_t v = 0;
  for (int i = 0; i < 8; ++i) v |= static_cast<uint64_t>(memByte(addr + i)) << (8 * i);
  return v;
}

bool loadImage() {
  FILE *f = std::fopen(opt.img.c_str(), "rb");
  if (!f) {
    std::fprintf(stderr, "PROBE error=cannot-open-image %s\n", opt.img.c_str());
    return false;
  }
  std::fseek(f, 0, SEEK_END);
  long n = std::ftell(f);
  std::fseek(f, 0, SEEK_SET);
  img.bytes.resize(n > 0 ? static_cast<size_t>(n) : 0);
  if (n > 0 && std::fread(img.bytes.data(), 1, img.bytes.size(), f) != img.bytes.size()) {
    std::fclose(f);
    return false;
  }
  std::fclose(f);
  img.base = opt.base;
  return true;
}

void drive() {
  dut->io_hartid = 0;
  dut->io_bootEnable = cycle >= bootCycle ? 1 : 0;
  dut->io_semi_resp_valid = 0;
  dut->io_semi_resp_value = 0;

  dut->io_imem_a_ready = 1;
  dut->io_dmem_a_ready = 1;

  const bool imemD = !imemQ.empty() && imemQ.front().due <= cycle;
  if (imemD && targetRespCycle == 0 && (imemQ.front().addr & ~7ULL) == opt.target)
    targetRespCycle = cycle;
  dut->io_imem_d_valid = imemD ? 1 : 0;
  dut->io_imem_d_bits_source = imemQ.empty() ? 0 : imemQ.front().source;
  dut->io_imem_d_bits_denied = 0;
  dut->io_imem_d_bits_data = imemQ.empty() ? 0 : beatAt(imemQ.front().addr);

  const bool dmemD = !dmemQ.empty() && dmemQ.front().due <= cycle;
  dut->io_dmem_d_valid = dmemD ? 1 : 0;
  dut->io_dmem_d_bits_denied = 0;
  dut->io_dmem_d_bits_data = 0;
}

void update() {
  if (dut->io_imem_a_valid && dut->io_imem_a_ready) {
    Pending p{dut->io_imem_a_bits_address, dut->io_imem_a_bits_source, cycle + 2, true};
    // Count the prefetches issued between the demand beat arriving and the
    // data access completing, and those issued strictly after the data request
    // was accepted (m12-020: the latter must be zero).
    if (targetRespCycle != 0 && dmemRespCycle == 0) ++fetchDuringStall;
    if (dmemReqCycle != 0 && dmemRespCycle == 0) ++fetchAfterDataReq;
    ++imemReqCount;
    imemQ.push_back(p);
  }
  // The fetch port's D channel is always ready (`io.imem.d.ready := true.B`),
  // so the generated model folds the ready signal away; every valid is taken.
  if (dut->io_imem_d_valid && !imemQ.empty()) imemQ.pop_front();

  if (dut->io_dmem_a_valid && dut->io_dmem_a_ready) {
    Pending p{dut->io_dmem_a_bits_address, 0, cycle + static_cast<uint64_t>(opt.latency), true};
    if (dmemReqCycle == 0) dmemReqCycle = cycle;
    dmemQ.push_back(p);
  }
  if (dut->io_dmem_d_valid && dut->io_dmem_d_ready && !dmemQ.empty()) {
    if (dmemRespCycle == 0) dmemRespCycle = cycle;
    dmemQ.pop_front();
  }
}

int reportCheck(const char *name, bool ok, const std::string &want, const std::string &got) {
  std::printf("  [%s] %s | expected=%s actual=%s\n", ok ? "PASS" : "FAIL", name,
              want.c_str(), got.c_str());
  return ok ? 0 : 1;
}

}  // namespace

int main(int argc, char **argv) {
  for (int i = 1; i < argc; ++i) {
    std::string a = argv[i];
    auto next = [&](const char *) { return (i + 1 < argc) ? argv[++i] : ""; };
    if (a == "--img") opt.img = next("--img");
    else if (a == "--base") opt.base = std::strtoull(next("--base"), nullptr, 0);
    else if (a == "--depth") opt.depth = std::atoi(next("--depth"));
    else if (a == "--latency") opt.latency = std::atoi(next("--latency"));
    else if (a == "--max-cycles") opt.maxCycles = std::atoi(next("--max-cycles"));
    else if (a == "--target") opt.target = std::strtoull(next("--target"), nullptr, 0);
    else {
      std::fprintf(stderr, "unknown argument %s\n", a.c_str());
      return 2;
    }
  }
  if (opt.img.empty()) {
    std::fprintf(stderr, "--img is required\n");
    return 2;
  }
  if (!loadImage()) return 2;

  Verilated::commandArgs(argc, argv);
  dut = new VWumingCore;
  dut->clock = 0;
  dut->reset = 1;
  for (int i = 0; i < 4; ++i) {
    dut->clock = 0;
    dut->eval();
    dut->clock = 1;
    dut->eval();
    ++cycle;
  }
  dut->reset = 0;

  for (; cycle < static_cast<uint64_t>(opt.maxCycles); ++cycle) {
    dut->clock = 0;
    drive();
    dut->eval();
    update();
    if (dut->io_halted && haltCycle == 0) haltCycle = cycle;
    dut->clock = 1;
    dut->eval();
    if (haltCycle != 0 && cycle > haltCycle + 2) break;
  }

  int fails = 0;
  const std::string imemReqs = std::to_string(imemReqCount);
  const std::string duringStall = std::to_string(fetchDuringStall);
  std::printf("PROBE fetch_requests=%llu\n", static_cast<unsigned long long>(imemReqCount));
  std::printf("PROBE data_request_cycle=%llu\n", static_cast<unsigned long long>(dmemReqCycle));
  std::printf("PROBE data_response_cycle=%llu\n", static_cast<unsigned long long>(dmemRespCycle));
  std::printf("PROBE fetch_requests_during_data_stall=%llu\n",
              static_cast<unsigned long long>(fetchDuringStall));
  std::printf("PROBE fetch_requests_after_data_request=%llu\n",
              static_cast<unsigned long long>(fetchAfterDataReq));
  std::printf("PROBE halted_cycle=%llu\n", static_cast<unsigned long long>(haltCycle));

  std::printf("PROBE demand_beat_cycle=%llu\n", static_cast<unsigned long long>(targetRespCycle));
  fails += reportCheck("data access was stalled", dmemRespCycle > dmemReqCycle + 100,
                       ">100 cycles", std::to_string(dmemRespCycle - dmemReqCycle));
  fails += reportCheck("data burst time == configured latency (no fetch contention)",
                       dmemRespCycle - dmemReqCycle == static_cast<uint64_t>(opt.latency),
                       std::to_string(opt.latency),
                       std::to_string(dmemRespCycle - dmemReqCycle));
  fails += reportCheck("no prefetch issued after the data request went out",
                       fetchAfterDataReq == 0, "0", std::to_string(fetchAfterDataReq));
  fails += reportCheck("at most one prefetch already in flight when the data request went out",
                       fetchDuringStall <= 1, "<=1", duringStall);
  fails += reportCheck("core halted after the store completed", haltCycle != 0, "halted",
                       std::to_string(haltCycle));
  if (haltCycle != 0 && dmemRespCycle != 0) {
    uint64_t after = haltCycle - dmemRespCycle;
    std::printf("PROBE cycles_from_data_response_to_halt=%llu\n",
                static_cast<unsigned long long>(after));
    fails += reportCheck("execution resumed from the prefetched queue", after <= 25,
                         "<=25 cycles", std::to_string(after));
  }
  std::printf("PROBE verdict=%s\n", fails == 0 ? "PASS" : "FAIL");
  delete dut;
  return fails == 0 ? 0 : 1;
}
