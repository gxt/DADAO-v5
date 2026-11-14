# m13-gem5-014: `ra0` 写口丢弃 SBZ `[63:54]`（`ISS-426`，gem5）

**模块**：gem5
**项目里程碑**：M13
**依赖**：`m13-testcases-031`（已合入：`ld.o_rrii_ra` 链例点 20）；`m13-qemu-012`（QEMU 侧同口径，可并行但 gem5 单写者）
**可并行分片**：否（gem5 组件单写者）
**预估**：2–3 h（含 gem5 增量重建 10–25 min）
**状态**：已验证

## 背景（`ISS-426`，实测）

- `spec/SimRISC-00 §2.4`：`ra0 = {SBZ(10), RACNT(6), MRPTR(48)}`，`[63:54]` **写无效**（读回恒 0）。
- chipyard `WumingRegFile.writeRa` 合规；QEMU `helper_ra_store` 无掩码（归 `m13-qemu-012`）。
- **gem5**：`b5.cc` 的 RA 写（`ctx.writeInt(Bank::Ra, idx, value)`）无掩码；只有 `writeRasHeader` 用 `kRasSbzMask = 0xFFC0…`（RAS 操作路径）⇒ `ld.o ra0` 写入 `[63:54]` 被保留并读回。
- 现场：`m13-testcases-031` 的 `ld.o_rrii_ra` 链例点 20 —— chipyard 退出 0、**gem5 退出 20**。

## 目标

1. gem5 的 **RA 写口**（`Bank::Ra` 的通用写路径）对 `[63:54]` 置 0，`RACNT[53:48]`/`MRPTR[47:0]` 生效。
2. **不动** RAS 头更新路径的既有语义（`kRasSbzMask` 那套）：`call`/`ret`/`escape` 的 RACNT/MRPTR 更新与改前逐字节一致。
3. 不改 `spec/`、契约；不改 chipyard/qemu。

## 验收

1. 点 20 转绿：节点（`server207`）`run_asm_suite.py --vectors tests/inst/01-load-store` 三平台 **234/235 → 235/235**（若 QEMU 侧尚未合入，则为「除 QEMU 外全绿」并写明；QEMU 由 `m13-qemu-012` 收口）。
2. 改前/改后对照：同一探针在改前二进制上仍红（钉值），改后绿。
3. RAS 回归：`05-arith-addr`、`06-control-flow` 两册三平台仍全绿（`call`/`ret` 的 RACNT/MRPTR 逐字节不变）。
4. 门控：`check-gem5-decode` 264/264+388/388+28/28+2/2、`check-wuming-cycles` 11/11、`check_patch_tree` gem5 段 0 问题、`--source-state` gem5 OK、`check-component-changelog` rc=0、`check-inst` 红集不变（除 `divrem.yaml[23]`）。
5. ≥2 路注入可达 FAIL + `cp`+md5 还原（例：掩码多留 1 位 ⇒ 点 20 红；去掉掩码 ⇒ 回到缺陷）。
6. 完成后 `ISS-426` 在完成区标注「QEMU + gem5 两侧均已修」。
7. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status -uall` 对账。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号）；动手前 `git rev-parse --show-toplevel` 自证；禁改主工作树。
2. 不提交 git；补丁用 `make_patch.py gem5` 导出。
3. 完成区与真实输出逐条对齐；计数现场统计；日志 `.work/log/gem5/<任务ID>-<用途>.log`。
4. 只动任务书范围；越界须披露。
5. 禁 `git checkout/restore/stash`/`git show <commit>:<path>`；注入还原用 `cp`+md5。
6. **共享安装根串行**：`build-gem5` 只写 `.work/build`，可跑；**不要**跑 `install-host`（LLVM/QEMU 写者可能在用）。
7. 大文件落 `/tmp/opencode/m13-gem5-014/` 并测完即删（`/tmp` 仅 16 GB；gem5 outdir 尤须清）。

## 待裁定

无（实现中未产生需用户裁定的语义问题）。

## 审阅记录

（待填）

## 完成区

**测试结果**：节点三平台：`01-load-store` **234/235**（唯一红 = `ld.o_rrii_ra` 链例点 20 —— QEMU `rc=20`，chipyard/gem5 `rc=0` 且结果各 176 B ⇒ 归 `m13-qemu-012`）；`05-arith-addr` **12/12**、`06-control-flow` **34/34** 全绿。本机 gem5 单平台 `01-load-store` **235/235**。点 20：改前 `rc=20` → 改后 `rc=0`（22 检查点 × 8 B = 176 B）。
**修改文件**：`components/gem5/patches/src/arch/dadao/inst.cc.patch`、`components/gem5/changelog.md`、本任务书（`git status -uall` 恰为这三项）；组件源树本地 commit `5cbdc1e`（base+1、clean），改动仅 `inst.cc` +9 行。
**验收结果**（真实退出码）：`check-gem5-decode` `rc=0`（264/264 + 388/388 + 28/28 + 2/2 = 694 PASS / 0 FAIL）；`check-wuming-cycles` `rc=0`（11/11）；`check_patch_tree` **gem5 段 0 问题**（全仓 `rc=1` = 6 问题全在 llvm-project/qemu，他人并发在改未导出，非本任务）；`--source-state` gem5 OK（HEAD=5cbdc1e count=1 clean）；`check-component-changelog` `rc=0`；`check-inst`：`make check-inst` `rc=2` 卡在**结构断言**（共享 gate 目录的 symlink 指向并发任务工作树，非语义失败），同门控语义改用私有 gate-dir ⇒ vast `rc=1`（1141 例：1135 passed / **1 failed = `divrem.yaml[23]`** / 5 deferred）、tiny `rc=0` ⇒ **红集不变**。
**注入**：A 掩码多留 1 位（`0x007F…`）⇒ 点 20 `rc=20` FAIL；B 去掉掩码（`& 0xFFFF…`）⇒ `rc=20` FAIL；两次均 `cp`+md5 还原（`c1c84b28…`）后重建回绿。一键证据脚本（本任务 ID，运行期证据目录）：plain 8/8、`--inject` 11/11（含「注入→3 项红→还原→回绿」）。
**新发现/坑**：① `gem5.opt` 含 `base/date.cc` 构建日期 ⇒ 同源重建 md5 会变（节点用 `29dbe3c6…`、本机最终 `f74abc70…`，同源且点 20 均绿）；② 并发任务的 `make check-inst` 会互踢共享 gate 目录的 symlink 归属断言（本任务用私有 gate-dir 取红集，未删改共享产物）；③ `check_patch_tree` 全仓红来自 llvm/qemu 在改。
**遗留问题**：`ISS-426` **QEMU + gem5 两侧均已修**（QEMU 侧 `m13-qemu-012`，gem5 侧本任务）；节点 `01-load-store` 唯一红待 `m13-qemu-012` 合入后复跑三平台转 235/235（chipyard/gem5 均绿证据已给）。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-14）

**结论**：改动 = `src/arch/dadao/inst.cc` 写口 9 行（+注释）；逐行核对：
- 掩码位置 = 唯一 `Bank::Ra` 通用写路径（`Gem5B1Context::writeInt`，B1–B7 全批共用），只对 `idx == 0` 生效；`ra1`–`ra63` 的 16 位 count 在 `[63:48]`，不受影响（已核 RAS push/evict 均写 `ra63`/`ra62…`，`idx != 0`）。
- RAS 头路径 `exec/b5.cc` 零改动（`b5.cc.patch` 与任务基线 `dd8116df` 逐字节相同 = 证据脚本 C4a/C4b）；其 `old & kRasSbzMask` 经本写口时 old 上 10 位已恒 0 ⇒ 输出逐字节不变。
- 旁路写 ra0（`arch/dadao/process.cc` 进程初始化 `mrptr`、`arch/dadao/se_workload.cc` 信号 RAS）值本身 SBZ=0、且不属指令执行路径，不改。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 掩码放 adapter 写口，而非 exec 核心的 b1/b5 目的地写 | ❌不修（决策） | 无；理由写入代码注释 | 写口是唯一汇聚点且 RAS 路径零改动；放 exec 核心须改 b1/b5 单测「opaque 64 bits」断言与 `check_converge` 冻结基线（b1 2156 / b5 1215） |
| `check_patch_tree` 全仓 `rc=1` | ❌不修（非本任务） | 无 | 6 问题全在 llvm-project/qemu；证据脚本 C6 现场断言 gem5 段 0 问题 |
| `make check-inst` `rc=2`（结构断言） | ⏸延后（并发/共享产物） | 无 | 私有 gate-dir 同门控语义：vast 唯一红 `divrem.yaml[23]`、tiny 全绿 |
| b5_test 的「ra0 SBZ bits preserved」初值含 `kSbz`，与 gem5 写口掩码不同层 | ⏸延后（需裁定） | 无 | 该断言只在 harness 自查层成立（mock 写口不掩码）；改它要动 `check_converge` 冻结 PASS 计数，须主会话裁定；不影响 gem5 行为 |

**状态对账**：无「✅已修」待办；两条 ⏸ 均附非本任务/需裁定理由 ⇒ 状态置「待验收」。

### 第 1 轮 reviewer 验收（2026-11-14）

**重跑记录（全部本人在任务 worktree 执行，真实退出码）**
- 证据脚本：plain **8/8 rc=0**；`--inject` **11/11 rc=0**（其注入 A `0x003F→0x007F` ⇒ C1/C3/C5 红、还原 md5 回绿）。
- 独立注入①（非其 A/B）：掩码改 `0x001FFFFFFFFFFFFF`（少留 1 位）⇒ 重建 rc=0 后探针 `gem5 rc=18` FAIL、C1/C3/C5/C6/C7 红（脚本 exit=1）；`cp`+md5 还原（`c1c84b28…`）重建 ⇒ 8/8 回绿。
- 独立注入②（验收 2「改前红」）：删掩码两行 ⇒ 探针 `gem5 rc=20`（钉值）FAIL；还原重建 ⇒ 回绿 8/8。
- 门控：`check-gem5-decode` rc=0（`[PASS]` 694 / `[FAIL]` 0，分桶 264+388+28+2）；`check-wuming-cycles` rc=0（11/11）；`check-component-changelog` rc=0；`check_patch_tree` gem5 段 **0 问题**（全仓 6 问题在 llvm/qemu 并发）；`--source-state` gem5 OK（HEAD=5cbdc1e count=1 clean）；`check-inst` rc=2 ⇒ vast 1141：1135 passed / **1 failed=`divrem.yaml[23]`** / 5 deferred，tiny（私有 gate-dir）44/44 rc=0 ⇒ **红集不变**。
- 套件：gem5 单平台 `01-load-store` **235/235** rc=0；三平台 `01-load-store` **235/235**（点 20 三平台 rc=0、176 B）、`05-arith-addr` **12/12**、`06-control-flow` **34/34**（均 rc=0）。
- 快照对账：`git status -uall`（审阅记录写入前）为空；`inst.cc`/`b5.cc`/`inst.cc.patch` md5 与开工快照一致（`c1c84b28`/`ff3cd83d`/`4256bb4d`）；gem5 outdir 与套件 work-dir 测完已删。

**约束核验**：① `b5.cc.patch` 与基线 `dd8116df` md5 同（`f0d6bfe664725916f90d5b45c8431dd7`）且 `git diff` 空 ⇒ 逐字节相同，`writeRasHeader`/`kRasSbzMask` 语义未动（`check_b5.py` rc=0，1215/0）；② 提交仅 3 文件，`spec/`、`contracts/`、`tests/`、`components/{qemu,chipyard,llvm-project}` diff 全空 ⇒ 无越界，未跑 `install-host`；③ 完成区 6 段 ≤30 行，「修改文件」与提交 `01eb8185` 一致。

**`b5_test` 旧期望结论**：存在（`exec/b5_test.cc:1598/1728`，`kSbz=0x2AA<<54` 哨兵、Mock 写口不掩码）；**不冲突，判为非未清理旧期望**——它断言的是 exec 层 `writeRasHeader` 不改 `[63:54]`（任务目标 2 明确要求保持该语义），系统层 ra0 的 SBZ 恒 0（`process.cc` 初始化 SBZ=0 + 写口掩码），两层可观测结果一致；`check_b5.py` rc=0（1215 PASS / 0 FAIL，两条均 PASS）。已按「⏸需裁定」登记（改动会动 `check_converge` 冻结计数 b1 2156 / b5 1215）⇒ 保留、不阻断。

**发现（非阻断，交 architect 收尾）**：F1 完成区「264+388+28+2 = 694」算术笔误（和=682；694 为日志 `[PASS]` 行数，实测 694/0）；F2 任务书有两个「## 审阅记录」标题（前一个 `（待填）` 占位未用）；F3 证据脚本 C4a 弱（`git diff <task_base> HEAD` 对同提交改动/工作树改动恒真），其「b5 补丁与基线相同」由我以 md5 独立补核；F4 `ld.o_rrii_ra.S` 注释仍写「QEMU/gem5 全 64 位可写 ⇒ 记红」已过期（`tests/` 不在本任务范围）；F5 我本机三平台为 235/235 而非 234/235——共享安装根 `qemu-system-dadao`（06:27 重建）已含 `m13-qemu-012` 修复（`helper_ra_store` 的 `val &= RA0_WRITE_MASK`，分支 `bb1df1a0` 尚未合 master），节点跑时尚未装机，属并发环境推进、非本任务缺陷。

**判决：Accepted**（验收命令全部由我本人重跑通过，约束无违反；上述发现均不涉代码行为、门控退出码与计数判据）。
