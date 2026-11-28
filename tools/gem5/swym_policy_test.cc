/*
 * Standalone policy harness for ``swym N`` (m19-gem5-001).
 *
 * Compiled by ``tools/gem5/check_swym.py`` together with the generated cycle
 * table and ``arch/dadao/wuming_latency.hh``; no gem5 headers and no gem5
 * build are needed, so the figure can be checked on its own.
 *
 * Checked contract (``spec/SimRISC-12 §2`` / ``.tao/contracts/contract-isa
 * §13.1``, user ruling 2026-11-27):
 *   * N = immu18[11:0], 12 bits, no cap (0 <= N <= 4095);
 *   * total cycles = 1 + N; ``extraFromTotal`` therefore returns N, which is
 *     the single lump timing.cc reschedules the next fetch by;
 *   * the SBZ high bits never widen the figure (B6 rejects them as ILLI
 *     first; the mask here is defence in depth).
 *
 * Exit status: 0 all checks passed, 1 at least one check failed.
 */
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <string_view>

#include "arch/dadao/wuming_latency.hh"

namespace wuming = gem5::DadaoISA::wuming;

namespace
{

int failures = 0;

void
check(bool ok, const char *fmt, ...)
{
    va_list args;
    va_start(args, fmt);
    std::printf("[%s] ", ok ? "PASS" : "FAIL");
    std::vprintf(fmt, args);
    std::printf("\n");
    va_end(args);
    if (!ok)
        ++failures;
}

} // namespace

int
main()
{
    const wuming::CycleRow *row = wuming::byId("swym_oiii_imm");
    if (row == nullptr) {
        std::printf("[FAIL] swym_oiii_imm missing from the generated table\n");
        return 1;
    }
    check(std::string_view(row->mnemonic) == "swym",
          "row carries mnemonic swym (actual %s)", row->mnemonic);
    check(!wuming::provisional(*row),
          "swym row is authoritative (provenance %s)", row->provenance);

    const uint64_t values[] = {0, 1, 0x7FF, 4095};
    for (uint64_t N : values) {
        const unsigned total = wuming::swymCycles(*row, N);
        check(total == 1 + N,
              "swym %llu: total cycles %u == 1 + N",
              static_cast<unsigned long long>(N), total);
        const unsigned extra = wuming::extraFromTotal(total);
        check(extra == N, "swym %llu: extra (fetch reschedule) %u == N",
              static_cast<unsigned long long>(N), extra);
    }

    // The 12-bit field is the whole parameter: high (SBZ) bits never extend
    // the delay even if a caller hands them over.
    check(wuming::swymCycles(*row, 0xFFF | 0x1000) == 4096,
          "swym: immu18[17:12] ignored, N = immu18[11:0]");
    check(wuming::swymCycles(*row, 0x3FFFF) == 4096,
          "swym: all-ones immu18 still 1 + 0xFFF");

    std::printf("summary: %d failure(s)\n", failures);
    return failures == 0 ? 0 : 1;
}
