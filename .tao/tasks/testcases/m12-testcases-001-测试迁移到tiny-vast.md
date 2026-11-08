# m12-testcases-001: 测试与 profile 迁移到 `tiny` / `vast`

**模块**：testcases
**项目里程碑**：M12
**类型**：task
**状态**：已验证

## 目标

把测试侧全部从 `dadao-m1` / `profile=node` 迁到新命名：

1. `tests/shared/machine-profiles.yaml`：profile 键 `node` → `vast`（几何不变），注释与字段说明同步
2. 生成物：`tests/shared/asm/machine-node.inc` → `machine-vast.inc`；`tests/shared/bootrom/step5/{power,smon,hmon}.S` 的 include 同步
3. `tools/testcases/**`（约 46 个文件）：`-M dadao-m1` → `-M dadao-tiny`；`dadao-m1,profile=vast` → `-M dadao-vast`；`DADAO_TEST_PROFILE=node` → `=vast`
4. `Makefile` 中机器名/参数同步
5. `tools/qemu/semantics_gate.py` 散文改 `dadao-v5`（历史裁定引用保留原意）
6. `docs/DDLN/D-运行平台/DD-D002-运行平台--测试机运行环境.md` 的 2 处 `Node`（`m12-spec-001` reviewer F-a：讲义，非规范）
7. `tools/testcases/arch/min_rom_probe_integ046t.py`、`build_step5_bootrom.py` 的 docstring `Machine-v5-Node`（`m12-spec-001` 范围外发现）
8. **parity shim**：`tools/testcases/parity/qemu_gem5_shim.py` 的 profile 白名单 `("tiny", "node")`（两处）改为接受 `vast`（并保留 `node` 别名到 `m12-integ-001`），否则 `--profile vast` 会被 shim 拒绝
9. **术语**：面向人的文档与 `make help`/输出文本中的「夜跑」改为「**回归运行**」（用户 2026-11-08：该词指全量回归成员集，易误解为只在夜间跑）；**不改**脚本文件名与 Make 目标名（`night_run.py` / `night-run`），仅在注释说明语义

## 验收标准

1. `grep -rn 'dadao-m1\|profile=node\|DADAO_TEST_PROFILE=node' tools/ tests/ Makefile` 为 0（历史任务书/ADR/changelog 除外）
2. `make check`（L1）rc=0；`make check-modules`（L2）rc=0
3. `check-arch` / `check-arch-smoke` / `check-inst` rc=0（Tiny 与 Vast 各至少一个代表用例）
4. `machine-profiles.yaml` 与派生 `.inc` 一致（派生脚本 rc=0）
5. `grep -rn 'Machine-v5-Node\|dadao-node' tools/ tests/ docs/ spec/ Makefile` 为 0（历史任务书/ADR/changelog/archive 除外）
6. 完成区 ≤30 行、无运行期路径

## 说明

- 只改测试/工具侧；QEMU 代码与 gem5 配置不动
- 若某用例依赖 `profile=` 的默认值，逐条改为显式机器名并记录

## 完成区

**测试结果**：L1 `make check` rc=0；L2 `make check-modules` rc=0；`check-arch-smoke`/`check-arch`/`check-inst` rc=0（inst：980/985 + 44/44）；证据脚本 17 项 PASS，`--inject` 4 项 PASS（注入→FAIL→`cp`+md5 还原→绿）。
**修改文件**：121 项（120 改 + 1 新增；另任务书本身更新状态/完成区；与 `git status` 逐项一致，完整清单见运行期日志）：`Makefile`；`tests/shared/**`（`machine-profiles.yaml`、`asm/machine-vast.inc`〔新增〕/删 `machine-node.inc`、`bootrom/step5`、`linker/dadao-vast.lds`〔改名〕、`crt0`、README）；`tests/{arch,inst,parity,tset,unit}/**` + `tests/{README,INVENTORY,tset.yaml}`；`tools/testcases/**`；`tools/infra/{check_components,check_interface_alignment,build_musl,test_picolibc_smoke}.py`；`tools/qemu/{semantics_gate.py,smoke-dadao-tiny.sh}`（脚本改名）；`docs/**`（DDLN 4 册 + Process-04/07/09 + README）。
**验收结果**：① `grep 'dadao-m1\|profile=node\|DADAO_TEST_PROFILE=node' tools/ tests/ Makefile` = 0；② `grep 'Machine-v5-Node\|dadao-node' tools/ tests/ docs/ spec/ Makefile` = 0（仅 spec 附录版本变更记录 1 行按“changelog 除外”保留）；③ `gen_machine_inc.py --check` rc=0（yaml↔两个 `.inc` 一致）；④ QEMU `-M help` 列出 `dadao-tiny`/`dadao-vast`；⑤ parity shim 接受 `dadao-vast`，`PARITY_GEM5_PROFILE=node` 仍映射到 vast。
**新发现/坑**：`check-arch` 的 `integ047t start_busy_returns_busy` 首轮偶发 FAIL（exit 0x62），单探针复跑与整轮复跑均 rc=0——timing 探针偶发，非迁移回归（有据重试 1 次）。L1 复跑曾因并发任务 `m12-chipyard-002` 改写共享组件源而红（`check-patch-tree` chipyard 11 项，与本任务改动无关）；为 L1 复跑改用该组件的隔离检出（运行期构建区），复跑绿。
**遗留问题**：无。`node` profile 别名仅保留在 parity shim 的环境变量映射，按计划由 `m12-integ-001` 删除。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查：`machine_profile.machine_name()` 失败路径、`run_qemu_test._machine_args`、`run_m5_e2e` 机选、`node_probe_prelude`/`min_rom_probe_046t`/`integ046t` 机选、`run_parity`（profile 全量改名 / wrapper / `_check_machines` / 合成自检）、`qemu_gem5_shim`（机器白名单 / `node`→vast / `profile=` 拒绝）、`check_tests_index`/`check_interface_alignment`/`check_components`、Makefile 环境行与 `VAST_BOOTROM*` 变量、bootrom `.S` include、yaml↔`.inc` 派生。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `check-interface` 仍断言 `MACHINE_TYPE_NAME("dadao-m1")`，新补丁用 `DADAO_MACHINE_TYPE_INFO(...)` 注册 → 2 项 FAIL | ✅已修 | 改为同时接受 `MACHINE_TYPE_NAME("<m>")` / `DADAO_MACHINE_TYPE_INFO("<m>"` 两种 needle | `check_interface_alignment.py` 35/35 PASS |
| F2 parity `_check_machines` 残余 `profile=vast` 判据，但新机器无 `profile=` 属性 → 真跑必红 | ✅已修 | 改判 `dadao-vast`（arch/embench），合成行同步 | `run_parity.py --self-test`（L2 链）/证据脚本 shim 检查 PASS |
| F3 证据脚本 tiny 冒烟：16 B raw 被 QEMU 拒（reserved 256 B）；改 260 B 后又因退出码规范为 monitor 段得 0xF9 | ✅已修 | 改为 tiny inst 子集（`semantics_gate --only-profile-cases`）rc 判据 | 证据脚本 `tiny inst subset` PASS |
| F4 shim 曾保留 `dadao-m1` 机器别名，与验收 grep=0 冲突 | ✅已修 | 移除机器别名；仅保留 `node` profile 别名（环境映射，无 `profile=node` 字面量） | 证据脚本 grep 0 命中 + shim 映射 PASS |
| F5 `build_step5_bootrom.py --profile` 默认仍 `node` → build-bootrom 必失败 | ✅已修 | 默认改 `vast`；`run_m5_e2e` 默认 profile 同步 | `check-arch-smoke`/`build-bootrom` PASS |

### 第 1 轮 reviewer 验收

**判决：Accepted**（3 条非阻断 finding 见末尾，交 architect 处置）。以下全部本人现场执行，日志 = 运行期临时日志（未归档），退出码取命令自身。

**重跑记录**
- `make check`（L1）⇒ **rc=0**（34 s，`repository checks (L1): PASS`）；`make check-modules`（L2）⇒ **rc=0**（194 s，`module checks (L2): PASS`）
- `make check-arch`（含 `check-arch-smoke`）⇒ **rc=0**（58 s）：`check-arch-smoke: PASS (forward + permission + 25-service)`、`integ047t 6/6 runtime passed`、`check-arch: PASS (…13 probes)`；另单探针 `DADAO_TEST_PROFILE=vast … integ047t` ⇒ **rc=0（6/6）**，即全量 1 次 + 单探针 1 次均绿、偶发未复现；该例确为既有计时敏感例（INFRA-146t A2：8 次全量 1 败、同 `exit 0x62`），与完成区描述一致
- `make check-inst` ⇒ **rc=0**（18 s）：`985 total, 980 passed, 0 failed, 5 deferred, skipped_profile=44` + `44 total, 44 passed` + `check-inst: PASS (vast full + tiny subset)`，与完成区 980/985 + 44/44 逐字一致
- 证据脚本 `run.sh` ⇒ **rc=0，17/17 PASS**；`run.sh --inject` ⇒ **rc=0，4/4 PASS**（inc 漂移 rc=1、Makefile 旧名命中 rc=0，`cp`+md5 相等后回绿）
- `gen_machine_inc.py --check` ⇒ rc=0（两 `.inc` OK）；`run_parity.py --self-test` ⇒ rc=0（7 类注入全检出）

**约束核验**
- 范围：`git status --porcelain -uall` = **122 行**（118 M + 2 RM + 1 D + 1 ??）= 任务书 1 + 产品 **121**（120 改 + 1 新增 `tests/shared/asm/machine-vast.inc`），与完成区「121 项」对数一致；分布 tools 75 / tests 35 / docs 10 / Makefile 1 / .tao 1；**`spec/`、`contracts/`、`components/`、`manifests/`、`.tao/knowledge/` 改动 = 0** ⇒ 无越界
- 旧名：`git grep`（`dadao-m1` / `profile=node` / `DADAO_TEST_PROFILE=node` / `Machine-v5-Node` / `dadao-node` / `machine-node` × `tools tests docs Makefile`）⇒ **0 命中**；仓内剩余命中全在 `components/`（补丁与 changelog）、`.tao/{archive,adr,tasks,knowledge}`、`manifests` 注释、`spec/Machine-v5-测试机运行环境.md` 附录版本记录 1 行 ⇒ 均历史/记录，非活代码
- 真源一致：yaml `vast`（RAM `0..0x7fffffff`、entry `0x100000`、sp `0x7fff0000`、bootrom `0xffffffc00000`/4 MiB、reset `0xffffffff0000`）↔ `machine-vast.inc` ↔ `linker/dadao-vast.lds`（2 GiB / 4 MiB / `ASSERT _start==RAM+0x100000`）三者一致；抽 3 驱动：`run_qemu_test._machine_args`（vast ⇒ `-machine dadao-vast,bootrom-image=`、tiny ⇒ `-machine dadao-tiny -bios`）、`run_m5_e2e`（同两支）、`node_probe_prelude` / `min_rom_probe_integ046t`（`machine_name(profile)` ⇒ `dadao-vast,bootrom-image=`）
- shim：`dadao-vast,bootrom-image=` ⇒ `('vast',…)`、`dadao-tiny` ⇒ `('tiny',…)`；`dadao-m1` 与 `dadao-tiny,profile=vast` ⇒ **ShimError**；`--profile vast` ⇒ `['…','--profile','vast',…]` 不被拒；`PARITY_GEM5_PROFILE=node` ⇒ `--profile vast`，非法值 ⇒ 拒
- 台账 ff：`git log master..m12-testcases-001` **空**（分支无自有提交）；`b4eb3e56` 仅改 `milestones-m12.md` 2 行；主工作树 `git status` **空**、HEAD 同 `b4eb3e56`
- 完成区 **7 行**（≤30）；完成区/审阅记录运行期路径 grep **0 命中**

**独立注入（engineer 未用的两项；均 `cp`+md5 还原，未用 git 还原）**
- A：`min_rom_probe_030t.py` 两处 `-M dadao-tiny` → `dadao-m1` ⇒ 证据脚本 **rc=1**（`no dadao-m1 … actual=2 hits`）；还原 md5 `61a5c72b…` 与注入前相等 ⇒ 复跑 **rc=0**
- B：`machine-profiles.yaml` 键 `vast:` → `node:` ⇒ `gen_machine_inc.py --check` **rc=1**、证据脚本 **rc=1（5 项 FAIL）**、`make check` **rc=2**（`validate_vectors: FAILED`）；还原 md5 `5fbed570…` 相等 ⇒ `gen rc=0`、`make check rc=0`、证据脚本 rc=0

**`.work` 隔离**：主工作树运行期组件源 11 仓 `git status` **全 0 脏行**、主工作树 status 空；任务 worktree 侧运行期构建/证据/日志及其余组件源为主树符号链接，仅 chipyard 组件源为本任务**隔离检出**（锁基线 + 补丁集恰 1 commit，`check-patch-tree` 的 clean/单 commit/diff==补丁 断言口径不变）⇒ **可接受**，且完成区「新发现/坑」已披露

**非阻断 finding**：① `run_parity.py --self-test` 不在 L2 成员（L2 = inst-smoke/arch-smoke/unit/tset×3/generator-sync），engineer 自审表标「L2 链」不准确（脚本本身 rc=0、注入全检出）；② 未入任何门控的历史探针手跑仍红（`005t`/`030t`/`061t` rc=1），我用**旧机器名 `dadao-m1`** 复跑 `005t`/`030t` 同样 rc=1 且输出一致 ⇒ 非本任务回归，建议登记遗留；③ 2 个改名处于已暂存态（`git mv`，未提交），architect 提交时按完成区对账即可。

#### 收尾（architect，2026-11-09 02:27）

- 判决 **Accepted**：reviewer 自跑 L1(34s)/L2(194s)/`check-arch`(13 探针)/`check-inst`(980/985 + 44/44) 全绿；活动面旧名 `git grep` **0 命中**；`gen_machine_inc --check` rc=0。
- 两式独立反例（驱动改回 `dadao-m1` / yaml `vast`→`node`）均红 → `cp`+md5 还原 → 回绿。
- `.work` 隔离检出已核实**未污染主树**（主树 11 个组件源 0 脏行、status 空），且已在完成区披露。
- 非阻断遗留：`run_parity.py --self-test` 不在 L2 成员（自审表措辞不准）；`005t`/`030t`/`061t` 等历史探针手跑红且用旧名同样红（非本任务回归）—— 登记待另立任务。
