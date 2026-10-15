#!/usr/bin/env python3
"""Exercise the Machine-01 platform and semihosting through gem5."""

import argparse
import json
import os
import struct
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = Path(
    subprocess.check_output(
        [sys.executable, str(ROOT / "tools/infra/paths.py"), "test_artifacts_dir"],
        text=True,
    ).strip()
) / "gem5-machine"

RAM_BASE = 0xFC0000000000
RAM_SIZE = 16 * 1024 * 1024
ROM_BASE = 0xFFFFFFFF0000
ROM_SIZE = 64 * 1024
HANDLER = ROM_BASE + 0x100
TAG = 0x30000
ADP_EXIT = 0x20026
EM_DADAO = 0x0DA0
RESULT = 0x700
EXIT_BLOCK = 0x800
K_OPEN = 0x100
K_SVC = 0x140
K_SVC2 = 0x180
K_BUF = 0x300
K_PATH = 0x400
K_STR = 0x600


def set_zw_rd(reg, wp, imm):
    return (0x4C << 24) | (reg << 18) | (wp << 16) | (imm & 0xFFFF)


def or_w_rd(reg, wp, imm):
    return (0x48 << 24) | (reg << 18) | (wp << 16) | (imm & 0xFFFF)


def set_zw_rb(reg, wp, imm):
    return (0x4E << 24) | (reg << 18) | (wp << 16) | (imm & 0xFFFF)


def or_w_rb(reg, wp, imm):
    return (0x4A << 24) | (reg << 18) | (wp << 16) | (imm & 0xFFFF)


def ld_o(rd, rb, offset=0):
    return (0x20 << 24) | (rd << 18) | (rb << 12) | (offset & 0xFFF)


def st_o(rd, rb, offset=0):
    return (0x21 << 24) | (rd << 18) | (rb << 12) | (offset & 0xFFF)


def cfx2rd(cfx, cg, rc, rd):
    return (0x7A << 24) | (cfx << 18) | (cg << 12) | (rc << 6) | rd


def cfx2rc(cfx, cg, rc, rd):
    return (0x7B << 24) | (cfx << 18) | (cg << 12) | (rc << 6) | rd


def escape(cfx, word_offset):
    return (0x7E << 24) | (cfx << 18) | (word_offset & 0x3FFFF)


def trap(cfx, function):
    return (0x7F << 24) | (cfx << 18) | (function & 0x3FFFF)


def load_rd(reg, value):
    words = [set_zw_rd(reg, 0, value)]
    for wp in (1, 2, 3):
        lane = (value >> (16 * wp)) & 0xFFFF
        if lane:
            words.append(or_w_rd(reg, wp, lane))
    return words


def load_rb(reg, value):
    words = [set_zw_rb(reg, 0, value)]
    for wp in (1, 2, 3):
        lane = (value >> (16 * wp)) & 0xFFFF
        if lane:
            words.append(or_w_rb(reg, wp, lane))
    return words


def sh_call(operation, argument, cfx=0):
    return load_rd(16, operation) + load_rb(16, argument) + [trap(cfx, TAG)]


def save_result():
    return load_rb(1, RAM_BASE) + [st_o(8, 1, RESULT)]


def exit_seq(code, operation=0x20):
    return (
        load_rb(16, RAM_BASE + EXIT_BLOCK)
        + load_rd(8, ADP_EXIT)
        + [st_o(8, 16, 0)]
        + load_rd(9, code)
        + [st_o(9, 16, 8)]
        + load_rd(16, operation)
        + [trap(7, TAG)]
    )


def finish(words, code):
    return words + save_result() + exit_seq(code)


def words_blob(words):
    return b"".join(struct.pack(">I", word & 0xFFFFFFFF) for word in words)


def rom_image(words, handlers=None):
    image = bytearray(words_blob(words))
    for offset, handler in sorted((handlers or {}).items()):
        if len(image) > offset:
            raise ValueError(f"ROM program overlaps handler at {offset:#x}")
        image.extend(b"\x77\x88\x00\x00" * ((offset - len(image)) // 4))
        image.extend(words_blob(handler))
    if not image or len(image) > ROM_SIZE:
        raise ValueError(f"invalid ROM size {len(image)}")
    return bytes(image)


def blk(*values):
    return b"".join(struct.pack(">Q", value & 0xFFFFFFFFFFFFFFFF)
                    for value in values)


def data_image(entries=None, size=0x1000):
    image = bytearray(size)
    for offset, data in (entries or {}).items():
        image[offset:offset + len(data)] = data
    return bytes(image)


def build_elf(payload, *, entry=RAM_BASE, vaddr=RAM_BASE, memsz=None,
              ei_class=2, ei_data=2, machine=EM_DADAO, flags=1):
    offset = 0x1000
    memsz = len(payload) if memsz is None else memsz
    ident = b"\x7fELF" + bytes((ei_class, ei_data, 1, 0)) + b"\0" * 8
    ehdr = ident + struct.pack(
        ">HHIQQQIHHHHHH",
        2, machine, 1, entry, 64, 0, flags, 64, 56, 1, 0, 0, 0,
    )
    phdr = struct.pack(
        ">IIQQQQQQ",
        1, 7, offset, vaddr, vaddr, len(payload), memsz, 0x10000,
    )
    return ehdr + phdr + b"\0" * (offset - len(ehdr) - len(phdr)) + payload


def expected_result(value, code):
    return {
        "event_code": code,
        "memory": [{
            "address": hex(RAM_BASE + RESULT),
            "size": 8,
            "value": hex(value & 0xFFFFFFFFFFFFFFFF),
        }],
    }


def invoke(gem5, name, rom, elf, expected, *, files_root, stdin=b"",
           initial_cfx=None, expected_stdout=None):
    case_dir = ARTIFACTS / name
    case_dir.mkdir(parents=True, exist_ok=True)
    rom_path = case_dir / "boot.bin"
    elf_path = case_dir / "app.elf"
    rom_path.write_bytes(rom)
    elf_path.write_bytes(elf)
    command = [
        str(gem5),
        "--outdir", str(case_dir / "m5out"),
        str(ROOT / "tests/gem5/machine_fixture.py"),
        "--rom", str(rom_path),
        "--application", str(elf_path),
        "--files-root", f"{files_root}{os.sep}",
        "--cmd-line", "gem5-case",
        "--expected", json.dumps(expected),
    ]
    if initial_cfx:
        command += ["--initial-cfx", json.dumps(initial_cfx)]
    result = subprocess.run(
        command, input=stdin, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, timeout=30, check=False,
    )
    output = result.stdout.decode(errors="replace")
    if result.returncode:
        print(f"[FAIL] {name}: fixture rc={result.returncode}")
        print(output[-3000:])
        return False
    if expected_stdout is not None and expected_stdout not in result.stdout:
        print(f"[FAIL] {name}: stdout lacks {expected_stdout!r}")
        print(output[-3000:])
        return False
    print(f"[PASS] {name}")
    return True


def expect_load_failure(gem5, name, elf):
    case_dir = ARTIFACTS / name
    case_dir.mkdir(parents=True, exist_ok=True)
    rom_path = case_dir / "boot.bin"
    elf_path = case_dir / "bad.elf"
    rom_path.write_bytes(words_blob([0x77880000]))
    elf_path.write_bytes(elf)
    result = subprocess.run(
        [
            str(gem5), "--outdir", str(case_dir / "m5out"),
            str(ROOT / "tests/gem5/machine_fixture.py"),
            "--rom", str(rom_path), "--application", str(elf_path),
        ],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=30, check=False,
    )
    if result.returncode == 0:
        print(f"[FAIL] {name}: malformed ELF was accepted")
        return False
    print(f"[PASS] {name}")
    return True


def run_platform_cases(gem5, files_root, inject):
    results = []

    app_entry = RAM_BASE + 0x100
    exit_addr = RAM_BASE + 0x200
    boot = (
        load_rd(1, app_entry)
        + [cfx2rc(0, 3, 10, 1)]
        + load_rd(1, 0)
        + [cfx2rc(0, 3, 8, 1), trap(0, 0)]
    )
    app = bytearray(0x280)
    app_code = words_blob(
        load_rd(4, 0x55)
        + load_rb(16, exit_addr)
        + load_rd(16, 0x20)
        + [trap(7, TAG)]
    )
    app[0x100:0x100 + len(app_code)] = app_code
    app[0x200:0x210] = blk(ADP_EXIT, 0x2A)
    startup_expected = {
        "event_code": 0x2A,
        "mode": 0,
        "rd": {"rd4": "0xdead" if inject else "0x55"},
        "memory": [
            {"address": hex(exit_addr), "size": 8, "value": hex(ADP_EXIT)},
            {"address": hex(RAM_BASE + 0x300), "size": 8, "value": "0"},
        ],
    }
    results.append(invoke(
        gem5, "startup_elf_handoff", rom_image(boot),
        build_elf(bytes(app), entry=app_entry, memsz=0x308),
        startup_expected, files_root=files_root,
    ))

    good = build_elf(data_image())
    results.append(expect_load_failure(
        gem5, "elf_bad_class",
        build_elf(data_image(), ei_class=1),
    ))
    results.append(expect_load_failure(
        gem5, "elf_bad_flags",
        build_elf(data_image(), flags=2),
    ))
    results.append(expect_load_failure(
        gem5, "elf_segment_outside_ram",
        build_elf(data_image(), entry=ROM_BASE, vaddr=ROM_BASE),
    ))

    trap_pc = ROM_BASE + 4 * 6
    general = (
        load_rd(1, HANDLER)
        + [cfx2rc(0, 3, 10, 1)]
        + load_rd(1, 0)
        + [cfx2rc(0, 3, 8, 1), trap(0, 0x123)]
        + exit_seq(0x30)
    )
    results.append(invoke(
        gem5, "trap_escape", rom_image(general, {0x100: [escape(0, 1)]}),
        good,
        {
            "event_code": 0x30,
            "mode": 3,
            "current_cfx": 0,
            "cfx": [
                {"cfx": 0, "cg": 4, "rc": 2, "value": 1},
                {"cfx": 0, "cg": 4, "rc": 5, "value": 1},
                {"cfx": 0, "cg": 5, "rc": 0, "value": 3},
                {"cfx": 0, "cg": 5, "rc": 1,
                 "value": "0xffffffffffffffff"},
                {"cfx": 0, "cg": 5, "rc": 2, "value": 1},
                {"cfx": 0, "cg": 5, "rc": 3, "value": hex(trap_pc)},
                {"cfx": 0, "cg": 5, "rc": 4,
                 "value": hex(trap(0, 0x123))},
            ],
        },
        files_root=files_root,
    ))

    fault_pc = ROM_BASE + 4 * 4
    fault = (
        load_rd(1, HANDLER)
        + [cfx2rc(3, 3, 10, 1), 0x00000000]
        + exit_seq(0x31)
    )
    results.append(invoke(
        gem5, "fault_vector_escape",
        rom_image(fault, {0x100: [escape(3, 1)]}), good,
        {
            "event_code": 0x31,
            "current_cfx": 3,
            "cfx": [
                {"cfx": 3, "cg": 4, "rc": 3, "value": 1},
                {"cfx": 3, "cg": 5, "rc": 0, "value": 3},
                {"cfx": 3, "cg": 5, "rc": 1,
                 "value": "0xffffffffffffffff"},
                {"cfx": 3, "cg": 5, "rc": 2, "value": hex(1 << 9)},
                {"cfx": 3, "cg": 5, "rc": 3, "value": hex(fault_pc)},
                {"cfx": 3, "cg": 5, "rc": 4, "value": 0},
            ],
        },
        files_root=files_root,
    ))

    results.append(invoke(
        gem5, "trap_mask_denied",
        rom_image([trap(0, 1)]), good,
        {"event_code": 0x88}, files_root=files_root,
        initial_cfx=[{"cfx": 0, "cg": 3, "rc": 6, "value": 1}],
    ))
    results.append(invoke(
        gem5, "reserved_cfx",
        rom_image([cfx2rd(7, 0, 0, 1)]), good,
        {"event_code": 0x88}, files_root=files_root,
    ))
    results.append(invoke(
        gem5, "unimplemented_cfx",
        rom_image([cfx2rd(4, 0, 0, 1)]), good,
        {"event_code": 0x82}, files_root=files_root,
    ))
    results.append(invoke(
        gem5, "cfx2rd_mask_denied",
        rom_image([cfx2rd(0, 0, 0, 1)]), good,
        {"event_code": 0x88}, files_root=files_root,
        initial_cfx=[{"cfx": 0, "cg": 3, "rc": 2, "value": 1}],
    ))
    results.append(invoke(
        gem5, "cfx_read_only_write",
        rom_image(load_rd(2, 1) + [cfx2rc(0, 4, 0, 2)]), good,
        {"event_code": 0x82}, files_root=files_root,
    ))
    results.append(invoke(
        gem5, "cfx_invalid_register",
        rom_image([cfx2rd(0, 5, 6, 1)]), good,
        {"event_code": 0x82}, files_root=files_root,
    ))
    cfx_rw = (
        load_rd(2, 0x12345678)
        + [cfx2rc(0, 5, 3, 2), cfx2rd(0, 5, 3, 3)]
        + exit_seq(0x32)
    )
    results.append(invoke(
        gem5, "cfx_register_rw", rom_image(cfx_rw), good,
        {
            "event_code": 0x32,
            "rd": {"rd3": "0x12345678"},
            "cfx": [
                {"cfx": 0, "cg": 0, "rc": 0, "value": "0x00090002"},
                {"cfx": 63, "cg": 3, "rc": 0, "value": "0x00010002"},
                {"cfx": 63, "cg": 4, "rc": 0, "value": 63},
                {"cfx": 63, "cg": 4, "rc": 6, "value": 4},
                {"cfx": 63, "cg": 5, "rc": 63, "value": "0x3f07"},
            ],
        },
        files_root=files_root,
    ))
    cross_escape = (
        load_rd(1, HANDLER)
        + [cfx2rc(0, 3, 10, 1), trap(0, 0x321)]
        + exit_seq(0x33)
    )
    results.append(invoke(
        gem5, "cross_cfx_escape",
        rom_image(cross_escape, {0x100: [escape(63, 1)]}), good,
        {
            "event_code": 0x33,
            "current_cfx": 0,
            "cfx": [{"cfx": 0, "cg": 4, "rc": 5, "value": 1}],
        },
        files_root=files_root,
    ))
    denied_escape = (
        load_rd(1, HANDLER)
        + [cfx2rc(0, 3, 10, 1)]
        + load_rd(2, 1 << 63)
        + [cfx2rc(0, 3, 7, 2), trap(0, 0x322)]
    )
    results.append(invoke(
        gem5, "cross_cfx_escape_denied",
        rom_image(denied_escape, {0x100: [escape(63, 1)]}), good,
        {"event_code": 0x88},
        files_root=files_root,
    ))
    umon_bad = load_rb(2, 0x100000) + [ld_o(2, 2)]
    results.append(invoke(
        gem5, "umon_cfxmem", rom_image(umon_bad), good,
        {"event_code": 0x81}, files_root=files_root,
    ))
    power_bad = load_rb(2, RAM_BASE + RAM_SIZE) + [ld_o(2, 2)]
    results.append(invoke(
        gem5, "power_unmapped", rom_image(power_bad), good,
        {"event_code": 0x87}, files_root=files_root,
    ))
    return results


def service_case(operation, entries, expected, code, *, prefix=None, cfx=0):
    words = sh_call(operation, RAM_BASE + K_SVC if entries is not None else 0,
                    cfx=cfx)
    return finish((prefix or []) + words, code), data_image(entries), \
        expected_result(expected, code)


def run_semihost_cases(gem5, files_root):
    results = []
    marker = 0x40

    def run(name, words, payload, expected, *, stdin=b"", stdout=None):
        nonlocal marker
        results.append(invoke(
            gem5, name, rom_image(words), build_elf(payload), expected,
            files_root=files_root, stdin=stdin, expected_stdout=stdout,
        ))
        marker += 1

    read_file = files_root / "semi_a.txt"
    read_file.write_bytes(b"ABCDEFGH")

    path = b"semi_a.txt"
    words, payload, expected = service_case(
        0x01, {
            K_SVC: blk(RAM_BASE + K_PATH, 0, len(path)),
            K_PATH: path,
        }, 1, marker,
    )
    run("svc_open", words, payload, expected)

    prefix = sh_call(0x01, RAM_BASE + K_OPEN) + load_rb(1, RAM_BASE) + [
        st_o(8, 1, K_SVC)
    ]
    words, payload, expected = service_case(
        0x02, {
            K_OPEN: blk(RAM_BASE + K_PATH, 0, len(path)),
            K_PATH: path,
        }, 0, marker, prefix=prefix,
    )
    run("svc_close", words, payload, expected)

    words, payload, expected = service_case(
        0x03, {K_SVC: b"Y"}, 0, marker,
    )
    run("svc_writec", words, payload, expected, stdout=b"Y")

    words, payload, expected = service_case(
        0x04, {K_SVC: b"gem5-write0\0"}, 0, marker,
    )
    run("svc_write0", words, payload, expected, stdout=b"gem5-write0")

    out_path = files_root / "semi_b.txt"
    if out_path.exists():
        out_path.unlink()
    prefix = sh_call(0x01, RAM_BASE + K_OPEN) + load_rb(1, RAM_BASE) + [
        st_o(8, 1, K_SVC)
    ]
    words, payload, expected = service_case(
        0x05, {
            K_OPEN: blk(RAM_BASE + K_PATH, 4, len(b"semi_b.txt")),
            K_SVC: blk(0, RAM_BASE + K_BUF, 4),
            K_PATH: b"semi_b.txt",
            K_BUF: b"WXYZ",
        }, 0, marker, prefix=prefix,
    )
    run("svc_write", words, payload, expected)
    results.append(out_path.read_bytes() == b"WXYZ")
    print(f"[{'PASS' if results[-1] else 'FAIL'}] svc_write_file")

    prefix = sh_call(0x01, RAM_BASE + K_OPEN) + load_rb(1, RAM_BASE) + [
        st_o(8, 1, K_SVC)
    ]
    words, payload, expected = service_case(
        0x06, {
            K_OPEN: blk(RAM_BASE + K_PATH, 0, len(path)),
            K_SVC: blk(0, RAM_BASE + K_BUF, 8),
            K_PATH: path,
        }, 0, marker, prefix=prefix,
    )
    expected["memory"].append({
        "address": hex(RAM_BASE + K_BUF), "size": 8,
        "value": "0x4142434445464748",
    })
    run("svc_read", words, payload, expected)

    words, payload, expected = service_case(0x07, None, 0x51, marker)
    run("svc_readc", words, payload, expected, stdin=b"Q")

    words, payload, expected = service_case(
        0x08, {K_SVC: blk(0x8000000000000001)}, 1, marker,
    )
    run("svc_iserror_be64", words, payload, expected)

    prefix = sh_call(0x01, RAM_BASE + K_OPEN) + load_rb(1, RAM_BASE) + [
        st_o(8, 1, K_SVC)
    ]
    words, payload, expected = service_case(
        0x09, {
            K_OPEN: blk(RAM_BASE + K_PATH, 0, len(path)),
            K_PATH: path,
        }, 0, marker, prefix=prefix,
    )
    run("svc_istty", words, payload, expected)

    prefix = sh_call(0x01, RAM_BASE + K_OPEN) + load_rb(1, RAM_BASE) + [
        st_o(8, 1, K_SVC)
    ]
    words, payload, expected = service_case(
        0x0A, {
            K_OPEN: blk(RAM_BASE + K_PATH, 0, len(path)),
            K_SVC: blk(0, 4),
            K_PATH: path,
        }, 0, marker, prefix=prefix,
    )
    run("svc_seek", words, payload, expected)

    prefix = sh_call(0x01, RAM_BASE + K_OPEN) + load_rb(1, RAM_BASE) + [
        st_o(8, 1, K_SVC)
    ]
    words, payload, expected = service_case(
        0x0C, {
            K_OPEN: blk(RAM_BASE + K_PATH, 0, len(path)),
            K_PATH: path,
        }, 8, marker, prefix=prefix,
    )
    run("svc_flen", words, payload, expected)

    words, payload, expected = service_case(
        0x0D, {K_SVC: blk(RAM_BASE + K_BUF, 1, 128)}, 0, marker,
    )
    expected["memory_nonzero"] = [{
        "address": hex(RAM_BASE + K_BUF), "size": 8,
    }]
    run("svc_tmpnam", words, payload, expected)

    remove_path = files_root / "semi_remove.txt"
    remove_path.write_bytes(b"remove")
    remove_raw = os.fsencode(remove_path)
    words, payload, expected = service_case(
        0x0E, {
            K_SVC: blk(RAM_BASE + K_PATH, len(remove_raw)),
            K_PATH: remove_raw,
        }, 0, marker,
    )
    run("svc_remove", words, payload, expected)
    results.append(not remove_path.exists())
    print(f"[{'PASS' if results[-1] else 'FAIL'}] svc_remove_file")

    old_path = files_root / "semi_old.txt"
    new_path = files_root / "semi_new.txt"
    old_path.write_bytes(b"rename")
    if new_path.exists():
        new_path.unlink()
    old_raw, new_raw = os.fsencode(old_path), os.fsencode(new_path)
    words, payload, expected = service_case(
        0x0F, {
            K_SVC: blk(RAM_BASE + K_PATH, len(old_raw),
                       RAM_BASE + K_SVC2, len(new_raw)),
            K_PATH: old_raw,
            K_SVC2: new_raw,
        }, 0, marker,
    )
    run("svc_rename", words, payload, expected)
    results.append(not old_path.exists() and new_path.read_bytes() == b"rename")
    print(f"[{'PASS' if results[-1] else 'FAIL'}] svc_rename_file")

    words, payload, expected = service_case(0x10, None, 0, marker)
    run("svc_clock", words, payload, expected)

    words, payload, expected = service_case(
        0x11, None, 1230768000, marker,
    )
    run("svc_time", words, payload, expected)

    command = b"exit 7"
    words, payload, expected = service_case(
        0x12, {
            K_SVC: blk(RAM_BASE + K_STR, len(command)),
            K_STR: command,
        }, 0x700, marker,
    )
    run("svc_system", words, payload, expected)

    bad_open = sh_call(0x01, RAM_BASE + K_OPEN)
    words, payload, expected = service_case(
        0x13, None, 22, marker, prefix=bad_open,
    )
    payload = data_image({K_OPEN: blk(0, 0, 0)})
    run("svc_errno", words, payload, expected)

    words, payload, expected = service_case(
        0x15, {
            K_SVC: blk(RAM_BASE + K_BUF, 128),
        }, 0, marker,
    )
    expected["memory"].append({
        "address": hex(RAM_BASE + K_BUF), "size": 8,
        "value": hex(int.from_bytes(b"gem5-cas", "big")),
    })
    run("svc_get_cmdline", words, payload, expected)

    words, payload, expected = service_case(
        0x16, {
            K_SVC: blk(RAM_BASE + K_BUF),
        }, 0, marker,
    )
    expected["memory"].append({
        "address": hex(RAM_BASE + K_BUF), "size": 8,
        "value": hex(RAM_BASE + 0x10000),
    })
    run("svc_heapinfo", words, payload, expected)

    exit_payload = data_image({K_SVC: blk(ADP_EXIT, 0x42)})
    run("svc_exit", sh_call(0x18, RAM_BASE + K_SVC),
        exit_payload, {"event_code": 0x42})

    words, payload, expected = service_case(0x19, None, 0, marker)
    run("svc_synccache", words, payload, expected)

    exit_payload = data_image({K_SVC: blk(ADP_EXIT, 0x43)})
    run("svc_exit_extended", sh_call(0x20, RAM_BASE + K_SVC),
        exit_payload, {"event_code": 0x43})

    words, payload, expected = service_case(
        0x30, {K_SVC: blk(0)}, 0, marker,
    )
    expected["memory_nonzero"] = [{
        "address": hex(RAM_BASE + K_SVC), "size": 8,
    }]
    run("svc_elapsed", words, payload, expected)

    words, payload, expected = service_case(0x31, None, 0, marker, cfx=7)
    expected = {
        "event_code": marker,
        "mode": 3,
        "current_cfx": 63,
        "cfx": [
            {"cfx": 0, "cg": 4, "rc": 2, "value": 0},
            {"cfx": 63, "cg": 4, "rc": 2, "value": 0},
        ],
        "memory_nonzero": [{
            "address": hex(RAM_BASE + RESULT), "size": 8,
        }],
    }
    run("svc_tickfreq_cfxha_agnostic", words, payload, expected)

    words, payload, expected = service_case(0xFF, None, -1, marker)
    run("semihost_unknown_service", words, payload, expected)

    words, payload, expected = service_case(
        0x01, {K_SVC: blk(0, 0, 0)}, -1, marker,
    )
    run("semihost_bad_argument", words, payload, expected)
    return results


def run_toolchain_case(gem5, files_root, bootrom, application, exit_code):
    return invoke(
        gem5,
        "toolchain_bootrom_elf",
        bootrom.read_bytes(),
        application.read_bytes(),
        {"event_code": exit_code, "mode": 0, "current_cfx": 0},
        files_root=files_root,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--gem5", type=Path,
        default=Path(os.environ.get(
            "DADAO_GEM5_BINARY",
            ROOT / ".work/source/gem5/build/DADAO/gem5.opt",
        )),
    )
    parser.add_argument(
        "--inject", action="store_true",
        help="corrupt the startup expectation for reverse testing",
    )
    parser.add_argument(
        "--toolchain-bootrom", type=Path,
        help="run only one integration case with this generated boot ROM",
    )
    parser.add_argument(
        "--toolchain-elf", type=Path,
        help="load this generated DADAO ELF with --toolchain-bootrom",
    )
    parser.add_argument(
        "--toolchain-exit", type=lambda value: int(value, 0), default=42,
        help="expected semihosting exit status for the toolchain integration",
    )
    args = parser.parse_args()
    gem5 = args.gem5.resolve()
    if not gem5.is_file():
        raise SystemExit(f"gem5-machine: missing {gem5}; run make build-gem5")

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    files_root = ARTIFACTS / "host-files"
    files_root.mkdir(parents=True, exist_ok=True)
    if bool(args.toolchain_bootrom) != bool(args.toolchain_elf):
        raise SystemExit(
            "gem5-machine: --toolchain-bootrom and --toolchain-elf "
            "must be provided together"
        )
    if args.toolchain_bootrom:
        if not args.toolchain_bootrom.is_file():
            raise SystemExit(
                f"gem5-machine: missing boot ROM {args.toolchain_bootrom}"
            )
        if not args.toolchain_elf.is_file():
            raise SystemExit(
                f"gem5-machine: missing ELF {args.toolchain_elf}"
            )
        passed = run_toolchain_case(
            gem5, files_root, args.toolchain_bootrom,
            args.toolchain_elf, args.toolchain_exit,
        )
        print(f"gem5-machine: {'PASS' if passed else 'FAIL'} "
              "1 toolchain integration check")
        return 0 if passed else 1

    results = run_platform_cases(gem5, files_root, args.inject)
    if not args.inject:
        results += run_semihost_cases(gem5, files_root)
    if not all(results):
        print("gem5-machine: FAIL")
        return 1
    print(f"gem5-machine: PASS {len(results)} checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
