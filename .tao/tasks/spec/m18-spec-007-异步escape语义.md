# m18-spec-007: 定义「异步 escape」——从异步进入现场返回

**模块**：spec
**项目里程碑**：M18
**依赖**：用户给出语义定义（本任务书「待裁定 1」）；`m18-spec-005`（ADR-0061 R2 现行口径）
**可并行分片**：否（spec/契约 + 活文档）
**预估**：待定（语义由用户给出后再标定）
**档位**：大改（异步模型 + `escape` 语义）
**状态**：**待开始（不派发：等用户回复可派发）**
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
19. **版本**：本批改动并入 **0.8.0 定版**（`0.8.0-rc` → `0.8.0`，去掉 `-rc`、补发布日期），**不是**升到 0.9.0；`DADAO-12` 与 `DADAO-22` **同批**定为 0.8.0（两册头部写明“与 SEE 版本号一致”），`contract-see` 随上游册同步（`check-spec-drift` 不变量）。

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
4. 版本：`DADAO-12` 与 `DADAO-22` 去掉 `-rc` 定为 **0.8.0** 并补发布日期；`contract-see` 同步 0.8.0；不动 `contract-syscall` 的 0.9.2。

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

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 engineer 自审
（工程师自审意见、问题、判决及 finding 处置）

### 第 1 轮 reviewer 验收
（审查者独立重跑记录、约束核验、判决）
