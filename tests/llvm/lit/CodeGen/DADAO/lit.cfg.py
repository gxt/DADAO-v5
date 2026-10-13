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

# Locate tools: prefer config.llvm_tools_dir (set by the site config) and the
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
             "set LLVM_TOOLS_DIR to the directory containing llc, "
             "or run 'make install-host' first")

# Ensure absolute paths so lit's internal shell can find the tools.
tools_dir = os.path.abspath(tools_dir)
llc = os.path.join(tools_dir, "llc")
file_check = os.path.join(tools_dir, "FileCheck")
not_tool = os.path.join(tools_dir, "not")

config.substitutions.append(("%llc", llc))
config.substitutions.append(("%FileCheck", file_check))
config.substitutions.append(("%not", not_tool))

# test_exec_root: lit's scratch output goes under the SDK test-artifacts root
# (.dadao/tests/lit-output/<name>, ADR-0016 D6), resolved through
# tools/infra/paths.py (D7), so tests never pollute the source tree.
config.test_exec_root = str(dadao_paths.test_artifacts_dir() / "lit-output" / config.name)
os.makedirs(config.test_exec_root, exist_ok=True)
