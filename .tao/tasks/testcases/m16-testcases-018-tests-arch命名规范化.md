# m16-testcases-018: `tests/arch` 命名规范化整理

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m16-testcases-015`/`017` 已合入
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：待验收

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

**测试结果**：`run.sh` 全绿（rc=0）：旧路径命中 0；`run_arch.py --self-test` PASS（26 case）；代表用例 `arch-umon-011` hmon/smon/umon 各 PASS；`make check-arch-smoke` PASS（10 smoke + 25 服务 + ptw 29/29）；`check-tests-index` rc=0（488 条）、`check-tasks` rc=0、`check-knowledge-refs` rc=0。

**修改文件**：
- 改名：`common/env/{hmon,smon,umon}/`→`common/env-{hmon,smon,umon}/`；`common/env/env.lds`→`common/env.lds`；`common/env/README.md`→`common/env-README.md`；`common/env/MIGRATION.md`→`common/env-MIGRATION.md`；`umon/check_mode_env.py`→`common/check_mode_env.py`；`umon/mode_regs.body.S`→`umon/umon_mode_regs.body.S`；`ptw/carrier_tlb.py`→`ptw/ptw_carrier_tlb.py`；`umon/m5_*.s`（10）→`m5_*.S`。
- 引用/代码：`Makefile`、`tests/arch.yaml`、`tests/arch/run_arch.py`、`tests/arch/common/platform.py`、`tests/arch/modes.yaml`、`tests/arch/umon/expected.yaml`、`tests/arch/ptw/{check_tlb.py,expected.yaml}`、`tests/arch/common/env/cfx_perm.inc`、`common/env-*/env.S`、`common/env.lds`、`umon/umon_mode_regs.body.S`、`tests/arch/README.md`、`PLAN.md`、`vast-arch-inventory.md`、`common/env-README.md`、`common/env-MIGRATION.md`、`tools/testcases/arch/run_m5_e2e.py`、本任务书。证据脚本在运行期目录（不入库）。

**验收结果**：`bash <运行期证据目录>/run.sh` → `RUN_RC=0`；注入 A（`tests/arch.yaml` 保留 `m5_semi_exit.s`）⇒ 旧路径扫描与 `check-tests-index` 均 rc=1，`cp`+md5 还原后回绿；注入 B（`Makefile` 的 `ARCH_PTW_CARRIER` 改回 `ptw/carrier_tlb.py`）⇒ 载体存在性与旧路径扫描均 rc=1，`cp`+md5 还原后回绿；`--inject` rc=0。

**新发现/坑**：
- 任务 1 未列 `common/env/cfx_perm.inc`，故 `common/env/` 保留该共享宏块；`-I` 仍为 `tests/arch/common/env`（`common/env/` 不再放 `env.S`）。若要求 `common/env/` 目录消失，需后续单独搬 `cfx_perm.inc` 并改 `-I`。
- 驱动搬到 `common/` 后，`run_arch.load_index` 需允许 `arch/common/` 并从 id 第二段派生 cfx 归属（`arch-umon-011`→`umon`）；`common/platform.py` 的 `_expected_yaml` 改用该逻辑目录，否则会找 `common/expected.yaml`。
- `check_mode_env.py` 上移一级后 `_ARCH`/`_REPO` 的 `parents` 索引恰好不变；`ENV_INC_DIR`（宏块 `-I`）与 `ENV_DIRS`（`env-<mode>/env.S`）已拆开。
- `run_m5_e2e.py` 的源文件过滤 `endswith(".s")` 随扩展名改名同步为 `.S`。
- 变更集外的旧路径引用仍在（见遗留），均为文档/历史，不影响可执行门控。

**遗留问题**：
- 变更集外的文档仍含旧名（未改）：`tests/shared/README.md`（`ptw/carrier_tlb.py`）、`tests/inst/inventory.md` 与 `tests/unit/llvm/lit/MC/DADAO/README-m5.md`（`m5_*.s`）、`components/qemu/changelog.md`（历史 changelog）、`.tao/knowledge/discussing.md`（旧 env 路径）；建议另立文档同步任务或在 `/complete` 更新知识库时一并处理。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 证据脚本「注入生效」仅看 `git diff` 非空，工作树本就脏 ⇒ 空注入可假绿 | ✅已修 | 注入后加「md5 必须变化 + 注入 token 必须在位 + `git diff` 含该文件」三重判据 | `run.sh --inject` rc=0；A/B 两路注入均先 FAIL 后回绿 |
| F2 `platform._expected_yaml` 用 `file` 第二段，搬 common 后会找 `common/expected.yaml` | ✅已修 | 改用 `case["cfx_dir"]`（缺省回退 `file` 第二段） | `--self-test` PASS；三模式 PASS |
| F3 `check_mode_env.py` 把宏块 `-I` 目录与 `env.S` 目录混用 | ✅已修 | 拆 `ENV_INC_DIR`（`common/env`）与 `ENV_DIRS`（`common/env-<mode>`） | `--selfcheck` PASS；三模式 PASS |
| F4 载体内部 usage/错误前缀仍写旧名 `carrier_tlb` | ✅已修 | 全文件同步为 `ptw_carrier_tlb`（保留 `_arch_ptw_carrier_tlb` 模块名） | `check_tlb --selfcheck` PASS；`check-arch-smoke` 29/29 |
| F5 `run_m5_e2e.py` 仍按 `.s` 过滤源文件 | ✅已修 | 过滤改 `.S` | `check-arch-smoke` 10 smoke 全 PASS |
| F6 README/PLAN/inventory/modes/env 文档/各 `.S` 头注释仍含旧路径 | ✅已修 | 逐文件同步新路径与新目录名 | 旧路径扫描 0 命中；`check-tests-index` rc=0 |
| F7 变更集外文档旧名（`tests/shared/README.md` 等） | ❌不修（变更集限） | 未动范围外文件 | 已在「遗留问题」登记，可执行引用扫描 0 命中 |

### 第 1 轮 reviewer 验收

**重跑**（worktree 根，reviewer 本人执行，不采信完成区）：
- `bash <运行期证据目录>/run.sh` ⇒ `RUN_RC=0`：10 项全 PASS（旧路径 0 命中、载体存在、`--self-test`、三模式 `arch-umon-011` QEMU、`make check-arch-smoke`、`check-tests-index`、`check-tasks`、`check-knowledge-refs`）+ 注入 A/B 各先 FAIL 后回绿。
- `bash <运行期证据目录>/run.sh --inject` ⇒ `INJECT_RC=0`（A 旧 `.s`：扫描 rc=1、`check-tests-index` rc=1；B 载体回退：存在性 rc=1、扫描 rc=1；两路还原 md5 对账一致后回绿）。
- 单项独立重跑：`run_arch.py --self-test` rc=0（`self-test: PASS`，含 `arch/common/check_mode_env.py` selfcheck）；`check_tests_index.py` rc=0（488 条）；`check_tasks.py` rc=0；`check_knowledge_refs.py` rc=0（0 悬空、0 运行期路径引用）。
- `make check-arch-smoke` 现场日志（时间戳=本轮）：`run_arch: PASS（10 case × 1 平台）`、`service coverage: all 25 service ids exercised`、`29/29 checks passed`。
- **独立注入 3 路**（`cp` 备份 + md5 对账，全程未用 git checkout/restore/stash）：
  - C `tests/arch.yaml` 回退 `m5_semi_exit.s` ⇒ `check-tests-index` rc=1（`file 不存在`）、`run.sh` rc=1；还原 md5 `b1d17796…` 一致 ⇒ 回绿 rc=0。
  - D `Makefile` 的 `ARCH_PTW_CARRIER` 回退旧载体 ⇒ `make check-arch-smoke` rc=2（`ERROR: tests/arch/ptw/carrier_tlb.py not found`）；还原 md5 一致。
  - E `check_mode_env.py` 的 `ENV_DIRS` 回退 `common/env/<mode>` ⇒ `run_arch.py --self-test` rc=1（驱动 selfcheck FAIL）；还原 md5 一致 ⇒ rc=0。

**hart/（021）引用同步**：`tests/arch/hart/` 三文件旧路径/旧 `.s` grep 0 命中（只含 `tests/shared/asm/signature.inc`）；`check_cfx15.py --root . --mode 3/2/0 --self-test` 三跑全 PASS；`llvm-mc -defsym TMODE=3 cfx15.S` rc=0 + `ld.lld -T cfx15.lds` rc=0（ELF 生成，`llvm-nm` rc=0）；`run_arch.py --list` 26 case 无 hart（021 未登记、与 README 声明一致，非本次回归）。

**语义不变**：10 个 `m5_*` 与 HEAD 逐字节比对，新名归一回旧名后 md5 全等（唯一差异 = 首行头注释文件名）；`umon_mode_regs.body.S`、`env-{h,s,u}mon/env.S`、`env.lds` 归一后全等；`ptw_carrier_tlb.py` 仅 `carrier_tlb:`→`ptw_carrier_tlb:` 错误前缀与 usage 行；`check_mode_env.py` 仅路径与 `ENV_INC_DIR`/`ENV_DIRS` 拆分；`arch.yaml` id 集不变（diff 仅 `file` 行）；`umon/expected.yaml` 仅 `sources` 改 `.S`；`Makefile` 仅 `ARCH_PTW_CARRIER` + 注释/echo 文案；`run_arch.py`/`platform.py` 仅 `cfx_dir` 派生与 `env-<mode>` 路径，门控断言未动。

**逐条核任务 1–7**：1 ✅ `common/env-{hmon,smon,umon}/`、`env.lds`、`env-README.md`、`env-MIGRATION.md` 均在；2 ✅ `common/check_mode_env.py`；3 ✅ `umon_mode_regs.body.S`；4 ✅ `ptw_carrier_tlb.py`；5 ✅ 10 个 `m5_*.S`；6 ✅（任务列的 `tests/arch/expected.yaml` 实不存在，现场只有 `expected-divergences.yaml` 与 `umon/`、`ptw/expected.yaml`，均无旧名）；7 ✅ 无 `data/`，`tools/` 仅改 `run_m5_e2e.py` 的 `.S` 过滤。

**遗留两条**：① `common/env/` 仅剩 `cfx_perm.inc`，`check_mode_env.py` 仍 `-I tests/arch/common/env`（`ENV_INC_DIR`）——属实、可接受；② 变更集外旧名确在（`tests/shared/README.md`、`tests/inst/inventory.md`、`tests/unit/llvm/lit/MC/DADAO/README-m5.md`、`components/qemu/changelog.md`、知识库），均为文档/历史，可执行引用 0 命中，受变更集约束未改——属实、可接受。

**快照对账**：审前/审后 `git status --porcelain -uall` 逐行 diff 为空；`Makefile`/`tests/arch.yaml`/`run_arch.py`/`platform.py` md5 前后一致；HEAD 仍 `667d10c3`（未提交）。

**finding（非阻断）**：`tests/arch/README.md` 命名规范「禁止」行仍以 `mode_regs.body.S` 作反例（`.md` 不在扫描面；语义仍指「无前缀随意名」，建议后续顺手换成现行新名作反例）。

**判决：Accepted** —— 验收命令在 reviewer 重跑下全绿、7 条任务项逐条落地、3 路注入可达 FAIL 且 `cp`+md5 还原回绿、语义无变化、变更集与硬约束无违反。
