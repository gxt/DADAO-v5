# -*- Python -*-
#
# lit configuration for DADAO E2E tests.
#
# This config locates the built llvm-mc, llvm-objcopy, qemu-system-dadao,
# and the ROM trampoline binary.
# When run via `llvm-lit`, config.llvm_tools_dir is set by the site config.
# When run standalone, set LLVM_TOOLS_DIR environment variable.

import os
import sys
import lit.util
import lit.formats

# name: The name of this test suite.
config.name = "DADAO-E2E"

# test_source_root: The root path where tests are located.
config.test_source_root = os.path.dirname(__file__)

# suffixes: A list of file extensions to treat as test files.
config.suffixes = [".test"]

# Use ShTest format (standard for .test files).
config.test_format = lit.formats.ShTest(False)

# Locate tools: prefer config.llvm_tools_dir (set by site config when running
# via llvm-lit from the build tree), fall back to LLVM_TOOLS_DIR env var.
tools_dir = getattr(config, 'llvm_tools_dir', None)
if not tools_dir:
    tools_dir = os.environ.get('LLVM_TOOLS_DIR', '')
if not tools_dir:
    # Try to infer from the location of this file: tests/lit/E2E/ is 3
    # levels deep from the repo root.
    here = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.join(here, '..', '..', '..', '.work', 'build',
                             'llvm', 'bin')
    candidate = os.path.normpath(candidate)
    if os.path.isdir(candidate):
        tools_dir = candidate

if not tools_dir:
    sys.exit("lit.cfg.py: could not locate LLVM tools directory; "
             "set LLVM_TOOLS_DIR to the directory containing llvm-mc, "
             "or run via llvm-lit from the build tree")

# Ensure absolute paths so lit's internal shell can find the tools.
tools_dir = os.path.abspath(tools_dir)
llvm_mc = os.path.join(tools_dir, "llvm-mc")
llvm_objcopy = os.path.join(tools_dir, "llvm-objcopy")

config.substitutions.append(("%llvm_mc", llvm_mc))
config.substitutions.append(("%llvm_objcopy", llvm_objcopy))

# Locate qemu-system-dadao: relative to tools_dir (which is <build>/bin)
# QEMU is at <build>/../qemu/qemu-system-dadao or <repo>/.work/build/qemu/
qemu_dir = os.path.join(os.path.dirname(tools_dir), "qemu")
qemu_bin = os.path.join(qemu_dir, "qemu-system-dadao")
if not os.path.isfile(qemu_bin):
    # Try <repo>/.work/build/qemu/qemu-system-dadao
    here = os.path.dirname(os.path.abspath(__file__))
    qemu_bin = os.path.normpath(os.path.join(here, '..', '..', '..', '.work',
                                              'build', 'qemu',
                                              'qemu-system-dadao'))
config.substitutions.append(("%qemu", os.path.abspath(qemu_bin)))

# Locate trampoline.bin: <repo>/tests/scripts/trampoline.bin
here = os.path.dirname(os.path.abspath(__file__))
trampoline = os.path.normpath(os.path.join(here, '..', '..', 'scripts',
                                           'trampoline.bin'))
config.substitutions.append(("%trampoline", trampoline))

# Locate e2e source directory: <repo>/tests/e2e/
e2e_dir = os.path.normpath(os.path.join(here, '..', '..', 'e2e'))
config.substitutions.append(("%e2e_dir", e2e_dir))

# test_exec_root: put lit's scratch output in the LLVM build tree so that
# running tests never pollutes the source / git-tracked tree.
# tools_dir is <build>/bin, so the build root is its parent.
build_root = os.path.dirname(tools_dir)  # <build>
config.test_exec_root = os.path.join(build_root, "test-output", config.name)
os.makedirs(config.test_exec_root, exist_ok=True)
