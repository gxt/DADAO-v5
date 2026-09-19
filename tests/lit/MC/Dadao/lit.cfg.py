# -*- Python -*-
#
# lit configuration for DADAO MC tests.
#
# This config locates the built llvm-mc and FileCheck binaries.
# When run via `llvm-lit`, config.llvm_tools_dir is set by the site config.
# When run standalone, set LLVM_TOOLS_DIR environment variable.

import os
import sys
import lit.util
import lit.formats

# name: The name of this test suite.
config.name = "DADAO-MC"

# test_source_root: The root path where tests are located.
config.test_source_root = os.path.dirname(__file__)

# suffixes: A list of file extensions to treat as test files.
config.suffixes = [".s"]

# Use ShTest format (standard for .s tests).
config.test_format = lit.formats.ShTest(False)

# Locate tools: prefer config.llvm_tools_dir (set by site config when running
# via llvm-lit from the build tree), fall back to LLVM_TOOLS_DIR env var.
tools_dir = getattr(config, 'llvm_tools_dir', None)
if not tools_dir:
    tools_dir = os.environ.get('LLVM_TOOLS_DIR', '')
if not tools_dir:
    # Try to infer from the location of this file: tests/lit/MC/Dadao/ is 4
    # levels deep from the repo root.
    here = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.join(here, '..', '..', '..', '..', '.work', 'build',
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
llvm_objdump = os.path.join(tools_dir, "llvm-objdump")
file_check = os.path.join(tools_dir, "FileCheck")

config.substitutions.append(("%llvm_mc", llvm_mc))
config.substitutions.append(("%llvm_objdump", llvm_objdump))
config.substitutions.append(("%FileCheck", file_check))

# test_exec_root: put lit's scratch output in the LLVM build tree so that
# running tests never pollutes the source / git-tracked tree.
# tools_dir is <build>/bin, so the build root is its parent.
build_root = os.path.dirname(tools_dir)  # <build>
config.test_exec_root = os.path.join(build_root, "test-output", config.name)
os.makedirs(config.test_exec_root, exist_ok=True)
