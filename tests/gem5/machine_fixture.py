"""Machine-01 full-system fixture for DADAO gem5 acceptance tests."""

import argparse
import json

import m5
from m5.objects import (
    AddrRange,
    DadaoBareMetal,
    DadaoSemihosting,
    Root,
    SimpleMemory,
    SrcClockDomain,
    System,
    SystemXBar,
    VoltageDomain,
)
from m5.objects.DadaoCPU import DadaoAtomicSimpleCPU


def number(value):
    return int(value, 0) if isinstance(value, str) else int(value)


parser = argparse.ArgumentParser()
parser.add_argument("--rom", required=True)
parser.add_argument("--application", default="")
parser.add_argument("--files-root", default="")
parser.add_argument("--cmd-line", default="dadao-gem5")
parser.add_argument("--stdin", default="stdin")
parser.add_argument("--initial-rd", default="{}")
parser.add_argument("--initial-rb", default="{}")
parser.add_argument("--initial-ra", default="{}")
parser.add_argument("--initial-cfx", default="[]")
parser.add_argument("--initial-memory", default="[]")
parser.add_argument("--initial-mode", type=lambda s: int(s, 0))
parser.add_argument("--initial-current-cfx", type=lambda s: int(s, 0))
parser.add_argument("--expected", default="{}")
parser.add_argument("--ticks", type=int, default=1000000)
args = parser.parse_args()

initial_rd = json.loads(args.initial_rd)
initial_rb = json.loads(args.initial_rb)
initial_ra = json.loads(args.initial_ra)
initial_cfx = json.loads(args.initial_cfx)
initial_memory = json.loads(args.initial_memory)
expected = json.loads(args.expected)

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
system.semihosting = DadaoSemihosting(
    cmd_line=args.cmd_line,
    files_root_dir=args.files_root,
    stdin=args.stdin,
    mem_reserve="64KiB",
    stack_size="1MiB",
)
system.workload = DadaoBareMetal(
    bootrom=args.rom,
    application=args.application,
    semihosting=system.semihosting,
)

root = Root(full_system=True, system=system)
m5.instantiate()

for name, value in initial_rd.items():
    system.workload.writeRd(int(name[2:]), number(value))
for name, value in initial_rb.items():
    system.workload.writeRb(int(name[2:]), number(value))
for name, value in initial_ra.items():
    system.workload.writeRa(int(name[2:]), number(value))
for entry in initial_cfx:
    system.workload.writeCfxReg(
        number(entry["cfx"]),
        number(entry["cg"]),
        number(entry["rc"]),
        number(entry["value"]),
    )
for entry in initial_memory:
    system.workload.writeMemory(
        number(entry["address"]), number(entry["value"]), number(entry["size"])
    )
if args.initial_mode is not None:
    system.workload.setMode(args.initial_mode)
if args.initial_current_cfx is not None:
    system.workload.setCurrentCfx(args.initial_current_cfx)

event = m5.simulate(args.ticks)
actual = {
    "event_code": event.getCode(),
    "event_cause": event.getCause(),
    "pc": system.workload.readPc(),
    "mode": system.workload.readMode(),
    "current_cfx": system.workload.readCurrentCfx(),
}
print(
    "gem5-machine: "
    f"cause={actual['event_cause']} code={actual['event_code']} "
    f"pc={actual['pc']:#014x} mode={actual['mode']}"
)

errors = []
for field in ("event_code", "pc", "mode", "current_cfx"):
    if field in expected and actual[field] != number(expected[field]):
        errors.append(
            f"{field}: expected {number(expected[field]):#x}, "
            f"got {actual[field]:#x}"
        )
if "event_cause" in expected and expected["event_cause"] not in actual["event_cause"]:
    errors.append(
        f"event_cause: expected substring {expected['event_cause']!r}, "
        f"got {actual['event_cause']!r}"
    )
for bank, reader in (
    ("rd", system.workload.readRd),
    ("rb", system.workload.readRb),
    ("ra", system.workload.readRa),
):
    for name, value in expected.get(bank, {}).items():
        observed = reader(int(name[2:]))
        if observed != number(value):
            errors.append(
                f"{name}: expected {number(value):#x}, got {observed:#x}"
            )
for entry in expected.get("cfx", []):
    observed = system.workload.readCfxReg(
        number(entry["cfx"]), number(entry["cg"]), number(entry["rc"])
    )
    if observed != number(entry["value"]):
        errors.append(
            "cfx[{cfx}][{cg}][{rc}]: expected {expected:#x}, got {actual:#x}".format(
                cfx=entry["cfx"],
                cg=entry["cg"],
                rc=entry["rc"],
                expected=number(entry["value"]),
                actual=observed,
            )
        )
for entry in expected.get("memory", []):
    observed = system.workload.readMemory(
        number(entry["address"]), number(entry["size"])
    )
    if observed != number(entry["value"]):
        errors.append(
            f"memory[{number(entry['address']):#x}]: "
            f"expected {number(entry['value']):#x}, got {observed:#x}"
        )
for entry in expected.get("memory_nonzero", []):
    observed = system.workload.readMemory(
        number(entry["address"]), number(entry["size"])
    )
    if observed == 0:
        errors.append(f"memory[{number(entry['address']):#x}]: expected nonzero")

if errors:
    for error in errors:
        print(f"gem5-machine: FAIL {error}")
    raise SystemExit(1)
print("gem5-machine: PASS")
