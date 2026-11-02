# INTEG-042t: Step 4 落地（cfx_pmem SRAM + DMA）

**模块**：integ
**项目里程碑**：M10
**依赖**：ADR-0042（Accepted）、ADR-0044（fence）、`INTEG-040t`（Step 3）
**状态**：已验证

## 背景

ADR-0042 已改为简化模型：不设 `cfxin/cfxout`，不设 per-cfx DMA；只在 `cfx_pmem`（cfx17）内提供 64 KiB SRAM，DMA 只在 SRAM 与 physical memory 之间搬运；CPU 用 `ld/st` 访问 SRAM，其它 cfx 也由 CPU 直接访问。设备↔pmem 由 CPU 中转；当前单 hart。

## 目标

1. **spec/文档**
   - `cfx5=cache`（原 cfx6 迁入），`cfx6–14/19–61` reserved；同步索引/别名/README。
   - `cfx_pmem`：64 KiB SRAM，内部偏移 0；DMA 寄存器在 cg15：rc0 src、rc1 dst、rc2 size、rc3 ctrl、rc4 status。
   - 地址/长度：src/dst 64 位；方向位 1 位（0=CFX→PA，1=PA→CFX）；CFX 低42、PA低56，高位忽略；size 30 位，1..2^29（512 MiB）。
   - ctrl/status：START/DIR/IRQ_EN；BUSY/DONE/ERROR/ERR_CODE（16 位 one-hot），W1C；PMEM_DMA=1<<8，异步可屏蔽，单 hart 投递 cfx_pmem。
   - 删除 cfxin/cfxout 及旧 crii/64 字节/块选择描述；不新增 DMA ISA 指令。
2. **contracts**
   - cfx aliases/PMEM 寄存器/异常 cause 同步；生成物重算。
3. **QEMU**
   - 实现 cfx_pmem SRAM 窗口、cg15 访问、DMA SRAM↔PA、status/W1C、PMEM_DMA/pending；单 hart；不实现多 hart/设备 DMA。
   - 不实现 cfxin/cfxout 指令。
4. **测试**
   - CPU `ld/st` 访问 cfx_pmem SRAM；
   - DMA 两方向、地址/长度边界、size=0/>512MiB、高位忽略、busy/start 冲突；
   - DONE/ERROR/ERR_CODE/W1C；PMEM_DMA 屏蔽/pending；
   - cfx5 别名/cfx6 reserved；
   - 回归 Step1–3 探针。

## 验收

- `make check`、`make check-modules`、`make check-arch-smoke`、`make check-arch`、`make check-lit`、`check-spec-readonly`、`check-spec-changelog`、`check-patch-tree`、`check-source-state`、`check-cfx-aliases` 全 rc=0。
- 证据 `.work/evidence/<任务号>/run.sh`：注入→FAIL→cp+md5 还原→PASS。
- 不改 multi-hart/设备 DMA/cfx 访问权限；不跑 full/夜跑。
- 完成区 ≤30 行；任务书/里程碑置 `待验收`；临时 `/tmp/opencode/INTEG-042t/`。

## 约束

- 只做 ADR-0042 范围；`cfx_pmem` 是唯一 DMA，CPU 直访其它 cfx。
- 不提交、不 push；重建先申报；失败保留现场。

## 完成区

**状态**：已验证
**测试结果**：新探针 `min_rom_probe_integ042t.py` 23/23；Step1–3 回归 044t/045t/049t/integ039t(37/37)/integ040t(34/34) 全 PASS；证据 `run.sh` 31/31（两次注入→FAIL→cp+md5 还原→PASS）。

**修改文件**
- spec：`DADAO-12`（§1 `cfx5=cache`/`cfx6–14、19–61` reserved；§2.1 cfx_pmem 64 KiB SRAM 窗口；§3.6 `1<<8` PMEM_DMA；§4.9 SRAM+cg15 DMA+ERR_CODE+PMEM_DMA 异常；§5.1/§5.2 保留编号；附录 0.7.3-rc）、`Machine-01`（§1.1 SRAM 行、§1.2/§3 保留编号与测试机 cfx 集+DMA 约定、附录）；`manifests/spec-readonly.lock.toml`（2 册 sha256 + 授权注记）。
- contracts：`contracts/cfx-aliases.txt`、`.tao/contracts/contract-cfx-aliases.md`（重生成：`cfx_cache`=5、5 条 `cfx_pmem_dma_*`）、`.tao/contracts/contract-see.md`（§2/§3/附录）。
- QEMU：`.work/source/qemu/target/dadao/{cpu.h,cpu.c,helper.c}`、`hw/dadao/dadao-machine.c`；4 份补丁（`hw/dadao/dadao-machine.c.patch`、`target/dadao/{cpu.c,cpu.h,helper.c}.patch`，总数仍 205）；`components/qemu/changelog.md`。
- 测试/门控：新增 `tools/testcases/arch/min_rom_probe_integ042t.py`（23 例）、`Makefile`（`ARCH_CFX_PROBES` 加 `integ042t`）。
- 证据/台账：`.work/evidence/INTEG-042t/run.sh`、`.tao/knowledge/milestones.md`、本任务书。

**既有字段核对**：`cfx_pmem` 原占 cg8（`pmem_exist`）、cg12–14（`start`/`size`/`attr`），cg15 全空；本次只新增 cg15 rc0–4，未覆盖任何既有字段（`contract-cfx-aliases.md` 重生成对比可证）。
**验收结果**（真实 rc）：`make check`=0；`check-modules`=0（L2 PASS）；`check-arch-smoke`=0；`check-arch`=0（`integ042t 23/23`，另 044t/045t/049t/039t/040t 全 PASS）；`check-lit`=0（159/159）；`check-spec-readonly`=0（21 册）；`check-spec-changelog`=0；`check-patch-tree`=0（205）；`check-source-state`=0（qemu clean、base+1）；`check-cfx-aliases`/`check-cfx-alias-table`=0。证据 `run.sh` rc=0：30 项 PASS；注入 A（`cfx_cache 5→6`）⇒ `gen --check` rc=1；注入 B（去掉 BUSY 时 W1C 抑制）⇒ 探针 `0/1`；两次 `cp`+md5 复原后回绿（`927882af…`/`e48921fa…`）。

**新发现/坑**：① `PMEM_DMA` 可屏蔽，而复位 `inner_cfx_mask` 全 1 ⇒ 异步中断只能进入「当前 cfx」；探针须先用不可屏蔽 CFXREG 进入 `cfx_pmem`（并把 `switch_cfx_mask` 置 0）再触发 DMA，才能观测投递。② `cause_nonmaskable` 的 monitor 基集含 bit8–13（ILLI 等），与异步 cause 位重叠；`cfx_pmem` 必须按 §4.9 表覆盖为仅 CFXTRAP/CFXMEM/CFXREG，否则 PMEM_DMA 被当成不可屏蔽。③ `check-run-artifacts` 只认 `check-<name>.log`/`<TASK-ID>-*.log`，首跑因日志名 `check.log` 被红（改名后回绿）。

**遗留问题**：多 hart PMEM_DMA 接收规则、device 本地 DMA、cfx 访问权限（Step 6）、`fence.vma`/`fence.i` 按派单未做；ADR-0042 D7.2 的「bit3..15（16 位 one-hot）」按用户裁定落为 13 位 one-hot（`dma_status[15:3]`），ADR 文本未改；`spec/SimRISC-11` 仍写「reserved 7–14、19–61」（上游 ISA 册引用 SEE 编号，改动牵动 13 册互锁版本，未在本次范围）；未跑 `check-full`/夜跑。

**用户裁定（原话）**：问「`bit3..15` 只有 13 位，装不下 16 位 one-hot，如何落位」→ 答「有几位占几位，你非要在spec中写什么16位是笔误做什么」⇒ 按 `dma_status[15:3]` 13 位 one-hot 落地，spec 不写「16 位」。

## 审阅记录 → 第 1 轮 engineer 自审

逐行审查 `helper.c` DMA/SRAM/cg15、`cpu.h` 状态、`cpu.c` 复位/投递、`dadao-machine.c` SRAM 区、spec §2.1/§4.9、探针 23 例与证据脚本：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `cfx_pmem` 的 `cause_nonmaskable` 沿用 monitor 基集，含 bit8 ⇒ PMEM_DMA 变不可屏蔽 | ✅已修 | `cpu.c` 复位对 `cfxha==17` 覆盖为仅 CFXTRAP/CFXMEM/CFXREG | 屏蔽用例 `pmem_dma_masked_pending` PASS（pending=0x100、未进入）；注入 B 可红 |
| F2 「BUSY 时忽略 W1C」用例原先在完成后再读，DONE 会被重新置位，注入不可观测 | ✅已修 | 探针增 `rd7`（W1C 后仍在 BUSY 时读）断言 `BUSY|DONE`；`observe()` 加 rd9 | 注入 B（去掉 BUSY 抑制）⇒ `dma_busy_w1c_ignored` FAIL（`0/1`） |
| F3 IRQ 用例首版直接 START+IRQ_EN，因复位 `inner_cfx_mask` 全 1 永远进不去 | ✅已修 | 改为「CFXREG 进 cfx_pmem（switch_cfx_mask=0）→ handler 内 START」；masked 用同一入口 + cause mask | `pmem_dma_irq_delivered`/`pmem_dma_masked_pending` PASS |
| F4 `dma_pa_read_rom` 期望值误把 `exit_seq` 的 `jump` 当 ROM 首字 | ✅已修 | 期望改为程序自身 `p[0]<<32|p[1]` | 该例 PASS |
| F5 cg15 保留 rc 的处理：`cfx_reg_ptr` 返回 NULL 会以目标 cfxha 抛 CFXREG（正确），但读写路径须先拦截以免 BUSY 忽略被误判 CFXREG | ✅已修 | `helper_cfx2rd/2rc` 在 `cfx_reg_ptr` 前拦截 cg15（pmem），BUSY 期间写返回成功 | `dma_busy_start_ignored`/`dma_busy_w1c_ignored`/`pmem_cg15_reserved_cfxreg` PASS |
| F6 user-mode 构建无系统地址空间 | ✅已修 | cg15 在 `CONFIG_USER_ONLY` 显式 CFXREG（桩返回 false），无静默成功；两种构建均编译 | `build-qemu` rc=0（system+user 链接） |
| F7 `DADAO-12 §5.1/§5.2` 正文仍写保留 cfx `7-14` | ✅已修 | 两处改 `6-14、19-61`；锁 sha256 重算 | `check-spec-readonly`=0、`check-spec-purity`/`check-asm-prose` 绿 |
| 范围核验 | — | 无 `cfxin/cfxout`、无 per-cfx DMA、无新 ISA 指令、无多 hart/设备 DMA/cfx 权限/fence.vma | grep 无 live 命中；`check-arch`/`check-lit` 回归绿 |
| 判决 | — | 无未修 finding；状态 `待验收` | — |

## 审阅记录 → 第 1 轮 reviewer 验收（2026-10-30）

**重跑记录**（均在 workdir=仓库根、相对路径，reviewer 亲自执行；输出为真实截取）：
- `make check` ⇒ **rc=0**（`repository checks (L1): PASS`）；`make check-modules` ⇒ **rc=0**（`module checks (L2): PASS`）
- `make check-arch-smoke` ⇒ **rc=0**（`check-arch-smoke: PASS (forward + permission + 25-service)`）
- `make check-arch` ⇒ **rc=0**（`[integ042t] … 23/23 passed`；`check-arch: PASS (arch-smoke + cfx probes: 044t 045t 049t integ039t integ040t integ042t)`）
- `make check-lit` ⇒ **rc=0**（`Passed: 159 (100.00%)`）
- `make check-spec-readonly` ⇒ **rc=0**（`21 read-only spec volume(s) OK`，两册 sha256 与 lock 实算一致：`f11f4a46…`/`c1980c3b…`）
- `make check-spec-changelog` ⇒ **rc=0** PASS；`make check-patch-tree` ⇒ **rc=0**（`5 component(s), 205 patches OK`）
- `make check-source-state` ⇒ **rc=0**（`qemu: OK HEAD=3f2cdd9a3089 count=1 clean=True`）
- `make check-cfx-aliases` ⇒ **rc=0**（`PASS (byte-identical)`）；`make check-cfx-alias-table` ⇒ **rc=0**（`12 scalars, 826 regs -- in sync with spec`）
- `python3 tools/testcases/arch/min_rom_probe_integ042t.py` ⇒ **rc=0**（`23/23 passed`）
- `bash .work/evidence/INTEG-042t/run.sh` ⇒ **rc=0**（**31 PASS / 0 FAIL**，含工程师两处注入：alias 注入 `gen_rc=1`、W1C 注入探针 `0/1 rc=1`，`cp`+md5 还原 `927882af…`/`e48921fa…` 回绿）

**独立注入**（第三处，非工程师 A/B；禁 checkout/restore/stash）：`cp` 备份 `helper.c`（md5 `927882af9090d9b884baaf269109e9f4`）→ 放宽 `dadao_pmem_dma_start` CFX 范围校验（`+0x100000`）→ `ninja` rc=0 → 探针 `--only dma_cfx_range_overflow` ⇒ **FAIL rc=1**（`rd5 exp=0x14 got=0x1`）→ `cp` 还原（md5 相等）→ `ninja` rc=0 → 探针 **23/23 rc=0**，qemu 二进制 md5 恢复 `5e85492b…` 与注入前一致。

**约束核验**：① ADR-0042 简化模型逐点对齐——无 cfxin/cfxout/per-cfx DMA/新指令（grep 无命中，`dadao_cfxha_map={0,1,2,3,4,17,63}`）；cfx_pmem 64 KiB SRAM 固定 offset 0、越界 CFXMEM；cg15 rc0–4；src/dst 64 位、DIR 1 位、CFX 低42（`DADAO_VA_MASK`）/PA 低56/高位忽略（探针 `dma_high_bits_ignored` PASS）；size 30 位 `1..2^29`（0/>2^29 ⇒ ERR_SIZE，两例 PASS）；START 自清、BUSY RO/DONE/ERROR W1C、ERROR W1C 清 ERR_CODE、BUSY 忽略写与 W1C；`PMEM_DMA=1<<8` 单 hart 投递、屏蔽置 pending、`cause_nonmaskable` 仅 CFXTRAP/CFXMEM/CFXREG；`cfx5=cache`、`cfx6–14/19–61` reserved（`DADAO_CFX_IS_RESERVED` + 别名表 + cfx5/cfx6 探针 PASS）。② 组件源 clean（base+1）、补丁 205 与源一致、锁 sha 实算一致。③ 未跑 full/夜跑；未提交未 push（`git log -1` 仍 `1d520dff`）。④ 快照对账：验收前后 `git status -uall` 均 15 行、4 目标文件 md5 全同（还原干净）。⑤ 完成区 18 行 ≤30、状态 `待验收`、临时物在 `/tmp/opencode/INTEG-042t/`。

**findings（非阻断，交 architect/用户）**：
1. **ERR_CODE 位宽差异**：ADR-0042 D7.2 文本写「`bit3..15` ERR_CODE（**16 位** one-hot）」，实际落地 13 位 one-hot（`dma_status[15:3]`，spec §4.9 与实现一致、未写 16 位）；任务书已落用户裁定原话「有几位占几位…16 位是笔误」。**ADR 文本未改，是否修订 ADR 由用户/architect 裁定**（reviewer 未改 ADR）。
2. **`spec/Machine-01` 正文 line 80 漏改**：「reserved cfxha（`7`–`14`/`19`–`61`）」与同节 line 74（`6`–`14`）及 DADAO-12 新编号矛盾（本次改动遗漏，非历史章节）。非验收判据、无行为/门控影响 ⇒ 按 6.5 记 finding；**architect 收尾改**（连带重算 machine-01 lock sha + 重跑 `check-spec-readonly`）。
3. 完成区「证据 `run.sh` 31/31」实为 **31 项 PASS**（文档数字笔误）。
4. 遗留已声明：`spec/SimRISC-11` 仍写 reserved `7–14/19–61`（13 册互锁，未在本次范围）。

**判决：Accepted** —— 验收命令块在 reviewer 独立重跑下全部 rc=0、独立注入反例产生真实 FAIL 并还原回绿、约束无违反。可提交（architect 显式 staging + 与完成区「修改文件」对账；建议收尾一并修 finding 2）。
