# m13-qemu-012: `ra0` 写口丢弃 SBZ `[63:54]`（`ISS-426`，QEMU）

**模块**：qemu
**项目里程碑**：M13
**依赖**：`m13-testcases-031`（已合入：链例点 20 用 `ld.o ra0` 写入 `0xFFFF000000000000`、期望读回 `0x003F000000000000`）
**可并行分片**：否（QEMU 组件单写者）
**预估**：1–2 h
**状态**：待开始

## 背景（`ISS-426`，实测）

- `spec/SimRISC-00 §2.4`：`ra0 = {SBZ(10), RACNT(6), MRPTR(48)}`，`[63:54]` **写无效**（读回恒 0）；`ra2rd`/`rd2ra` 为全 64 位块赋值。
- chipyard `WumingRegFile.writeRa` 合规（`racnt := data(53,48); mrptr := data(47,0)`）。
- QEMU：`helper.c` 的 `helper_ra_store` 直接 `env->ra[phys] = val;` ⇒ 写入位被保留并读回。
- 现场：`m13-testcases-031` 的 `ld.o_rrii_ra` 链例点 20 —— chipyard 退出 0、**QEMU 退出 20**。

## 目标

1. QEMU 的 **RA 写口**（`helper_ra_store` 及其调用者）对 `[63:54]` 置 0：写入值按 `val & 0x003F_FFFF_FFFF_FFFF` 落 `RACNT[53:48]` / `MRPTR[47:0]`。
2. 不影响 RAS 操作的**头更新**路径（那里已有 `kRasSbzMask` 语义）：`call`/`ret`/`escape` 的 RACNT/MRPTR 更新必须与改前逐字节一致。
3. 不改 `spec/`、契约；不改 chipyard/gem5。

## 验收

1. 点 20 转绿：`run_asm_suite.py --vectors tests/inst/01-load-store` 在节点（`server207`）三平台 **235/235**（故障例 197 全绿、链例 38 全绿）。
2. 改前/改后对照：同一探针在**改前二进制**上仍红（钉值），改后绿。
3. RAS 回归：`05-arith-addr`、`06-control-flow` 两册三平台仍全绿（`call`/`ret` 的 RACNT/MRPTR 逐字节不变）。
4. 门控：`check-inst` 红集不变（除既有 `divrem.yaml[23]`）、`check_qemu_trans` 264/264、`check_patch_tree` qemu 段 0 问题、`--source-state` qemu OK、`check-component-changelog` rc=0、安装根 == 构建树。
5. ≥2 路注入可达 FAIL + `cp`+md5 还原（例：掩码改成 `0x007F...`（多留 1 位）⇒ 点 20 红；去掉掩码 ⇒ 回到缺陷）。
6. 完成后 `ISS-426` 在完成区标注「QEMU 侧已修，gem5 侧归 `m13-gem5-014`」。
7. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status -uall` 对账。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号）；动手前 `git rev-parse --show-toplevel` 自证；禁改主工作树。
2. 不提交 git；补丁用 `make_patch.py qemu` 导出。
3. 完成区与真实输出逐条对齐；计数现场统计；日志 `.work/log/qemu/<任务ID>-<用途>.log`。
4. 只动任务书范围；越界须披露。
5. 禁 `git checkout/restore/stash`/`git show <commit>:<path>`；注入还原用 `cp`+md5。
6. **`install-host` 串行**：开工前确认没有别的会话在 `build-qemu`/`install-host`（LLVM 写者可能在跑）。
7. 大文件落 `/tmp/opencode/m13-qemu-012/` 并测完即删。

## 待裁定

（实现中写）

## 审阅记录

（待填）
