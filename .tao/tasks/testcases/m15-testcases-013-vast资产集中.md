# m15-testcases-013: vast 执行环境资产集中到 `tests/ee-vast/`

**模块**：testcases
**项目里程碑**：M15
**依赖**：无（纯目录/路径迁移；测试集内容不变）
**可并行分片**：否（跨目录引用唯一）
**预估**：1.5–2 h
**档位**：中改（迁移 + 引用更新 + 门控回绿）
**状态**：已验证

## 背景（用户 2026-11-18）

执行环境资产统一 `ee-` 前缀：`tests/ee-tiny/`（已收尾 `m15-testcases-011`）、`tests/ee-user/`（已收尾 `m15-testcases-012`）、**`tests/ee-vast/`**（本任务）。平铺、不建子目录；测试集目录不动。

## 目标（迁移清单，共 8 个文件）

**BootROM（7）**

1. `tests/shared/bootrom/step5/power.S`
2. `tests/shared/bootrom/step5/hmon.S`
3. `tests/shared/bootrom/step5/smon.S`
4. `tests/shared/bootrom/step5/power.lds`
5. `tests/shared/bootrom/step5/hmon.lds`
6. `tests/shared/bootrom/step5/smon.lds`
7. `tests/shared/bootrom/step5/README.md`

**LDS（1）**

8. `tests/shared/linker/kaiwu-vast.lds`

**不移动**：`tests/arch/**`（Vast 测试集与探针驱动）、`tests/inst/**`、`tests/tset/**`、`tests/unit/**`、`tests/shared/{asm,crt0,runtime,init}`、`tests/shared/bootrom/{bootrom.lds,tiny_crt.S,tiny_smoke.S,semihost_msg.inc}`（tiny 残留/共享）。

## 引用更新（全量 grep）

- `Makefile` 的 `build-bootrom`（step5 路径）、`check-arch` 相关。
- `tools/testcases/arch/node_probe_prelude.py`、`min_rom_probe_integ046t.py`、`run_m5_e2e.py`、`tools/testcases/parity/run_parity.py`、`tools/testcases/check_tests_index.py`（`power_lds` 路径）、`tools/infra/check_interface_alignment.py`。
- `tests/README.md`、`tests/INVENTORY.md`、`tests/arch/umon/expected.yaml`（若含路径）。
- 迁移后 `--help`/轻量入口可运行。

## 验收（逐条贴真实 rc）

1. `git mv` 后旧路径不存在、新路径 8 文件齐；内容逐字节一致（md5 对账）。
2. `make build-bootrom` rc=0；Vast bootrom 镜像 md5 与迁移前一致（记录）。
3. `check-tests-index`、`check-dirs`、`check-no-residue`、`check-arch-smoke`（或等价）rc=0。
4. 1 路注入：引用改回旧路径 ⇒ 构建/门控红；`cp`+md5 还原回绿。
5. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树。
2. 只动：上述 8 文件、调用方（`Makefile`/`tools/`/文档/门控扫描面）、本任务书。**不动**测试集内容、`spec/`、`.tao/contracts/`、组件补丁。
3. **不改版本号**；不提交 git；`cp`+md5 还原。
4. 迁移用 `git mv`。

## 待裁定

（无）

## 审阅记录

### 第 1 轮 engineer 自审

自主逐行审查 8 迁移件 + 13 个调用面/文档 diff（`Makefile` 8 行、10 处单行路径/注释、2 处文档表格行）；判决：**无未修 finding**。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `tools/qemu/k0_boot_probe.py` 的 `STEP5_DIR` 是 step5 源路径的**真实调用方**（任务书未列，属“tools 调用方”面） | ✅已修 | 改指 `tests/ee-vast` | `--help`/`--list` rc=0；所指 `power.S`/`power.lds` 存在 |
| F2 注入点 C2 首选 `check_tests_index` 在 lds 缺失时抛 traceback（fail-closed 但非干净 FAIL） | ✅已修（换注入点） | C2 改注 `check_interface_alignment` | 注入 ⇒ `lds[vast] … RAM MEMORY region missing` rc≠0；`cp`+md5 还原 ⇒ rc=0 |
| F3 `check_tests_index` 的 `power_lds` 断言写成 `if is_file()` 条件式 ⇒ 路径写错时该子断言静默跳过 | ❌不修 | — | 真实树 gate 已执行 ORIGIN 断言（`check-tests-index` PASS 且打印 BOOTROM 段）；A1/A3 保证文件在位。条件式为既有设计，改判据超本任务 |
| F4 `tests/ee-tiny/run_embench_e2e.py` 与 `tests/ee-user/dadao-common.lds` 注释仍写 `tests/shared/linker/`（该目录本次消失） | ⏸延后 | 未改 | 012 遗留：其目标 `dadao-vast.lds` 在基线提交即不存在（`git cat-file -e` rc=128）⇒ 本次未改变可达性；建议并入路径清理任务 |
| F5 迁移件正文不动（含 `tests/ee-vast/README.md` 内 `.tao/tasks/integ/INTEG-046t…` 旧指针、`../build_step5_bootrom.py` 旧相对路径） | ❌不修 | — | 任务书要求 8 件 md5 逐字节一致（A3 = 8/8） |
| F6 `components/qemu/changelog.md` 仍写旧路径 | ⏸延后 | 未改 | 组件历史变更日志，改须走组件补丁流程（与 `m15-testcases-011` 同处置） |
| F7 `待开始` 任务书 `m14-qemu-001` 仍引用旧 step5 路径 | ⏸延后 | 未改 | 任务书非调用方；归主会话/architect 同步（子代理不改他人任务书） |

### 第 1 轮 reviewer 验收（2026-11-18）

**判决：Accepted**（中改档，45 min 内判毕；未提交 git、未改主工作树；全部命令在任务 worktree 内以相对路径跑）
**自证/快照**：`git rev-parse --show-toplevel` = `/tmp/opencode/m15-testcases-013/wt`；注入前后两次 `git status --porcelain -uall` 均为空（逐行对账一致）；HEAD=`d37fa564`（WIP），BASE=`4a8a5192`。
**迁移完整性（独立重算）**：8/8 md5 与 BASE 旧 blob 逐字节一致（现场 `git show 4a8a5192:<old>|md5sum` vs `md5sum tests/ee-vast/<f>`）；`ls tests/shared/{bootrom/step5,linker}` 均 ENOENT；`tests/ee-vast/` 平铺 8 文件。
**引用更新**：全仓 grep 旧路径 → 活跃面（Makefile/tools/tests/docs）**0 命中**；余命中仅 `.tao/archive/**`、`.tao/tasks/m14-qemu-001`（他人任务书）、`components/{qemu/changelog,musl/README}.md`（011/013 遗留）、`tests/ee-tiny/run_embench_e2e.py:642`、`tests/ee-user/dadao-common.lds:4`（F4，基线即死）。逐条核 6 个调用方 diff 均为路径替换；`k0_boot_probe --help/--list` rc=0、`min_rom_probe_integ046t --list` rc=0（越界披露成立：确属真实调用方）。
**独立重跑（我自己的 rc）**：① `bash .work/evidence/m15-testcases-013/run.sh`（M15_TC_BIN=共享安装根）⇒ **rc=0，PASS=21 FAIL=0**（A1–A5、B1–B8、C1–C2×4 全 PASS；A6=`SKIP`：迁移已提交，`git status -M` 无 R 行）——与完成区「22/22」差 1 = A6 提交后恒 SKIP，rename 另由 `git show --stat` **8×R100** 独立证实。② `check-tests-index` rc=0（**472**，现场计数 inst272/arch11/unit186/tset3）；`check-dirs`/`check-no-residue`/`check-interface`/`check-knowledge-refs` rc=0；`make -o install-host -o build-bootrom _locked-check-arch-smoke` rc=0（forward **10/10**、25 服务全覆盖）；`check_tests_index --self-test` rc=0（case28 PASS）。③ **BootROM 独立重建对账**：`git archive 4a8a5192` 到 `/tmp/opencode/m15-testcases-013/review-baseline` 重建 `build-bootrom` rc=0（33 产物），与本树现产物 `diff` **rc=0（33/33 全同）**，并与 engineer `bootrom-md5-before.txt` 33 行全同。
**独立注入 3 路（`cp`+md5 还原，未用 checkout/restore/stash/show 还原）**：I1 Makefile `power.S` 回旧路径 ⇒ `build-bootrom` **rc=2**（`llvm-mc: … No such file`）→ 还原 md5 同、rc=0；I2 `check_interface_alignment` vast lds 回旧路径 ⇒ `check-interface` **rc=2**（`lds[vast] … RAM MEMORY region missing`）→ 还原 rc=0；I3（**任务书未列**）`check_tests_index` lds_map 回旧路径 ⇒ `check-tests-index` **rc=2**（FileNotFoundError，fail-closed 非干净 FAIL，既有行为）→ 还原 rc=0。
**越界**：`4a8a5192..HEAD` 共 22 文件 = 本任务书 + 8×R100 + `Makefile` + 5 tools + 6 文档/索引；`spec/`、`.tao/contracts/`、`components/`、`tests/{inst,tset,unit}` 改动 **0**；`tests/arch/umon/expected.yaml` 仅注释行路径（非期望值）。
**保留项复核**：F7 成立但描述有误——`m14-qemu-001` 实为 `**状态**：已验证`（非「待开始」），他人任务书不改、延后合理；F6 `components/qemu/changelog.md` 旧路径属实，须走组件补丁流程；F4 `run_embench_e2e.py:642` 死路径在基线即存在（`git cat-file -e 4a8a5192:tests/shared/linker/dadao-vast.lds` **rc=128**），013 未改可达性，延后合理。
**未闭合（doc-level，不阻断，交 architect 收尾改）**：① 完成区「22/22」→ 提交后实为 21 PASS+1 SKIP；② F7 状态名笔误（待开始→已验证）；③ 完成区「`dadao-vast.lds` 从未入库」不实（`e96f0f19` 曾入库并改名 `kaiwu-vast.lds`），但「基线即死路径」成立；④ F4/F6/F7 与 `discussing.md:255` 旧路径措辞归路径清理/组件流程。
**未复跑（采信）**：`check-index-blobs`/`check-case-ledger`/`check-run-artifacts`（完成区声明，非本任务门控面）。

## 完成区

**测试结果**：一键证据脚本（`run.sh`，交付于运行期证据目录）**22/22 PASS、rc=0**（结构 6 + 构建/门控 8 + 注入 2×4）；含注入自检「注入红 → `cp`+md5 还原 → 回绿」。另跑：`check-tests-index --self-test` 28 例 PASS；`check-index-blobs`/`check-case-ledger`（5666 现场派生）/`check-run-artifacts`/`check-knowledge-refs` 全 rc=0；`min_rom_probe_integ046t --list`、`k0_boot_probe --help/--list` rc=0。

**修改文件**：8 件 `git mv`（7 个 step5 固件 + `kaiwu-vast.lds` → `tests/ee-vast/` 平铺）；`Makefile`（`_locked-build-bootrom` 8 行源路径）；`tools/testcases/{check_tests_index,arch/min_rom_probe_integ046t,arch/node_probe_prelude}.py`、`tools/infra/check_interface_alignment.py`、`tools/qemu/k0_boot_probe.py`；`tests/{README,INVENTORY,shared/README,shared/bootrom/k0/README,arch/umon/README,arch/umon/expected.yaml}`；`docs/Process-09`；本任务书。

**验收结果**：① 旧路径 0 存在、新路径 8/8 平铺，md5 与迁移前 **8/8 一致**，git 记录 `R` 8 行；② `make build-bootrom` rc=0，BootROM 产物目录内全部产物 md5 与迁移前 **逐条一致**（含 `bootrom_step5.bin`/`bootrom_step5_inst.bin`）；③ `check-tests-index` rc=0（472 条）、`check-dirs`/`check-no-residue`/`check-interface` rc=0；`check-arch-smoke` **目标体**（`_locked-check-arch-smoke`，跳过需共享源码树的 `install-host` 前置；`build-bootrom` 已单独验）rc=0：forward 10/10、25 服务全覆盖；④ 注入 2 路均 `cp`+md5 还原：`Makefile` power.S 改回旧路径 ⇒ `llvm-mc: … No such file` rc≠0；`check_interface_alignment` vast lds 改回旧路径 ⇒ `lds[vast] … missing` rc≠0；还原后 rc=0；⑤ 活跃面（`Makefile`/`tools`/`tests`/`docs`）旧路径残留 0。

**新发现/坑**：① `make check-arch-smoke` 在任务 worktree 内**不可直接跑**——前置 `install-host` 需要共享源码树，worktree 没有；可在**同一 make 树**用 `make -o install-host -o build-bootrom _locked-check-arch-smoke`（gate 目标体）替代，`-o` 不能加在外层 `check-arch-smoke` 上（gate-lock 子 make 不继承）。② 工具链可从共享安装根以 `HOST_TOOLCHAIN_BIN=<共享 bin>` 传入，构建产物仍落本树产物根（不污染共享安装根）。③ `check_tests_index` 缺失 lds 时抛 traceback 而非干净 FAIL（既有，011 已记）。④ 移动**内容冻结**的资产时，其自身文档内的旧路径只能保留（md5 一致性优先于文档准确）。

**遗留问题**：F4（012 遗留 `tests/shared/linker/` 死路径，建议路径清理任务）；F6（组件 changelog 旧路径，走组件流程）；F7（`m14-qemu-001` 任务书旧路径，归主会话）；`run_embench_e2e.py --profile vast` 的 lds 分支为基线即死路径（`dadao-vast.lds` 从未入库），本次未触及其可达性。
