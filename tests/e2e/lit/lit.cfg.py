# -*- Python -*-
#
# lit configuration for DADAO E2E tests.
#
# This config locates llvm-mc/llvm-objcopy/qemu-system-dadao (the install-root
# host toolchain bin by default) and the ROM trampoline binary.
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

# Resolve the repo root (the dir holding the install-dirs manifest) and the
# single-source-of-truth path module (ADR-0016 D7), used both to locate the
# tools and to place lit's scratch output.
here = os.path.dirname(os.path.abspath(__file__))
root = here
while (root != os.path.dirname(root)
       and not os.path.isfile(os.path.join(root, 'manifests',
                                           'install-dirs.lock.toml'))):
    root = os.path.dirname(root)
sys.path.insert(0, os.path.join(root, 'tools', 'infra'))
import paths as dadao_paths

# Locate tools: prefer config.llvm_tools_dir (set by a site config) and the
# LLVM_TOOLS_DIR env override; otherwise default to the install root's host
# toolchain bin (ADR-0016 D9).
tools_dir = getattr(config, 'llvm_tools_dir', None)
if not tools_dir:
    tools_dir = os.environ.get('LLVM_TOOLS_DIR', '')
if not tools_dir:
    candidate = str(dadao_paths.host_toolchain_bin())
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
clang = os.path.join(tools_dir, "clang")
file_check = os.path.join(tools_dir, "FileCheck")

config.substitutions.append(("%llvm_mc", llvm_mc))
config.substitutions.append(("%llvm_objcopy", llvm_objcopy))
config.substitutions.append(("%clang", clang))
config.substitutions.append(("%FileCheck", file_check))

# Locate qemu-system-dadao.  In the install root it sits in the same bin/ as the
# other host tools (ADR-0016 D4); when tools_dir is an LLVM build tree's bin/ it
# is the sibling qemu build tree instead.
qemu_bin = os.path.join(tools_dir, "qemu-system-dadao")
if not os.path.isfile(qemu_bin):
    qemu_bin = os.path.join(os.path.dirname(tools_dir), "qemu",
                            "qemu-system-dadao")
config.substitutions.append(("%qemu", os.path.abspath(qemu_bin)))

# Locate trampoline.bin: <repo>/tests/scripts/trampoline.bin
trampoline = os.path.normpath(os.path.join(here, '..', '..', 'scripts',
                                           'trampoline.bin'))
config.substitutions.append(("%trampoline", trampoline))

# Locate e2e source directory: <repo>/tests/e2e/ (this config lives in
# tests/e2e/lit/, so the source dir is its parent).
e2e_dir = os.path.normpath(os.path.join(here, '..'))
config.substitutions.append(("%e2e_dir", e2e_dir))

# test_exec_root: lit's scratch output goes under the SDK test-artifacts root
# (.dadao/tests/lit-output/<name>, ADR-0016 D6), resolved through
# tools/infra/paths.py (D7), so tests never pollute the source tree.
config.test_exec_root = str(dadao_paths.test_artifacts_dir() / "lit-output" / config.name)
os.makedirs(config.test_exec_root, exist_ok=True)
