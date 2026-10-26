#!/usr/bin/env python3
"""薄 wrapper（TESTCASES-072t）：真实实现在 `tools/testcases/lib/test_harness_exit_path.py`。

旧命令行 `python3 tests/scripts/test_harness_exit_path.py ...` 仍等价可用（本文件只转发，不含实现）。
迁移去向见 `docs/Process-09` §6；删除旧入口见 `TESTCASES-076t`。
"""

import os
import runpy
import sys

_IMPL = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "tools", "testcases", "lib", "test_harness_exit_path.py"))

sys.path.insert(0, os.path.dirname(_IMPL))
runpy.run_path(_IMPL, run_name="__main__")
