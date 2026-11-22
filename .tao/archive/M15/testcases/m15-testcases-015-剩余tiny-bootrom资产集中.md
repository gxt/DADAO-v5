# m15-testcases-015: 剩余 tiny bootrom 资产集中到 `tests/ee-tiny/`

**模块**：testcases
**项目里程碑**：M15
**依赖**：`m15-testcases-011`/`014`（ee-tiny 已建立；本任务补齐遗漏）
**可并行分片**：否（跨目录引用）
**预估**：1.5–2 h
**档位**：中改
**状态**：已验证

## 背景（用户 2026-11-18）

`tests/shared/bootrom/` 仍残留 tiny 资产未被 011 的清单覆盖。按「tiny 的 bootrom/lds/脚本集中到 `tests/ee-tiny/`」口径补齐。

## 目标（迁移清单，共 11 个文件）

**k0 固件目录（7）**

1. `tests/shared/bootrom/k0/README.md`
2. `tests/shared/bootrom/k0/hmon.S`
3. `tests/shared/bootrom/k0/hmon.lds`
4. `tests/shared/bootrom/k0/smon.S`
5. `tests/shared/bootrom/k0/smon.lds`
6. `tests/shared/bootrom/k0/probe_kernel.S`
7. `tests/shared/bootrom/k0/probe_kernel.lds`

**BootROM 杂项（4）**

8. `tests/shared/bootrom/bootrom.lds`
9. `tests/shared/bootrom/tiny_crt.S`
10. `tests/shared/bootrom/tiny_smoke.S`
11. `tests/shared/bootrom/semihost_msg.inc`

**不移动**：`tests/shared/bootrom/` 下若有其它多机型文件（迁移后复查）；`tests/ee-vast/**`、`tests/ee-user/**`、`tests/inst/**`、`tests/arch/**`。

## 引用更新（全量 grep）

- `tools/linux/check_k1.py`、`tools/qemu/k0_boot_probe.py`、`tools/linux/semihost_pa_probe.{S,lds}`、`tools/linux/semihost_readc_probe.S`、`tools/linux/check_k0.py` 等（`bootrom/k0` 路径）。
- `tests/ee-tiny/semihost_smoke.S`、`tests/ee-tiny/run_semihosting_smoke.py`（`semihost_msg.inc`）。
- `Makefile`（`build-bootrom` 的 `k0`/`bootrom.lds` 路径）。
- `tests/README.md`、`tests/INVENTORY.md`、`tests/shared/README.md`。
- 迁移后 `k0/hmon.S` 的 `OPEN_SUPV_ALL`/`K2_TIME_PERM` 引用与 `m14-testcases-006` 的 md5 记录保持一致（**不改内容**，只改路径）。

## 验收（逐条贴真实 rc）

1. `git mv` 后旧路径 0、新路径 11 文件齐；内容逐字节一致（md5 对账；`k0/hmon.S` 与 `m14-testcases-006` 的 bootrom md5 `b662183a` 构建结果一致）。
2. `make build-bootrom` rc=0（K0/K1 镜像 md5 不变）；`check-linux-k0`（119/119）、`check-linux-k1`（112/112）rc=0。
3. `check-tests-index`、`check-dirs`、`check-no-residue`、`check-interface` 全 rc=0。
4. 1 路注入：引用改回旧路径 ⇒ 构建/门控红；`cp`+md5 还原回绿。
5. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树。
2. 只动：11 文件 + 调用方/文档 + 本任务书；**不动**测试集内容、`spec/`、`.tao/contracts/`、组件补丁。
3. **不改版本号**；不提交 git；`cp`+md5 还原。
4. 迁移用 `git mv`。

## 待裁定

**D1 已裁定（2026-11-18，主会话按事实判定；无需再问用户）：`k0/` 7 件归 `tests/ee-vast/`。**

- 事实依据：原 `tests/shared/bootrom/k0/README.md` 自述为 **Kaiwu-Vast K1 boot 链**固件，
  `tools/qemu/k0_boot_probe.py` 在 `-M kaiwu-vast` 上跑、`check-linux-k0`/`check-linux-k1` 消费；
  按 `docs/Process-09 §6`「只服务一个执行环境 ⇒ `ee-<env>/`」归 `tests/ee-vast/`（与 step5 同环境）。
- 落点：`tests/ee-vast/k0_README.md`、`tests/ee-vast/k0_{hmon,smon,probe_kernel}.{S,lds}`
  （保留 `k0_` 前缀，与 step5 的 `hmon.S`/`smon.S` 区分；内容零改动）。
- Tiny 侧只收 4 个散件：`tests/ee-tiny/{bootrom.lds,tiny_crt.S,tiny_smoke.S,semihost_msg.inc}`。

## 审阅记录

### 第 1 轮 engineer 自审

自主逐行审查 15 个改动文件 + 11 件迁移（`git diff`/`git diff --stat` 逐行看）；判决：**无未修 finding**（F5/F6 属预存/环境，非本改动缺陷）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `tests/ee-tiny/semihost_smoke.S` 的 `.include` 改新路径会改变被汇编载体 | ✅已修（并证实无副作用） | `.include "tests/ee-tiny/semihost_msg.inc"` | `build-bootrom` rc=0 且 4 个 `semihost_*.elf` md5 与迁移前逐一致（include 只换路径、内容同） |
| F2 `k0/` 7 件平铺同名冲突（`ee-tiny/hmon.*` 已存） | ✅已修（裁决待定） | 加 `k0_` 前缀；写入「待裁定 D1」 | A1/A2/A3 11/11；`git mv` 前先判重名（直落会被 git 拒绝） |
| F3 `tools/linux/k1_boot_probe.py` 硬编码 `K0_DIR + "/hmon.S"`，任务书未列 | ✅已修（越界披露：真实调用方） | 改为 `"/k0_hmon.S"` | `check-linux-k1` **112/112** rc=0 |
| F4 任务书列了 `tools/linux/check_k0.py` 但该文件无 `bootrom/k0` 路径 | ✅核查（0 处需改） | 未改 | `grep -n "bootrom" check_k0.py` 仅命中 git 作者名 `k0`，无路径 |
| F5 `check-arch-smoke` 在本 worktree 跑不起来 | ⏸延后（环境） | 未改 | 前置 `install-host` 需共享 llvm 源树；本任务私有 work root 只链 linux/musl/qemu ⇒ `CMake: source directory ... does not exist`。替代证据见「遗留问题」 |
| F6 迁移件正文冻结（`k0_smon.S` 注释仍写旧目录） | ❌不修 | — | 任务书要求 11 件 md5 逐字节一致（A3 11/11）；证据脚本 B1 单列该命中为 INFO |
| F7 自建日志名触发 `check-run-artifacts` A3 | ✅已修 | 日志改为 `<TASK-ID>-<purpose>.log` | 复跑 A3：本人 0 条；余 51 条 mtime 早于本任务开工（`m14-linux-012`/`m14-testcases-006`/`linux`） |

### 第 2 轮 engineer 自审（D1 裁定后的返工）

按主会话 D1 裁定把 `k0_*` 从 `tests/ee-tiny/` 再迁到 `tests/ee-vast/`，逐行复审全部落点与证据脚本；判决：**无未修 finding**。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F8 证据脚本的守卫路径、`PAIRS` 与注入 sed 仍指 `ee-tiny` ⇒ 守卫 FATAL、I2 注入注入「同值」假 FAIL | ✅已修 | 守卫/7 条 `PAIRS`/I2 sed 目标/冻结注释白名单改 `ee-vast/k0_*`；新增 A5「`ee-tiny` 无 `k0_*` 残留」 | 默认 34/34、`WITH_LINUX=1` 36/36、`--inject` 8/8（I2 注入后 k0_probe rc=1：`llvm-mc: No such file`；`cp`+md5 `1e9f322a…` 还原回绿） |
| F9 文档两行（`tests/README` 的 ee-tiny/ee-vast 行）需按新落点重新切分 | ✅已修 | ee-tiny 行去 `k0_*`；ee-vast 行补 `k0_*` 与 `check-linux-k0{,-k1}`/`k0_boot_probe` 消费方 | 全仓 `grep ee-tiny/k0_` = 0 命中 |
| F10 `check_k1.py` 的 `BOOTROM_MAGIC` 注释、`gen_machine_inc.py` 的「Makefile 直接汇编哪些目录」注释已过时 | ✅已修 | 前者指 `tests/ee-vast/k0_*`；后者改 `tests/ee-{tiny,vast}/*.S` | `check-linux-k1` 112/112；`gen_machine_inc --check` 未受影响的生成物不变（`build-bootrom` 全绿） |
| F11 `tests/ee-tiny/__pycache__`（`check_tests_index` 的 `sys.path` 副作用） | ❌不修 | — | 已被 `.gitignore` 忽略，`git status -uall` 不列；`check-no-residue` rc=0 |

### 第 1 轮 reviewer 验收（2026-11-18；中改；全部本人重跑）

**工作树自证**：`/tmp/opencode/m15-testcases-015/wt`，分支 `m15-testcases-015`，HEAD `2948a25e`，开工 `git status -uall` 空（基线干净）。

**迁移完整性（本人重跑）**
- `git ls-tree -r --name-only HEAD~1 tests/shared/bootrom` = **11 件**（恰为清单）；11 对新位 `md5sum` 与 `git show HEAD~1:<old>` **逐一致，MISMATCH=0**；`ls tests/shared/bootrom` → `No such file or directory`（rc=2）；新位 11/11 在位。
- 全仓 `grep -rn "tests/ee-tiny/k0_"` = **0**；`tests/shared/bootrom/k0` 残留 34 处，全部落在：本/历史任务书 5、`components/linux/{changelog,4 补丁}` 5、`tests/ee-vast/k0_smon.S:39`（md5 冻结）1 —— 代码面（`Makefile`/`tools/`/`tests` 的 `.S/.py/.lds/.inc`）**0**（脚本 B1 PASS exp=0 act=0）。
- 调用方逐条核：`k0_boot_probe.py` `K0_DIR/STEP5_DIR`=ee-vast + 7 个 `k0_*` 文件名；`k1_boot_probe.py:341` `k0_hmon.S`；`check_k1.py` 注释指 `tests/ee-vast/k0_*`；`Makefile` 4 行 lds/`.S` 路径；`check_k0.py` grep 无该路径（rc=1，0 处）；4 份文档（tests/README、INVENTORY、shared/README、arch/README）+ `docs/Process-09` 新增 2026-11-18 更新段与 §6 glue 路径一致。

**独立重跑（真实输出/退出码）**
- `make build-bootrom` → **rc=0**（1.6 s）；10 产物 md5 全 == `baseline-md5.txt`：`bootrom.bin b8c88a3e`、`bootrom_app.bin c0ef98d0`、`tiny_smoke.elf db0dc649`、`tiny/bootrom_tiny.bin 51430087`（== `tests/arch/hmon/expected.yaml::shared_bootrom_md5`）、`step5/{bootrom_step5,bootrom_step5_inst}.bin b3d90294/00883cc0`、4 个 semihost ELF —— **mismatch=0**。
- `DADAO_TMP_ROOT=… python3 tools/qemu/k0_boot_probe.py` → **rc=0，`result: 101 passed, 0 failed`**；`bootrom_k0.bin` md5 **`b662183a70586e2f463f0811a04a6e0e`** == baseline。
- L1：`check-tests-index` **rc=0（结果: PASS，472 条）**、`check-dirs` rc=0（`check-dirs: PASS`）、`check-no-residue` rc=0（`PASS`）、`check-interface` rc=0（`全部机械可判定项 PASS`，Schema 41 + Opcodes 8）。
- `make check-linux-k0`：默认共享树 **rc=2，116/119**（仅 K12：`apply-series: linux HEAD (0a2d2cfcc42b) is neither base (7b20d05fd38d) nor base+1 matching the patch set`）；将 `manifests/components.lock.toml` 的 `work_root` 临时改 `../work`（本任务私有 linux 树 76 补丁 == 仓库 76）后 **rc=0，119/119**；`make check-linux-k1` **rc=0，`check-linux-k1: PASS (112/112)`**；跑完 `cp`+md5 还原 `5c4a8cc5…`、`git status -uall` 空。
- 证据脚本 运行期证据目录内的 `run.sh`：默认 **rc=0，`checks: 34 passed, 0 failed`**；`WITH_LINUX=1`（同上临时 work_root，跑完还原）**rc=0，`checks: 36 passed, 0 failed`**；`--inject` **rc=0，`checks: 8 passed, 0 failed`**，且红路径真实：`ld.lld: error: cannot find linker script tests/shared/bootrom/bootrom.lds`、`llvm-mc: error: …/tests/shared/bootrom/k0/k0_hmon.S: No such file or directory`。

**独立注入 2 路（均非任务书列明的注入点；一律 `cp`+md5，未用 checkout/restore/stash/show）**
- **IC（未列）** `tests/ee-tiny/semihost_smoke.S` 的 `.include` 改回旧路径 → `make build-bootrom` **rc=2**（`Could not find include file 'tests/shared/bootrom/semihost_msg.inc'`）→ 还原 md5 `a0ae36fd…` → **rc=0**。
- **ID（未列）** `tests/ee-tiny/run_semihosting_smoke.py` 的 `_MSG_INC` 改回旧路径 → `make linux-semihosting-smoke` **rc=2**（`SETUP ERROR: …/tests/shared/bootrom/semihost_msg.inc not found`）→ 还原 md5 `b4eb8b0d…` → **rc=0**（`run_semihosting_smoke: PASS (failed checks: 0)`）。

**约束核验**
- `$BASE..HEAD` 仅 27 文件 = 本任务书 + 11 件 `git mv`（rename0 行改动）+ 调用方/文档；`spec/`、`.tao/contracts/`、`contracts/`、`components/`、`manifests/`、`tests/inst/`、测试集内容 **0 改动**；`tests/arch/README.md` 仅 1 行文档。
- 无 `cmd | tee`（全部重定向落盘 + 单独取 `$?`）；探测均带 `timeout`，无 124 通过项；**未提交 git**（HEAD 仍 `2948a25e`）；结束快照：`git status -uall` 空、4 个注入目标 md5 与开工快照逐一相等、`work_root` 已回 `.work`。
- 归属 D1：`k0_README.md` 首行自述 **Kaiwu-Vast K1 boot chain**；`k0_boot_probe.py:403` `-machine kaiwu-vast`；`check_k1.py PROFILE="vast"` + `-machine kaiwu-vast,bootrom-image=`；`docs/Process-09:229`「只服务一个执行环境 ⇒ `ee-<env>/`」⇒ 归 `tests/ee-vast/` 成立。
- `check-arch-smoke` BLOCKED 的**替代证据判定：充分**——该门控独占输入只有「安装根工具链（本任务未重建）+ bootrom 产物（10 件 md5 逐一致）+ `tests/arch/**`/min-ROM 探针（未改，仅 README 1 行）」；11 件迁移文件的全部消费方我已直接覆盖（4 散件→`build-bootrom`+`linux-semihosting-smoke`；`k0_*` 7 件→`k0_boot_probe`+`check-linux-k0/k1`）。
- 预存红三项确与本任务无关（本人跑）：`check-knowledge-refs` rc=2 唯一命中在 **本任务未改动** 的 `.tao/tasks/testcases/m15-testcases-013-*.md:81`；`check-run-artifacts` rc=2，A3 非法 **51 条**（汇总行 `51 illegal`）且 `grep m15-testcases-015` = **0**；`check-temp-dirs` rc=2，5 项全是 `m14-*` 陈旧目录；K12 红因 `$BASE..HEAD` 不含 `components/`/`manifests/` ⇒ BASE 同红。

**finding（非阻断，交 architect 收尾处理）**：① 遗留① 的 BLOCKED **归因不准**——`LLVM_SRC/QEMU_SRC/LLVM_BUILD/QEMU_BUILD` 是 Makefile 硬编码 `.work/**`（实测 `ninja -n` LLVM `no work to do`、QEMU 尚有 22 步待链接），与 `work_root` 无关；真实不宜跑的理由是共享安装根/构建树处在途任务窗口（AGENTS「禁边构建边测试」，我因此未跑 `install-host`）。② 冻结正文 1 处 `k0_smon.S:39` 仍指旧路径（md5 冻结，已声明）。③ `k0_README.md`「power.S/power.lds — not here（`tests/ee-vast/`）」迁入后自指，待下次内容修订（已声明）。

**判决：Accepted** —— 验收命令块在我的重跑下全绿、硬约束无违反；BLOCKED 项替代证据充分。本判决仅证明工程师达标，最终接受权在 architect。

## 完成区

**测试结果**：一键证据 `run.sh` 默认 **34/34**、`WITH_LINUX=1` **36/36**、`--inject` **8/8**（逐项 rc 见运行期日志）。
- 迁移：11/11 新路径在位、旧路径 0、md5 与迁移前提交逐字节一致、`tests/shared/bootrom/` 目录已消失、`tests/ee-tiny/` 无 `k0_*` 残留（4 散件入 ee-tiny、`k0_*` 7 件入 ee-vast）。
- 引用：代码面（`Makefile`/`tools/`/`tests` 的 `.S/.py/.lds/.inc`）旧路径 **0**、`ee-tiny/k0_*` 旧落点 **0**；迁移件正文冻结 1 处、组件/历史文档 11 文件只报告（见遗留）。
- 构建：`make build-bootrom` rc=0，10 个产物 md5 与迁移前逐一致（`bootrom.bin` `b8c88a3e…`、`tiny/bootrom_tiny.bin` `51430087…`、`step5` 两镜像、4 个 semihost ELF）；`k0_boot_probe` 101/101，K1 镜像 `b662183a…` 不变。
- 门控：`check-linux-k0` **119/119**、`check-linux-k1` **112/112**、`check-tests-index`（472 条）/`check-dirs`/`check-no-residue`/`check-interface` 全 rc=0。
- 注入：`Makefile` 的 `bootrom.lds` 改回旧路径 ⇒ `build-bootrom` rc=2（`ld.lld: cannot find linker script`）；`k0_boot_probe` 的 `K0_DIR` 改回旧目录 ⇒ rc=1（`llvm-mc: No such file`）；`cp`+md5 还原（`6b42627d…`/`1e9f322a…`）后回绿。
**修改文件**：11 件 `git mv`（4 件同名入 `tests/ee-tiny/`；`k0/` 7 件加 `k0_` 前缀入 `tests/ee-vast/`，见「待裁定 D1」）；`Makefile`（4 行）；`tools/qemu/k0_boot_probe.py`（`K0_DIR` → ee-vast + 7 文件名 + 2 处 docstring）、`tools/linux/k1_boot_probe.py`（1 行）、`tools/linux/{check_k1.py,semihost_pa_probe.S,semihost_pa_probe.lds,semihost_readc_probe.S}`（路径/注释）、`tests/ee-tiny/{semihost_smoke.S,run_semihosting_smoke.py}`、`tests/{README,INVENTORY,shared/README,arch/README}.md`、`docs/Process-09`、`tools/testcases/arch/gen_machine_inc.py`（注释）；本任务书。任务书列举的 `check_k0.py` 经 grep **0 处**含该路径。
**验收结果**：同上逐条 rc 对齐；运行期证据（`run.sh` 含 `--inject` 自检；K0/K1 在任务私有 linux 源/构建树上跑）与日志留在运行期证据/日志目录，未入库。
**新发现/坑**：① `tests/shared/bootrom/k0/` 实为 **Vast K1 boot 链**固件（D1 已按事实裁定归 ee-vast；任务书原「tiny 残留」口径只对 4 散件成立）；② 平铺同名冲突必然（`ee-tiny/hmon.*`、`ee-vast/hmon.S`/`smon.S` 均已存在）⇒ 迁移前须判重名，`k0_` 前缀即区分手段；③ 共享 linux 源树被在途任务占据 ⇒ K12 红（**BASE 同红**；实测共享树 HEAD 树 == `m14-linux-019` 分支补丁集），K0/K1 须在任务私有 linux 源/构建树上跑；④ `.work/log/**` 文件名门控只认 `check-<name>.log` / `<TASK-ID>-<purpose>.log`，自建日志须带任务号（且勿批量改名他人日志）；⑤ 证据脚本的注入点与守卫路径须随落点一起改，否则「注入=同值」会变成假 FAIL。
**遗留问题**：① `check-arch-smoke` **BLOCKED**（前置 `install-host` 需共享 llvm 源树；本任务私有 work root 只链 linux/musl/qemu，且在途 linux 任务窗口内不宜跑共享 `install-host`）⇒ 替代证据 = 全部 bootrom 产物 md5 与迁移前逐一致（含 `tests/arch/hmon/expected.yaml` 钉住的 `tiny/bootrom_tiny.bin`）+ `k0_boot_probe` 101/101 + K0/K1 119/112。② 预存红（BASE 同红、非本任务）：`check-knowledge-refs`（`m15-testcases-013` 任务书含具体 `.work/**` 引用）、`check-run-artifacts` 余 51 条他人非法日志名、`check-temp-dirs` 5 个陈旧临时目录。③ 组件/历史文档旧路径按 013 先例未改（`components/{chipyard,linux}` 与 4 份 linux 补丁注释、3 处历史迁移注记）；迁移件注释因 md5 冻结保留：`k0_smon.S:39` 仍写旧目录；`k0_README.md` 的「`power.S`/`power.lds` — **not here**（`tests/ee-vast/`）」一句在迁入同目录后已自指，建议随下次内容修订一并改（本任务禁改正文）。
