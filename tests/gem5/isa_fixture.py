"""One-instruction full-system DADAO fixture for gem5's embedded Python."""

import argparse
import json

import m5
from m5.objects import (
    AddrRange,
    DadaoBareMetal,
    Root,
    SimpleMemory,
    SrcClockDomain,
    System,
    SystemXBar,
    VoltageDomain,
)
from m5.objects.DadaoCPU import DadaoAtomicSimpleCPU


parser = argparse.ArgumentParser()
parser.add_argument("--rom", required=True)
parser.add_argument("--initial-rd1", type=lambda s: int(s, 0), required=True)
parser.add_argument("--expected-rd1", type=lambda s: int(s, 0), required=True)
parser.add_argument("--initial-rd", default="{}")
parser.add_argument("--expected-rd", default="{}")
parser.add_argument("--expected-fault", default="none")
parser.add_argument("--initial-pc", type=lambda s: int(s, 0),
                    default=0xFFFFFFFF0000)
parser.add_argument("--initial-rb", default="{}")
parser.add_argument("--expected-rb", default="{}")
args = parser.parse_args()
FCSR_RESET = 0x7FF800007FC00000  # SimRISC-00 rf0 fixed qNaN fields.
initial_rd = json.loads(args.initial_rd)
expected_rd = json.loads(args.expected_rd)
initial_rb = json.loads(args.initial_rb)
expected_rb = json.loads(args.expected_rb)

system = System()
system.clk_domain = SrcClockDomain(clock="1GHz", voltage_domain=VoltageDomain())
system.mem_mode = "atomic"
system.mem_ranges = [
    AddrRange(0xFC0000000000, size="16MiB"),
    AddrRange(0xFFFFFFFF0000, size="64KiB"),
]
system.cpu = DadaoAtomicSimpleCPU()
system.cpu.createThreads()
system.membus = SystemXBar()
system.cpu.icache_port = system.membus.cpu_side_ports
system.cpu.dcache_port = system.membus.cpu_side_ports
system.cpu.createInterruptController()
system.system_port = system.membus.cpu_side_ports
system.ram = SimpleMemory(range=system.mem_ranges[0])
system.rom = SimpleMemory(range=system.mem_ranges[1])
system.ram.port = system.membus.mem_side_ports
system.rom.port = system.membus.mem_side_ports
system.workload = DadaoBareMetal(
    bootrom=args.rom, initial_rd1=args.initial_rd1,
    initial_pc=args.initial_pc,
)
root = Root(full_system=True, system=system)
m5.instantiate()
for name, value in initial_rd.items():
    system.workload.writeRd(int(name[2:]), int(value, 0))
for name, value in initial_rb.items():
    system.workload.writeRb(int(name[2:]), int(value, 0))
if (system.workload.readRd(0) != 0 or
        system.workload.readRb(0) != args.initial_pc or
        system.workload.readPc() != args.initial_pc or
        system.workload.readMode() != 3 or
        system.workload.readFcsr() != FCSR_RESET or
        system.workload.readRa(0) != 0 or
        system.workload.readRa(1) != 0 or
        system.workload.readRf(0) != FCSR_RESET or
        system.workload.readRf(1) != 0):
    raise SystemExit("gem5-isa: reset state mismatch")
system.workload.writeFcsr(0xFFFFFFFFFFFFFFFF)
if system.workload.readRf(0) != (FCSR_RESET | 0x30000001F):
    raise SystemExit("gem5-isa: misc FCSR write did not update rf0/mask")
system.workload.writeRf0(0)
if system.workload.readFcsr() != FCSR_RESET:
    raise SystemExit("gem5-isa: rf0 write did not update misc FCSR")
# The first AtomicSimpleCPU tick executes the instruction at tick zero.
# Stop before its second tick (one nanosecond later at this clock rate).
event = m5.simulate(1)
actual = system.workload.readRd(1)
pc = system.workload.readPc()
rd0 = system.workload.readRd(0)
rb0 = system.workload.readRb(0)
mode = system.workload.readMode()
fcsr = system.workload.readFcsr()
print(f"gem5-isa: cause={event.getCause()} rd1={actual:#018x} "
      f"pc={pc:#014x} rd0={rd0} rb0={rb0:#014x} mode={mode} fcsr={fcsr} "
      f"code={event.getCode()}")
fault_codes = {"none": None, "ILLI": 0x88, "UNDI": 0x89,
               "IALIGN": 0x8d}
expected_code = fault_codes[args.expected_fault]
if expected_code is None:
    ok = event.getCode() == 0 and pc == args.initial_pc + 4
else:
    ok = event.getCode() == expected_code and pc == args.initial_pc
ok &= actual == args.expected_rd1 and rd0 == 0 and rb0 == pc
ok &= mode == 3 and fcsr == FCSR_RESET
for name, value in expected_rd.items():
    ok &= system.workload.readRd(int(name[2:])) == int(value, 0)
for name, value in expected_rb.items():
    ok &= system.workload.readRb(int(name[2:])) == int(value, 0)
if not ok:
    raise SystemExit(1)
