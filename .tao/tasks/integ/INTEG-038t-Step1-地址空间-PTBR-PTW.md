# INTEG-038t: Step 1 落地（地址空间 + PTBR + PTW）

**模块**：integ
**项目里程碑**：M10
**依赖**：ADR-0039（Step 1 已冻结）、当前 master
**状态**：待开始

## 背景
ADR-0039 §8.5 已冻结 Step 1，但 `spec/DADAO-12`、contracts、QEMU 仍是旧口径：48 位 VA、高 6 位选 64 个 PTBR、`pahi/pthi` 拼 PA、`ptbr_enable` 位图。本任务只落地 Step 1，**不实现 PTE/TLB/DMA/启动**。

## 目标（只做 Step 1）
1. **SEE spec（DADAO-12 §2.1/§2.2 相关）**
   - CPU 地址 48 位；`[47:42]==0` 为内存窗口（PTW），`1..63` 为 cfx 1–63 核内空间；cfx0=umon 无内部空间；
   - VA 42 位、PA 56 位；
   - 单 PTBR，只存 PPN[55:16]，64KiB 对齐；无数组、无 valid、无 `pahi/pthi`、无 `ptbr_enable` 位图；
   - `ptw_enable`：0 时 `high6=0` 访存 → **CFXMEM**（当前模式 cfx）；1 时走 PTW；
   - 写 PTBR/`ptw_enable=1` 允许，**不隐含 TLB invalidate**；
   - 复位 PTBR=0、`ptw_enable=0`、TLB 空；
   - 保留：reserved cfx 普通 ld/st → CFXMEM；trap/escape reserved → 现有 ILLI；
   - 不定义 cfx1–63 访问权限（Step 6）。
2. **contracts/别名/生成物**：同步单 PTBR、`ptw_enable`、删除 pahi/pthi/perm/ptbr_enable 相关条目（仅 Step1 范围）。
3. **QEMU**：地址分区、PTBR、`ptw_enable`、PTW off 的 CFXMEM、reserved cfx ld/st；不实现 PTE/TLB/DMA。
4. **测试**：QEMU/单元/向量覆盖：
   - high6=0 且 `ptw_enable=0` → CFXMEM（各模式目标）；
   - `ptw_enable=1` 但 PTBR 未建页表 → 页表异常（若当前 QEMU 已有 ptw 雏形则验证；无则明确 BLOCKED 到 Step2）；
   - PTBR 写入/复位值、单 PTBR；
   - reserved cfx ld/st → CFXMEM；
   - 不影响 cfx 内部直接 ld/st。
5. 更新 spec 锁 sha/changelog/版本；`check-spec-readonly`/`check-spec-changelog`。

## 验收
- `make check` rc=0；`check-spec-readonly`/`check-spec-changelog` rc=0；`check-patch-tree` rc=0（若改组件补丁）。
- QEMU 定向/单元测试全绿；证据 `.work/evidence/<任务号>/run.sh`（注入→FAIL→`cp`+md5 还原→PASS）。
- 不改 PTE 格式/TLB/DMA/启动/HSJU/cfx 权限。
- 完成区 ≤30 行；状态 `待验收`；`milestones.md` 行同步；临时目录 `/tmp/opencode/INTEG-038t/`。

## 约束
- 只做 Step 1；不提前做 Step 2+。
- 不改 Linux/arch、不做 user/kernel 划分。
- 不跑 `check-full`/夜跑；长构建申报。
- 不提交、不 push。

## 完成区

**状态**：待开始

### 修改文件
（待填）

### 验收命令与结果
（待填）

### 遗留
（待填）
