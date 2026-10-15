"""Run one spec-derived DADAO FP probe case in gem5."""

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
parser.add_argument("--expected-rd", default="{}")
parser.add_argument("--expected-rf", default="{}")
parser.add_argument("--expected-code", type=lambda value: int(value, 0),
                    required=True)
parser.add_argument("--ticks", type=int, required=True)
args = parser.parse_args()

expected_rd = json.loads(args.expected_rd)
expected_rf = json.loads(args.expected_rf)

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
    bootrom=args.rom,
    initial_pc=0xFFFFFFFF0000,
    image_addr=0xFFFFFFFF0000,
)

root = Root(full_system=True, system=system)
m5.instantiate()
event = m5.simulate(args.ticks)

ok = event.getCode() == args.expected_code
for index, value in expected_rd.items():
    ok &= system.workload.readRd(int(index)) == int(value)
for index, value in expected_rf.items():
    ok &= system.workload.readRf(int(index)) == int(value)

print(
    f"gem5-fp: cause={event.getCause()} code={event.getCode():#x} "
    f"expected={args.expected_code:#x} pc={system.workload.readPc():#x}"
)
if not ok:
    for index, value in expected_rd.items():
        actual = system.workload.readRd(int(index))
        if actual != int(value):
            print(
                f"gem5-fp: rd{index} expected={int(value):#018x} "
                f"actual={actual:#018x}"
            )
    for index, value in expected_rf.items():
        actual = system.workload.readRf(int(index))
        if actual != int(value):
            print(
                f"gem5-fp: rf{index} expected={int(value):#018x} "
                f"actual={actual:#018x}"
            )
    raise SystemExit(1)
