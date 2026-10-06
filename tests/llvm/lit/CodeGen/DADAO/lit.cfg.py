# -*- Python -*-
#
# lit configuration for DADAO CodeGen (L2 structural) tests.
#
# Placeholder suite: it currently holds no tests (see README.md).  It is NOT
# wired into `make check-lit`.  The first real L2 test should add the tool
# substitutions (%llc, %FileCheck, ...) and a build-tree `test_exec_root`,
# mirroring tests/llvm/lit/MC/DADAO/lit.cfg.py.

import os
import lit.formats

# name: The name of this test suite.
config.name = "DADAO-CodeGen"

# test_source_root: The root path where tests are located.
config.test_source_root = os.path.dirname(__file__)

# suffixes: A list of file extensions to treat as test files.
config.suffixes = [".ll"]

# Use ShTest format (standard for llc/FileCheck-driven tests).
config.test_format = lit.formats.ShTest(False)
