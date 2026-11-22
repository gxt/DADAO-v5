# m16-testcases-007: `check-arch` / `check-arch-smoke` 按新 `tests/arch` 重写

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m16-testcases-006`（`run_arch.py` 骨架）已合入
**可并行分片**：否（共享 Makefile）
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景（用户 2026-11-22 裁定）

`check-arch-smoke` 要按新的 `tests/arch` 重写；`check-arch` **与 `check-arch-smoke` 一致**（同一代表集），L3 的 arch 成员保留，不再跑旧的 15 个 `ARCH_CFX_PROBES` min-ROM 探针（文件保留，后续 cfx4 迁移任务处理）。

## 要做

1. **代表集来源**：从 `tests/arch.yaml` 的 `level: smoke` 条目现场派生（不写死条数），经 `tests/arch/run_arch.py --level smoke --platforms qemu --cache-model on` 执行（arch 固定 on，off 会 rc=2）；输出 rc 与逐 case 签名结果。
2. **`check-arch-smoke`**：Makefile 的 `_locked-check-arch-smoke` 改为调用上述命令；保留 25 服务覆盖（`min_rom_probe_046t`）作为 smoke 的一部分。
3. **`check-arch`**：与 `check-arch-smoke` **一致**——同一 recipe（别名或直接复用），不再遍历 `ARCH_CFX_PROBES`；L3 的 `l3_run.DEFAULT_MEMBERS` 仍指向 `make check-arch`，`check-l3-report` 四 scope 覆盖不变。
4. **旧探针**：`ARCH_CFX_PROBES` 变量保留（010 后 14 项），对应 min-ROM 探针文件保留，但不再被 `check-arch` 调用；在 Makefile 注释与 `tests/arch/README.md` 写明"待 cfx4 迁移任务处理"。
5. **fail-closed**：代表集为空、`run_arch.py` 缺失、case 失败都必须非零；不得 `|| true`。

## 不做

- 不删旧探针文件、不改其判据；
- 不新增 cfx 语义用例；
- 不改 `tests/arch.yaml` 的条目语义（只读 level）；
- 不改 Process-07/09（004 已改）。

## 约束

- 独立 `git worktree`；**不提交 git**；
- 变更集限 `Makefile`、`tests/arch/README.md`、`tests/arch/run_arch.py`（若需 `--level`）、本任务书；
- 不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. `make check-arch-smoke` 与 `make check-arch` 均 rc=0；**结构断言**：`_locked-check-arch` 只有「依赖 `check-arch-smoke` + echo」、无其它 recipe 行（两次 `run.json` 相同属同源拷贝，不能单独作证据）；
2. 代表集条数现场派生，与 `tests/arch.yaml` 的 smoke 条目数一致；**可达 FAIL 用「清空代表集 ⇒ rc=2」或「删载体 ⇒ rc=2」**（删 1 条后仍 9 条会绿，不作判据）；
3. 旧 `ARCH_CFX_PROBES` 不再被 `check-arch` 调用（日志无 min-ROM probe）；**15 个 min-ROM 探针文件保留**（010 已删 `min_rom_probe_tlb.py`，以合并后 master 为准）；
4. `make check-tests-index`、`make check-tasks`、`make check-knowledge-refs` 记录 rc；
5. **签名流口径**：`run_arch.py --case arch-ptw-002` 改错一槽 ⇒ `rc=1`；smoke 的 10 条 umon 无签名流，签名门控归 carrier（L3），**不要求 smoke 红**；
6. `--inject` ≥2 路；
7. **合并处置（010 已合入 master `a388baa4`）**：把 `ARCH_PTW_CARRIER = tests/arch/ptw/carrier_tlb.py` 的调用**并入 `_locked-check-arch-smoke`**（让两目标同跑、维持「一致」裁定）；`ARCH_CFX_PROBES` 取 010 版（14 项、无 `tlb`）；`run_arch.py`/`README` 保留 010 的 gem5/`cross_platform` 改动；合并后重跑 `check-arch-smoke` 与 `check-arch`。

## 完成区

**测试结果**：证据脚本 30/30 PASS（基线 12 + 注入 18）。`make check-arch-smoke` / `make check-arch` 均 rc=0；`check-tests-index` / `check-tasks` / `check-knowledge-refs` 均 rc=0；6 路注入全部「红 → `cp`+md5 还原 → 回绿」。
**修改文件**：`Makefile`、`tests/arch/README.md`、`tests/arch/run_arch.py`、本任务书。运行期证据：证据目录内 `run.sh` / `run-r2.out` / `logs/`（不入库）。
**验收结果**：
- 合并：`git merge --ff-only 0829f94a`（master，含 010 `a388baa4` + 008 + 任务书订正）；HEAD = `0829f94a`，无冲突（先存本任务补丁→`git apply -R`→ff→按合并版重放）。
- `make -o install-host check-arch-smoke` rc=0：`level=smoke ... cases=10` 10/10 PASS；046t「all 25 service ids」`RESULT: PASS`；carrier **29/29 checks（15 个 arch-ptw id）** PASS。
- `make -o install-host check-arch` rc=0：同一 smoke（含 carrier）全跑；结构断言 `_locked-check-arch` = `deps=check-arch-smoke, recipe_lines=1, echo`。
- 现场数：`ARCH_CFX_PROBES` **14 项、无 tlb**；`ARCH_PTW_CARRIER = tests/arch/ptw/carrier_tlb.py`（yaml 15 条）；旧探针日志 0 条 `cfx min-ROM probe`，无新 `check-arch-probe-*.log`。
- 注入：A 错 m5 期望 token→smoke rc=2；B ptw 签名槽 1 错→`run_arch --case arch-ptw-002` rc=1；C smoke 清空→rc=2；D 删 smoke 载体→rc=2；E 删 `run_arch.py`→smoke rc=2；F 删 `carrier_tlb.py`→smoke rc=2；均 md5 还原后回绿。
**新发现/坑**：① `run_arch.py` 的 010 gem5/`cross_platform` 与 `--level` 已兼容（`run.json` 同时有 `level` 与 `cross_platform`）。② `level: smoke` 的 10 条 umon 无签名流，签名门控按订正口径归 carrier/L3。③ `writer_guard` 跨 worktree：他人 `install-host` 期间直跑 rc=75，证据脚本按 10 s 重试至 30 min。
**遗留问题**：① `docs/Process-07/09` 仍写 `check-arch` 为全 cfx；按任务约束未改，待收口更新。② 010 的 `ARCH_PTW_CARRIER` 已按订正并入 smoke，15 条 arch-ptw 均跑到；其 `run_arch --level full` 跨平台比对仍按需/里程碑跑。

## 审阅记录

### 第 2 轮 engineer 自审

**审查范围**：合并后 `git diff` 三文件逐行 + `run.sh` 基线/注入实跑输出。
**判决**：无未修 finding；状态置「待验收」。未提交 git。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| R1 master+010 合并，保留 010 gem5/`cross_platform` 与 `--level` | ✅已修 | `run_arch.py` 在 010 版上重放 `LEVELS/select_level/--level/run.json level` | 两门控 rc=0；`run.json` 含 `level`+`cross_platform` |
| R2 `ARCH_CFX_PROBES` 取 010 版（14、无 tlb） | ✅已修 | Makefile 变量保持 010 版 | 证据脚本现场读到 14；`tlb` 不在列表 |
| R3 carrier 并入 smoke，两目标同跑 15 条 | ✅已修 | `_locked-check-arch-smoke` 第 3 步跑 `ARCH_PTW_CARRIER` | 两门控日志均 `[3/3] carrier`；carrier 15 ids / 29 checks PASS |
| R4 `_locked-check-arch` 只「依赖 smoke + echo」 | ✅已修 | recipe 删到 1 行 echo | 结构断言 `deps=check-arch-smoke recipe_lines=1 echo` |
| R5 验证 2 不用「删 1 条」作判据 | ✅已修 | 删除 D 注入；用清空集/删载体 | C rc=2、D rc=2 |
| R6 签名口径：ptw 改错槽 rc=1，不强求 smoke 红 | ✅已修 | 证据脚本 B 直跑 `--case arch-ptw-002` | 注入 B rc=1；还原后 rc=0 |
| R7 `--cache-model on` | ✅已修 | Makefile 与证据脚本均 `on` | 两门控日志 `cache-model=on` |
| R8 证据脚本探针断言改 14+carrier15 | ✅已修 | `ARCH_CFX_PROBES` 现场数 + carrier yaml 计数 | `14 min-ROM + carrier 15` PASS |
| R9 README 合并 010 内容（gem5 shim/ptw carrier） | ✅已修 | 仅叠加门控/`--level`，保留 010 段落 | README diff 无 010 段落删除 |
| R10 fail-closed：驱动/索引/carrier 缺失、空集均非零 | ✅已修 | recipe 显式 `test -f/-x`；`select_level` 空集 rc=2 | 注入 C/D/E/F 均红 |

### 第 2 轮 reviewer 验收

**重跑（仓库根执行运行期证据目录内的 `run.sh`，各一次）**：
- `make check-arch-smoke` rc=0（`level=smoke ... cases=10`；`all 25 service ids` PASS；`29/29 checks passed`）；
- `make check-arch` rc=0（同一 smoke 全跑 + carrier；尾行 `check-arch: PASS (same checks as check-arch-smoke)`；`cfx min-ROM probe` 0 条）；
- `run.sh` rc=0、`run.sh --inject` rc=0，两次均 **30 PASS / 0 FAIL**（基线 12 + 注入 18）；
- 两门控日志各含 `[3/3] cfx4 PTW/TLB carrier (15 cases)` + `29/29 checks passed`（carrier 日志 15 个 `arch-ptw-0xx` 唯一 id，0 `FAIL`）。

**结构/字段核（我的独立解析，非采信脚本）**：`_locked-check-arch` 仅 `deps=check-arch-smoke` + 1 行 `@echo`，`ARCH_CFX_PROBES`/`ARCH_PTW_CARRIER` 均不在其 recipe；carrier 三处 `test -f` 守卫与 `[3/3]` 步只在 `_locked-check-arch-smoke`。`run_arch.py` 保留 010 的 69 行新增**逐行全在**（`cross_platform`/`qemu_gem5_shim`/`--gem5*` 未丢），同时有 `--level`/`select_level`/`run.json.level`；`tests/arch/ptw/**`、`common/platform.py`、`arch.yaml` 与 HEAD 逐文件 md5 一致。

**计数口径**：`ARCH_CFX_PROBES` 现场 14（无 `tlb`）+ carrier 由 yaml 现场派生 15；旧「15 个探针」断言已改为 14 列表项 + carrier yaml 计数，`min_rom_probe_*.py` 磁盘数只报不断言。代表集条数 = yaml `smoke` 现场值 10 == `run.json.cases`。

**合并核**：HEAD `0829f94a`（= master，含 010 `a388baa4` + 008 `2df23636`），reflog 显示 `merge … Fast-forward`；`git status` 仅 4 个预期文件（本任务书/`Makefile`/`tests/arch/README.md`/`tests/arch/run_arch.py`），无 untracked、无 `.orig/.rej/.preinject`、`git stash` 空；注入前后 4 文件 md5 与审查开始快照逐一相同；注入涉及的 6 个文件中 5 个非改动文件（`arch.yaml`/`ptw|umon/expected.yaml`/`m5_semi_writec.s`/`carrier_tlb.py`）md5 全等于 HEAD，`run_arch.py` 与审查开始快照一致。

**独立注入 2 路（`cp` 备份 + md5 对账，非 `git checkout`）**：① 清空代表集 ⇒ rc=2（`代表集为空…不得静默当作通过`），还原 md5 `01b5bd94…` 一致 ⇒ rc=0；② 删 `tests/arch/ptw/carrier_tlb.py` ⇒ rc=2（`ERROR: … not found`），还原 md5 `249b0b84…` 一致 ⇒ rc=0 且 `29/29`。

**约束核**：变更集 = 任务书声明的 4 文件，未越界；未改 `tests/arch.yaml`/`ptw`/`platform.py`/`Process-07/09`/`l3_run.py`；任务书与 README 无运行期路径；「银行」仅存于 Makefile 既有行（不在本次 diff）。**判决：Accepted**（返工项 R1–R10 全部复验通过，无新增阻断 finding）。
