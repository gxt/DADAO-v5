# m18-spec-007: 定义「异步 escape」——从异步进入现场返回

**模块**：spec
**项目里程碑**：M18
**依赖**：用户已逐条给出语义（本任务书「已确定」1–21）；`m18-spec-005`/`m18-spec-006`（ADR-0061 R2 现行口径）
**可并行分片**：否（spec/契约 + 活文档）
**预估**：待定（语义由用户给出后再标定）
**档位**：大改（异步模型 + `escape` 语义）
**状态**：已验证
**执行环境**：本地

## 背景

`m18-linux-024` 为“内核态异步返回”不得不借一个**未被使用的 monitor cfx（jmon）**：异步进入把当前 cfx 置为 `cfx_hart`，而 `escape` 只能从**当前 cfx 的 `cg5`** 恢复 `prev_run_mode`/`prev_cfx_code`，且要求 `cg5.cause_id != 0`；异步进入只填 `cg9`，不填 `cg5`，所以无法直接 `escape cfx_hart`。

用户 2026-11-25 裁定：**定义“异步 escape”，使软件可以从异步中断现场直接返回**（不再借 jmon 或其它 monitor）。

## 讨论记录（2026-11-25，与用户）

### 已作废（2026-11-25，用户明确“刚才讨论的内容作废”）

- ~~删除 `cfx_hart cg9 rc0/rc1/rc2`、复用 `cg5 rc0/rc1/rc3`~~
- ~~删除 `cg9 rc3 async_src_frame`，改由 mask + pending 推导源~~
- ~~删除 `cfx_hart` 异常原因表的 `IPI`~~

（用户明确：**不合并同步/异步入口**，改为增加 `escape` 的出口。）

### 已确定（用户 2026-11-25）

1. `cg5 rc8`–`rc11`（escape run mode / escape cfx code / escape ip / escape intr mask）由**硬件在进入时自动填**（同步与异步都填）；软件只在需要改返回点时改写。
2. **分两层：入口记录 + 出口意图**。入口记录由硬件写、软件只读；出口意图进入时由硬件复制一份，handler 可改，`escape` 只认这一份。
3. **入口记录改只读（方案 A）**：`rc0`–`rc3` 硬件写、软件只读；现存所有软件改写点迁到 `rc8`–`rc10`。
4. **`cg5` 重新排序**（与出口意图一一对应）：
   - `rc0` = prev run mode（对应 `rc8` escape run mode）
   - `rc1` = prev cfx code（对应 `rc9` escape cfx code）
   - `rc2` = prev ip（对应 `rc10` escape ip；原 `excp_cause_ip`）
   - `rc3` = prev intr mask（对应 `rc11` escape intr mask）
   - `rc4` = excp cause id（原 `rc2`）
   - `rc5` = excp cause info（原 `rc4`）
   - `rc8` = escape run mode、`rc9` = escape cfx code、`rc10` = escape ip、`rc11` = escape intr mask
   - `excp pending`（原 `rc5`）**删除**
5. **异步只写 `cg9` 的记录与 `cg5` 的出口意图**：异步进入把入口记录写在 `cg9 rc0`–`rc3`，把出口意图写在 `hart cg5 rc8`–`rc11`；hart 的 `cg5 rc0`–`rc3` **不填**。同步进入则写自身的 `cg5 rc0`–`rc3` + `rc8`–`rc11`。
6. **`escape` 的权限规则**：只允许“同级或降权”（目标模式特权等级 ≤ 当前模式）；向更高特权级返回一律 `CFXESC`。
7. **`escape` 指令形态**：汇编/工具链格式 `escape cfxHA`（只提供 `cfxha` 操作数，`imms18` 编码恒 0）；`cfxha` 必须等于当前 cfx（否则 `CFXESC`）；返回地址精确取 `rc10`。
8. **嵌套纪律（软件快照）**：硬件单帧；入口把 `rc8`–`rc11`（连同 `cg9` 记录）抄到每任务/每 CPU 内存，返回前写回 `rc8`–`rc11` 再 `escape`；嵌套按 LIFO。
9. **`rc11` 的写入口径**：整字写入“目标运行模式（由 `rc8` 决定）monitor 的 `cg8 rc1`”；与切模式/切 cfx/跳转原子完成，写入在 `rc10` 第一条指令前生效（user→umon、supv→smon、hypv→hmon）。
10. **`cfx_hart cg9` 的 `rc0`–`rc3` 采用同样顺序**：`rc0` prev run mode、`rc1` prev cfx code、`rc2` prev ip、`rc3` prev intr mask。
11. **保留“本次源集合”位图槽（方案 B）**：`cg9 rc4` = 本次进入的源集合（硬件写、只读）；`pending` 语义保持现状（投递即清）。
12. **`cg9` 其余槽位**：`rc5` = `async_src_pending`、`rc14` = `async_switch_run_mode`、`rc15` = `async_excp_vector`（2026-11-26 由 `rc8`/`rc10` 改为 `rc14`/`rc15`）。
13. **出口帧不设有效位（方案 A）**：只要 `cfxha == 当前 cfx` 且目标 run mode 不升权限即可 `escape`；不跟踪“是否进入过/是否已返回”，重复 `escape` 由软件负责。
14. **删除 `excp pending`**：`DADAO-22` 的 `cfx_uart_excp_pending` 举例改到 `cfx_uart` 自己的专用寄存器（或删除该例）。
    - 更正（我此前口误）：重排后新 `rc5` = `excp cause info`，**没有空闲槽**，不存在“`rc5` 归 reserved”这回事；`rc6`/`rc7` 维持现状。
15. **计数口径**：`escape_num` 每次 `escape` 执行 +1（同步/异步一视同仁）；`excp_async_num` 保持“每次异步进入 +1”。
16. **`cg0`–`cg3`（各 cfx 的四个模式行）**：`<mode>_switch_run_mode` 由 `rc8` 改为 **`rc14`**；`<mode>_excp_vector` 由 `rc10` 改为 **`rc15`**（与 `cg9` 的 `rc14`/`rc15` 对齐）。
17. **空出的 `rc8`/`rc10` 归 reserved（方案 A）**：`cg0`–`cg3` 的 `rc8`/`rc10`、`cg9` 的 `rc8`/`rc10` 均标 reserved，访问 ⇒ `CFXREG`。
20. **`escape` 编码不变，但 `imms18` 必须为 0（SBZ）**：机器码布局不改（仍带原 `cfxha`/`imms18` 字段位）；汇编格式写 `escape cfxHA`（`imms18 = 0`）；`imms18 != 0` ⇒ `ILLI`（旧的 `+4`/cg9 编码作废，不兼容旧二进制）。
21. **`escape` 的目标非法**：`rc9` 指向未实现 cfx，或目标模式没有对应 monitor（如 jail→jmon 不存在）⇒ `CFXESC`。
22. **`rc11` 复位值**：全 1（fail-safe，默认屏蔽所有源）。
23. **`trap` 也自动填 `rc8`–`rc11`**：`trap` 是同步进入，目标 cfx 的 `cg5` 同时得到入口记录与出口意图。
24. **`rc0`–`rc3` 只读**：软件写入 ⇒ `CFXREG`。
18. **`escape` 汇编格式**：改为 **`escape cfxHA`**——只提供 `cfxha` 操作数；机器码中的 `imms18` 字段保留但必须为 0（见第 20 条），`+0/+4` 偏移与 `cg9` 选择位作废；返回地址取 `rc10`。
19. **ADR**：用户 2026-11-26 裁定 **修订 `ADR-0061`（加 R3）**——撤销“`escape imms18[1]=1 ⇒ CFXESC`、异步无返回帧”，改为 `cg5 rc8–rc11` 出口 + 异步 escape；R2 段保留为历史。
20. **SimRISC 版本**：`SimRISC-00`（及各分册“与 SimRISC-00 一致”的版本行）由 `0.5.7` 升为 **`0.5.8-rc`**。
    - **DADAO 册不做交叉引用**：删除 `DADAO-12`/`DADAO-22` 头部括号内的「基于 SimRISC 0.5.5 指令系统设计」，并删除两册变更记录里的「与上游 SimRISC 0.5.5 基线对齐。」整行（不再写 SimRISC 版本）。
    - **同批一并删除**：`DADAO-11`/`13`/`21`/`23` 头部括号内的「基于 SimRISC 0.5.5 指令系统设计」，以及各自变更记录里的「与上游 SimRISC 0.5.5 基线对齐。」整行（与 12/22 合计 **六册**：11/12/13/21/22/23）。历史上「基于 SimRISC 0.4.1」之类的变更记录条目保持原样。
21. **版本**：本批改动并入 **0.8.0 定版**（`0.8.0-rc` → `0.8.0`，去掉 `-rc`、补发布日期），**不是**升到 0.9.0；`DADAO-12` 与 `DADAO-22` **同批**定为 0.8.0（两册头部写明“与 SEE 版本号一致”），`contract-see` 随上游册同步（`check-spec-drift` 不变量）。

（原“增加 cg5 rc8–rc11 的提议”已逐条转为上方已确定项。）

### 事实核对（删除 `excp pending` 的连带面）

- Linux 侧：`components/linux/patches/` 内 **0 处**使用 `excp_pending`。
- QEMU 侧：`cg5 rc5` 映射到 `r->pending`，但只在该 cfx 复位时清零、被 dump 打印，**没有任何写入路径**（异步 pending 在 `cg9 rc4`）——属死状态。
- IDL：`CG5_PENDING` 有建模（读写/复位）。
- spec/契约/别名：`DADAO-12 §3.6` 表行、`contract-syscall`（“硬件现场只有 cg5 六个字段”列举）、`contract-see`、`contract-cfx-aliases`、`DADAO-22` 的 `cfx_uart_excp_pending` 举例。

## 待裁定

无（讨论完成；等用户说“开始”再派发）。

## 目标

1. `spec/DADAO-12`：
   - `§3.6 cg5`：改为 `rc0` prev run mode / `rc1` prev cfx code / `rc2` prev ip / `rc3` prev intr mask（均只读）/ `rc4` cause id / `rc5` cause info；删除 `excp pending`；新增 `rc8`–`rc11` 出口意图（escape run mode / cfx code / ip / intr mask），进入时硬件复制、软件可写。
   - `§4.7 cg9`：`rc0` prev run mode / `rc1` prev cfx code / `rc2` prev ip / `rc3` prev intr mask；`rc4` 本次源集合（只读）；`rc5` `async_src_pending`；`rc14` `async_switch_run_mode`；`rc15` `async_excp_vector`；原 `rc8`/`rc10` 归 reserved（⇒ `CFXREG`）；其余 reserved。异步进入只写 `cg9 rc0–rc4` 与 `hart cg5 rc8–rc11`，**不写** `hart cg5 rc0–rc3`。
   - `§3.1`–`§3.4`：四个模式行的 `<mode>_switch_run_mode` → `rc14`、`<mode>_excp_vector` → `rc15`（原 `rc8`/`rc10` 归 reserved ⇒ `CFXREG`）；`§5.2/§5.3/§5.4` 伪码同步。
   - `§5.1`/`§5.3`：`escape` 汇编格式改为 `escape cfxHA`（`imms18` 编码恒 0，非 0 ⇒ `ILLI`）；语义改为“按当前 cfx 的 `cg5 rc8–rc11` 返回”：`cfxha` 必须等于当前 cfx；目标 run mode 不得高于当前模式（否则 `CFXESC`）；返回地址精确取 `rc10`；`rc11` 整字写入目标模式 monitor 的 `cg8 rc1`，与切模式/切 cfx/跳转原子完成。
   - `§5.4`：异步进入的写入集合与 `cg9` 新布局；同步与异步共用同一 `escape` 出口。
2. `spec/DADAO-22`：`cfx_uart_excp_pending` 举例改用 `cfx_uart` 自己的专用寄存器（或删除该例）；版本随 SEE 定为 0.8.0。
3. `.tao/contracts/contract-see.md` / `contract-syscall`（cg5 字段列举）/ `contract-cfx-aliases`：同步新布局与 `escape` 口径。
4. 版本：`DADAO-12` 与 `DADAO-22` 去掉 `-rc` 定为 **0.8.0** 并补发布日期；`contract-see` 同步 0.8.0；不动 `contract-syscall` 的 0.9.2。`SimRISC-00` 及分册升 `0.5.8-rc`；`DADAO-11/12/13/21/22/23` 六册删除 SimRISC 版本交叉引用（头部短句 + 变更记录整行）。

## 验收

1. `check-spec-codeblocks`/`-changelog`/`-purity`、`check-contracts-dir`/`-pending`、`check-contract-relocs`、`check-manifests-guard`、`check-spec-drift`、`check-knowledge-refs` 全 rc=0。
2. 全文一致性：`cg5 rc0–rc5/rc8–rc11`、`cg9 rc0–rc5/rc8/rc10` 的槽位在 `DADAO-12`、契约、别名表、`DADAO-22` 举例中**唯一且一致**；无 `excp pending` 现行条文；无“+0/+4”旧 `escape` 偏移；无“`escape` 不以 `cg9` 为返回帧”与“异步无返回帧”的旧结论残留（变更记录里的历史条文可保留原样）。
3. 版本：`DADAO-12`、`DADAO-22`、`contract-see` 三处均为 `0.8.0`（无 `-rc`），附录/§7 有对应定版记录与日期；`check-spec-drift` 不变量成立。
4. 可达 FAIL ≥2 路：① 把某槽位改回旧号 ⇒ 一致性扫描红；② 把 `escape` 的“不得升权”删掉 ⇒ 词条断言红；`cp`+md5 还原回绿。
5. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动 spec/契约/活文档 + 本任务书；不改实现组件。
3. **语义由用户给出**：未给出前不得自行发挥、不得把 `m18-linux-024` 的现状反推成规范。
4. 术语「bank = 寄存器组」；还原 `cp`+md5。

## 完成区

**测试结果**：证据脚本 69/69 PASS（21 个 spec/契约门控 rc=0 + 44 条一致性/版本/ADR 断言 + 2 组注入/还原）。跨实现门控仅 `check-cfx-vectors` rc=2（测试向量旧 rc3，见遗留 KNOWN-RED）；其余 L1 红为基线环境（缺 llvm-mc/toolchain、milestones/temp dirs）。
**修改文件**：`spec/` DADAO-12/22（0.8.0 定版、异步 escape、cg5/cg9 重排、删 SimRISC 交叉引用）、DADAO-11/13/21/23（删 SimRISC 引用）、SimRISC-00/01–12（0.5.8-rc；00 变更记录、11 escape 语义）、`.manifests.toml`；`.tao/contracts/` contract-see/syscall/cfx-aliases/asm-list/README、contract-cache/tlb/semihosting；`contracts/` opcodes.yaml/legality_rules.yaml/cfx-aliases.txt；`tools/spec/{generate_opcodes,check_asm_prose}.py`、`tools/llvm/gen_asm_list.py`；`README.md`；`.tao/adr/adr-0061`（R3）。
**验收结果**：运行期证据目录内 `run.sh` → `checks: PASS=69 FAIL=0`、`m18-spec-007 evidence: PASS`。注入①cg2 槽位改回 `rc8` ⇒ 槽位扫描 FAIL；注入②删“不得高于” ⇒ 词条断言 FAIL；均 `cp`+md5 还原回绿。
**新发现/坑**：SimRISC-11 的 IDL 渲染块仍是旧 escape 语义（不改 `idl/`，`check-idl-sync` 因块未动而绿），需实现任务改 `.idl` 源后重渲染；别名表重算为 12 标量 / 47 通用模板 / 46 专有（`cfx-aliases.txt` regs=1330）；`check-manifests-guard` 每次改 spec 后须重算 sha。
**遗留问题**：① ADR-0061 R3 已在本任务落地（用户 2026-11-26 裁定 A）。② `spec/` 与 `.tao/contracts/` 本任务独占：`m18-spec-001` 等其它 spec 任务在 m18-spec-007 合入前不得动同一批文件。③ KNOWN-RED（等实现/测试任务）：`check-cfx-vectors`（`tests/unit/llvm/lit/MC/DADAO/cfx2-trap-escape.s` 旧 rc3 向量）、`check-cfx-alias-install`（需 install-host，旧副本）、QEMU/RTL/IDL/汇编器按 R3 的语义任务。④ 基线环境红：`check-isa-coverage`/`check-width-sizes`/`check-components`/`check-linux-toolchain`（缺 llvm-mc/toolchain）、`check-milestones-fresh`、`check-temp-dirs`、`check-writer-guards`；`make check` 在 `check-isa-coverage` 早停（开工基线同）。⑤ `contract-isa`/`contract-asm`/`Toolchain-01`/`Kaiwu`/`DADAO-23` 示例仍按已发布 0.5.7 旧 escape 语法，未授权改，待实现/发布任务同步。

## 审阅记录

### 第 1 轮 engineer 自审

自主逐行审查 DADAO-12 §3.1–§3.6/§4.7/§5.1–§5.4、contract-see §3/§4/§6、别名生成与版本定版。核对：cg0–cg3 `rc14/15` 与原 `rc8/10` reserved；cg5 入口/出口两层、`rc0–rc3` 只读、`rc11` 全 1；cg9 `rc0–rc5` + `rc14/15`；同步写目标 cfx `cg5 rc0–rc5+rc8–rc11`、异步只写 `cg9 rc0–rc4` + hart `cg5 rc8–rc11`；`escape` 的 `imms18=0`、不升权、目标未实现/无 monitor ⇒ `CFXESC`、`rc11` 整字原子恢复、无帧有效位、`escape_num+1`。确认无旧 offset 现行条文；版本/清单/别名/ADR 均重算。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 §4.7 仍写“7 槽 + rc7–rc15 reserved” | ✅已修 | 改为 `rc0–rc5` 入口记录 + `rc14/15` 配置 | `grep "7 槽"` 仅历史变更记录 |
| F2 手改 SimRISC-11 生成表导致 `check-asm-list` 红 | ✅已修 | 改 `tools/llvm/gen_asm_list.py` 渲染 `escape cfxHA` 并重生成 spec/契约表 | `check-asm-list`/`-drift` rc=0 |
| F3 证据脚本 `excp_cause_ip,` 误中寄存器名 | ✅已修 | 收紧为 `[excp_cause_ip,` | 证据脚本 `PASS=69 FAIL=0` |
| F4 定版后 contract-semihosting/cache 版本漂移 | ✅已修 | 两约升至 0.8.0；cache/tlb 源指针改 0.8.0 | `check-spec-drift` rc=0 |
| F5 `check-cfx-vectors` 红 | ⏸延后 | 不动 `tests/**`；归因 LLVM MC 向量旧值 | 日志：`cfx_umon_excp_cause_ip` 期望旧 rc3 编码 |
| F6 完成区写了具体 `.work/**` 路径 | ✅已修 | 改为「运行期证据目录内 `run.sh`」 | `check-knowledge-refs` rc=0；证据 69/69 |

残留：SimRISC-11 IDL 块、外围旧语法示例（见遗留）。所有可修 finding 已修，状态对账为「待验收」。

### 第 2 轮 engineer 自审

针对 reviewer F1/F2 返工：

- **F1 ✅已修**：`spec/DADAO-22 §7.1` 异步入口注释 `cg9 rc5` → **`cg9 rc15`**；该示例其余槽位核对无误（`async_src_frame`=rc4、`cg5 rc4` cause id、`cg5 rc5` cause info、`cg8 rc5` ISTATUS、`cg15 rc4` dma_status），并补「也可用 hart `cg5 rc8–rc11` 出口意图 `escape cfx_hart` 直接返回」。
- **F2 ✅已修**：`spec/Kaiwu` §5/§6 的「异步没有 escape 返回路径」「不恢复任何来源掩码」改为新口径（`escape cfxHA`、同步/异步共用 `escape cfx_hart`、`trap` 只抄 `rc11`、`escape` 按 `rc11` 整字恢复 `cg8 rc1`）；`spec/DADAO-23 §3` 两处同步，并补 smon 移交的 `escape_run_mode/cfx_code/ip/intr_mask` 出口意图（`intr_mask = 全 1` fail-safe）。Kaiwu 旧 escape 语法一并改为 `escape cfxha` + 写 `rc10`。
- **机械扫描**：`不保存、不恢复` / `异步没有 escape` / `没有 escape 返回路径` / `不恢复任何来源掩码` 在 spec+contracts 现行散文 **0 处**（仅 `IDL-ISA` 与 `SimRISC-11` IDL 块保留，F3 排除；历史变更记录保留）。
- **证据**：`run.sh` 新增 7 条断言（`cg9 rc15` 示例、Kaiwu/HBI 新口径、HBI mask 初始化、旧表述 0 处）→ **PASS=76 FAIL=0**；21 条 spec/契约门控仍全 rc=0；`check-cfx-vectors` 仍为唯一新增红（LLVM 向量旧 rc3，归因不变）。
- 未改 `tests/**`/`idl/**`/ADR；完成区与第 1 轮审阅记录未改；状态保持 **待验收**。

### 第 1 轮 reviewer 验收

**重跑记录**（仓库根、审查者本人执行）：运行期证据目录内 `run.sh` → `checks: PASS=69 FAIL=0`、`m18-spec-007 evidence: PASS`，退出码 0；其内 **21 条门控全部 rc=0**（spec-drift/numbering/changelog/purity/refs/codeblocks/cite-targets、legality-drift/-invariants、asm-prose/-list/-list-drift、opcodes-repro、cfx-aliases/-alias-table、contracts-dir/-pending、contract-relocs、manifests-guard、knowledge-refs、idl-sync）。单跑 `make -s check-spec-drift` rc=0（12 合约 0 错；README 表 SEE/SBI 已发布 0.8.0、SimRISC 0.5.7 + 在研 0.5.8-rc）。`make -s check-cfx-alias-table` rc=0 → `12 scalars, 1330 regs`（与完成区 12 标量/47 模板/46 专有/1330 一致）。
**KNOWN-RED 核实**：`make -s check-cfx-vectors` → rc=2，32 条向量仅 1 错 `cfx2-trap-escape.s:57 cfx2rd cfx_umon_excp_cause_ip 期望 7a0050c2（rc3）/ 独立派生 7a005082（rc2）`；基线 `contracts/cfx-aliases.txt` 该别名 `0 5 3`、当前 `0 5 2` ⇒ **归因成立（tests/** 未动，旧槽位向量）**，为唯一新增红。`make check` → exit 2，停在 `check-isa-coverage`（`找不到 llvm-mc`，环境红，与本 diff 无关），其前门控全 PASS。
**自设注入（第三路，与 engineer 两路不同）**：`cp` 备份 DADAO-12 → md5 `ed06a98f0924ed2c4eb02fd29dd1bd72`；把 §5.1/§5.3 的「整字写入目标模式 monitor 的 `cg8 rc1`」改为「按位增量写入」⇒ `run.sh` 退出 **1**，`FAIL check-manifests-guard rc=2` + `FAIL rc11 whole-word restore`，`checks: PASS=67 FAIL=2`；`cp` 还原 → md5 相等，重跑 `run.sh` 69/69、退出 0；前后 `git status --porcelain -uall` 均为空。
**约束核验**：37 文件与完成区逐一对齐（spec 21 + 契约 8 + contracts 3 + tools 3 + README + ADR + 本任务书）；零 `components/**`/`tests/**`/`idl/**`/内核/QEMU/RTL；工具仅 `generate_opcodes`/`check_asm_prose`/`gen_asm_list`；**未 push**（无 `origin/m18-spec-007`，`8c3251bd` 不在任何远端分支）；状态 `待验收`；工作树干净。「已确定」1–24 条齐全并逐条映射（编号 20/21 重复、18/19 错序，属已豁免的记录瑕疵）。ADR-0061 有 `## R3 修订`（R3-D1…D6，显式 supersede D9/D10），R2 段未改。版本：DADAO-12/22 = 0.8.0（附录 `### 0.8.0（2026-11-26）`）、contract-see = 0.8.0、SimRISC-00–12 = 0.5.8-rc、六册 DADAO「SimRISC 0.5.5」0 处、0.4.1 历史条目保留。
**证据脚本审核**：21 `gate` + 44 `has`/`lacks` 均有可达 FAIL（三路注入实证），无恒真/两支同果，计数现场派生；脚本合格，不需返工脚本。

**发现（findings）**：
- **F1（阻断）**：`spec/DADAO-22` §7.1 示例注释仍写「由 `cfx_hart cg9 rc5`（`async_excp_vector`）进入」——新布局向量在 **`rc15`**、`rc5` 已是 `async_src_pending`。该文件属验收 2 明列的「DADAO-22 举例槽位唯一且一致」且本任务已改过它；证据脚本无对应断言（应补一条 `has`）。
- **F2（阻断，须处置）**：`spec/Kaiwu` 现行条文「**异步没有 `escape` 返回路径**」「`escape` **不恢复任何来源掩码**」、`spec/DADAO-23`「`trap`/`escape` 不保存、不恢复该掩码」与已确定 9/13/19 直接相反（均为 spec 散文、无 `idl/` 依赖，本任务可改）；完成区遗留⑤ 只写「旧 escape 语法」，未覆盖该语义面。
- **F3（登记即可）**：`spec/IDL-ISA` §4.6 散文（`cg9` 七槽、`rc5`/`rc6` 为向量/开关、`imms18[1]` 恒 `CFXESC`）与其 IDL 块、`SimRISC-11` IDL 渲染块同源陈旧，须随 `idl/**` 任务一并改（单改散文会同节自相矛盾）；`Toolchain-01`/`contract-isa`/`contract-asm` 旧语法已披露。
- **F4（非阻断）**：`DADAO-13` 变更记录「`cg3 rc10`」、`contract-see` 历史条目按「变更记录豁免」处理。

**判决：Needs Revision**（F1 直接不满足验收 2；F2 需本任务改掉或由 architect 明确登记语义面遗留）。

### 第 2 轮 reviewer 验收

**F1 闭环 ✅**：`spec/DADAO-22 §7.1` 注释已改「由 `cfx_hart cg9 rc15`（`async_excp_vector`）进入」；同示例其余槽位逐一核对一致——`async_src_frame`=cg9 rc4、`cfx2rd cfx_hart_excp_cause_id`=cg5 rc4、`excp_cause_info`=cg5 rc5、`cfx_hart cg8 rc5`=timer_ctrl/ISTATUS、`cfx_pmem cg15 rc4`=dma_status（均与 `DADAO-12 §4.7`/`§4.9` 表与别名表一致）；新增「也可不 handoff：用 hart `cg5 rc8`–`rc11` 出口意图 `escape cfx_hart` 直接返回」不越权（`§5.4`/`§5.1` 明文允许）。
**F2 闭环 ✅ 且无越界改语义**：`Kaiwu §4.2` 改为「按当前 cfx `cg5 rc8`–`rc11` 出口意图恢复、跳 `rc10`、按 `rc11` 整字恢复目标模式 monitor `cg8 rc1`、`imms18` 必须 0」，同步/异步共用出口、异步可 `escape cfx_hart`；`Kaiwu` 旧 `escape cfxha, [offset]` 全部改 `escape cfxha` + 写 `rc10`（hmon 返回：重试保持 `rc10` 进入值、跳过前 `rc10 = excp_cause_ip + 4`，与 `DADAO-22 §1` 等价，**未改语义**）；`DADAO-23 §3` mask 句改「`trap` 只把进入前值抄入 `rc11`、`escape` 按 `rc11` 整字恢复 `cg8 rc1`」；smon 移交段写 `escape_run_mode=supv`/`cfx_code=smon`/`ip=rb16`/`intr_mask=全 1` 后 `escape cfx_smon`——`rc8`–`rc11` 本就软件可写、全 1 = 复位 fail-safe，终点掩码与原「`cg8 rc1` 初始化全 1」一致，**与规范一致、无越权**。
**全局残留扫描**：三类旧表述（`不保存、不恢复` / `异步没有 escape 返回路径` / `不恢复任何来源掩码`）在现行散文 **0 处**，仅 `IDL-ISA:322/324` 与 `SimRISC-11:98` IDL 块保留（F3 豁免）；旧偏移语法在 `Kaiwu`/`DADAO-22`/`DADAO-23` 现行 **0 处**；全库仍 5 处（`Toolchain-01:172/438`、`contract-asm:175/312`、`contract-isa:1201`）＝已披露遗留⑤（已发布 0.5.7 语法、未授权改），非阻断。
**门控（本人重跑）**：运行期证据目录内 `run.sh` → **`checks: PASS=76 FAIL=0`、exit 0**，其中 21 条 spec/契约门控全部 rc=0（spec-drift/numbering/changelog/purity/refs/codeblocks/cite-targets、legality-drift/-invariants、asm-prose/-list/-list-drift、opcodes-repro、cfx-aliases/-alias-table、contracts-dir/-pending、contract-relocs、manifests-guard、knowledge-refs、idl-sync）。`make -s check-cfx-vectors` → **exit 2**，仍仅 1 条 `cfx2-trap-escape.s:57 期望 7a0050c2（rc3）/ 派生 7a005082（rc2）`，归因不变、唯一新增红。`make check` → **exit 2**，仍停 `check-isa-coverage`（`找不到 llvm-mc`，环境红），其前门控全 PASS，与上轮/基线一致。
**自设注入（两路，本轮新角度）**：① 把 `Kaiwu` 的 `escape cfxha` 改回 `escape cfxha, [excp_cause_ip, 4]` ⇒ `run.sh` **exit 1**、`FAIL check-manifests-guard rc=2`、`checks: PASS=75 FAIL=1`；② 把 `Kaiwu` 的「按 `rc11` 整字恢复」删「整字」⇒ **exit 1**、`FAIL check-manifests-guard` + `FAIL Kaiwu rc11 mask restore`、`checks: PASS=74 FAIL=2`。两路均 `cp` 备份（md5 `9350e087fcc45855fc78e357a1f94ba5`）→ 还原 md5 相等 → 重跑 **76/76 exit 0**，`git status --porcelain -uall` 为空。
**范围 ✅**：`git diff 833402e6^ 833402e6 --name-only` 恰 **5 文件**（任务书 + `spec/.manifests.toml`（3 条 sha 重算，`check-manifests-guard` rc=0）+ `DADAO-22` + `DADAO-23` + `Kaiwu`）；无 `components/**`/`tests/**`/`idl/**`/ADR 改动；未 push（`833402e6` 不在任何远端分支）；状态 `待验收`；工作树干净。
**非阻断 finding**：`Kaiwu §4.2` 仍把「返回 cfx、运行模式与 IP 均取自当前 cfx 的异常帧」标为 `DADAO-12 §5.3` 原文，该句在 `§5.3` 无逐字对应（`§5.1` 现表述为「取自 `cg5` 出口意图 `rc8`–`rc11`」）——措辞级引述不准，交 architect 收尾改，不阻断。

**判决：Accepted**（F1/F2 均闭环、语义无越界；门控 76/76 与 KNOWN-RED 归因复核一致；范围与注入还原合规）。
