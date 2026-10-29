# INTEG-039t: Step 2 落地（PTE/页表步进/页权限）

**模块**：integ
**项目里程碑**：M10
**依赖**：ADR-0039（地址空间/PTBR）、ADR-0040（PTE/页表/权限）、master `e601034b`
**状态**：待开始

## 背景
Step 1 已落地单 PTBR/`ptw_enable`，但 `ptw_enable=1` 仍是显式 fail-closed；`spec/DADAO-12` §2.2.3/§2.2.4 仍是旧 PTE 布局（32 位 PPN、顶部 SPF/GPF）。本任务按 ADR-0040 实现页表步进与页权限，**不做 TLB/A-D/DMA/启动**。

## 目标
1. **spec（DADAO-12 §2.2.1–§2.2.6）**
   - PTE 64 位：HSJU `[63:60]`、PPN `[55:16]`/超页 `[55:29]`、SPF/GPF `[15:8]`、flags `[7:0]`（P=0/SP=1/D=2/A=3/X=5/W=6/R=7）；保留位/PPN 低位按 ADR-0040 D9。
   - L1 next-level、L1 超页、L2 普通页；L1/L2 64 KiB、8192 项；索引 `VA[41:29]`/`[28:16]`，页内 `[15:0]`；PA56。
   - HSJU 访问规则；SPF/GPF 8 位小页存在位（64 MiB/8 KiB，`VA[28:26]`/`[15:13]`）；位 0 的 fault 编码。
   - 异常优先级：`P=0`/超页缺失 → SPF/GPF=0 → HSJU → R/W/X；`NUPERM/NJPERM/NSPERM/NHPERM`、`NRPERM/NWPERM/NXPERM`、`IGPTRAP/ISPTRAP/IGPFTRAP/ISPFTRAP` 及 D 对应；页表异常进 `cfx_ptw`。
   - A/D 只定义、不更新（Step 3）；保留位忽略、PPN 低位强制清零。
   - 同步 contracts/spec 引用、`manifests/spec-readonly.lock.toml`、changelog。
2. **QEMU**
   - 用页表步进替换 `ptw_enable=1` 的显式失败；从 PA 读 PTE，检查 P/SP/SPF/GPF/HSJU/RWX，形成 PA56；错误按上述异常。
   - 不实现 TLB、A/D 更新、DMA、启动；不改变 Step 1 的地址分区/PTBR/CFXMEM 语义。
3. **测试**
   - 页表步进：L1 next-level + L2、超页、PA56、页内偏移。
   - 缺失/权限：L1 P=0、L2 P=0、SPF/GPF 位 0、HSJU 四模式、R/W/X、优先级。
   - 保留位忽略、PPN 低位清零、PTBR/页表在 pmem；A/D 不更新（断言）。
   - 覆盖 QEMU 探针/单元/向量；不改 oracle 生成方式。

## 验收
- `make check`、`make check-modules`、`make check-arch-smoke`、`make check-lit`、`check-spec-readonly`、`check-spec-changelog`、`check-patch-tree`、`check-source-state` 全 rc=0。
- 证据 `.work/evidence/<任务号>/run.sh`：注入→FAIL→`cp`+md5 还原→PASS。
- 不改 TLB/A-D/DMA/启动/HSJU 之外的 Step 3+；不跑 `check-full`/夜跑。
- 完成区 ≤30 行；任务书与 `milestones.md` 置 `待验收`；临时目录 `/tmp/opencode/INTEG-039t/`。

## 约束
- 只做 Step 2；不做 Step 3–6。
- 不提交、不 push；长构建先申报。
- 用户已授权 Step 1 的额外 spec 同步；本任务新增 spec 改动须在完成区列出并说明。

## 完成区

**状态**：待开始

### 修改文件
（待填）

### 验收命令与结果
（待填）

### 遗留
（待填）
