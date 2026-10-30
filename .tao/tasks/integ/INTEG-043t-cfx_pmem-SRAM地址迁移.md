# INTEG-043t: cfx_pmem SRAM 地址迁移（0x47ff_0000_0000）

**模块**：integ
**项目里程碑**：M10
**依赖**：INTEG-042t（cfx_pmem SRAM+DMA）、ADR-0043
**状态**：已验证

## 背景

用户裁定 cfx_pmem SRAM 的核内起始地址改为 `0x47ff_0000_0000`（cfx17，内部偏移 `0x3ff_0000_0000`），不是原来的 `0x0000_4400_0000_0000`。当前分支已有未提交 WIP：spec 表/说明、QEMU tlb_fill/DMA 映射、探针地址已部分修改；需要按任务流程完成、验证并评审。

## 目标

1. spec：
   - `DADAO-12 §2.1` 表：pmem 起始 `0x47ff_0000_0000`（48 位）；
   - §4.9/说明中的内部偏移改为 `0x3ff_0000_0000`；
   - `Machine-01`、`contract-see` 同步；
   - spec 锁 sha、aliases 重算。
2. QEMU：
   - cfx_pmem SRAM 只在内部偏移 `0x3ff_0000_0000..+64KiB` 映射；
   - DMA 的 CFX 侧地址按该偏移校验，保存 SRAM 相对偏移；
   - 现有 0x0100/0xFFF8 等测试偏移改为相对 SRAM 基址；
   - 不改变其它 cfx/DMA 语义。
3. 测试：
   - `min_rom_probe_integ042t.py` 使用新绝对基址 `0x47ff_0000_0000`；
   - 覆盖 SRAM 正确地址、越界 CFXMEM、DMA 两方向、DMA size/地址边界；
   - 回归 Step1–4 相关探针。
4. 验收：
   - `make build-qemu`、`make check`、`make check-modules`、`make check-arch`、`make check-lit`、spec/patch/source/aliases 全 rc=0；
   - 证据 `.work/evidence/<任务号>/run.sh` 注入→FAIL→cp+md5 还原→PASS。
   - 完成区 ≤30 行；状态 `待验收`；`milestones.md` 同步；临时 `/tmp/opencode/INTEG-043t/`。

## 约束

- 只做 cfx_pmem SRAM 地址迁移；不改 DMA 寄存器语义、cfx5/cfx6、多 hart、设备 DMA、cfx 权限。
- 不提交、不 push；QEMU 组件源保持 base+1、clean；补丁用 `make_patch.py qemu` 导出。
- 当前 WIP 现场不得丢弃；engineer 接管完成。

## 完成区

**状态**：已验证
**测试结果**：探针 25/25；回归 044t/045t/049t/integ039t(37/37)/integ040t(34/34) 全 PASS；证据 `run.sh` 43/43（两处注入→FAIL→cp+md5→PASS）。

**修改文件**
- `spec/DADAO-12`：§2.1 说明/§4.9/附录内部偏移 → `0x3ff_0000_0000`（§2.1 表起始 `0x47ff_0000_0000` 前笔已改）。
- `spec/Machine-01`：§1.1 表、附录 0.3.2-rc 内部偏移同步。
- `.tao/contracts/contract-see.md`：cfx_pmem SRAM 条同步。
- `manifests/spec-readonly.lock.toml`：DADAO-12 / Machine-01 sha256 重算 + 授权注记。
- `components/qemu/patches/target/dadao/{cpu.h,helper.c}.patch`：`make_patch.py qemu` 导出（源树 base+1 clean，63 patch 0 written）。
- `tools/testcases/arch/min_rom_probe_integ042t.py`：新基址/偏移常量 + old-offset CFXMEM、DMA below-offset 两例（25 例）。
- `.work/evidence/INTEG-043t/run.sh`、`.tao/knowledge/milestones.md`、本任务书。

**授权（spec 改动，Process-06 §5）**：任务书 §背景 用户原话「用户裁定 cfx_pmem SRAM 的核内起始地址改为 `0x47ff_0000_0000`（cfx17，内部偏移 `0x3ff_0000_0000`）」。

**验收结果（真实 rc）**：`make build-qemu`=0；`make check`=0；`make check-modules`=0（L2 PASS）；`make check-arch`=0（integ042t 25/25 + 044t/045t/049t/039t/040t PASS）；`make check-lit`=0（159/159）；`check-spec-readonly`=0（21 册）；`check-patch-tree`=0（5 组件/205 patch）；`check-source-state`=0（qemu HEAD=60061bb count=1 clean=True）；`gen_cfx_alias_table --check`=0。证据 `run.sh` rc=0：43/43；注入 A（禁用 tlb_fill 窗口判定）⇒ 探针 0/1 FAIL；注入 B（spec 偏移回 0）⇒ grep miss + lock FAIL；均 `cp`+md5 复原回绿。

**新发现/坑**：① QEMU tlb_fill 与 DMA 统一按 42 位核内偏移比较 `0x3ff_0000_0000`，DMA 落盘 `pmem_dma_cfx_off` 存相对偏移；`size > 64KiB` 先判 CFX_RANGE，再判 `addr-offset > SIZE-size`，避免减法下溢。② 旧基址 `17<<42`（offset 0）现为非法窗口，探针新增两例锁住该回归。③ 证据注入 QEMU 后必须重建 `.work/build/qemu` 再用 `--only` 观测，还原后重建回绿。

**遗留问题**：ADR-0042 D3/D7.3 仍写「内部偏移 0」，与本次 spec 迁移矛盾；按 AGENTS.md「改 Accepted ADR 的 decision 须逐条确认」，未改，待用户/architect 裁定（建议就地修订或标 Superseded）。`spec/Machine-01` 的 `0.3.2-rc` 未发布，偏移按同一对象最终态改写、未另开条目。

## 审阅记录 → 第 1 轮 engineer 自审

逐行审查 spec 三处偏移、QEMU tlb_fill/DMA 两处、探针 25 例与证据脚本：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `spec/Machine-01` 附录 0.3.2-rc 仍写「内部偏移 0」 | ✅已修 | 改为 `0x3ff_0000_0000` | `run.sh` 第 1 节 grep PASS |
| F2 探针 docstring 仍写「internal offset 0」；新增 `PMEM_SRAM_CFX_OFFSET` 若不用会成孤儿 | ✅已修 | docstring 同步；模块级 assert 校验 `PMEM_BASE == (17<<42)|offset` | `--list` 25 例、25/25 PASS |
| F3 旧基址/低于偏移的 DMA 地址无负向用例 | ✅已修 | 新增 `sram_old_offset_cfxmem`、`dma_cfx_below_offset` | 两例 PASS；注入 A 可红 |
| F4 QEMU 源树是否需改：核对后发现 WIP 已在 base+1 内提交新偏移 | ✅已修（无需改源） | 仅 `make_patch.py qemu` 幂等导出（0 written） | `check-patch-tree`/`--source-state` rc=0 |
| F5 证据注入 B 直接改受锁 spec，须可复原 | ✅已修 | `cp` 备份 + `sed` 注入 + md5 对账还原 | 注入 lock rc=1；还原 md5 相等、lock rc=0 |
| F6 ADR-0042 D3/D7.3 与 spec 矛盾 | ⏸延后 | 未改 ADR（改 Accepted decision 须用户逐条确认） | 已在完成区遗留披露 |
| 判决 | — | 无未修 finding；状态 `待验收` | — |

## 审阅记录 → 第 1 轮 reviewer 验收

**分析文件**：任务书；spec/DADAO-12、spec/Machine-01、contract-see、lock、2 个 QEMU patch、探针、run.sh、ADR-0042；QEMU 源树 `.work/source/qemu`（HEAD=60061bb count=1 clean）。

**独立重跑（全部在 workdir 内、真实 rc）**：
- `make build-qemu` → **rc=0**（`build-qemu: PASS`）
- `make check` → **rc=0**（`repository checks (L1): PASS`）
- `make check-modules` → **rc=0**（`module checks (L2): PASS`，embench/tset 全 PASS）
- `make check-arch` → **rc=0**（044t/045t/049t PASS；integ039t 37/37；integ040t 34/34；integ042t **25/25**）
- `make check-lit` → **rc=0**（159/159）
- `make check-spec-readonly` → **rc=0**（21 册 OK）；`check-patch-tree` → **rc=0**（5 组件/205 patch）；`check-source-state` → **rc=0**（`qemu: OK HEAD=60061bb2c3af count=1 clean=True`）；`check-cfx-aliases` → **rc=0**（byte-identical）
- `python3 tools/testcases/arch/min_rom_probe_integ042t.py` → **rc=0，25/25**（`--list` 25 行）
- `bash .work/evidence/INTEG-043t/run.sh` → **rc=0，43/43 PASS**（含脚本内注入 A/B 均 FAIL→cp+md5→回绿）

**独立注入（reviewer 自做，非采信 engineer）**：`cp helper.c helper.c.preinject`+md5=`cede1904…` → sed 把 `pmem_dma_cfx_off = cfx_addr - DADAO_PMEM_SRAM_CFX_OFFSET` 改回绝对地址（禁 checkout/restore/stash）→ 重建 → **run.sh rc=1，4 项 FAIL**（`DMA saves SRAM-relative offset`、`check-patch-tree 2 problem(s)`、`check-source-state`、探针 `15/25`）→ `cp` 还原 + **md5 相等** → 重建 → run.sh **rc=0，43/43**。快照对账：注入前后 `git status --porcelain -uall` 与开工快照逐行 `diff` 一致（9 文件，与完成区「修改文件」对账一致）；8 个目标文件 `md5sum -c` 全 OK。

**约束核验**：偏移 `0x3ff_0000_0000`/起始 `0x47ff_0000_0000` 数值自洽（17<<42|offset，探针模块级 assert 通过）✓；tlb_fill 仅映射 `>=OFFSET && -OFFSET <64KiB` 窗口 ✓；DMA 先判 `size>64KiB` 再判 `cfx_addr<OFFSET || -OFFSET > SIZE-size`（防下溢）、存相对偏移 ✓；探针新基址 + old-offset/below-offset 两负例 ✓；QEMU 源 base+1 clean、补丁与源一致 ✓；无临时残留（`*_tmp/_gate/*.orig/*.rej` grep 空）；未提交、未 push、未改设计 ✓。

**Finding（不阻断，交用户/architect 裁定）**：ADR-0042 **D3**（「核内起始 `0x47ff_0000_0000`，内部偏移 0」——本身即自相矛盾）与 **D7.3**（「固定内部偏移 0」）仍与本迁移冲突，且 contract-see 该条仍引 `[ADR-0042 D3/D6/D7.1–D7.3]`；ADR 状态 `Accepted`，改 decision 须逐条确认，reviewer 未改。

**判决：Accepted** —— 验收命令块在我自己的重跑下全部 rc=0、注入 FAIL→还原→回绿真实、约束无违反；可提交（由 architect 在本分支提交，ADR-0042 修订待用户裁定）。
