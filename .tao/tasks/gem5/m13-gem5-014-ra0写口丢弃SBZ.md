# m13-gem5-014: `ra0` 写口丢弃 SBZ `[63:54]`（`ISS-426`，gem5）

**模块**：gem5
**项目里程碑**：M13
**依赖**：`m13-testcases-031`（已合入：`ld.o_rrii_ra` 链例点 20）；`m13-qemu-012`（QEMU 侧同口径，可并行但 gem5 单写者）
**可并行分片**：否（gem5 组件单写者）
**预估**：2–3 h（含 gem5 增量重建 10–25 min）
**状态**：待开始

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

（实现中写）

## 审阅记录

（待填）
