#!/usr/bin/env python3
"""Run independent DADAO ISA vectors through gem5 AtomicSimpleCPU."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = Path(
    subprocess.check_output(
        [sys.executable, str(ROOT / "tools/infra/paths.py"), "test_artifacts_dir"],
        text=True,
    ).strip()
) / "gem5"


def memory_entries(case: dict, state: str) -> list[dict]:
    entries = (case.get(state) or {}).get("memory", [])
    if not entries:
        return []
    size_by_op = {
        **dict.fromkeys((0x10, 0x13, 0x18, 0x28, 0x2B, 0x30), 1),
        **dict.fromkeys((0x11, 0x14, 0x19, 0x29, 0x2C, 0x31), 2),
        **dict.fromkeys((0x12, 0x15, 0x1A, 0x2A, 0x2D, 0x32), 4),
        **dict.fromkeys(range(0x20, 0x28), 8),
        **dict.fromkeys(range(0x38, 0x40), 8),
        0x74: 8, 0x75: 8, 0x76: 8,
    }
    op = int(case["encoding"]["word"], 0) >> 24
    result = []
    for entry in entries:
        size = entry.get("size", size_by_op.get(op))
        if size is None:
            raise ValueError(f"memory size is unknown for opcode {op:#x}")
        result.append({
            **entry,
            "value": hex(int(entry["value"], 0) & ((1 << (size * 8)) - 1)),
            "size": size,
        })
    return result


def smoke_sequences() -> list[dict]:
    base = 0xFC0000000000
    setup = [
        0x4A4100FF,  # or.w rb16, wp1, 0x00ff
        0x4A40F000,  # or.w rb16, wp0, 0xf000
        0x4A42FC00,  # or.w rb16, wp2, 0xfc00
        0x4C190002,  # set.zw rd6, wp1, 0x0002
        0x48180026,  # or.w rd6, wp0, 0x0026
        0x21190000,  # st.o rd6, [rb16, 0]
    ]
    common = {
        "initial_pc": base,
        "image_addr": base,
        "input_state": {},
    }
    return [
        {
            **common,
            "id": "smoke_add",
            "encoding": {"word": hex(setup[0])},
            "words": setup + [
                0x4C040064, 0x4C080037, 0x5907FFD3,
                0x40283042, 0x402430C0, 0x6B0C0004,
                0x210D0008, 0x4C400018,
            ],
            "ticks": 13001,
            "expected_pc": hex(base + 0x38),
            "expected_state": {
                "rd": {"rd1": "0x37", "rd2": "0x37", "rd3": "0",
                       "rd16": "0x18"},
                "rb": {"rb16": "0xFC0000FFF000"},
                "memory": [
                    {"address": "0xFC0000FFF000", "value": "0x20026",
                     "size": 8},
                    {"address": "0xFC0000FFF008", "value": "0", "size": 8},
                ],
            },
        },
        {
            **common,
            "id": "smoke_arith",
            "encoding": {"word": hex(setup[0])},
            "words": setup + [
                0x4C04002A, 0x59040007, 0x4C080031,
                0x40AC3042, 0x6B0C0004, 0x210D0008, 0x4C400018,
            ],
            "ticks": 12001,
            "expected_pc": hex(base + 0x34),
            "expected_state": {
                "rd": {"rd1": "0x31", "rd2": "0x31", "rd3": "0",
                       "rd16": "0x18"},
                "rb": {"rb16": "0xFC0000FFF000"},
                "memory": [
                    {"address": "0xFC0000FFF000", "value": "0x20026",
                     "size": 8},
                    {"address": "0xFC0000FFF008", "value": "0", "size": 8},
                ],
            },
        },
        {
            **common,
            "id": "smoke_jump",
            "encoding": {"word": hex(setup[0])},
            "words": setup + [
                0x4C140000, 0x4C100001, 0x70000004,
                0x21110008, 0x4C400018, 0x40000000,
                0x21150008, 0x4C400018,
            ],
            "ticks": 10001,
            "expected_pc": hex(base + 0x38),
            "expected_state": {
                "rd": {"rd4": "1", "rd5": "0", "rd16": "0x18"},
                "rb": {"rb16": "0xFC0000FFF000"},
                "memory": [
                    {"address": "0xFC0000FFF000", "value": "0x20026",
                     "size": 8},
                    {"address": "0xFC0000FFF008", "value": "0", "size": 8},
                ],
            },
        },
    ]


def expected_registers(case: dict, bank: str) -> dict:
    expected = dict(case.get("input_state", {}).get(bank, {}))
    op = int(case["encoding"]["word"], 0) >> 24
    if bank == "ra" and op in {0x74, 0x75, 0x76} and \
            not case.get("expected_fault"):
        expected = {}
        initial_ra0 = case.get("input_state", {}).get("ra", {}).get("ra0")
        if initial_ra0 is not None:
            expected["ra0"] = initial_ra0
    expected.update((case.get("expected_state") or {}).get(bank, {}))
    return expected


def expected_memory(case: dict) -> list[dict]:
    entries = {
        (entry["address"], entry["size"]): entry
        for entry in memory_entries(case, "input_state")
    }
    entries.update({
        (entry["address"], entry["size"]): entry
        for entry in memory_entries(case, "expected_state")
    })
    return list(entries.values())


def supported_memory_case(case: dict) -> bool:
    if case.get("status") != "active":
        return False
    if case.get("class") in {"semantic", "boundary"}:
        return True
    if case.get("class") != "legality":
        return False
    if case.get("expected_fault") in {"CFXMEM", "MALIGN"}:
        return True
    if case.get("expected_fault") != "ILLI":
        return False
    word = int(case["encoding"]["word"], 0)
    op, ha, count = word >> 24, (word >> 18) & 63, word & 63
    load = op in range(0x10, 0x16) or op in {0x20, 0x22, 0x24} or \
        op in range(0x28, 0x2E) or op in {0x38, 0x3A, 0x3C}
    rd_or_rb = op not in {0x24, 0x25, 0x3C, 0x3D}
    block = op in range(0x28, 0x33) or op in range(0x38, 0x3E)
    return (load and rd_or_rb and ha == 0) or \
        (block and (count == 0 or ha + count > 64))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gem5", type=Path,
                        default=Path(os.environ.get(
                            "DADAO_GEM5_BINARY",
                            ROOT / ".work/source/gem5/build/DADAO/gem5.opt")))
    parser.add_argument("--profile",
                        choices=("current", "skeleton", "sequences",
                                 "remaining"),
                        default="current",
                        help="select current, GEM5-003t, or smoke sequences")
    parser.add_argument("--inject", action="store_true",
                        help="corrupt a smoke expectation for reverse testing")
    parser.add_argument(
        "--inject-excluded",
        action="store_true",
        help="replace one excluded encoding with accepted swym; gate must fail",
    )
    parser.add_argument("--vector-root", type=Path,
                        default=ROOT / "tests/vectors/isa",
                        help="read ISA YAML files from this directory")
    args = parser.parse_args()
    gem5 = args.gem5.resolve()
    vector_root = args.vector_root.resolve()
    if not gem5.is_file():
        raise SystemExit(f"gem5-isa: missing {gem5}; run make build-gem5")
    if not vector_root.is_dir():
        raise SystemExit(f"gem5-isa: missing vector root {vector_root}")
    if args.inject and args.profile != "sequences":
        raise SystemExit("gem5-isa: --inject requires --profile sequences")
    if args.inject_excluded and args.profile != "remaining":
        raise SystemExit(
            "gem5-isa: --inject-excluded requires --profile remaining")
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    vectors = yaml.safe_load((vector_root / "reg-arith.yaml").read_text())
    cases = [
        x for x in vectors
        if x.get("id") == "add.si_riii_rd"
        and x.get("class") in {"semantic", "legality"}
        and x.get("status") == "active"
        and (x.get("class") == "legality" or
             x.get("input_state", {}).get("rd", {}).get("rd1"))
    ]
    if len(cases) < 3:
        raise SystemExit("gem5-isa: expected at least two active add.si semantic vectors")
    arithmetic_ids = {
        "add.uo_rrrr_rd", "add.so_rrrr_rd", "sub.uo_rrrr_rd",
        "sub.so_rrrr_rd", "mul.uo_rrrr_rd", "mul.so_rrrr_rd",
        "add.o_orrr_bbd", "sub.o_orrr_bbd",
        "div.uo_orrr_rd", "div.so_orrr_rd", "rem.uo_orrr_rd",
        "rem.so_orrr_rd",
    }
    arithmetic = [x for x in vectors if x.get("id") in arithmetic_ids
                  and x.get("class") in {
                      "semantic", "boundary", "overlap", "legality",
                  }
                  and x.get("status") == "active"]
    reserved = yaml.safe_load((vector_root / "reserved.yaml").read_text())
    rb_arithmetic = [x for x in vectors if x.get("id") == "add.si_riii_rb"
                     and x.get("class") in {"semantic", "legality"}
                     and x.get("status") == "active"]
    scalar = []
    control = []
    if args.profile == "current":
        scalar_ids = {
            "or.w_rwii_rd", "andn.w_rwii_rd", "or.w_rwii_rb",
            "andn.w_rwii_rb", "set.zw_rwii_rd", "set.ow_rwii_rd",
            "set.zw_rwii_rb", "cmp.ui_rrii_rd", "cmp.si_rrii_rd",
            "cmp.uo_orrr_dbb", "cmp.uo_orrr_rd", "cmp.so_orrr_rd",
            "rd2rd_orri_rd", "rd2ra_orri_ra", "ra2rd_orri_ra",
            "rb2rb_orri_rb", "rd2rb_orri_rb", "rb2rd_orri_rb",
        }
        for filename in ("reg-imm-block.yaml", "reg-compare.yaml"):
            scalar.extend(x for x in yaml.safe_load(
                (vector_root / filename).read_text())
                if x.get("id") in scalar_ids
                and x.get("class") in {
                    "semantic", "boundary", "overlap", "legality",
                }
                and x.get("status") == "active")
        misc_ids = {
            "and.o_orrr_rd", "or.o_orrr_rd", "xor.o_orrr_rd",
            "xnor.o_orrr_rd", "ext.uo_orrr_rd", "ext.so_orrr_rd",
            "shr.uo_orrr_rd", "shr.so_orrr_rd", "shl.uo_orrr_rd",
            "ext.uo_orri_rd", "ext.so_orri_rd", "shr.uo_orri_rd",
            "shr.so_orri_rd", "shl.uo_orri_rd", "cs.n_rrrr_rd",
            "cs.z_rrrr_rd", "cs.p_rrrr_rd", "cs.eq_rrrr_rd",
            "cs.ne_rrrr_rd",
        }
        for filename in (
                "reg-logic.yaml", "reg-shift-extend.yaml",
                "reg-cond-assign.yaml"):
            scalar.extend(x for x in yaml.safe_load(
                (vector_root / filename).read_text())
                if x.get("id") in misc_ids
                and x.get("class") in {
                    "semantic", "boundary", "overlap", "legality",
                }
                and x.get("status") == "active")
        for filename in (
                "reg-arith.yaml", "reg-compare.yaml",
                "reg-shift-extend.yaml"):
            scalar.extend(x for x in yaml.safe_load(
                (vector_root / filename).read_text())
                if int(x["encoding"]["word"], 0) >> 24 in {0x41, 0x42, 0x43}
                and x.get("class") in {
                    "semantic", "boundary", "legality",
                }
                and x.get("status") == "active")
        scalar.extend(x for x in yaml.safe_load(
            (vector_root / "misc.yaml").read_text())
            if x.get("id") == "swym_oiii_imm"
            and x.get("class") == "semantic"
            and x.get("status") == "active")
        for filename in ("ctrl-br.yaml", "ctrl-jump.yaml"):
            control.extend(x for x in yaml.safe_load(
                (vector_root / filename).read_text())
                if x.get("class") == "semantic"
                and x.get("status") == "active")
        for filename in ("ctrl-call.yaml", "ctrl-ret.yaml"):
            control.extend(x for x in yaml.safe_load(
                (vector_root / filename).read_text())
                if x.get("class") in {"semantic", "legality"}
                and x.get("status") == "active"
                and x.get("expected_fault") != "UNMAPPED")
        for case in control:
            case["initial_pc"] = 0xFC0000000000
            case["image_addr"] = 0xFC0000000000
        for filename in ("mem-rd.yaml", "mem-rb.yaml", "mem-ra.yaml"):
            scalar.extend(x for x in yaml.safe_load(
                (vector_root / filename).read_text())
                if supported_memory_case(x))
    cases += arithmetic + rb_arithmetic + scalar + control + reserved
    # SimRISC-04: imms18 is signed; 0x3ffff sign-extends to -1.
    cases.append({"encoding": {"word": "0x5907ffff"},
                  "input_state": {"rd": {"rd1": "0x0"}},
                  "expected_state": {"rd": {"rd1": "0xffffffffffffffff"}}})
    cases.append({"encoding": {"word": "0x00000000"},
                  "expected_fault": "UNDI", "input_state": {}})
    cases.append({
        "id": "sub.o_orrr_dbb",
        "encoding": {"word": "0x40cc1083"},
        "input_state": {"rb": {"rb2": "0x64", "rb3": "0x1e"}},
        "expected_state": {"rd": {"rd1": "0x46"}},
    })
    cases.append({"encoding": {"word": "0x59040001"},
                  "initial_pc": 0xFFFFFFFF0002,
                  "expected_fault": "IALIGN", "input_state": {}})
    review_cases = [{
        "encoding": {"word": "0x70000001"},
        "initial_pc": 0xFFFFFFFFFFFC,
        "image_addr": 0xFFFFFFFFFFFC,
        "expected_pc": "0x0",
        "input_state": {},
        "expected_state": {"rb": {"rb0": "0x0001000000000000"}},
    }, {
        "encoding": {"word": "0x77880000"},
        "initial_pc": 0xFFFFFFFFFFFC,
        "image_addr": 0xFFFFFFFFFFFC,
        "expected_pc": "0x0",
        "input_state": {},
        "expected_state": {"rb": {"rb0": "0x0001000000000000"}},
    }, {
        "encoding": {"word": "0x40b40041"},
        "input_state": {"rd": {"rd1": "0xffffffffffffffff"}},
        "expected_state": {"ra": {"ra0": "0x003fffffffffffff"}},
    }, {
        "encoding": {"word": "0x24003000"},
        "input_state": {
            "rb": {"rb3": "0x0000fc0000000100"},
            "memory": [{
                "address": "0x0000fc0000000100",
                "value": "0xffffffffffffffff",
                "size": 8,
            }],
        },
        "expected_state": {"ra": {"ra0": "0x003fffffffffffff"}},
    }, {
        "encoding": {"word": "0x77880000"},
        "input_state": {"ra": {"ra0": "0xffffffffffffffff"}},
        "expected_state": {"ra": {"ra0": "0x003fffffffffffff"}},
    }, {
        "encoding": {"word": "0x39043002"},
        "input_state": {
            "rd": {"rd1": "0x1111111111111111",
                   "rd2": "0x2222222222222222"},
            "rb": {"rb3": "0xfffffffffffffff8"},
        },
        "expected_state": {
            "memory": [{
                "address": "0xfffffffffff8", "value": "0", "size": 8,
            }],
        },
        "expected_fault": "CFXMEM",
    }]
    if args.profile == "current":
        cases += review_cases + smoke_sequences()
    elif args.profile == "sequences":
        cases = smoke_sequences()
    elif args.profile == "remaining":
        for filename in (
                ROOT / "tests/vectors/rev/rev.yaml",
                ROOT / "tests/vectors/bitcnt/bitcnt.yaml"):
            cases.extend(
                case for case in yaml.safe_load(filename.read_text())
                if case.get("status") == "active"
                and case.get("class") in {
                    "semantic", "boundary", "legality",
                }
            )
        opcodes = yaml.safe_load(
            (ROOT / "contracts/opcodes.yaml").read_text())
        cases.extend({
            "id": opcode["id"],
            "encoding": {"word": opcode["value"]},
            "input_state": {},
            "expected_fault": "ILLI",
        } for opcode in opcodes if opcode["scope"] == "excluded")
        if args.inject_excluded:
            excluded_ids = {
                opcode["id"] for opcode in opcodes
                if opcode["scope"] == "excluded"
            }
            case = next(case for case in cases
                        if case.get("id") in excluded_ids)
            case["encoding"]["word"] = "0x77880000"
    if args.inject:
        cases[0]["expected_state"]["rd"]["rd1"] = "0xdead"
    for number, case in enumerate(cases):
        word = int(case["encoding"]["word"], 0)
        rom = ARTIFACTS / f"isa_{number}.bin"
        words = case.get("words", [word])
        rom.write_bytes(b"".join(x.to_bytes(4, "big") for x in words))
        initial_rd = case.get("input_state", {}).get("rd", {})
        expected_rd = expected_registers(case, "rd")
        initial_rb = case.get("input_state", {}).get("rb", {})
        expected_rb = expected_registers(case, "rb")
        initial_ra = case.get("input_state", {}).get("ra", {})
        expected_ra = expected_registers(case, "ra")
        initial = int(initial_rd.get("rd1", "0"), 0)
        expected = int(expected_rd["rd1"], 0) if "rd1" in expected_rd else initial
        command = [
            str(gem5), "--outdir", str(ARTIFACTS / f"run_{number}"),
            str(ROOT / "tests/gem5/isa_fixture.py"),
            "--rom", str(rom), "--initial-rd1", hex(initial),
            "--expected-rd1", hex(expected),
            "--initial-rd", json.dumps(initial_rd),
            "--expected-rd", json.dumps(expected_rd),
            "--initial-rb", json.dumps(initial_rb),
            "--expected-rb", json.dumps(expected_rb),
            "--initial-ra", json.dumps(initial_ra),
            "--expected-ra", json.dumps(expected_ra),
            "--initial-memory", json.dumps(memory_entries(case, "input_state")),
            "--expected-memory", json.dumps(
                expected_memory(case)),
            "--expected-fault", case.get("expected_fault") or "none",
            "--initial-pc", hex(case.get("initial_pc", 0xFFFFFFFF0000)),
            "--image-addr", hex(case.get("image_addr", 0xFFFFFFFF0000)),
            "--ticks", str(case.get("ticks", 1)),
        ]
        if case.get("expected_pc") is not None:
            command += ["--expected-pc", case["expected_pc"]]
        print(f"gem5-isa: vector {number} word={word:#010x}", flush=True)
        result = subprocess.run(command, timeout=30, check=False)
        if result.returncode:
            return result.returncode
    print(f"gem5-isa: PASS {len(cases)} {args.profile} spec vectors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
