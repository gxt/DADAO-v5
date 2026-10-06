# -*- Python -*-
#
# lit configuration for DADAO CodeGen (L2 structural) tests.
#
# The suite drives `llc` and checks its output with `FileCheck`; the two vector
# kinds are LLVM IR (`.ll`) and post-RA MIR (`.mir`).  Mirrors
# tests/llvm/lit/MC/DADAO/lit.cfg.py.
#
# It is wired into `make check-lit` by INTEG-016t (this also resolves ISS-152).

import os
import sys
import lit.util
import lit.formats

# name: The name of this test suite.
config.name = "DADAO-CodeGen"

# test_source_root: The root path where tests are located.
config.test_source_root = os.path.dirname(__file__)

# suffixes: `.ll` (IR -> llc) and `.mir` (MIR -> llc -run-pass=...).
config.suffixes = [".ll", ".mir"]

# Use ShTest format (standard for llc/FileCheck-driven tests).
config.test_format = lit.formats.ShTest(False)

# Locate tools: prefer config.llvm_tools_dir (set by the site config when
# running via llvm-lit from the build tree), fall back to LLVM_TOOLS_DIR env.
tools_dir = getattr(config, 'llvm_tools_dir', None)
if not tools_dir:
    tools_dir = os.environ.get('LLVM_TOOLS_DIR', '')
if not tools_dir:
    # Infer from this file's location: tests/llvm/lit/CodeGen/DADAO/ is 5 levels
    # deep from the repo root.
    here = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.normpath(os.path.join(here, '..', '..', '..', '..',
                                              '..', '.work', 'build', 'llvm',
                                              'bin'))
    if os.path.isdir(candidate):
        tools_dir = candidate

if not tools_dir:
    sys.exit("lit.cfg.py: could not locate LLVM tools directory; "
             "set LLVM_TOOLS_DIR to the directory containing llc, "
             "or run via llvm-lit from the build tree")

# Ensure absolute paths so lit's internal shell can find the tools.
tools_dir = os.path.abspath(tools_dir)
llc = os.path.join(tools_dir, "llc")
file_check = os.path.join(tools_dir, "FileCheck")
not_tool = os.path.join(tools_dir, "not")

config.substitutions.append(("%llc", llc))
config.substitutions.append(("%FileCheck", file_check))
config.substitutions.append(("%not", not_tool))

# test_exec_root: put lit's scratch output in the LLVM build tree so that
# running tests never pollutes the source / git-tracked tree.
# tools_dir is <build>/bin, so the build root is its parent.
build_root = os.path.dirname(tools_dir)  # <build>
config.test_exec_root = os.path.join(build_root, "test-output", config.name)
os.makedirs(config.test_exec_root, exist_ok=True)
