# m16-testcases-024: `tests/arch` 收尾二（临时目录清理 + `check_ptw_rtl --mode`）

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m16-testcases-021`、`m16-testcases-022` 已合入
**可并行分片**：否（共享 `tests/arch/ptw/`、运行期证据脚本）
**预估**：1–1.5 h
**档位**：小改（复核 ≤20 min）
**状态**：待开始

## 背景

- `ISS-m16-007`：`m16-testcases-021` 证据脚本 `checks.py` 的 `a5`/`a8` 用 `tempfile.mkdtemp(dir=TMP)` 且**从不清理**；每次 `run.sh` 在运行期临时目录遗留约 300 MiB（A8 注入态 `flood.bin`），4 次全量后 952 MiB（`/tmp` 曾 82%）。
- `ISS-m16-010`：`tests/arch/ptw/check_ptw_rtl.py` **缺 `--mode`**，而 `modes.yaml` 声明 ptw 三模式 ⇒ `run_arch --cfx 4 --platforms chipyard` 15/15 报 `unrecognized arguments: --mode`（rc=1）；另外单平台 `run_arch`（只给 `--platforms chipyard`）会对未跑的 QEMU/gem5 腿报假"跨平台不一致"。

## 要做

1. **临时目录清理**：`checks.py` 的每个 `mkdtemp` 在断言完成/注入还原后 `shutil.rmtree`（异常路径也要清）；跑 4 次全量后临时目录残留应 ≈0；保留失败现场的开关（如 `KEEP_TMP=1`）并写进 README。
2. **`check_ptw_rtl --mode`**：接受 `--mode hmon|smon|umon`（与 `check_cache_rtl`/`check_hart_rtl` 同接口），按模式选择 `modes.yaml` 的 `cfx_access`；三模式均能跑（RTL 的 cfx4 若仍只 hmon，按 `DIV-09` 显式排除并给原因，不得静默）。
3. **单平台假不一致**：`run_arch.py` 在只给一个平台时，不应把未跑的腿当作"不一致"（按 `ISS-m16-010` 的记录，`ref` 空集导致 `ref_ok` 恒 false）；改为显式"单平台模式：仅本平台对照 expected"，或要求至少两平台。
4. **不回归**：`run_arch --cfx 4 --platforms qemu,gem5,chipyard` 恢复 rc=0（或按 gap 登记）；`check_ptw_rtl --selfcheck` 集合不变；`arch-cache/time/hart/pmem` 代表集不回归。

5. **证据脚本的健壮性（`m16-testcases-023` 复核 finding）**：① `run.sh` 的 `[ -x "$GEM5" ]` 只验可执行位，拦不住"可执行但截断的非 ELF"（22:57 曾出现 41.8 MB 半成品）⇒ 加 `file`/ELF magic 校验；② flake 重试计数会把"注入导致的 rc=77"也算成重试 ⇒ 重试只统计非注入轮；③ inventory 的收口注槽数（13→11）与现场核对后订正。

## 不做

- 不改 RTL/用例语义；
- 不修 `ISS-m16-011`（flake，另任务）。

## 约束

- 独立 `git worktree`；**不提交 git**；只动 `tests/arch/**`、`tools/testcases/arch/**`、运行期证据脚本、本任务书；
- 不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. 4 次全量后临时目录残留 ≈0（贴 `du` 前后）；
2. `run_arch --cfx 4 --platforms chipyard --mode {hmon,smon,umon}` 不再报 `--mode` 未知；三平台 `--cfx 4` rc=0 或 gap 登记；
3. **可达 FAIL ≥2**：注入"mkdtemp 不清理"、"把 `--mode` 去掉" ⇒ 红；`cp`+md5 还原回绿；
4. `check-tests-index`、`check-tasks`、`check-knowledge-refs`、`run_arch --self-test` 记录 rc。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
