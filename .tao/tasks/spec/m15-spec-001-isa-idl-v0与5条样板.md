# m15-spec-001: ISA 语义源（`idl/`）v0 + 5 条样板 + 渲染器

**模块**：spec
**项目里程碑**：M15
**依赖**：无
**可并行分片**：否（`idl/` 单写者）
**预估**：2–3 天
**档位**：中改
**状态**：待验收

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
3. `idlc` 编写期 oracle（人工跑一次并记录退出码，**两段式**）：① `README.md §4` 的语义库（含 `enum`/`function`/`builtin function`）⇒ `idlc compile --root isa` **exit 0**；② 每条 operation 单独（注入解码变量）⇒ `compile --root instruction_operation` **5/5 exit 0**。（`isa` 根只接受声明，库与 operation 不能拼成一个文件跑 `isa`。）
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

### 第 1 轮 engineer 自审（实现完成）

自审方式：自主逐行审查（深度 1，不外派）。审查面 = `idl/render.py`、`idl/README.md`、5 册 `.idl`、5 册标记块、Makefile/Process-06/07 接线、证据脚本。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `ip()` 若写成 `body { return ip64[47:0]; }`，`idlc` 的 `PartSelectAst#const_eval?`（`ast.rb:2663` 把 bool 当 Var 再调一次）在 operation `type_check` 调 `jump`/`ip` 时崩 | ✅已修 | `ip` 改 `builtin function`（描述仍写「= `rb0` 低 48 位」，语义不变） | 改前 type-check 5/5 全 `NoMethodError`；改后库 16/16、operation 5/5 PASS |
| F2 验收 3「§4 库 + `.idl` 拼接 → `compile --root isa` 0」按字面**不可能**（`isa` 根只接受声明，operation 是 `instruction_operation` 根） | ✅已修（口径） | 写法拆成「库→`isa`；operation 逐条→`instruction_operation`」并**同时记录字面形式的 rc=1**（`all.idl:166` SyntaxError） | 见「验收结果」3 与 `idl/README.md §6.1` 第 7/8 行 |
| F3 自检里 `drop-id` 注入触发 `RenderError` 冒泡，把「检出」误判成「自检失败」 | ✅已修 | 新增 `run_rc()`：断言失败 rc 化（`run()` 仍抛，CLI 侧照常非零） | `--self-test` 6/6 PASS；注入 2/3/4/5 各自 rc=1 |
| F4 「逐字节」原先用 `read_text` 字符串比较 | ✅已修 | 新增 `same_bytes()`（`read_bytes` 与 UTF-8 编码全等）；写盘改 `write_bytes` | `--check` 仍 PASS；注入 A（改一字符）rc=1 |
| F5 只用 `# id:`/标记做搬运 ⇒ 语义库与 operation 可「互相不认识」 | ✅已修 | 新增断言 E：operation 调用的函数必须在 `idl/README.md §4` 声明（排除 `$signed(` 与 if/for/return） | 自检第 5 类注入（`rd_read_typo(`）rc=1；正向 PASS |
| F6 `spec/README.md` 的 IDL 指针指向 WIP 已删的 `contracts/isa/idl-v0.md`（死引用） | ✅已修（越界披露） | 该节改为「源在 `idl/`、块由 `render.py` 生成、语义库见 `idl/README.md`」并重算 sha256 | `check-spec-purity` 0；`grep contracts/isa` 0（除归档/discussing/本任务书） |
| F7 `make check` 的 4 项红（patch-tree / milestones-fresh / run-artifacts / temp-dirs）与本任务无关 | ⏸延后 | 不改（均属其它任务/共享 `.work`） | 主工作树复现 patch-tree 同样 11 条；milestones 违例为 `m16-chipyard-005`/`m16-gem5-013`；run-artifacts 16 条全属 `m16-gem5-012`/`k4_stack` |
| F8 `discussing.md` 仍有 2 行引用 `contracts/isa/idl-v0.md` | ⏸延后 | 不改（子代理禁改该文件） | 见「待裁定」2 |

判决：无未修 finding（F7/F8 属跨任务口径，已登记）；任务置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-19；中改档：4 路注入 + 证据脚本重跑）

**改动面**：`git diff bd43172e..HEAD --name-status` = 20 文件，全落在硬约束 4 清单 + 已披露的 `spec/README.md`；`contracts/isa/**` 与 `tools/spec/extract_idl.py` 已删；`contracts/README.md` 净零改动（WIP 所加 isa 行已移除）。

**方向核（独立逐字节比对，非目测）**：5 个 `idl` 围栏块与 `idl/SimRISC-*.idl` 对应段全等（5/5，正文 12/6/14/8/16 行）；标记 5 对、每册恰 1 对、均落在对应指令小节内；标记区外无其它 `idl` 围栏；`python3 idl/render.py --check` 两跑输出全等 **rc=0**。

**四路注入（自跑，cp+md5 还原）**：① 改 spec 块一字符 ⇒ **1** → 还原 **0**（首跑经管道误取 `head` 的 rc，已无管道重跑取真值）；② 改 `.idl` 不重渲染 ⇒ **1** → **0**；③ 删一条 `# id:` 留标记 ⇒ **1** → **0**；④ **（未列）** id 改为 `opcodes.yaml` 不存在的 `trap_ciii_cfx_zz` ⇒ **1**（`源里的 id 不在 contracts/opcodes.yaml`）→ 还原 **0**。终态 13/13 目标文件 md5 = 审前基线，`git status --porcelain -uall` 干净。

**证据脚本**：审运行期证据目录内的 `run.sh`——`check()` 直取被检命令 rc（无管道吞码）、三路注入均有可达 FAIL、计数现场派生（5/5/5）、还原用 cp+md5；重跑 **25/25 PASS，rc=0**。[22] 排除 archive/discussing/本任务书系披露项（F8/待裁定 2）；master 侧 discussing 已改 `idl/`（我核 grep = 0）。

**语义库（逐条对裁定）**：`read_memory`/`write_memory`（**无 `_be`**）、`fetch_memory`、`raise(code,mode,addr)` 三参、`is_naturally_aligned`、`ras_push/pop/cnt`、`reservation_set/clear_all` 均在 README §4；`rd[]/rb[]/rf[]/ra[]/fo[]/ft[]` 数组式声明，§3 的 0 号语义表 6 行齐备；`ExceptionCode` 位值与 Kaiwu §7.1 一致（ILLI=1<<8、MALIGN=1<<12、CFXPERM=1<<7）。

**5 样板 vs 正文**：`add.so` 双目的+rd0 规则（`rdHA==rdHB`⇒ILLI）✓；`ld.o` rd0⇒ILLI ✓；`br.eq` `ip()`≡rb0 读、`{imms12,2'b00}`=<<2 ✓；`lr` hb SBZ⇒ILLI + `reservation_clear_all`→`reservation_set(ea,64)`（键=地址+宽度）✓；`trap` 三分支（reserved⇒ILLI / denied⇒CFXPERM / else `cfx_trap_enter`）✓；字段名与 `opcodes.yaml` 相符。

**idlc 两段式（修订后验收 3，自跑）**：§4 库 → `idlc compile --root isa` **rc=0**；5 条 operation → `compile --root instruction_operation` **5/5 rc=0**；Ruby 驱动 **16/16 + 5/5 rc=0**，注入 `read_memory(ea)` 少一参 ⇒ **rc=1**；`grep -n idlc Makefile` **0 命中（rc=1）**。（用任务运行期探测环境离线取证；`bin/idlc` 的 mise 包装现挂起于下载工具链——环境问题，非交付物缺陷。）

**门控（自跑）**：`check-idl-sync`、`check-manifests-guard`、`check-spec-drift`、`-purity`、`-refs`、`-numbering`、`-changelog`、`check-knowledge-refs` 全 **rc=0**。

**最小性/越界**：5 册 diff = 纯标记块新增，正文与版本行 `0.5.7-rc` 零改动；`spec/.manifests.toml` 22 条 sha256 与现场全等；`idl/.manifests.toml` 7 文件无 sha256、与现场集合一致；Process-06 §9 / Process-07 表行与计数 63+1 正确；`spec/README.md` 净改动仅 6 行 IDL 指针节——越界披露属实，**接受**（待裁定 3）。

**判决：Accepted**。留档（不阻断）：① 分支内任务书验收 3 仍为字面旧式，master 已改两段式 ⇒ squash 合并以 master 版为准、勿回退（待裁定 1/2 已在 master 侧闭合）；② `run.sh` [22] 对 discussing 的排除建议后续补一条独立断言；③ 未复核采信项 = README §6 的 strace 网络计数与 UDB 许可/版本溯源行（非验收项）。

## 完成区

**测试结果**：一键证据脚本 25/25 通过（4 类自检 + 3 路可达 FAIL 各含 md5 还原回绿 + 9 项门控 + 幂等 + 越界断言）；`make check` 的红项全为基线（F7）。
**修改文件**：新增 `idl/README.md`、`idl/render.py`、`idl/.manifests.toml`、`idl/SimRISC-{01,04,06,11,12}.idl`；5 个 spec 册的 `<!-- IDL:… -->` 标记块（块内容全部由 `render.py` 生成）；`spec/README.md`（IDL 一节改指 `idl/`，越界披露见 F6）；`spec/.manifests.toml`（6 册 sha256 同笔重算）；`manifests/dir-guard-roots.toml`（`roots` 加 `idl`）；`Makefile`（`check-idl-sync` + 进 `_locked-check` + help 行）；`docs/Process-06`（新增 §9 生成段不许手改）；`docs/Process-07`（§1.1 登记行 + §7 表格行 + 现场计数 63/64 订正）；删除 `contracts/isa/**`、`tools/spec/extract_idl.py`；本任务书。**未动版本号**（5 册册头 `0.5.7-rc` 原样）。
**验收结果**（逐条 rc）：
1. `make check-idl-sync` **0**、`idl/render.py --check` **0**（两次输出全等）；`--self-test` **0**（6/6）。
2. 三路可达 FAIL：改 spec 块一字符 **1** → md5 还原 → **0**；改 `.idl` 不重渲染 **1** → 还原 → **0**；删一条 `# id:` 留标记 **1** → 还原 → **0**（md5 三处逐项对账）。
3. `idlc` 编写期 oracle：§4 库 `compile --root isa` **0**；**字面形式「库 + 各册 `.idl` 拼接」`compile --root isa` = 1**（`isa` 根只接受声明，`all.idl:166` SyntaxError ⇒ 见待裁定 1）；逐条 operation `compile --root instruction_operation` **0（5/5）**；Ruby 驱动类型检查 **0**（库函数 16/16、operation 5/5）；负向（`read_memory` 少一参）**1**；`strace` 网络调用 **0**。不进 `Makefile`。
4. `make check-manifests-guard` **0**（5 份清单，`idl` 受检；`idl/.manifests.toml` 只列文件名、无 `sha256`）。
5. `check-spec-purity`/`-codeblocks`/`-numbering`/`-changelog`/`-cite-targets`/`-drift`/`-refs`、`check-asm-list`、`check-legality-drift`、`check-contracts-dir`、`check-knowledge-refs` 全 **0**。
6. `contracts/isa/` 已移除；`grep -rn "contracts/isa"` 仅剩 `.tao/archive/**`（历史）、`.tao/knowledge/discussing.md` 2 行（待裁定 2）、本任务书自身。
7. 完成区 ≤30 行；状态 → `待验收`。
**新发现/坑**：① `idlc` 的 `PartSelectAst#const_eval?`（`ast.rb:2663`）把 `const_eval?` 的布尔值再当 Var 调一次，**只在**「被调用函数体的 `return` 里含位切片」时触发（UDB 因 `X[]` 是 `RegFileElementType` 早退而掩盖）；② `isa` 根只接受声明、operation 必须走 `instruction_operation` ⇒ 「库与 operation 拼一个文件编译」不是这套语法的用法；③ 纯 `Bits<N>` 数组足以表达四组寄存器（不必借 `register_files:`），0 号语义只能写成**模型不变量**；④ 建议沉淀：「标记对 + 生成器 + 逐字节 `--check`」的生成段范式（已与 ASSEMBLY_LIST/LEGALITY 并列入 Process-06 §9）。
**遗留问题**：① 基线红（与本任务无关，主工作树复现）：`check-patch-tree` 11 条（linux 组件）、`check-milestones-fresh` 2 条（`m16-chipyard-005`/`m16-gem5-013` 有 worktree 却在「待开始」）、`check-run-artifacts` 16 条（`m16-gem5-012`/`k4_stack` 日志命名）、`check-temp-dirs` 4 个陈旧 `m14-linux-*` 目录；② 待裁定 1–3。

## 待裁定

1. **验收 3 的字面形式不可达**：`isa` 根只接受声明（枚举/数组/函数），operation 是 `instruction_operation` 根，故「§4 库 + `idl/*.idl` 拼接后 `compile --root isa`」实测 rc=1。临时处置：按「库→`isa`、operation 逐条→`instruction_operation`」取证（更强：另有 Ruby 驱动类型检查 16/16 + 5/5）。建议：把验收 3 改成这种两段式写法。
2. **`discussing.md` 残留 2 行**引用 `contracts/isa/idl-v0.md`（第 148、212 行）——该文件只由主会话改，需主会话同笔更新为 `idl/` 口径，否则验收 6 的 grep 永不为 0。
3. **`spec/README.md` 越界**：硬约束 4 的文件清单未列它，但该册的「ISA 语义（IDL）」小节是 WIP 加的、指向已删的 `contracts/isa/idl-v0.md`。临时处置：改写该节并重算 sha256（只改指针与「块由 `render.py` 生成」的说明，未动任何指令语义与版本号）。若不接受，请指示回退该节（回退后 `grep contracts/isa` 会命中 `spec/README.md`）。
