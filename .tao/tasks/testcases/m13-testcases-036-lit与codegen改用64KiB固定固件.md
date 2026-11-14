# m13-testcases-036: lit E2E 与 codegen E2E 改用 64 KiB 固定固件（去 legacy trampoline）

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-qemu-011`（`-bios` 只收 64 KiB 固定固件，已合入/待合入）
**可并行分片**：否（同一批测试入口）
**预估**：1–2 h
**状态**：待开始

## 背景（2026-11-14 实测）

- `m13-qemu-011` 把 Tiny 的 `-bios` 收紧为「必须恰好 64 KiB，与 `bootrom-image` 同一固定固件」（`spec/Machine-v5 §6`；用户 2026-11-13 裁定），并删掉 Tiny 的 flat trampoline 旁路。
- 但两条 E2E 通路仍在用旧的 56 B `tools/testcases/lib/trampoline.bin` 当 `-bios`：
  - `tests/unit/llvm/e2e/lit/` 的 **5 个**测试（`smoke_add`/`smoke_arith`/`smoke_fp`/`smoke_jump`/`tool_env`）用 `-bios %trampoline -kernel %t.raw`（live count 现场核）；
  - `tools/testcases/unit/run_codegen_e2e.py` 用 `--trampoline` 默认 `tools/testcases/lib/trampoline.bin` 作 `-bios`（L100/L329）。
- 后果（现场）：`make check-lit` 4 FAIL、`make test-codegen` 19/19 FAIL，QEMU 报 `-bios … is 56 bytes; the Machine-v5-Tiny -bios path accepts only the fixed 65536-byte BootROM firmware`。
- 注意：安装根里的 qemu 已被刷新为含该收紧的版本（事故记录见 `ISS-373` 复核），这不是「安装根坏了」，而是**测试侧落后于 spec**。

## 目标

1. **lit E2E**：`%trampoline` 不再用于 `-bios`；改用已在 `lit.cfg.py` 里定义的 `%bootrom`（`bootrom/tiny/bootrom_tiny.bin`，64 KiB）。`-kernel %t.raw` 的 raw 应用路径**保留**（`-bios` 固定固件 + raw `-kernel` 仍是契约路径）。`tool_env.test` 的存在性检查同样改成 `%bootrom`。
2. **codegen E2E**：`run_codegen_e2e.py` 的 `-bios` 改用固定固件（`tools/testcases/lib/` 或 `dadao_paths` 的 bootrom 路径，**复用既有解析方式**，不要新造第二套）；`--trampoline` 参数与 `trampoline.bin` 依赖删除或改名（若外部脚本引用，保留兼容别名并在帮助里标注 deprecated）。
3. **`gen_trampoline.py` 的处置**：其「把 hmon 向量指到不可达地址」的第 0 步属 legacy 口径（`m13-testcases-034` 已迁 oracle）。本任务**只**处理测试入口改用固定固件；`gen_trampoline.py` 是否整体退役留给 `m13-testcases-030`，请在完成区写明边界。

## 验收（逐条给真实 rc）

1. `make check-lit` **rc=0**（现场例数；若仍有非本任务红，逐条归因并证明与本任务无关）。
2. `make test-codegen`（或 `check-unit` 中对应目标）**rc=0**，例数现场统计（原 19）。
3. **不得用「放宽 qemu」或「改安装根」凑绿**：`-bios` 仍必须是 64 KiB；核 QEMU 源码未改（`git diff` 无 `components/qemu/**`）。
4. 反例可达：把某个 lit 测试的 `%bootrom` 改回 `%trampoline` ⇒ 该例应红（贴注入→FAIL→还原→回绿，`cp`+md5）。
5. `check-lit-full` 不在本任务范围（opt-in）；`check-tests-index`/`check-case-ledger`/`check-no-residue` 不变。
6. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status -uall` 对账；`**状态**` → `待验收`；不改台账/`discussing.md`。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号）；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；**禁跑 `install-host` / `check-modules` / 真 `build-*`**（`check-lit`/`test-codegen` 依赖安装根里已有的二进制，直接跑即可；若缺 bootrom 用 `make build-bootrom`——该目标只产镜像、不装）。
3. 禁 `git checkout/restore/stash`；注入还原用 `cp`+md5。
4. 只改 `tests/unit/llvm/e2e/lit/**`、`tools/testcases/unit/run_codegen_e2e.py`、必要时 `tools/testcases/lib/**`（bootrom 路径解析复用）；**不改** `spec/`、`contracts/`、`components/**`、`tests/inst/**`。
5. 大文件落 `/tmp/opencode/m13-testcases-036/` 并测完即删。

## 待裁定

（实现中写）

## 审阅记录

（待填）
