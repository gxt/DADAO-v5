#!/usr/bin/env python3
"""Build and run applicable bare-metal E2E and Embench programs on gem5."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import time
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/infra"))
import paths as dadao_paths  # noqa: E402

RAM_BASE = 0xFC0000000000
EM_DADAO = 0x0DA0
ARTIFACTS = dadao_paths.test_artifacts_dir() / "gem5-programs"
TOOLCHAIN_BIN = dadao_paths.host_toolchain_bin()
RESULT_RE = re.compile(
    r"gem5-machine: cause=(.*?) code=(\d+) pc=(0x[0-9a-fA-F]+) "
    r"mode=(\d+) cfx=(\d+)"
)


class SetupError(RuntimeError):
    pass


def require_file(path: Path, description: str, *, executable=False) -> Path:
    path = Path(os.path.abspath(path))
    if not path.is_file() or (executable and not os.access(path, os.X_OK)):
        raise SetupError(f"missing {description}: {path}")
    return path


def run_command(command: list[str], timeout: int) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
            text=True,
        )
    except subprocess.TimeoutExpired as error:
        output = error.stdout or ""
        if isinstance(output, bytes):
            output = output.decode(errors="replace")
        return subprocess.CompletedProcess(command, 124, output)


def load_manifest(path: Path) -> dict:
    document = yaml.safe_load(path.read_text())
    if not isinstance(document, dict) or \
            document.get("schema") != "gem5-programs-v1":
        raise SetupError(f"{path}: expected schema gem5-programs-v1")
    programs = document.get("programs")
    exclusions = document.get("exclusions")
    if not isinstance(programs, list) or not programs:
        raise SetupError(f"{path}: programs must be a non-empty list")
    if not isinstance(exclusions, list):
        raise SetupError(f"{path}: exclusions must be a list")

    selection = document.get("selection") or {}
    discovered = {
        item.relative_to(ROOT).as_posix()
        for pattern in selection.get("source_globs", [])
        for item in ROOT.glob(pattern)
        if item.is_file()
    }
    declared = {
        entry["source"] for entry in programs
    } | {
        source
        for entry in programs
        for source in entry.get("extra_sources", [])
    } | {
        entry["source"] for entry in exclusions
    }
    if discovered != declared:
        missing = sorted(discovered - declared)
        unknown = sorted(declared - discovered)
        raise SetupError(
            f"{path}: E2E inventory is not closed; "
            f"unclassified={missing}, unknown={unknown}"
        )
    if any(not entry.get("reason") for entry in exclusions):
        raise SetupError(f"{path}: every exclusion needs a reason")
    for entry in programs:
        for key in ("name", "category", "source", "build",
                    "expected_exit", "oracle"):
            if key not in entry:
                raise SetupError(f"{path}: program lacks {key}: {entry}")
    return document


def expand_e2e_cases(document: dict, profile: str) -> list[dict]:
    cases = []
    for program in document["programs"]:
        opts = program.get("opts", [""])
        for opt in opts:
            suffix = f"-{opt}" if opt else ""
            cases.append({
                **program,
                "suite": "e2e",
                "case": f"e2e/{program['name']}{suffix}",
                "opt": opt,
            })
    if profile == "full":
        return sorted(cases, key=lambda case: case["case"])

    representatives = {}
    for case in sorted(cases, key=lambda item: item["case"]):
        representatives.setdefault(case["category"], case)
    if not representatives:
        raise SetupError("representative E2E set is empty")
    return sorted(representatives.values(), key=lambda case: case["case"])


def expand_embench_cases(document: dict, profile: str,
                         embench_src: Path) -> list[dict]:
    selection = document.get("selection") or {}
    overrides = selection.get("embench_correctness_overrides")
    required_overrides = {"WARMUP_HEAT", "LOCAL_SCALE_FACTOR"}
    if not isinstance(overrides, dict) or \
            set(overrides) != required_overrides or \
            any(not isinstance(value, int) or value < 0
                for value in overrides.values()):
        raise SetupError(
            "manifest selection.embench_correctness_overrides must contain "
            "non-negative integer WARMUP_HEAT and LOCAL_SCALE_FACTOR"
        )
    if not selection.get("embench_override_reason"):
        raise SetupError(
            "manifest selection.embench_override_reason must be non-empty"
        )
    source_root = embench_src / "src"
    if not source_root.is_dir():
        raise SetupError(
            f"missing Embench source root: {source_root}; run make fetch"
        )
    benchmarks = sorted(
        entry.name for entry in source_root.iterdir()
        if entry.is_dir() and list(entry.glob("*.c"))
    )
    if not benchmarks:
        raise SetupError(f"no Embench benchmarks under {source_root}")
    if profile == "representative":
        scales = {}
        for benchmark in benchmarks:
            matches = [
                int(match.group(1))
                for source in (source_root / benchmark).glob("*.c")
                if (match := re.search(
                    r"(?m)^#define LOCAL_SCALE_FACTOR\s+(\d+)\s*$",
                    source.read_text(),
                ))
            ]
            if len(matches) != 1:
                raise SetupError(
                    f"{benchmark}: expected one LOCAL_SCALE_FACTOR, "
                    f"found {len(matches)}"
                )
            scales[benchmark] = matches[0]
        minimum = min(scales.values())
        benchmarks = [
            benchmark for benchmark in benchmarks
            if scales[benchmark] == minimum
        ]
    key = "embench_full_opts" if profile == "full" \
        else "embench_representative_opts"
    opts = selection.get(key)
    if not isinstance(opts, list) or not opts:
        raise SetupError(f"manifest selection.{key} must be non-empty")
    return [{
        "suite": "embench",
        "case": f"embench/{benchmark}-{opt}",
        "name": benchmark,
        "category": benchmark,
        "opt": opt,
        "expected_exit": 0,
        "oracle": "Embench verify_benchmark via support/main.c return !correct",
        "build": "embench",
        "correctness_overrides": overrides,
    } for opt in opts for benchmark in benchmarks]


def compile_one(command: list[str], commands: list[list[str]],
                timeout: int = 60) -> None:
    commands.append(command)
    result = run_command(command, timeout)
    if result.returncode:
        detail = result.stdout.strip()[-2000:]
        raise RuntimeError(
            f"build command rc={result.returncode}: {' '.join(command)}"
            + (f"\n{detail}" if detail else "")
        )


def assembly_input(source: Path, outdir: Path, name: str) -> Path:
    """Materialize comment-free assembly for old and new installed parsers."""
    output = outdir / name
    lines = []
    for line in source.read_text().splitlines():
        lines.append(line.split("@@", 1)[0].rstrip())
    output.write_text("\n".join(lines) + "\n")
    return output


def wrap_raw_elf(payload: bytes) -> bytes:
    offset = 0x1000
    ident = b"\x7fELF" + bytes((2, 2, 1, 0)) + b"\0" * 8
    header = ident + struct.pack(
        ">HHIQQQIHHHHHH",
        2, EM_DADAO, 1, RAM_BASE, 64, 0, 1, 64, 56, 1, 0, 0, 0,
    )
    program = struct.pack(
        ">IIQQQQQQ",
        1, 7, offset, RAM_BASE, RAM_BASE, len(payload), len(payload), 0x10000,
    )
    return header + program + b"\0" * (offset - len(header) - len(program)) \
        + payload


def build_e2e(case: dict, outdir: Path, tools: dict,
              commands: list[list[str]]) -> Path:
    source = ROOT / case["source"]
    build = case["build"]
    crt0 = outdir / "crt0.o"
    crt0_source = assembly_input(tools["crt0"], outdir, "crt0.s")
    compile_one([
        str(tools["llvm_mc"]), "--triple=dadao-unknown-elf",
        "-filetype=obj", str(crt0_source), "-o", str(crt0),
    ], commands)

    if build == "c-elf":
        objects = []
        sources = [source] + [
            ROOT / item for item in case.get("extra_sources", [])
        ]
        for index, item in enumerate(sources):
            obj = outdir / f"source-{index}.o"
            if item.suffix == ".c":
                compile_one([
                    str(tools["clang"]), "-target", "dadao-unknown-elf",
                    "-nostdlib", f"-{case['opt']}", "-x", "c", "-c",
                    str(item), "-o", str(obj),
                ], commands)
            else:
                asm_source = assembly_input(
                    item, outdir, f"source-{index}.s"
                )
                compile_one([
                    str(tools["llvm_mc"]), "--triple=dadao-unknown-elf",
                    "-filetype=obj", str(asm_source), "-o", str(obj),
                ], commands)
            objects.append(obj)
        elf = outdir / "program.elf"
        compile_one([
            str(tools["ld"]), "-T", str(tools["linker"]), str(crt0),
            *(str(item) for item in objects), "-o", str(elf),
        ], commands)
        return elf

    obj = outdir / "program.o"
    asm_source = assembly_input(source, outdir, "program.s")
    compile_one([
        str(tools["llvm_mc"]), "--triple=dadao-unknown-elf",
        "-filetype=obj", str(asm_source), "-o", str(obj),
    ], commands)
    if build == "asm-elf":
        elf = outdir / "program.elf"
        compile_one([
            str(tools["ld"]), "-T", str(tools["linker"]), str(crt0),
            str(obj), "-o", str(elf),
        ], commands)
        return elf
    if build == "asm-raw":
        binary = outdir / "program.bin"
        compile_one([
            str(tools["objcopy"]), "-O", "binary", "--only-section=.text",
            str(obj), str(binary),
        ], commands)
        elf = outdir / "program.elf"
        elf.write_bytes(wrap_raw_elf(binary.read_bytes()))
        return elf
    raise RuntimeError(f"unknown E2E build kind {build!r}")


def build_embench(case: dict, outdir: Path, tools: dict,
                  embench_src: Path, commands: list[list[str]]) -> Path:
    opt = case["opt"]
    bench = case["name"]
    overrides = case["correctness_overrides"]
    flags = [
        "-target", "dadao-unknown-elf", f"-{opt}", "-ffreestanding",
        "-fno-builtin", "-std=gnu99",
        f"-DWARMUP_HEAT={overrides['WARMUP_HEAT']}",
        "-DGLOBAL_SCALE_FACTOR=1",
    ]
    include_dirs = [
        ROOT / "tests/scripts/embench_include",
        embench_src / "support",
        embench_src / "examples/dadao",
        embench_src / "src" / bench,
    ]
    includes = [
        value for directory in include_dirs
        for value in ("-I", str(directory))
    ]
    sources = [
        embench_src / "support/main.c",
        embench_src / "support/beebsc.c",
        embench_src / "examples/dadao/boardsupport.c",
        *sorted((embench_src / "src" / bench).glob("*.c")),
    ]
    compile_sources = []
    scale_overrides = 0
    for index, source in enumerate(sources):
        text = source.read_text()
        reduced, count = re.subn(
            r"(?m)^#define LOCAL_SCALE_FACTOR\s+\d+\s*$",
            "#define LOCAL_SCALE_FACTOR "
            f"{overrides['LOCAL_SCALE_FACTOR']}",
            text,
        )
        scale_overrides += count
        if count:
            generated = outdir / f"reduced-{index}.c"
            generated.write_text(reduced)
            compile_sources.append(generated)
        else:
            compile_sources.append(source)
    if scale_overrides != 1:
        raise RuntimeError(
            f"{bench}: expected one LOCAL_SCALE_FACTOR definition, "
            f"found {scale_overrides}"
        )
    objects = []
    for index, source in enumerate(compile_sources):
        obj = outdir / f"source-{index}.o"
        compile_one([
            str(tools["clang"]), *flags, *includes, "-c", str(source),
            "-o", str(obj),
        ], commands)
        objects.append(obj)

    runtime = outdir / "embench-runtime.o"
    compile_one([
        str(tools["clang"]), "-target", "dadao-unknown-elf", f"-{opt}",
        "-ffreestanding", "-fno-builtin", "-std=gnu99",
        "-I", str(ROOT / "tests/scripts/embench_include"),
        "-c", str(ROOT / "tests/scripts/embench_runtime.c"),
        "-o", str(runtime),
    ], commands)
    objects.append(runtime)

    memory = outdir / "memory-runtime.o"
    compile_one([
        str(tools["llc"]), "-march=dadao", "-O0", "-filetype=obj",
        str(ROOT / "tests/scripts/dadao_mem_runtime.ll"), "-o", str(memory),
    ], commands)
    objects.append(memory)

    crt0 = outdir / "crt0.o"
    crt0_source = assembly_input(tools["crt0"], outdir, "crt0.s")
    compile_one([
        str(tools["llvm_mc"]), "--triple=dadao-unknown-elf",
        "-filetype=obj", str(crt0_source), "-o", str(crt0),
    ], commands)
    objects.insert(0, crt0)

    elf = outdir / "program.elf"
    compile_one([
        str(tools["ld"]), "-T", str(tools["linker"]),
        *(str(item) for item in objects), "-o", str(elf),
    ], commands)
    return elf


def run_gem5(case: dict, elf: Path, tools: dict, outdir: Path,
             timeout: int, ticks: int, *, drop_exit=False) -> tuple[dict, str]:
    command = [
        str(tools["gem5"]), "--outdir", str(outdir / "m5out"),
        str(ROOT / "tests/gem5/machine_fixture.py"),
        "--rom", str(tools["bootrom"]), "--application", str(elf),
        "--files-root", f"{outdir}{os.sep}", "--cmd-line", case["case"],
        "--expected", "{}", "--ticks", str(ticks),
    ]
    started = time.monotonic()
    result = run_command(command, timeout)
    elapsed = time.monotonic() - started
    match = RESULT_RE.search(result.stdout)
    actual = {
        "command": command,
        "command_exit": result.returncode,
        "event_cause": match.group(1) if match else None,
        "event_code": int(match.group(2)) if match else None,
        "pc": int(match.group(3), 0) if match else None,
        "mode": int(match.group(4)) if match else None,
        "current_cfx": int(match.group(5)) if match else None,
        "elapsed_seconds": round(elapsed, 6),
    }
    if drop_exit:
        actual["event_code"] = None
    return actual, result.stdout


def differences(expected: dict, actual: dict) -> dict:
    delta = {}
    if actual["command_exit"] != 0:
        delta["command_exit"] = {
            "expected": 0, "actual": actual["command_exit"],
        }
    for key, value in expected.items():
        observed = actual.get(key)
        if key == "event_cause":
            matches = observed is not None and value in observed
        else:
            matches = observed == value
        if not matches:
            delta[key] = {"expected": value, "actual": observed}
    return delta


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("representative", "full"),
                        default="representative")
    parser.add_argument("--suite", choices=("all", "e2e", "embench"),
                        default="all")
    parser.add_argument("--manifest", type=Path,
                        default=ROOT / "tests/gem5/programs.yaml")
    parser.add_argument("--gem5", type=Path,
                        default=ROOT / ".work/source/gem5/build/DADAO/gem5.opt")
    parser.add_argument("--bootrom", type=Path,
                        default=dadao_paths.test_artifacts_dir()
                        / "bootrom/bootrom.bin")
    parser.add_argument("--embench-src", type=Path,
                        default=ROOT / ".work/source/embench-iot")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--ticks", type=int, default=1_000_000_000_000)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--inject-result", action="store_true",
                        help="corrupt the first expected guest exit")
    parser.add_argument("--inject-drop-exit", action="store_true",
                        help="simulate a swallowed first guest exit result")
    args = parser.parse_args()

    try:
        manifest = load_manifest(args.manifest.resolve())
        tools = {
            "gem5": require_file(args.gem5, "gem5 binary", executable=True),
            "bootrom": require_file(args.bootrom, "boot ROM"),
            "clang": require_file(TOOLCHAIN_BIN / "clang", "clang",
                                  executable=True),
            "llc": require_file(TOOLCHAIN_BIN / "llc", "llc",
                                executable=True),
            "llvm_mc": require_file(TOOLCHAIN_BIN / "llvm-mc", "llvm-mc",
                                    executable=True),
            "objcopy": require_file(TOOLCHAIN_BIN / "llvm-objcopy",
                                    "llvm-objcopy", executable=True),
            "ld": require_file(TOOLCHAIN_BIN / "ld.lld", "ld.lld",
                               executable=True),
            "crt0": require_file(ROOT / "tests/scripts/codegen_crt0.s",
                                 "crt0 source"),
            "linker": require_file(ROOT / "tests/scripts/dadao.lds",
                                   "linker script"),
        }
        cases = []
        if args.suite in {"all", "e2e"}:
            cases += expand_e2e_cases(manifest, args.profile)
        if args.suite in {"all", "embench"}:
            cases += expand_embench_cases(
                manifest, args.profile, args.embench_src.resolve()
            )
        if not cases:
            raise SetupError("selected program set is empty")
    except (OSError, SetupError, KeyError, TypeError, ValueError) as error:
        print(f"gem5-programs: setup error: {error}", file=sys.stderr)
        return 2

    build_root = ARTIFACTS / "build" / args.profile
    run_root = ARTIFACTS / "runs" / args.profile
    shutil.rmtree(build_root, ignore_errors=True)
    shutil.rmtree(run_root, ignore_errors=True)
    build_root.mkdir(parents=True)
    run_root.mkdir(parents=True)
    results = []
    built = []
    for index, case in enumerate(cases):
        case_dir = build_root / f"{index:03d}"
        case_dir.mkdir()
        commands = []
        record = {
            "case": case["case"],
            "suite": case["suite"],
            "category": case["category"],
            "oracle": case["oracle"],
            "expected": {
                "event_cause": "semi:ADP_Stopped_ApplicationExit",
                "event_code": int(case["expected_exit"]),
                "mode": 0,
                "current_cfx": 0,
            },
            "build_commands": commands,
        }
        if args.inject_result and index == 0:
            record["expected"]["event_code"] = \
                (record["expected"]["event_code"] + 1) & 0xff
        try:
            if case["suite"] == "e2e":
                elf = build_e2e(case, case_dir, tools, commands)
            else:
                elf = build_embench(
                    case, case_dir, tools, args.embench_src.resolve(), commands
                )
            built.append(case["case"])
            actual, output = run_gem5(
                case, elf, tools, run_root / f"{index:03d}",
                args.timeout, args.ticks,
                drop_exit=args.inject_drop_exit and index == 0,
            )
            record["artifact"] = str(elf)
            record["actual"] = actual
            record["delta"] = differences(record["expected"], actual)
            record["status"] = "pass" if not record["delta"] else "fail"
            if record["delta"]:
                record["output_tail"] = output[-3000:]
        except (OSError, RuntimeError) as error:
            record["actual"] = None
            record["delta"] = {"build": {"expected": "success",
                                           "actual": str(error)}}
            record["status"] = "fail"
        results.append(record)
        print(
            f"[{record['status'].upper()}] {case['case']} "
            f"expected={record['expected']['event_code']} "
            f"actual={None if record['actual'] is None else record['actual']['event_code']}",
            flush=True,
        )

    planned = [case["case"] for case in cases]
    closure = built == planned
    if not closure:
        print(
            f"[FAIL] build closure: planned={len(planned)} built={len(built)}",
            file=sys.stderr,
        )

    repeat = {"status": "not-run"}
    passing = [
        (case, result) for case, result in zip(cases, results)
        if result["status"] == "pass"
    ]
    if passing:
        case, baseline = passing[0]
        repeat_actual, repeat_output = run_gem5(
            case, Path(baseline["artifact"]), tools, run_root / "repeat",
            args.timeout, args.ticks,
        )
        stable_fields = ("event_cause", "event_code", "pc", "mode",
                         "current_cfx")
        repeat_delta = {
            field: {
                "first": baseline["actual"][field],
                "second": repeat_actual[field],
            }
            for field in stable_fields
            if baseline["actual"][field] != repeat_actual[field]
        }
        repeat = {
            "case": case["case"],
            "status": "pass" if not repeat_delta else "fail",
            "delta": repeat_delta,
            "actual": repeat_actual,
        }
        if repeat_delta:
            repeat["output_tail"] = repeat_output[-3000:]
        print(f"[{repeat['status'].upper()}] deterministic-repeat "
              f"{case['case']}")

    failed = [record for record in results if record["status"] != "pass"]
    ok = closure and not failed and repeat.get("status") == "pass"
    report = {
        "schema": "gem5-program-results-v1",
        "profile": args.profile,
        "suite": args.suite,
        "selection": manifest["selection"],
        "exclusions": manifest["exclusions"],
        "summary": {
            "planned": len(planned),
            "built": len(built),
            "passed": len(results) - len(failed),
            "failed": len(failed),
            "closure": closure,
            "status": "pass" if ok else "fail",
        },
        "deterministic_repeat": repeat,
        "results": results,
    }
    report_path = args.report or ARTIFACTS / f"{args.profile}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"gem5-programs: {report['summary']['status'].upper()} "
        f"{report['summary']['passed']}/{len(results)} "
        f"profile={args.profile} report={report_path}"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
