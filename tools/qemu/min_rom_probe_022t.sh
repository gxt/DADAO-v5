#!/bin/bash
# 薄 wrapper（TESTCASES-073t）：真实实现在 tools/testcases/arch/min_rom_probe_022t.sh。
# 旧命令行 `bash tools/qemu/min_rom_probe_022t.sh` 仍等价可用（本文件只转发）。
# 删除旧入口见 TESTCASES-076t。

set -euo pipefail
exec bash "$(dirname "$0")/../testcases/arch/min_rom_probe_022t.sh" "$@"
