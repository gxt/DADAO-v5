# m16-testcases-010: cfx4 PTW/TLB 用例纳管与 QEMU/gem5 跑通

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m16-testcases-006`（`run_arch.py` 骨架）已合入
**可并行分片**：是（15 条可分片，但共享 `tests/arch/ptw/expected.yaml`）
**预估**：3–4 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景

现有 cfx4 的 15 条 TLB/PTW 探针载体在 `tools/testcases/arch/min_rom_probe_tlb.py`（QEMU bootrom），不在 `tests/arch.yaml`。按 004 的落点方案，把它们迁入 `tests/arch/ptw/`，由 `run_arch.py --cfx 4` 驱动，先跑 QEMU + gem5（shim），RTL 侧由 `m16-chipyard-018`。

## 要做

1. **迁入**：15 条 case 的载体/期望/生成器落到 `tests/arch/ptw/`；`expected.yaml` 保留现有判据来源（`contract-tlb`/`contract-see`/`spec/DADAO-12`）。
2. **索引**：`tests/arch.yaml` 登记 15 条（`kind: driver`，`machine: vast`，`platforms: [system]`）。
3. **驱动**：`run_arch.py --cfx 4 --platforms qemu,gem5` 能逐条跑并取签名；gem5 经 `qemu_gem5_shim.py`（`-machine kaiwu-vast`）。
4. **三方预留**：RTL 后端未接时显式 fail-closed（不静默），由 `m16-chipyard-018` 接。
5. **覆盖**：每条 case 的检查点映射到 `contract-tlb` 条款，回填 `tests/arch/data/vast-arch-inventory.md` 的 cfx4 行。

6. **HSU 覆盖**（用户 2026-11-22：HSU 纳入、J 不纳入）：PTE 的 `H`/`S`/`U` 与 `R/W/X` 组合（正常页/超页、允许/拒绝）；J 位不测，未覆盖的 J 组合写入清单。

## 不做

- 不新增语义用例（先迁现有 15 条）；
- 不改 QEMU/gem5/RTL 实现；
- 不接 RTL 后端（下一件）。

## 约束

- 独立 `git worktree`；**不提交 git**；用例/驱动/期望集中 `tests/arch/ptw/`；
- 不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. 15 条在 QEMU 上逐条 rc=0 且签名与现有期望一致；
2. 15 条在 gem5（shim）上逐条跑；与 QEMU 签名一致，或逐条登记差异（原因+用户裁定状态）；
3. `check-tests-index` 现场统计 `arch` 条数 = yaml 条数；注入「删一条」⇒ 红；
4. **可达 FAIL**：改一条期望槽 ⇒ 红；`cp`+md5 还原回绿；
5. `check-tasks`、`check-knowledge-refs` 记录 rc；`--inject` ≥2 路。

## 完成区

**测试结果**：运行期证据目录内的 `run.sh` → **18/18 PASS，rc=0**；`run.sh --inject` → **32/32 PASS，rc=0**（3 路注入：改期望槽 / 删 arch 条 / 后端假绿，均「注入红 → `cp`+md5 还原 → 回绿」）。`run_arch.py --cfx 4 --platforms qemu,gem5`：**15 case × 2 平台全 PASS**，QEMU 与 gem5 各 **29/29** 检查；`arch-ptw-002/006/007` 的签名槽 **3/3/4** 逐槽等于 `expected.yaml`，QEMU 与 gem5 **逐字节相同**；其余 12 条按既有设计无签名槽（0 槽空流），以「同驱动同检查集 + verdict」跨引擎一致（`run.json` 的 `cross_platform[*].checks_equal`）。**无 gem5 差异**，无待裁差异项。

**修改文件**：`tests/arch/ptw/carrier_tlb.py`（新增，由 `tools/testcases/arch/min_rom_probe_tlb.py` 迁入并改路径/聚合签名）、`tests/arch/ptw/check_tlb.py`（改指向本地载体）、`tests/arch/ptw/expected.yaml`（注释：新载体 + 聚合口径）、`tests/arch/common/platform.py`（gem5 driver 承载经 shim；chipyard 仍 fail-closed；跨平台签名/检查集字段）、`tests/arch/run_arch.py`（`--gem5/--gem5-config`、后端自检、跨平台一致性）、`tests/arch.yaml`（登记 15 条 `arch-ptw-*`）、`Makefile`（`ARCH_PTW_CARRIER` 路径同步）、`tests/arch/README.md`、`tests/arch/PLAN.md`、`tests/arch/data/vast-arch-inventory.md`（cfx4 行 + 检查点映射）、`tests/shared/README.md`（签名消费者路径）、`tools/testcases/arch/min_rom_probe_tlb.py`（删除，已迁出）；运行期证据目录内的 `run.sh`（不入库）。

**验收结果**：① `run.sh` rc=0（18/18）：`--self-test`、carrier/driver `--selfcheck`、`check-tests-index`（arch=25 == yaml=25；ptw 15 == expected 15 == carrier 15；checks 29 == 29）、`check-tasks`（rc=0，报告型；本任务转 `待验收` 后计①，属预期）、`check-knowledge-refs`、QEMU+gem5 30 PASS、chipyard SKIP+rc1、gem5 缺件 SKIP+rc1。② `run.sh --inject` rc=0（32/32）：改 `expected.yaml` 首槽 ⇒ `run_arch --case arch-ptw-002` rc=1 且含「签名流」⇒ 还原 md5 `3c16f1a5…` 回绿；删 `arch-ptw-015` ⇒ 独立计数 14≠15 红 ⇒ 还原 md5 `01b5bd94…` 回绿；`CHIPYARD_IMPLEMENTED=True` ⇒ `--self-test` rc=1 且报「未实现后端未 fail-closed」⇒ 还原 md5 `4d9c9f8b…` 回绿。③ 跨平台：`run.json` 15 条 `cross_platform` 全 `ok`，`check_count` 两侧相等（共 29），002/006/007 签名 md5 两侧相同。④ `check-case-ledger`、`check-dirs`、`check-no-residue` 均 rc=0（附加）。

**新发现/坑**：① 多检查 case 的签名流会互相覆盖：`P.run(console_out=SIG_OUT)` 每个检查都重置同一文件，而 `run_arch` 按 `expected.yaml` 的 checks 顺序拼接比较（007 = 2+2=4 槽）；已在载体 `main` 收集各检查 blob 后聚合写回，`expected.yaml` 注释同步。② `check-tests-index` 的 `arch=N` 与直接数 `tests/arch.yaml` 同源（m16-006 reviewer 已指出），删一条仍可能绿；证据脚本另用「`expected.yaml` cases / 载体 `--list` 的 case+check 数」独立对账，删条注入会红。③ gem5 仅接 `kind: driver`；`kind: asm` 在 gem5 上显式 `PlatformError`（避免把 umon 等未接载体静默漏跑）。④ carrier 的 `-machine` 未带 `cache-model=on`（QEMU cfx5 未就绪，`m16-qemu-001`）；ptw 功能与 cache 无关，QEMU/gem5 逐条结果不受影响。⑤ 载体迁移必须同步 `Makefile` 的 `check-arch` 路径，否则 `make check-arch` 会找旧文件。

**遗留问题**：① `make check-arch` 全量未跑（前置 `install-host`/`build-bootrom` 会重建工具链/固件）；已用同一 shell 块实跑 `integ007t` 64/64 + `carrier_tlb` 29/29，并核过 Makefile 展开。② RTL 侧未接，`chipyard` 保持 SKIP+rc1，由 `m16-chipyard-018`。③ 12 条 case 无签名槽是既有设计（`m16-testcases-002` 只接线 002/006/007）；本任务未扩签名面，跨引擎以「同检查集 + verdict」判。④ gem5 的 asm 载体未接（不影响 cfx4）。**待裁定**：是否要为 12 条无签名槽的 case 补签名接线（属扩观测面，非本任务「只迁现有」范围）。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 载体迁到 `tests/arch/ptw/` 后 `_REPO` 层级错（3 层 → 实为 4 层） | ✅已修 | `carrier_tlb.py` 改 4 层 dirname，并显式把 `tools/testcases/arch` 加入 `sys.path`（`node_probe_prelude` 不随迁） | `carrier_tlb.py --selfcheck` rc=0；`check_tlb.py --selfcheck` rc=0 |
| 007 有两个带签名检查，逐检查写同一 `SIG_OUT`，与 `expected.yaml` 的 4 槽拼接不符 | ✅已修 | 载体 `run_check` 返回 blob，`main` 按检查顺序聚合并写回 `SIG_OUT` | 007 `signature.bin` 32 B = 4 槽；`run_arch` 007 PASS；QEMU/gem5 md5 相同 |
| 未接线 case 不产生 `signature.bin`，跨平台比较遇缺文件口径不一 | ✅已修 | `platform._finish` 对 `want is None` 显式写 0 槽空流、`signature_count=0` | `run.json` 12 条 `signature_count=0`，文件存在且 0 B |
| gem5 实现后 `self_test_fail_closed` 仍要求 gem5 抛错，会导致自检假红 | ✅已修 | 改为「gem5 `implemented` 为真」+ 仅 chipyard 探针 fail-closed | `--self-test` PASS；后端假绿注入 rc=1 |
| gem5 driver 承载缺前置检查，缺件会被当成 0 结果 | ✅已修 | `_ensure_gem5_ready` 检查 shim/gem5.opt/fs.py/可执行位，缺失抛 `PlatformError` | `--gem5 no-such` ⇒ SKIP + rc=1；正常路径 15/15 |
| `check-tests-index` 的 arch 计数与 yaml 同源，删条注入抓不住 | ✅已修（证据侧独立对账） | 证据脚本加 `expected.yaml` cases / carrier `--list` case+check 独立计数；删条注入按独立计数判红 | 基线 15==15、29==29；删条注入「different」 |
| 迁移后 `Makefile` 的 `check-arch` 仍找旧 `min_rom_probe_tlb.py` | ✅已修 | `ARCH_CFX_PROBES` 去 `tlb`，新增 `ARCH_PTW_CARRIER` 并在循环后调起 | 同 shell 块实跑 `integ007t` 64/64 + carrier 29/29，rc=0 |
| 旧路径引用散在 README/PLAN/inventory/shared README | ✅已修 | 逐处更新为 `tests/arch/ptw/carrier_tlb.py`（历史盘点注保留「迁入自」） | `grep -rn min_rom_probe_tlb` 非 `.tao` 仅剩「迁入自」与历史 PLAN 行 |

判决：全部 finding 已修；状态 `待验收`。

### 第 1 轮 reviewer 验收

**重跑（均我在 worktree 仓库根自跑；证据 = 运行期证据目录内的 `run.sh`）**

1. `run.sh` → **18/18 PASS，rc=0**。首次 rc=2 `preflight: qemu or gem5 not executable`（共享 gem5 构建树正被并行会话链接，环境干扰非交付物缺陷），重试 1 次后 rc=0。
2. `run.sh --inject` → **32/32 PASS，rc=0**（3 路均「注入红 → `cp`+md5 → 回绿」；还原 md5 `3c16f1a5…`/`01b5bd94…`/`4d9c9f8b…` 与完成区逐字一致）。
3. **独立注入 A（改期望槽，走脚本外路径）**：`arch-ptw-006` 槽 2 `…ffed→…ffec` ⇒ `run_arch --cfx 4 --case arch-ptw-006 --platforms qemu` **rc=1**、日志含「签名流: 槽 1 期望…」；`cp` 还原后 md5 与注入前相等 ⇒ 复跑 **rc=0**。
4. **独立注入 B（删一条 case）**：删 `arch-ptw-014` 整块 ⇒ `run.sh` **rc=1**（4 FAIL：15≠14 ×2、PASS 30→28、cross-check rc=1）；同一注入下 `make check-tests-index` **rc=0 仍绿**（arch=24 同源自比，与完成区披露②一致）；`cp` 还原 md5 相等 ⇒ `check-tests-index` rc=0（arch=25）、`run.sh` **rc=0（18/18）**。
5. 门控自跑：`check-tests-index` rc=0（arch=25==yaml=25）、`check-tasks` rc=0（报告型 ①=1，本任务待验收，预期）、`check-knowledge-refs` rc=0、`check-dirs`/`check-no-residue`/`check-case-ledger` rc=0。
6. 快照对账：注入前后 `git status --porcelain -uall` 逐行相同；7 个目标文件 md5 前后相同；`tools/testcases/arch/min_rom_probe_tlb.py` 盘上无、`git status` = `D`。

**迁移完整性**：`tests/arch/ptw/` = `carrier_tlb.py`（新）/`check_tlb.py`/`expected.yaml`；非 `.tao` 无残留可执行引用（仅「迁入自」注释 6 行 + PLAN 迁移表/分期行）。`arch.yaml` 15 条 `arch-ptw-*` 现场 yaml 对账：`file=arch/ptw/check_tlb.py`、`kind=driver`、`machine=vast`、`platforms=[system]`、`level=full` 全一致；id 序 == `expected.yaml` 15；checks 29 == carrier `--list` 29。`Makefile` recipe 实跑 `carrier_tlb.py --qemu <安装根>/qemu-system-dadao` → **29/29 checks passed，rc=0**。

**三方口径**：`run.json` 30 结果、failures=[]、qemu/gem5 各 15 PASS；`cross_platform` 15 条全 ok、check_count 两侧各 29；002/006/007 = 3/3/4 槽两侧相等且字节相同（`run.sh` 内独立 python 断言 q==g 通过）。**12 条 0 槽判定**：实质比较 = 同一驱动日志逐检查 `PASS/FAIL <id>/<label> rc=…` 行集合 + verdict（29 行由 `run.sh` 现场断言，非空、非恒真）；在「只迁现有、不扩签名面」范围内**足够**，`expected.yaml` 本无这 12 条状态期望，补签名属扩观测面 ⇒ **不阻断，记待裁/后续**（同遗留③）。次要：`run_arch.py` 注释称不把空流当「签名一致」，但 `entry["ok"]` 仍含恒真的 `signature_equal`；实际判据由 `checks_equal` 承担，无假绿（注释/代码口径轻微不一致，非阻断）。

**Makefile 合并顺序风险（不替 007 判断）**：010 改动正确（`ARCH_CFX_PROBES` 去 `tlb`、新增 `ARCH_PTW_CARRIER` 在 `done` 后调起、PASS 串加 `+ ptw/tlb`，命令实跑 29/29 rc=0）。**风险**：`m16-testcases-007` 已在其树重写同一 Makefile 区段（`_locked-check-arch*` + `ARCH_CFX_PROBES` 注释/变量），并同改 `tests/arch/run_arch.py`、`tests/arch/README.md` ⇒ 合并必冲突，需人工合并非盲 squash；007 语义「不再遍历 `ARCH_CFX_PROBES`」若后落且未补 `ARCH_PTW_CARRIER` 调用，迁移后 15 条将失去唯一 make 门控（010 现态有门控）；007 任务书「15 个 min-ROM 探针文件保留」对已删文件已过时。合并顺序与处置由 architect 定，合并后须复跑 `make check-arch` 确认 ptw 载体仍被某门控覆盖。

**finding（不阻断）**：`m16-gem5-014`（已验证）等历史任务书仍以 `min_rom_probe_tlb.py` 作回归手段 —— 文档级，交 architect 收尾改。

**判决：Accepted** —— 验收命令块在我自己的重跑下全部通过；约束（独立 worktree、不提交 git、用例/驱动/期望集中 `tests/arch/ptw/`、术语「寄存器组」、不写运行期路径）无违反；两路独立注入红 → `cp`+md5 还原 → 回绿闭环。
