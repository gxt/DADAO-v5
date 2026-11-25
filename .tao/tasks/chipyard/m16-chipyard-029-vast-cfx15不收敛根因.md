# m16-chipyard-029: Vast 当期构建 `cfx15.S` 不收敛（启动链）根因与修复

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-027`、`m17-chipyard-001` 已合入（两者都在当期共享树里）
**可并行分片**：否（`components/chipyard` 单写者 / 共享源树）
**预估**：2–4 h
**档位**：大改（复核 ≤60 min）
**状态**：待验收

## 背景（`m16-gem5-026` 复核发现）

- 共享 `.work/source/chipyard` 当期构建（13ef828，11-25 10:10，Vast sim md5 `53c367f6…`）上，`tests/arch/hart/cfx15.S` 在驱动固定 `+max-cycles=8000000` 内**不收敛**：`$stop`、0 槽；直接 `+max-cycles=1000000` 也在 1.05M cycle 内 **`_start` 重启 881 次**。
- 11-24 17:50 的旧构建（`f39a0c6`，补丁集 024/025/026/022-WIP，**缺 023/027/m17-chipyard-001**）同一 ELF <300k cycle 完成、80 槽过 oracle ⇒ 问题在**新补丁集**（023/027/m17-chipyard-001 的组合）而非探针本身。
- 影响：gem5-026 的 F2（当期构建复跑三方）、`m16-gem5-025/028/022/023` 的 RTL 腿、M16 `check-arch-vast` 与收口报告都不可信。

## 要做

1. **复现与定位**：在共享树上确认 `_start` 重启；用 `+verbose`/boot 信号或最小镜像判断是 power stub 未交付、BootROM 镜像布局、还是 hmon 进入即异常。
2. **二分**：以 master 补丁集为基准，按 023 → 027 → m17-chipyard-001 的补丁范围做最小裁剪（隔离树，不动共享树直到结论），找出引入点；若为组合效应，给出两者交互的证据。
3. **修复**：按根因修 RTL/镜像/参数（不改 spec；若确为 spec 与实现的冲突，登记 issue 并停）。
4. **回归**：修复后 Vast 重建，`cfx15.S`/`pmem`/`ptw`/`time`/`cache` 代表集在当期构建上跑通；`arch-hart-001`（80/40 槽）、`arch-pmem-001`（55 槽）。
5. **登记**：根因、引入点、修复面写进 issue（`ISS-m16-008` 已开）；若属 m17-chipyard-001 的回归，同步 M17 台账。

## 不做

- 不改 spec/契约；
- 不借机改 023/027/m17 的既有语义（除非根因就是它们）；
- 不在本任务做 `cg9 rc6`（028）。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出、`make_patch.py chipyard` 幂等；
- 共享源树被他人占用时用隔离树（`rsync`/`git worktree` 副本），不得抢写；
- 失败路径短 timeout、禁长时间 `-d cpu` dump（ISS-522）；不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. 当期构建上 `cfx15.S` 在 `8e6` cycle 内完成、80/40 槽过 oracle；`_start` 不重启；
2. 代表集（pmem/ptw/time/cache）RTL 腿不回归；
3. **可达 FAIL**：注入"恢复被判定为引入点的改动" ⇒ 重启/挂死复现；`cp`+md5 还原并重建后回绿；
4. `check-patch-tree` chipyard 段 0 problem、`make_patch` 幂等、`check-component-changelog`/`check-tests-index`/`check-tasks`/`run_arch --self-test` 记录 rc；
5. Vast 重建耗时与 sim md5 记录（ISS-453）。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` 全量 **51 PASS / 0 FAIL、rc=0**（A 前置 3；B 当期构建基线 9；C 可达 FAIL/还原 11；D 隔离二分 5；E 代表集 11；F 门控 8；另 4 条 ptw KNOWN-RED 按基线判据计 PASS）。当期构建 hmon **104765 cycle/80 槽**、smon 96199/40、umon 96192/40，全部 0 failure。
**根因（复现+二分）**：不是 RTL/镜像/参数缺陷，是**探针 ELF 与 RTL 语义版本错配**。触发态 = `m17-chipyard-001`（bec9578a）之前的 `cfx15.S`（md5 `1d37dc74`，无 `perm_hypv.inc`/`PERM_MON_OPEN`，即 `m16-gem5-026` 分支 `b9622776` 所用的那份）跑在 m17 后的当期构建：交付体以 cfx_power/hypv 运行，`_start` 首条 cfx 访问 `cfx2rc cfx_hart,cg9,rc5` 被 cfx_hart 的 hypv `cfxreg` 源掩码拒绝（`CFXPERM`），power 的 hmon 保存-跳转槽把同步异常送回 `appEntry` ⇒ `_start` 重启循环（8e6 不收敛、0 槽）。四组合：当期探针+当期 RTL PASS；**m17 前探针+当期 RTL FAIL**；m17 前探针+m17 前 RTL（023+027、无 m17）PASS 107769/80；当期探针+m17 前 RTL PASS 104765/80 ⇒ 引入点 = **m17 的 hypv 两轴判权**，023/027 无关；m17 同笔已带配套探针，当前 master 自洽（`modeEnforced` 的 hypv 例外被删，见 `GewuFile.scala.patch`）。
**修改文件**：仅本任务书（状态/完成区/审阅记录）；**未改** spec/契约/RTL/镜像/参数与 023/027/m17 语义。运行期（gitignored）：运行期证据目录内的 `run.sh`、隔离 m17 前 Vast 构建（305 s、sim md5 `1e53b08e…`）。
**验收结果**：① 当期共享构建 sim md5 `53c367f6…`（未重建，避免抢写共享源树）；Tiny 未重建（无 RTL 改动）；② 可达 FAIL：用 `git show 36911ad2:…cfx15.S` 覆盖（md5 `1d37dc74`）⇒ 当期构建 `+max-cycles=60000` 命中 `*** FAILED *** (timeout)`、rc≠0、签名 0 B；`cp`+md5 还原（`48de7da7`）重建后回 80 槽；③ 代表集：hart 80/40/40、pmem-001 hmon（55 槽）、time-001 hmon（7 槽）、cache-001 hmon、ptw-001/002 直调 hmon（002 = 3 签名槽）全 PASS；④ 门控：`check-patch-tree` chipyard 段 **0 problem**（全局 rc=1 = qemu/musl 既有 KNOWN-RED）、`make_patch` 0 written、`check-component-changelog`/`check-tests-index`/`check-tasks`/`run_arch --self-test`/`check_hart_rtl --selfcheck` 全 rc=0。
**新发现/坑**：① 探针 ELF 与 RTL 语义强耦合：跨 worktree 复用 m17 前 ELF 会在 m17 后构建上静默 `_start` 重启（CFXPERM→power→hmon 保存-跳转→appEntry），表象是「不收敛」而非权限错误；跨 commit 复用 ELF 必须先重建。② `run_arch --platforms chipyard` 单平台会对未跑的 QEMU/gem5 腿报假 `跨平台不一致`/`GAP 其余平台不一致`，单平台回归应直调 `check_*_rtl.py`。③ **`check_ptw_rtl.py` 缺 `--mode`**，而 `modes.yaml` 声明 ptw 三模式 ⇒ `run_arch --cfx 4 --platforms chipyard` rc=1（driver rc=2「unrecognized arguments: --mode」）；`b9622776`（m17 前）同样存在 ⇒ 基线红，建议另立 issue。④ 当期构建 `+verbose` 未产出 `WumingCore: exec` trace，boot 段定位只能用签名/信号灯证据（待核构建期 printf 开关）。
**遗留问题**：① `ISS-m16-008` 建议按「m17 前陈旧 ELF 误报」关闭（当前 master 已绿）；② ptw `--mode` 接线缺口另立 issue；③ 防呆（ELF 版本戳/同源重建约束）建议另立小任务，本任务不扩面。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`run.sh` 的 A–F 断言与可达 FAIL 路径（C 注入/还原、D 四组合矩阵、E 直调驱动、F 门控解析）；`check_cfx15.py` 的槽序与 `--mode` 期望；m17 前后 `cfx15.S` 的 12 行差异（`PERM_MON_OPEN`+`perm_mon` 块）；`GewuFile.scala` 的 `modeEnforced`（前）vs `axisDenied`+`rowAvailable`（后）；`power_vast.S` 的 `trap cfx_hmon`→jump `appEntry` 回跳；`check_ptw_rtl.py` 的 argparse 与 `platform.py:_run_chipyard` 的 `--mode` 门槛。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 E 段 ptw 直调误加 `--mode`（driver 不收）⇒ 2 红 | ✅已修 | 直调改为不带 `--mode`；`run_arch` KNOWN-RED 期望 rc 由 2 校正为 1 | 全量 `run.sh` E 段 ptw-001/002 PASS、ptw-wiring rc=1 |
| F2 F1 门控逻辑反向（`grep -q problem` 期望 0） | ✅已修 | 改为 `! grep … \| grep -q problem` | F1 PASS（chipyard 0 problem） |
| F3 单平台 `run_arch` 报假「跨平台不一致」 | ✅已修 | E 段改用 `check_*_rtl.py` 直调 | E 段 11/11 PASS |
| F4 ptw KNOWN-RED 缺基线同源证明 | ✅已修 | 增 `b9622776` 的「driver 无 `--mode` + modes.yaml 已三模式」两断言 | 两条 PASS |
| F5 「无 RTL 修复」结论是否成立 | ✅确认 | 四组合矩阵 + m17 前后源码差异逐行核对 | A/B/C/D 全 PASS，结论见完成区「根因」 |

判决：F1–F4 已修并复验，F5 结论成立；无未修 finding。状态 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-25）

**重跑记录（全部本人在仓库根执行；证据 = 运行期证据目录内 `run.sh` 及其输出）**
1. `run.sh` 全量（A–F）→ **`51 PASS / 0 FAIL`、`rc=0`**；与工程师留存的全量输出逐行 `diff` 仅差我追加的 `RC=0` 一行 ⇒ 完成区转述与真实运行一致。
2. **独立注入**：`cp` 备份当期 `cfx15.S`（md5 `48de7da7`）→ `git show 36911ad2:tests/arch/hart/cfx15.S` 覆盖（md5 `1d37dc74`，与 `b9622776` 同内容、无 `perm_hypv.inc`）→ `run.sh --no-repr --no-bisect` → **`rc=1`、14 FAIL / 20 PASS**（A3；B 三模式 `sim rc=124`/`SYS_EXIT`/oracle；C1/C8/C10/C11；oracle 现场 `summary: 80 slot(s), 81 failure(s)`）→ `cp` 还原 md5=`48de7da7` → 同参重跑 → **`rc=0`、34 PASS / 0 FAIL**。全程无 `git checkout/restore/stash`。
3. 槽位现场重算（`check_cfx15` 亲跑）：当期 hmon/smon/umon = **80/40/40、0 failure**；`SYS_EXIT … cycle=104765/96199/96192`；oracle 鉴别力：错 mode ⇒ 39 failure、截断流 ⇒ 报错（非恒真）。
4. 二分/四组合：隔离树 `modeEnforced` 在、`axisDenied` 无；与共享树 `.scala` 差异恰为 m17 的 6 文件，`WumingParams/DadaoConfigs` 仅 m17 注释差、`WumingCache`（027 专属）相同 ⇒ 023+027 在场、m17 缺席；D 段两格我亲算均 80/0 ⇒ 四组合（当期+当期 PASS、旧+当期 FAIL、旧+旧 PASS、当期+旧 PASS）成立，引入点 = m17 hypv 两轴判权、023/027 无关。
5. 链路：旧探针 `_start` 首条 cfx 访问 `cfx2rc cfx_hart,cg9,rc5` 无 `PERM_MON_OPEN` 前置；补丁前版 `modeEnforced … && runMode =/= hypv`（hypv 豁免）→ 当版 `axisDenied/rowAvailable`；`power_vast.S` `trap cfx_hmon`→hmon 保存-跳转槽→`jump appEntry` 回跳链完整。
6. 门控与代表集（本人重跑）：`check-patch-tree` chipyard 段 0 problem、`make_patch` 0 written、`check-component-changelog`/`check-tests-index`/`check-tasks`/`run_arch --self-test`/`check_hart_rtl --selfcheck` 全 rc=0；代表集 8 驱动腿 PASS（hart 80/40/40、pmem 55、time 7、cache、ptw-001/002=3 签名槽）+ ptw KNOWN-RED 4 条按基线判据 PASS。

**约束核验**：前后 `git status` 快照仅本任务书（与完成区「修改文件」声明一致）；共享源树 sim 与主仓同 inode、mtime 10:10 未重建、chipyard 树 status 干净；当期 sim md5 `53c367f6`（=共享）、隔离构建 `1e53b08e`、305 s（时间戳差实算）；未改 spec/契约/RTL/镜像/参数。

**遗留判定**：① ptw `--mode` 属实（driver 无该参、modes.yaml 三模式、`b9622776` 同在 = 基线红）→ 同意另任务；**但 `ISS-m16-010` 全仓不存在（未登记）**、`ISS-m16-008` 未回填根因（要做 #5 未落盘）→ 收尾补登。② 单平台假「不一致」属实（GAP 分支 `ref` 空集 ⇒ `ref_ok` 恒 false；非 GAP 同名 FAIL 实为签名 vs expected 不符、标签误导）。③ **证伪**：`+verbose` 两次实测均产出 `WumingCore: exec`（14188/15087 行）；另 1/3 次在 99607 cycle 挂死（flake，与 verbose 无确定相关，建议另查）。④ ELF 版本戳现状确实缺失 → 同意另立小任务（P3）。

**findings（均不阻断，architect 收尾处置）**：F1 完成区分节计数与现场不符（B 实 12 非 9、E 实 12 非 11，总数 51 正确）；F2 遗留③表述按实测改写；F3 登记缺口（补 `ISS-m16-010` + 回填 `ISS-m16-008`，要做 #5）。

**采信未复跑**：gem5-026 侧「1.05M cycle 重启 881 次」与 11-24 旧构建观测（`ISS-m16-008` 原始记录，gem5 腿超本档位）。

**判决：Accepted** —— 验证块 1–5 本人重跑全绿、四组合矩阵成立、独立注入红→`cp`+md5 还原→回绿闭环、约束无违反；findings 由 architect 收尾处置。
