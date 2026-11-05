# INTEG-054t: 5 个屏蔽寄存器实现清理

**模块**：integ
**项目里程碑**：M11
**依赖**：`SPEC-188t`/`SPEC-189t`/`SPEC-190t`（已验证；定义与路由已定稿）、`SPEC-191t`（旧码清理，文档）
**状态**：已验证

## 执行环境
本地；跨 QEMU/gem5/tests 的实现清理，按 QEMU → gem5 → tests 串行。

## 背景

`SPEC-188t` 已删除 5 个无效屏蔽寄存器的语义，编号保留 reserved：

- `inner_cfx_mask`
- `switch_cfx_mask`（cg0–3 rc9）
- `excp_cause_mask`（cg0–3 rc11）
- `excp_prev_cfx_mask`（cg5 rc1）
- `excp_cause_nonmaskable`（cg5 rc63）

保留：

- `cfx_intr_mask`（cg0–3 rc4）
- `global_cfx_intr_mask`（cg8 rc1）
- `excp_pending`（cg5 rc5）

实现仍按旧寄存器工作，需清理。

## 目标

1. **QEMU**：删除 5 个寄存器的读写/状态路径；reserved 访问 ⇒ `CFXREG`；`escape` 不再恢复 `excp_prev_cfx_mask`，保留 `global_cfx_intr_mask` 的 trap 保存/escape 恢复；保留 `cfx_intr_mask`/`excp_pending`。
2. **gem5**：同 QEMU，逐处对齐。
3. **tests**：
   - `tests/shared/bootrom/step5/hmon.S` 删除 `cfx_umon, cg3, rc9` 写；
   - 更新依赖这些寄存器的探针/向量/期望；
   - 保留 `CFXREG` 期望与 Node/Tiny 语义。
4. 三阶段串行：QEMU → gem5 → tests；共享测试只在 tests 阶段改。

## 验收标准

1. 5 个寄存器在 QEMU/gem5 活代码与 tests 活资产中 0 命中（历史/注释除外）。
2. reserved 访问 ⇒ `CFXREG`；合法路径不变；`escape` 只恢复 `global_cfx_intr_mask`。
3. `hmon.S` 不再写 rc9；Node/Tiny boot 正常。
4. `make build-qemu`/`build-gem5`、`check-source-state`/`check-patch-tree`、`check-arch`/`check-inst`、L1 rc=0。
5. `matrix-M11` 重跑：`node/arch` 249 AGREE、0 fail；无回归。
6. 反例：写回一处 rc9/inner mask ⇒ 断言 FAIL；还原回绿。
7. 完成区 ≤30 行；状态 `待验收`。

## 范围 / 非范围

**在范围内**：`components/qemu/**`、`components/gem5/**`、`tests/**`（相关 bootrom/arch/inst 期望）、`tools/testcases`（仅相关读取）、本任务书、`milestones.md`。

**不在范围内**：`spec/**`、ADR、`contracts/**`、`.tao/contracts/**`（别名已由 188t 清理）、退出码语义。

## 说明

- 这是 `SPEC-188t` 的实现落地；不改 spec。
- 若某测试必须保留旧寄存器才能表达，先留问，不自行改语义。
- 退出码实现由 `INTEG-055t` 独立处理，本任务不改退出码映射。

## 完成区

**测试结果**：9/9 门控 0 失败——`build-qemu`/`install-host` PASS；`check-inst` PASS（node 965/970、0 failed；tiny 44/44）；`check-arch` PASS（smoke 10/10 + 13 个 cfx 探针）；`build-gem5` PASS；`check-gem5-decode` PASS（264/264 + 388/388 + 28/28 + 2/2）；`parity` node/arch 269 total / **249 AGREE / 0 fail / 20 BLOCKED / 0 diff**（与 TESTCASES-098t 基线一致）；`check-patch-tree` 303 patches OK；`check-source-state` qemu/gem5 `base+1 clean`；L1 rc=0。
**修改文件**：`components/qemu/patches/target/dadao/{cpu.c,cpu.h,helper.c}.patch`、`components/qemu/changelog.md`；`components/gem5/patches/src/arch/dadao/{isa.cc,node_cfx.cc,node_cfx.hh}.patch`、`components/gem5/{README.md,changelog.md}`；`tests/shared/bootrom/step5/hmon.S`；`tools/testcases/arch/{README.md,node_probe_prelude.py,min_rom_probe_044t.py,min_rom_probe_045t.py,min_rom_probe_async_094t.py,min_rom_probe_integ040t.py,min_rom_probe_integ042t.py,min_rom_probe_integ044t.py,min_rom_probe_integ046t.py,min_rom_probe_integ048t.py,min_rom_probe_integ050t.py,min_rom_probe_integ051t.py}`、`tools/testcases/validate_m5_vectors.py`；本任务书、`.tao/knowledge/milestones.md`。
**验收结果**：运行期证据脚本 **15/15**（含反例：把 `cg0-3 rc9` 恢复为活寄存器 ⇒ `044t cfxreg_badcombo` FAIL（`syncn:3` 6→4）⇒ `cp`+md5 还原 ⇒ 重建/安装后回绿）；探针实跑见 运行期日志目录。
**新发现/坑**：① 旧实现用 `cause_nonmaskable` 兼做「同步异常豁免掩码」，删除该寄存器后必须由 `cfx_enter(..., sync)` 表达，否则同步异常会被两级中断掩码误挡；② dump 删字段后所有 `-d cpu` 解析器须同步（044t/045t/integ044t/integ046t）；③ 旧探针把 `switch_cfx_mask` 当「进入 cfx 的开关」，改后只剩当前 cfx 的 `cfx_intr_mask`（integ051t 的 tail-kick 用例按此改写）；④ gem5 `NodeState.cfxMask` 随 `cfx_enter` 去掩码一并删除。
**遗留问题**：无（退出码映射由 `INTEG-055t` 独立处理）。

## 审阅记录

#### 第 1 轮 engineer 自审

逐行审查 QEMU `cpu.h/cpu.c/helper.c`、gem5 `node_cfx.{hh,cc}/isa.cc` 与全部改动探针；结论：实现与 `DADAO-12 §5.2/§5.3` 一致。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 同步异常掩码豁免原由 `cause_nonmaskable` 承担，直接删字段会改变行为 | ✅已修 | `cfx_enter` 以 `sync` 参数跳过掩码；异步仅走两级来源过滤 | `check-inst`/parity/13 探针全绿 |
| 删 dump 字段导致 4 个探针解析失配 | ✅已修 | 044t/045t/integ044t 去字段，integ046t 正则改为 `SWMODE:… VEC:` | 对应探针 PASS |
| 探针仍在写 reserved 寄存器（044t/045t/048t/integ042t/integ044t/integ050t/integ051t/async094t） | ✅已修 | 删除写路径，改由 `cfx_intr_mask`/`global_cfx_intr_mask` 表达屏蔽 | `check-arch` 全绿 |
| 反例可达性 | ✅已验 | 注入 rc9 活寄存器 ⇒ 探针 FAIL | `run.sh` injection 段 |

#### 第 1 轮 reviewer 验收

**重跑记录（命令/输出/退出码均为我自己的终端；日志 运行期日志）**
- 运行期证据脚本 ×3：基线 `SUMMARY: checks=15 failures=0` `RUNSH_BASELINE_EXIT=0`；gem5 注入态 `failures=3`（`static-gem5-no-removed-state actual=2 hits`、`check-patch-tree: 3 problem(s)`、`check-source-state rc=1`）`EXIT=1`；还原后 `failures=0` `EXIT=0`。
- 门控链 `make build-gem5 / check-gem5-decode / check-inst / check-arch / check` → `EXIT=0/0/0/0/**2**`；两次 `check` rc=2 **均为我自致**：① 我的日志名 `REVIEW-*` 违反 `check-run-artifacts`，改名 `INTEG-054t-review-*` 后 rc=0；② 本审阅记录里一个字面路径被 `check-knowledge-refs` 判悬空，改写措辞后 rc=0；均非交付物缺陷，如实记录。`build-qemu`/`install-host` 由 `run.sh` 与注入 A 各跑 2 次，全部 rc=0。
- 末轮（全部注入还原后）复跑：`check-inst` rc=0（`965/970` + `44/44`，0 failed）、`check-arch` rc=0（`14/14` = smoke `10/10` + 13 探针）、`make check` rc=0（`repository checks (L1): PASS`、`[FAIL]` 0 条）。
- `make check-patch-tree` rc=0（`7 component(s), 303 patches OK`）；gem5 `check_b6.py` rc=0（`B6 coverage 30/30, failures 0`）。
- `python3 tools/testcases/parity/run_parity.py --profiles node --scopes arch …` → `run_parity: PASS`、`PARITY EXIT=0`；由 `parity.json` 现场重算 `node/arch total 269 = agree_pass 249 + blocked 20`，`agree_fail/diff/gem5_only_fail/qemu_only_fail/deferred/skip_profile 全 0`；`arch/probe/044t/cfxreg_badcombo` = `AGREE_PASS / PASS / PASS`（gem5 侧同样判 `CFXREG`）。
- 源树：qemu 源树 `git status` 0 行、`HEAD f88564d`；gem5 0 行、`HEAD 034e744`（base+1 clean）；主工作树 `git status --porcelain` 0 行。

**独立注入（我方，非 engineer 自检；全程 `cp`+`md5sum -c`，未用任何 git 还原）**
- A · QEMU 运行期，**cg5 rc1 复活**（锚点 `case 0: return &r->prev_run_mode;`，与 engineer 的 rc9 锚点不同）：`helper.c md5 93fb5a89…→164ffc09…` ⇒ `build-qemu`/`install-host` rc=0 ⇒ `044t --only cfxreg_badcombo` **`RESULT: FAIL`、`PROBE_INJECT_EXIT=1`、`syncn:3 exp=0x6 got=0x5`** ⇒ `cp` 还原 + `md5sum -c … OK` ⇒ 重建/安装 rc=0 ⇒ `RESULT: PASS` rc=0。
- B · gem5 静态，**rc9 / `switchCfxMask` 复活**（`node_cfx.cc`+`node_cfx.hh`）⇒ **同一 `run.sh` `EXIT=1`、`checks=15 failures=3`**（静态断言与两条门控断言有可达 FAIL 路径、非恒真）⇒ 两文件 `md5sum -c` 均 `OK` ⇒ 重跑 `run.sh` `15/15`、`EXIT=0` 回绿。

**约束核验（逐条）**
- 5 个寄存器 0 命中：`grep -riE 'inner_cfx_mask|switch_cfx_mask|excp_cause_mask|excp_prev_cfx_mask|cause_nonmaskable'` 全仓检索（已排除规范正文、台账、证据目录、组件源码检出与 git 元数据）仅剩 `manifests/spec-readonly.lock.toml` 注释与 `components/{qemu,gem5}/changelog.md` 历史条目；`tests/`+`tools/` 连 dump 字段 `CFXMASK|PREVMASK|NONMASK|SWMASK|CAUSEMASK` 也 0 命中。
- reserved ⇒ `CFXREG`：QEMU `cfx_mode_reg`/`cfx_reg_ptr` 删 `case 9/11`、`case 1/63`→NULL；gem5 同步删 `case 9/11`、`case 1/63`→nullptr；`044t cfxreg_badcombo` 现场覆盖 4 个地址化 reserved（rc9 读+写、rc11 读、cg5 rc1 读、cg5 rc63 读）+ scratch 越界，期望 `syncn:3=6`；`inner_cfx_mask` 非 cg/rc 面，由静态 grep 覆盖。
- 保留项在位：`cfx_intr_mask`（cg0–3 rc4）/`global_cfx_intr_mask`（cg8 rc1）/`excp_pending`（cg5 rc5）读写与复位未动；`helper_cfx_escape` 首步仍 `saved_global_intr_mask → global_cfx_intr_mask`（QEMU/gem5 一致），体内无任何屏蔽恢复；`escape_return`/`trap_vector_roundtrip` 双引擎 AGREE_PASS。
- 语义对 spec：`spec/DADAO-12 §5.2`（同步全不可屏蔽、进入步骤 1–7、不切换独立屏蔽层、异步仅两级来源过滤）与 `§5.3`（escape 步 0–3）逐条对齐；L1 内 `check-sync-nonmaskable` rc=0。
- `hmon.S` 已删 `cfx_umon, cg3, rc9` 写（diff 核对）；`check-arch` 重建 BootROM 后 13 探针全绿 ⇒ Node/Tiny boot 正常。
- 期望值未降：探针删除的只是被删寄存器的观测/写路径（`cfxmask`、`prevmask`、`rd12/rd40/rd55`、rc9/rc11/rc1/rc63 写），断言反而更严（044t `syncn:3` 1→6）；`validate_m5_vectors` 仅删**无活向量**的 `inner_cfx_mask_denied` 规则（`tests/` 无该 rule），L1 `validate-vectors` rc=0。
- 范围：改动 25 文件 = `components/{qemu,gem5}` 8 + `tests/` 1 + `tools/testcases/` 13 + 本任务书 + `milestones.md`；`spec/`、`contracts/`、`Makefile`、退出码映射 **0 改动**（`git status` 逐条核）。
- 任务书：`**状态**：待验收`；完成区 9 行（≤30）；无 `/tmp`、`/mnt`、家目录等运行期路径。

**findings（不阻断，交 architect）**
1. `run.sh` 以 `$0` 反推 `REPO`：经主工作树绝对路径调用会解析到 `master`（实测：相对/任务树路径 → 任务 worktree；主树绝对路径 → 主工作树），门控对象会错位；本次按任务 worktree 调用无误。建议改 `git rev-parse --show-toplevel` + 分支校验。
2. `node_probe_prelude.power_extra` 在本任务删掉全部调用方后成为孤儿参数（无行为影响），建议下轮清掉。
3. 证据脚本对 gem5 只有字段名静态 grep、无 gem5 运行期反例；gem5 运行期由 parity 兜底（我方 rc=0，gem5 侧 `cfxreg_badcombo` PASS）。

**判决：Accepted** —— 上述 rc 全部来自我自己的终端：`run.sh` 15/15、五门控 + L1 + `check_b6` + parity 全绿，两次独立注入「注入 → FAIL → `cp`+`md5sum -c` 还原 → 回绿」真实成立，硬约束无违反。

#### 收尾（architect，2026-11-05）

- F1：证据脚本 `$0` 反推 REPO 的健壮性问题记入遗留；后续改用 `git rev-parse --show-toplevel` + 分支校验。
- F2：`node_probe_prelude.power_extra` 孤儿参数记入遗留，下轮清理。
- F3：gem5 运行期反例由 parity 兜底，证据脚本仅静态字段检查；不阻断。
- 判决 Accepted，状态置 `已验证`。
