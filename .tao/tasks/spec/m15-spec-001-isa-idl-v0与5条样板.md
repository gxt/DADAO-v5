# m15-spec-001: ISA 语义源（`idl/`）v0 + 5 条样板 + 渲染器

**模块**：spec
**项目里程碑**：M15
**依赖**：无
**可并行分片**：否（`idl/` 单写者）
**预估**：2–3 天
**档位**：中改
**状态**：待开始

## 背景与方向修正（用户 2026-11-18）

原 WIP（`0584a64b`）走的是「spec Markdown 是真源 → 抽取 `.idl` 投影」，**方向已反转**（用户 2026-11-18 裁定）：

- **`.idl` 是机器可读语义源**；spec 正文里的 ```idl 块是**渲染结果**，不许手改；
- 源与消费它的工具**放一起**，放仓库根 **`idl/`**（用户：`tools/` 已用废，不再往那儿塞）；
- `contracts/` 只放**从 spec 派生的**机器数据，不再放 IDL 源。

## 用户裁定（逐条，返工必须遵守）

1. **目录**：仓库根 `idl/`；每册一个 `.idl`（`SimRISC-0x.idl`）。
2. **寄存器模型（方案 C）**：`rd[]`/`rb[]`/`rf[]`/`ra[]` 各 64×64；`fo[]`（64 位视图）/`ft[]`（低 32 位视图）是 `rf` 的数据视图；`rf[]` 只用于整 64 位搬移（`rf2rf`/`rf2rd`/`rd2rf`）与 FCSR。
3. **0 号语义**：`rd[0]` 读 0、写丢弃（目的是否 ILLI 由各指令判）；`rb[0]` 读出 = IP、写 ⇒ ILLI；`rf[0]` = FCSR（`ft[0]` 只覆盖可写 `[4:0]`）；`ra[0]` = `{RACNT, MRPTR}` 元数据。
4. **`ra`**：逻辑栈序（`ra63` = 栈顶）+ `ras_*` 函数；物理环状缓冲不暴露（`spec/SimRISC-00 §2.4` 已加实现注）。
5. **写宽度**：`rd`/`rb`/`ra`/`rf` 整 64；`ft` 只写低 32；`ld.t`/`ldm.t` 走 `ft[]`。
6. **访存函数**：**不带 `_be` 后缀**（DADAO 只支持大端），用 `read_memory(width_bits, ea)` / `write_memory(width_bits, ea, value)`，与 UDB 同名；**取指单独 `fetch_memory(...)`**。
7. **`raise` 带三参**：`raise(code, mode, addr)`（与 UDB 同形）；`mode()` 返回当前运行模式。
8. **对齐判定按 UDB**：`is_naturally_aligned(N, value) -> Boolean`，异常由 operation 显式 `raise`（不再用会抛异常的 `check_alignment`）。
9. **`idlc` 不进门控**，只作编写期 oracle。
10. **语法子集「用到再说」**（不现在扩 tuple/struct/include）。
11. **`.idl` 的 sha256 锁延后**：`idl/.manifests.toml` 本轮**只列文件名**（双向集合断言照做），**不写 `sha256`**；M15 收口统一补（`discussing.md` N21）。

## 交付物

### 1. `idl/README.md`（语法与语义库说明）

- §1 语法基线（UDB 子集，逐条列出实际用到的构造；不复制 `doc/idl.adoc` 全文）；
- §2 命名约定（编码字段名 ↔ 解码变量；立即数「汇编层宽 2 位」的移位表：`br.eq` `<<2`、`aip.si` `<<12` 等）；
- §3 寄存器模型（四组数组 + `fo`/`ft` 视图 + 0 号语义表 + 写宽度）；
- §4 语义库（函数签名 + `description` + `body` 或 `builtin`）：
  ```
  ip() -> Bits<48>
  mode() -> RunMode
  jump(Bits<64> target)
  raise(ExceptionCode, RunMode, Bits<64> addr)
  fetch_memory(U32 width_bits, Bits<48> ea) -> Bits<64>
  read_memory(U32 width_bits, Bits<48> ea) -> Bits<64>
  write_memory(U32 width_bits, Bits<48> ea, Bits<64> value)
  is_naturally_aligned(U32 width_bits, Bits<48> ea) -> Boolean
  cfx_is_reserved(Bits<6>) -> Boolean
  cfx_trap_denied(Bits<6>) -> Boolean
  cfx_trap_enter(Bits<6> cfxha, Bits<18> immu18)
  reservation_set(Bits<48> ea, U32 width_bits)
  reservation_clear_all()
  ras_push(Bits<48>) / ras_pop() -> Bits<48> / ras_cnt() -> Bits<6>
  ```
- §5 语法扩展提案（三态：采纳/搁置/否决；当前应为 0 条语法扩展）；
- §6 `idlc` 复用评估（沿用 WIP 的实测结论，注明「不进门控」）。

### 2. `idl/SimRISC-0x.idl`（每册一个，本任务只做 5 册）

- `SimRISC-01.idl`（`ld.o_rrii_rd`）、`SimRISC-04.idl`（`add.so_rrrr_rd`）、`SimRISC-06.idl`（`br.eq_rrii_rd`）、`SimRISC-11.idl`（`trap_ciii_cfx`）、`SimRISC-12.idl`（`lr.o.nn_orrr_rd`）；
- 每条以 `# id: <instr-id>` 开头，id 必须存在于 `contracts/opcodes.yaml`；
- **按第 2–8 条重写**（数组式、`read_memory`、`raise` 三参、`is_naturally_aligned`）。

### 3. `idl/render.py`（渲染器，**完全重写**）

- 读 `idl/*.idl`，按 `# id:` 切分；
- 在对应 spec 册里找 `<!-- IDL:<instr-id> BEGIN -->` … `<!-- IDL:<instr-id> END -->`，替换为 fenced ```idl 块；
- `--check`：重渲染后与 spec 文件逐字节比对，不一致 ⇒ 非零；
- 断言：`.idl` 的 id ∈ `opcodes.yaml`；每个 id 在 spec 有标记；spec 的标记都有对应 id（防空标记）；
- `--self-test`：三类注入（改 `.idl` 未重渲染 / 改 spec 块 / 删除一条 id）。

### 4. spec 册加标记块

5 册各加一个标记块（内容由 `render.py` 生成，**禁止手写**）。`spec/*.md` 改动后**同笔重算** `spec/.manifests.toml` 的对应 sha256（既有门控要求）。

### 5. 目录与门控

- `manifests/dir-guard-roots.toml` 的 `roots` 加 `"idl"`；
- `idl/.manifests.toml`：列 `README.md`、`render.py`、`SimRISC-*.idl`（**无 sha256**），可在 `subdirs` 预留 `m17`；
- `Process-06` 加「生成段不许手改」规则与 `<!-- IDL:… -->` 标记约定；
- `Process-07` 门控表加 `check-idl-sync`（L1，调 `idl/render.py --check`）；
- `Makefile` 加 `check-idl-sync` 目标（进 `_locked-check`）；
- **移除** `contracts/isa/`（WIP 产物）与 `contracts/README.md` 对应行。

## 验收（逐条贴真实 rc）

1. `make check-idl-sync` rc=0；`idl/render.py --check` 幂等（两次一致）。
2. **可达 FAIL（三路）**：改 spec 块的一个字符 ⇒ 红；改 `.idl` 后不重渲染 ⇒ 红；删一条 `# id:` 但留标记 ⇒ 红。各自 `cp`+md5 还原 ⇒ 绿。
3. `idlc` 编写期 oracle（人工跑一次并记录退出码）：把 `idl/*.idl` 与 `README.md §4` 的库按序拼接 ⇒ `idlc compile --root isa` **exit 0**；对 5 条 operation 逐条 `compile --root instruction_operation` exit 0。
4. `make check-manifests-guard` rc=0（`idl` 在受检目录内；`idl/.manifests.toml` 的文件集合与现场一致）。
5. `check-spec-drift`/`-purity`/`-refs`/`-numbering`/`-changelog` rc=0（spec 只加标记块，正文语义未改）。
6. `contracts/isa/` 已移除；`grep -rn "contracts/isa" --include=*.md --include=*.py --include=Makefile .` = 0（历史任务书/归档除外，逐条列明）。
7. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree（分支 `m15-spec-001`，**先 `git merge master`** 并解决冲突；冲突以 master 版任务书/台账为准）。
2. 禁改主工作树；**禁提交 git**；**不改版本号**（spec 册只加标记块与生成内容，版本行不动）。
3. **不手写 spec 里的 ```idl 块**——一律由 `render.py` 生成。
4. 只动：`idl/**`、5 个 spec 册的标记块、`spec/.manifests.toml`（重算 sha256）、`manifests/dir-guard-roots.toml`、`Makefile`、`docs/Process-06`、`docs/Process-07`、`contracts/README.md`（删行）、`contracts/isa/**`（移除）、本任务书。
5. `cp`+md5 还原（禁 checkout/restore/stash/show）。

## 待裁定

（执行中如有 → 写入本节并返回）

## 审阅记录

（待填）
