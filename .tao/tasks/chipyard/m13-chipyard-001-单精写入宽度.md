# m13-chipyard-001: 单精写入宽度（`ld.t`/`ldm.t` 不扩展 + ft 结果只写低 32 位）

**模块**：chipyard
**项目里程碑**：M13
**依赖**：无（spec 已裁定并落文：`SimRISC-01 §4` 注 + `SimRISC-07` 单精写宽 + `contract-fp §1`）
**可并行分片**：否（chipyard 组件单写者）
**预估**：3–5 h（含 Verilator 重建；开工前申报）
**状态**：待开始

## 背景（用户 2026-11-14 裁定）

`SimRISC-00 §2.3.1` 的 FCSR 写语义是正确口径，其余按它修订。裁定要点：

1. **`ld.t`/`ldm.t` 只写目的寄存器低 32 位，高 32 位保持原值**（不符号扩展、不零填）；
2. 写入 `rf0` 时，低 32 位里位于可写域的只有 `[4:0]`（异常状态）⇒ `[33:32]`/`[31:22]`/`[21:5]` **全部保持原值**；
3. **凡以 ft（单精）寄存器为目的的指令，只写低 32 位、高 32 位保持原值**（含 `ft2ft`）；`fo2fo` 与跨组复制 `rd2rf`/`rf2rd` 按 64 位二进制搬移。

chipyard 现状（`m13-qemu-007` 实测）：`ld.t` 的写数据是**符号扩展**到 64 位（`MO_BESL` 同源语义），`WumingRegFile.writeRf` 对 `idx≠0` 写整个 64 位 ⇒ `ld.t rf0 ← 0xFFFF_FFFF` 得 `0x7FF8_0003_7FC0_001F`（`[33:32]` 被改成 `11`）。按新裁定应为 `0x7FF8_0000_7FC0_001F`（只有 `[4:0]` 被写）。

## 目标

1. `ld.t`/`ldm.t` 的 32 位数据**不扩展**：只写 `rf[idx][31:0]`，`[63:32]` 保持原值。
2. 其余产生 ft 结果的指令（算术/取余/开方/取整/缩放/最小最大/转换到 ft）同样**只写低 32 位**；实现方式自选（如把 ft 结果的写使能改为按半字写），但必须**逐条列出你改了哪些指令族**并给证据。
3. **`ft2ft` 也按本裁定改**：只搬低 32 位、目的高 32 位保持原值（不再是 64 位二进制搬移）。`fo2fo`、跨组复制 `rd2rf`/`rf2rd`、`ld.o`/`ldm.o` 等 64 位通路**行为不变**。

## 验收

1. **探针（三平台同一 ELF）**：
   - `ld.t rf0 ← 0xFFFF_FFFF` ⇒ `0x7FF8_0000_7FC0_001F`（`[33:32]` 保持、`[4:0]` 被写）；
   - `ld.t rf5 ← 0xFFFF_FFFF` 后 `rf2rd rdX, rf5` ⇒ 高 32 位 == 写前 `rf5` 的高 32 位（先 `rd2rf rf5, rdY` 填入已知图案再验）；
   - `ld.t ← 0x7FFF_FFFF`、`ld.t ← 0`、`ldm.t {rf0:rf1}` 各一例；
   - `ftadd`（产生 ft 结果）后 `rf2rd` 验高 32 位保持；
   - `ft2ft` 只搬低 32 位：目的高 32 位保持写前值（反向对照：`fo2fo`/`rd2rf`/`rf2rd` 仍 64 位不变）。
2. **回归**：`01-load-store`、`05-arith-addr`、`06-control-flow`、`07-floating-point` 四册三平台全绿（数值与改前一致；高 32 位相关检查点按新口径更新）。
3. **RTL 单元台/仿真**：`tools/chipyard/fp_*`、`tools/chipyard/fp_unit/` 的既有断言全绿；如有「ft 结果高半」相关旧期望，按新口径修并说明。
4. 门控：`check_patch_tree` chipyard 段 0 问题、`--source-state` chipyard OK（base+1）、`check-component-changelog`、`check-index-blobs`。
5. **≥2 路注入可达 FAIL** + `cp`+md5 还原（例：恢复符号扩展 ⇒ 探针第 1 点红；把 ft 结果改回写全 64 ⇒ 高半检查点红）。
6. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status -uall` 对账。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号）；动手前 `git rev-parse --show-toplevel` 自证；禁改主工作树。
2. 不提交 git；补丁 `make_patch.py chipyard` 导出。
3. **chipyard 构建后必须删 `.classpath_cache/chipyard.jar` 与 `generated-src/<cfg>` 再 `make verilog`**，否则静默沿用旧固件/RTL（`m12-chipyard-028` 踩过）；判「新 RTL 真进模拟器」要独立解析产物（如 `TLROM.sv`/`Wuming*` 生成物）而非只看 `make` rc。
4. 完成区与真实输出逐条对齐；计数现场统计；日志 `.work/log/chipyard/<任务ID>-<用途>.log`。
5. 禁 `git checkout/restore/stash`/`git show <commit>:<path>`；注入还原用 `cp`+md5。
6. 三平台对比在节点（`server207`/`server208`）；节点 chipyard sim 需与主控机一致（`ISS-429`），无 JDK 不能自建 ⇒ 同步主控机构建产物。
7. 大文件落 `/tmp/opencode/m13-chipyard-001/` 并测完即删。

## 待裁定

（实现中写）

## 审阅记录

（待填）
