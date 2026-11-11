// Verilator test bench for the m12-chipyard-011/012 FP unit bench
// (`WumingFPUnitHarness`, emitted by `wuming.common.WumingFPUnitEmit`).
//
// The bench is a plain combinational multiplexer over the FP primitives plus a
// `WumingFcsr` instance, so the TB only drives `op`/`mode`/`in` and reads the
// outputs; every check is done on the Python side (`fp_unit.py`), which owns
// the vector files and the oracle.  This program prints
//
//   * `--vectors FILE`, one line per vector:
//         V <op> <inLo> <inHi> <mode> <outLo> <outHi> <flags> <hfLo> <hfHi> <hfFlags>
//   * `--fcsr FILE`, one clocked step per line:
//         F <wr_en> <wr_data> <fflags> <read>
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

int main(int argc, char **argv) {
    Verilated::commandArgs(argc, argv);
    dut = new VWumingFPUnitHarness;

    dut->clock = 0;
    dut->reset = 1;
    dut->io_op = 0;
    dut->io_mode = 0;
    dut->io_inLo = 0;
    dut->io_inHi = 0;
    dut->io_fcsrWrEn = 0;
    dut->io_fcsrWrData = 0;
    dut->io_fcsrFflags = 0;
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
            unsigned long long inLo, inHi;
            if (std::sscanf(line, "%u %llx %llx %u", &op, &inLo, &inHi, &mode) != 4) {
                std::fprintf(stderr, "tb_fp_unit: bad vector line: %s", line);
                return 3;
            }
            dut->io_op = op & 0x1f;
            dut->io_mode = mode & 0x7;
            dut->io_inLo = inLo;
            dut->io_inHi = inHi;
            dut->eval();
            dut->eval();
            std::printf("V %u %llx %llx %u %llx %llx %x %llx %llx %x\n", op, inLo,
                        inHi, mode, (unsigned long long)dut->io_outLo,
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
