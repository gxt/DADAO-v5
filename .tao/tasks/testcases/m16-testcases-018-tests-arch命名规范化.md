# m16-testcases-018: `tests/arch` 命名规范化整理

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m16-testcases-015`/`017` 已合入
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（用户 2026-11-22）

`tests/arch/` 下不要乱起名字、不要乱加脚本，尽量规范化。规范已写入 `tests/arch/README.md`「命名规范」；本任务把现有文件按规范整理。

## 要做

按 `tests/arch/README.md`「命名规范」：

1. **env 目录**：`common/env/{hmon,smon,umon}/` → `common/env-{hmon,smon,umon}/`；`common/env/env.lds` → `common/env.lds`；`common/env/README.md` → `common/env-README.md`；`common/env/MIGRATION.md` → `common/env-MIGRATION.md`。
2. **env 驱动**：`umon/check_mode_env.py` → `common/check_mode_env.py`（env 是跨 cfx 的）。
3. **body**：`umon/mode_regs.body.S` → `umon/umon_mode_regs.body.S`。
4. **ptw 载体**：`ptw/carrier_tlb.py` → `ptw/ptw_carrier_tlb.py`。
5. **扩展名**：`umon/m5_*.s`（10 个）→ `*.S`（统一大写）。
6. **引用同步**：`tests/arch.yaml`、`tests/arch/modes.yaml`、`tests/arch/expected.yaml`、`tests/arch/README.md`、`tests/arch/PLAN.md`、`tests/arch/run_arch.py`、`tests/arch/common/platform.py`、`Makefile`（`ARCH_PTW_CARRIER`）、`tools/testcases/arch/*` 的旧路径。
7. **禁止**：不新增 `data/`、不在 `tools/` 下加 arch 专用脚本。

## 不做

- 不改用例语义/期望/门控逻辑；
- 不重命名 bin/ELF/镜像 id（`arch-*` 保持不变）；
- 不改 QEMU/gem5/RTL。

## 约束

- 独立 `git worktree`；**不提交 git**；变更集限 `tests/arch/**`、`tests/arch.yaml`、`Makefile`、`tools/testcases/arch/**`、本任务书；
- 不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. 旧路径/旧文件名在可执行引用中 0 命中（历史任务书/归档除外）；
2. `python3 tests/arch/run_arch.py --self-test` rc=0；`make check-arch-smoke` rc=0；代表用例三模式各跑一次；
3. `check-tests-index`、`check-tasks`、`check-knowledge-refs` 记录 rc；
4. **可达 FAIL**：注入「保留旧路径引用」⇒ 判据红；`cp`+md5 还原回绿；`--inject` ≥2 路。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
