// Verilator test bench for the m12-chipyard-011/012/013 FP unit bench
// (`WumingFPUnitHarness`, emitted by `wuming.common.WumingFPUnitEmit`).
//
// The bench is a plain combinational multiplexer over the FP primitives plus a
// `WumingFcsr` instance, so the TB only drives `op`/`mode`/`in` and reads the
// outputs; every check is done on the Python side (`unit_run.py`), which owns
// the vector files and the oracle.  This program prints
//
//   * `--vectors FILE`, one line per vector:
//         V <op> <inLo> <inHi> <mode> <extra> <outLo> <outHi> <flags> <hfLo> <hfHi> <hfFlags>
//   * `--fcsr FILE`, one clocked step per line:
//         F <wr_en> <wr_data> <fflags> <read>
//
// Vector input lines are `<op> <inLo> <inHi> <mode> [<extra>]`; `extra` is the
// fused multiply-add's third source (the addend) and defaults to 0.
//
// Values are printed as hex without a prefix.

#include "VWumingFPUnitHarness.h"
#include "verilated.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>

static VWumingFPUnitHarness *dut;

static void tick() {
    dut->clock = 0;
    dut->eval();
    dut->clock = 1;
    dut->eval();
    dut->clock = 0;
    dut->eval();
}

static bool is_slow(unsigned op) { return op >= 41 && op <= 46; }
static bool has_hf(unsigned op) { return op >= 41 && op <= 44; }

int main(int argc, char **argv) {
    Verilated::commandArgs(argc, argv);
    dut = new VWumingFPUnitHarness;

    dut->clock = 0;
    dut->reset = 1;
    dut->io_op = 0;
    dut->io_mode = 0;
    dut->io_inLo = 0;
    dut->io_inHi = 0;
    dut->io_inExtra = 0;
    dut->io_fcsrWrEn = 0;
    dut->io_fcsrWrData = 0;
    dut->io_fcsrFflags = 0;
    dut->io_slowStart = 0;
    tick();
    tick();
    dut->reset = 0;
    tick();

    if (argc < 3) {
        std::fprintf(stderr, "usage: %s --vectors FILE | --fcsr FILE\n", argv[0]);
        return 2;
    }
    const bool fcsr = std::strcmp(argv[1], "--fcsr") == 0;
    FILE *f = std::fopen(argv[2], "r");
    if (!f) {
        std::fprintf(stderr, "tb_fp_unit: cannot open %s\n", argv[2]);
        return 2;
    }

    char line[512];
    while (std::fgets(line, sizeof(line), f)) {
        if (line[0] == '#' || line[0] == '\n') continue;
        if (!fcsr) {
            unsigned op, mode;
            unsigned long long inLo, inHi, inExtra = 0;
            const int n = std::sscanf(line, "%u %llx %llx %u %llx", &op, &inLo,
                                      &inHi, &mode, &inExtra);
            if (n < 4) {
                std::fprintf(stderr, "tb_fp_unit: bad vector line: %s", line);
                return 3;
            }
            dut->io_op = op & 0x3f;
            dut->io_mode = mode & 0x7;
            dut->io_inLo = inLo;
            dut->io_inHi = inHi;
            dut->io_inExtra = inExtra;
            if (is_slow(op)) {
                // m12-014: clocked operation.  A one-cycle `slowStart` pulse
                // starts both units (hardfloat's `inReady` is high in idle);
                // then tick until each side has reported its result.
                unsigned long long oLo = 0, oHi = 0, hLo = 0, hHi = 0;
                unsigned fl = 0, hfl = 0;
                bool gotMine = false, gotHf = !has_hf(op);
                int ticks = 0;
                dut->io_slowStart = 1;
                dut->eval();
                tick();
                dut->io_slowStart = 0;
                for (int g = 0; g < 40000 && !(gotMine && gotHf); g++) {
                    dut->eval();
                    if (!gotMine && dut->io_slowDone) {
                        oLo = dut->io_outLo; oHi = dut->io_outHi;
                        fl = dut->io_flags; gotMine = true;
                    }
                    if (!gotHf && dut->io_hfValid) {
                        hLo = dut->io_hfOutLo; hHi = dut->io_hfOutHi;
                        hfl = dut->io_hfFlags; gotHf = true;
                    }
                    if (gotMine && gotHf) break;
                    tick();
                    ticks++;
                }
                if (!gotMine || !gotHf) {
                    std::fprintf(stderr, "tb_fp_unit: op %u did not finish "
                                 "(mine=%d hf=%d)\n", op, (int)gotMine,
                                 (int)gotHf);
                    return 4;
                }
                // `C` reports the measured latency (clock ticks until both
                // sides finished); `unit_run.py` prints the per-op range.
                std::printf("C %u %d\n", op, ticks);
                std::printf("V %u %llx %llx %u %llx %llx %llx %x %llx %llx %x\n",
                            op, inLo, inHi, mode, inExtra, oLo, oHi, fl,
                            hLo, hHi, hfl);
                continue;
            }
            dut->eval();
            dut->eval();
            std::printf("V %u %llx %llx %u %llx %llx %llx %x %llx %llx %x\n", op,
                        inLo, inHi, mode, inExtra,
                        (unsigned long long)dut->io_outLo,
                        (unsigned long long)dut->io_outHi, (unsigned)dut->io_flags,
                        (unsigned long long)dut->io_hfOutLo,
                        (unsigned long long)dut->io_hfOutHi,
                        (unsigned)dut->io_hfFlags);
        } else {
            unsigned wr_en, fflags;
            unsigned long long wr_data;
            if (std::sscanf(line, "%u %llx %u", &wr_en, &wr_data, &fflags) != 3) {
                std::fprintf(stderr, "tb_fp_unit: bad fcsr line: %s", line);
                return 3;
            }
            dut->io_fcsrWrEn = wr_en;
            dut->io_fcsrWrData = wr_data;
            dut->io_fcsrFflags = fflags & 0x1f;
            tick();
            std::printf("F %u %llx %u %llx\n", wr_en, wr_data, fflags & 0x1f,
                        (unsigned long long)dut->io_fcsrRead);
        }
    }
    std::fclose(f);
    dut->final();
    delete dut;
    return 0;
}
