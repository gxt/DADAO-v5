# INTEG-040t: Step 3 落地（TLB、G、A/D、PTWERR）

**模块**：integ
**项目里程碑**：M10
**依赖**：ADR-0039（地址空间）、ADR-0040（PTE，Accepted）、ADR-0041（TLB，Accepted）、`INTEG-039t`（Step 2）
**状态**：待开始

## 背景

Step 2 已落地页表步进/HSJU/SPF/GPF/RWX，但还没有 TLB；`cfx_tlb` 仍是旧寄存器块（cfx5），PTE bit4 仍写“保留”，A/D 不更新。ADR-0041 已 Accepted：`cfx_tlb` 合并进 `cfx_ptw`，ASID 16 位，cg12 正交失效接口，A/D dirty 回写，`PTWERR=1<<7`，PTE bit4=G。

## 目标

1. **spec**
   - `DADAO-12` §2.2.5/§4.6：删除 `cfx_tlb`/cfx5/`tlb_enable`/`tlb_exist`；TLB 并入 `cfx_ptw`。
   - PTE flags bit4 从“保留”改为 **G**；叶子 G=1 全局，next-level G 忽略/写 0。
   - cg12 接口：rc0 `tlb_control`（op `00=none/01=clean/10=invalid/11=flush`，addr_scope `00=all/01=VA/10=range/11=reserved`，bit4 `ASID_ANY`），rc1 ASID[15:0]，rc2 start，rc3 size。
   - 正交匹配 `(ASID match) AND (address match)`；`all` 忽略 start/size，`VA` 只看 start，`range` 用 start/size（size=0→CFXREG），scope=11→CFXREG。
   - G 失效：`asid_any=1` 包含 G；`asid_any=0` 跳过 G。
   - A/D：fill 不置 dirty；读/取指置 A，写置 A/D；缺页/权限失败不更新；CLEAN 保留、FLUSH 写回后删、INVALID 不写回删；FLUSH 写回失败保留条目。
   - `PTWERR=1<<7`：A/D 回写失败进 `cfx_ptw`，不可屏蔽，`cause_info=PTE PA`。
   - 同步 contracts/spec 引用、锁 sha/changelog。
2. **QEMU**
   - 实现 TLB（可简化结构，行为必须完整）：ASID/G 匹配、命中/填充、权限同序、A/D dirty、CLEAN/FLUSH/INVALID、PTWERR。
   - 页表步进仍是唯一 fill 来源；TLB 命中不重读 PTE；没有 `tlb_enable`；写 PTBR/ASID 不自动 flush。
   - 不实现 DMA、启动、cfx 访问权限。
3. **测试**
   - ASID 隔离、G 跨 ASID 命中、指定 ASID 不失效 G、ASID_ANY 失效 G；
   - 命中权限优先级、fill 只接受合法 PTE；
   - A/D：fill 不置 dirty、读置 A、写置 A/D、CLEAN/FLUSH/INVALID、回写原子 OR、PTWERR；
   - op/scope/asid 组合、VA/range、size=0/scope=11 的 CFXREG；
   - 回归 Step 1/2 探针、页表步进、`ptw_enable=0` CFXMEM。

## 验收

- `make check`、`make check-modules`、`make check-arch-smoke`、`make check-lit`、`make check-arch`、`check-spec-readonly`、`check-spec-changelog`、`check-patch-tree`、`check-source-state` 全 rc=0。
- 新探针/测试全绿；证据 `.work/evidence/<任务号>/run.sh` 注入→FAIL→cp+md5 还原→PASS。
- 不改 DMA/启动/cfx 权限/Linux 划分；不跑 `check-full`/夜跑。
- 完成区 ≤30 行；任务书与 `milestones.md` 置 `待验收`；临时目录 `/tmp/opencode/INTEG-040t/`。

## 约束

- 只做 Step 3；G 和 PTWERR 必须一起收口，不能只做 TLB。
- 不提交、不 push；重建先申报；失败保留现场。
- 若 QEMU 实现简化导致某些行为无法验证，必须在完成区明确 BLOCKED，不能假绿。

## 完成区

**状态**：待开始

### 修改文件
（待填）

### 验收命令与结果
（待填）

### 遗留
（待填）
