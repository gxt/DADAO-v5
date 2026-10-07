# -*- Python -*-
#
# lit configuration for DADAO MC tests.
#
# This config locates the llvm-mc/llvm-objdump/llvm-readobj/FileCheck/not binaries
# (the install-root host toolchain bin by default).
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

# Locate tools: prefer config.llvm_tools_dir (set by a site config) and the
# LLVM_TOOLS_DIR env override; otherwise default to the install root's host
# toolchain bin (ADR-0016 D9), resolved through the single source of truth
# (D7, tools/infra/paths.py) rather than a hardcoded build path.
tools_dir = getattr(config, 'llvm_tools_dir', None)
if not tools_dir:
    tools_dir = os.environ.get('LLVM_TOOLS_DIR', '')
if not tools_dir:
    # Walk up to the repo root (the dir holding the install-dirs manifest).
    here = os.path.dirname(os.path.abspath(__file__))
    root = here
    while (root != os.path.dirname(root)
           and not os.path.isfile(os.path.join(root, 'manifests',
                                               'install-dirs.lock.toml'))):
        root = os.path.dirname(root)
    sys.path.insert(0, os.path.join(root, 'tools', 'infra'))
    import paths as dadao_paths
    candidate = str(dadao_paths.host_toolchain_bin())
    if os.path.isdir(candidate):
        tools_dir = candidate

if not tools_dir:
    sys.exit("lit.cfg.py: could not locate LLVM tools directory; "
             "set LLVM_TOOLS_DIR to the directory containing llvm-mc, "
             "or run 'make install-host' first")

# Ensure absolute paths so lit's internal shell can find the tools.
tools_dir = os.path.abspath(tools_dir)
llvm_mc = os.path.join(tools_dir, "llvm-mc")
llvm_objdump = os.path.join(tools_dir, "llvm-objdump")
llvm_readobj = os.path.join(tools_dir, "llvm-readobj")
file_check = os.path.join(tools_dir, "FileCheck")
not_tool = os.path.join(tools_dir, "not")

config.substitutions.append(("%llvm_mc", llvm_mc))
config.substitutions.append(("%llvm_objdump", llvm_objdump))
config.substitutions.append(("%llvm_readobj", llvm_readobj))
config.substitutions.append(("%FileCheck", file_check))
config.substitutions.append(("%not", not_tool))

# test_exec_root: put lit's scratch output beside tools_dir (under the install
# root by default), which is gitignored, so tests never pollute the source tree.
build_root = os.path.dirname(tools_dir)  # <prefix> when tools_dir = <prefix>/bin
config.test_exec_root = os.path.join(build_root, "test-output", config.name)
os.makedirs(config.test_exec_root, exist_ok=True)
