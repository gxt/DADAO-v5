# m15-spec-008: SimRISC 0.5.7 发布

**模块**：spec
**项目里程碑**：M15
**依赖**：无（M15 其余任务全绿；本任务须在 M15 归档**之前**完成）
**可并行分片**：否
**预估**：1 h
**档位**：小改（版本发布 + 清单）
**状态**：已验证

## 背景（用户 2026-11-20 指示）

M15 归档前把 **SimRISC 发布版本定为 0.5.7**：13 册当前均为 `0.5.7-rc`（未发布），本次把 `-rc` 去掉、记为正式发布。**DADAO-12 与其它册的版本不动**。

## 目标

1. **13 册册头**（`SimRISC-00`–`12`）：`> **版本：0.5.7-rc**（与 SimRISC-00 一致）` → `> **版本：0.5.7**（与 SimRISC-00 一致）`；
2. **`SimRISC-00` 变更记录（用户 2026-11-20：这是给人看的，要重新整理）**：
   - 顶部段改为 `### 0.5.7（2026-11-20）`；
   - **按主题重组**（建议五组，可微调）：浮点语义（NaN/标志/溢出/取整）· 指令与编码（新增/删除/编码不兼容）· 访存与原子（`ldm`/`stm` 精确性、地址重叠、`lr`/`sc`）· 伪指令与形式化语义 · 文档与措辞；
   - 每组一句导语 + 要点；**删掉逐条重复的「版本号不变（用户 …）」元话术**，改为段首一句总述（保留必要的裁定日期）；
   - **只重组、不新增事实**：给「原条目 → 新分组」映射表，证明无内容丢失；
3. **`spec/.manifests.toml`**：13 册的 `sha256` 同笔重算；
4. 全仓确认 `0.5.7-rc` **零残留**（历史归档目录除外；归档里的旧版本记录不改）。

## 验收（逐条贴真实 rc）

1. `check-spec-changelog` **rc=0** 且报告里 **`rc_segments` 相关统计为 0**（无未发布段）；`check-spec-numbering`、`check-spec-purity`、`check-spec-refs`、`check-spec-codeblocks`、`check-manifests-guard` 全 rc=0；
2. `grep -rn "0\.5\.7-rc" spec/ .tao/contracts/ docs/` ⇒ **0 命中**（`.tao/archive/**` 与任务书历史记录除外，逐条列出）；
3. 13 册册头版本一致（脚本现场统计，别手数）；
4. **可达 FAIL ≥2 路**（临时树/`cp`+md5）：① 把某一册改回 `0.5.7-rc` ⇒ `check-spec-changelog` 红（册头与附录不一致）；② 改一册版本号与 `SimRISC-00` 不同 ⇒ 红；
5. 只改版本相关行；**正文零改动**（剥版本行后逐字节比对）。

## 不在范围

不改任何语义正文、不动契约、不动 `DADAO-*` 的版本；不建 git tag（如需要发布标签，另行确认）。

## 约束

独立 `git worktree`；不提交 git；术语「寄存器组」；完成区不写具体 `.work/**` 路径。

## 完成区

**测试结果**：验收检查 28/28（证据脚本正常模式，rc=0）；反例注入 4/4 均命中预期 FAIL、经 `cp` 备份 + md5 对账还原后回绿（证据脚本 `--inject`，rc=0）。

**修改文件**：`spec/SimRISC-00…12`（13 册册头）；`spec/SimRISC-00`（变更记录 `0.5.7` 段按主题重排）；`spec/.manifests.toml`（13 册 sha256 重算）；本任务书。

**验收结果**（真实输出）：

- `check-spec-changelog` rc=0：`files=22 segments=58 rc_segments=9 bullets=285 simrisc_header_versions=['0.5.7']`；其中 SimRISC 的 `-rc` 段**现场派生 = 0**，9 个 `-rc` 段分别属于 DADAO-11/12/13/21/22/23、IDL、Kaiwu、Toolchain（本任务范围外）。
- `check-spec-numbering` / `check-spec-purity` / `check-spec-refs` / `check-spec-codeblocks` / `check-manifests-guard` / `check-idl-sync` / `check-spec-cite-targets` / `check-asm-list` / `check-legality-drift` / `check-spec-drift` 全 **rc=0**（PASS 行见证据脚本输出）。
- `grep -rn "0\.5\.7-rc" spec/ .tao/contracts/ docs/` ⇒ 三处各 **0 命中**；全仓除 `.tao/archive/**` 与历史任务书外仅 `README.md` 1 处（声明例外，见「遗留问题」）。
- 13 册册头现场统计：`count=13 unique=['0.5.7']`。
- 正文零改动：13 册剥掉册头版本行（`SimRISC-00` 另剥变更记录段）后与基线逐字节相同（`差异=无`）；`01–12` 各只改 1 行。
- 清单：13 册 sha256 现场重算全符；`spec/.manifests.toml` 只改 13 行（13/13）。
- 段内 `code` 标志 token 对账（原段 vs 新段，现场派生）：113 → 112，**唯一缺失 = `0.5.7-rc`（本次发布本身就是去掉它）**，新增 0。
- 反例（4 路，均 `cp` 备份 + md5 还原）：I1 一册册头改回 `0.5.7-rc` ⇒ `check-spec-changelog` 红（册头 `-rc` 与附录顶部段不一致 + 互锁组不一致）；I2 一册册头改 `0.5.6` ⇒ `check-spec-changelog` 红（互锁组不一致）；I3 `SimRISC-05` 正文注入 1 字符 ⇒ 正文零改动检查红；I4 删 1 个事实标志串 ⇒ 21 条无丢失检查红。4 路还原后 md5 与注入前一致、全量复跑回绿。

**0.5.7 段映射表（原 21 条 → 新分组；21 条事实标志串逐条机械核对，缺失=无）**

| # | 原条目（首句） | 新位置 |
|---|---|---|
| 1 | 两处浮点措辞明确 | 浮点语义 · 取整 `0x20` 档的 `NX` 与 `*2it`/`*2ut` 的写宽 |
| 2 | signaling compare 的无序结果改为 canonical quiet NaN | 浮点语义 · 结果 NaN 统一为 canonical quiet NaN（并入该条） |
| 3 | `lr` 的窄宽度写入不定高位 | 访存与原子 · `lr` 的窄宽度写入不定高位 |
| 4 | §5 伪指令改为简述 + 实现表 | 伪指令与形式化语义 · §5 伪指令改为简述 + 实现表 |
| 5 | `set.ft rf, 0` 的展开订正 | 伪指令与形式化语义 · `set.ft rf, 0` 的展开订正 |
| 6 | `fo2ft` 溢出按舍入方向 | 浮点语义 · 浮点→浮点转换与融合乘加的溢出按舍入方向 |
| 7 | 融合乘加溢出按舍入方向 | 浮点语义 · 同上条（合并） |
| 8 | `ftrem`/`forem` 的 NaN 优先级 | 浮点语义 · `ftrem`/`forem` 的 NaN 优先级 |
| 9 | 浮点规范性引用 | 规范性引用 · 浮点规范性引用 |
| 10 | 多元素内存指令的精确性例外 | 访存与原子 · 多元素内存指令的精确性例外 |
| 11 | `ldm` 的地址寄存器不得落入传送范围 | 访存与原子 · `ldm` 的地址寄存器不得落入传送范围 |
| 12 | `rootn(±0, 2)` 收严为 `+0` | 浮点语义 · `rootn(±0, 2)` 收严为 `+0` |
| 13 | 结果 NaN 统一为 canonical | 浮点语义 · 结果 NaN 统一为 canonical quiet NaN（与第 2 条合并） |
| 14 | 浮点比较族的异常标志 | 浮点语义 · 浮点比较族的异常标志 |
| 15 | `ext.uo`/`ext.so` 的扩展起始位取低 6 位 | 指令与编码 · `ext.uo`/`ext.so` 的扩展起始位取低 6 位 |
| 16 | semihosting 的服务号通道 | 指令与编码 · semihosting 的服务号通道 |
| 17 | 删除同格式纯复制、新增 rf 组块复制（编码不兼容） | 指令与编码 · 删除同格式纯复制、新增 rf 组块复制（编码不兼容） |
| 18 | 单精（ft）结果的写入宽度归位 | 浮点语义 · 单精（ft）结果的写入宽度归位 |
| 19 | 伪指令正文迁入本册 §5、16 位立即数操作册按寄存器组拆分 | 伪指令与形式化语义 · 同名条目 |
| 20 | 伪指令表 8 行 → 7 行：两行寄存器源形式合并为 `set.rf rf, rs` | 伪指令与形式化语义 · 同名条目 |
| 21 | 形式化语义块改为节末集中 + 三级标题 | 伪指令与形式化语义 · 同名条目 |

分组条目数（现场统计）：浮点语义 7 · 指令与编码 3 · 访存与原子 3 · 伪指令与形式化语义 5 · 规范性引用 1 = **19 条**，原 21 条中 2 组各两两合并（第 2+13 条、第 6+7 条），无条目丢失、无新增事实。

**重排后的 0.5.7 段（`spec/SimRISC-00` 现状）**

````text
### 0.5.7（2026-11-20）

本版改动集中在浮点语义（对齐 IEEE 754-2019）、指令编码面（删两条纯复制、增 `rf2rf`）、访存精确性与伪指令/形式化语义的组织方式；各条裁定均已在开发期落定（2026-11-16 至 2026-11-20），下文只记「改了什么」。

**浮点语义** —— 本组统一 NaN 结果与比较标志、按舍入方向处理溢出、收严 `rootn(±0, 2)` 与取整的 `NX`，并把单精写宽归位。

- **结果 NaN 统一为 canonical quiet NaN**：凡结果应为 quiet NaN 的情形（算术、缩放、开方、取余、融合乘加、取整、最小最大、格式转换，以及比较的 quiet 无序结果与一切无效操作产生的 qNaN）一律返回 **canonical quiet NaN**（符号位 0、payload 全零 ⇒ ft `0x7FC0_0000`、fo `0x7FF8_0000_0000_0000`）；复制类（`rf2rf` 等纯位搬移）、最小最大的单 NaN 情形不适用；IEEE 754-2019 §6.2.3 对 payload 传播仅为 *should*、§6.3 不规定结果符号位 ⇒ 取 canonical 属允许的实现选择、**不是**有意偏离。`ftscmp`/`foscmp` 在无序时**不再返回 sNaN 位型**，与 `ftqcmp`/`foqcmp` 一样返回 canonical quiet NaN——IEEE 754-2019 §6.2.1 规定一般计算类操作收到 signaling NaN 时**必须**返回 quiet NaN，原「Signaling Compare 的结果为 sNaN」不符合该 `shall`、作废；「两个 NaN 取哪个 payload」随之消解（统一 canonical，不再传播 payload）。
- **浮点比较族的异常标志**：signaling compare 只要无序（sNaN 或 qNaN 操作数）即置 `NV`；quiet compare 仅在含 sNaN 时置 `NV`，只含 qNaN 为安静无序、不置标志；有序比较不置标志。四条比较指令只可能置 `NV`，不置 `DZ`/`OF`/`UF`/`NX`，标志 sticky 写入 `rf0[4:0]`。
- **`ftrem`/`forem` 的 NaN 优先级**：remainder 的无效操作条件按 IEEE 754-2019 §7.2 f) 补全「且两个操作数都不是 NaN」的限定——除数为 ±0 或被除数为 ±Inf 时，仅当两者均非 NaN 才置 `NV`；任一操作数为 quiet NaN ⇒ 返回 qNaN 且不置标志（NaN 输入优先于该无效条件），signaling NaN 仍按 §7.2 a) 置 `NV`；除数为 ±0 属无效操作而**不是**除零（`DZ`）。另逐条写明「qNaN × ±0 / sNaN × ±0 / 有限 × ±0 / Inf × 有限 / Inf × Inf / 有限 × Inf / 有限 × 有限」七种组合的结果与标志。
- **浮点→浮点转换与融合乘加的溢出按舍入方向**：两者均按 IEEE 754-2019 §7.4 决定——RNE/RNA ⇒ `±Inf`（符号随精确结果）；RTZ ⇒ `±` 最大有限值（符号随精确结果）；RUP ⇒ 正溢出 `+Inf`、负溢出为最负的有限值；RDN ⇒ 正溢出为最大有限值、负溢出 `−Inf`；无论结果为 `±Inf` 还是最大有限值，均置 `OF` 并置 `NX`。融合乘加（`ftfma`/`fofma`，舍入方向取 `rf0[33:32]`）的判据同构：以无限指数范围按该方向舍入后的精确和，其绝对值大于该格式最大有限值（ft `0x7F7F_FFFF`、fo `0x7FEF_FFFF_FFFF_FFFF`）即构成溢出；精确和仅轻微超出最大有限值、而无限指数范围的舍入结果仍回到该值时**不构成溢出** ⇒ 结果为最大有限值、**只置 `NX`**、不置 `OF`。原「`fo2ft` 溢出恒返回 `±Inf`」「融合乘加溢出恒返回 `±Inf`」两条作废。
- **`rootn(±0, 2)` 收严为 `+0`**：`ftroot`/`foroot` 与平方根运算相同，唯一例外是零的符号——按 IEEE 754-2019 §9.2.1，`rootn(±0, 2) = +0`（该节 NOTE 明确其与 `squareRoot(−0) = −0` 不同），源为 `+0` 或 `−0` 时结果一律为 `+0`、不置任何标志；原「结果未予规定」的口径作废。
- **取整 `0x20` 档的 `NX` 与 `*2it`/`*2ut` 的写宽**：① `*2it`/`*2ut` 的 32 位结果**符号扩展/零扩展**写满 64 位 `rdHB`（`.io`/`.uo` 直接整 64 位写）；② §2.3 取整的 `0x20` 档**只有「结果 ≠ 输入且输入非 NaN」才置 `NX`**——NaN 输入经 canonical 化改变位型不算 inexact（IEEE 754-2019 §5.9）。
- **单精（ft）结果的写入宽度归位**：总则移入 §2.3（浮点寄存器），浮点册册首保留一份同等效力说明；判据不变——以 ft 寄存器为目的的指令只写目的寄存器低 32 位、高 32 位保持原值（不符号扩展、不零填），例外为宽度透明的整 64 位搬移（跨组复制 `rd2rf`/`rf2rd`、rf 组块复制 `rf2rf`、浮点条件赋值的 rf 形式）。

**指令与编码** —— 本组删除两条同格式纯复制并新增 `rf2rf`（编码不兼容），订正 `ext.uo`/`ext.so` 的起始位与 semihosting 的服务号通道。

- **删除同格式纯复制、新增 rf 组块复制（编码不兼容）**：原两条同格式纯复制指令（单精窄写搬移与双精整宽搬移）连同其编码删除——`OPC-RF` 子表的 000 行与 001 行各腾出一格（`xxx-010`）转为保留编码（执行 ⇒ UNDI）。rf 组内连续寄存器复制改由 `rf2rf` 承担（`OPC-octa` `111-100`、`orri`、`immu6` 1–63），按整 64 位逐位复制；限制沿用块复制族（`immu6` = 0、任一起始 + `immu6` > 64、源/目的范围任何重叠 ⇒ ILLI），并新增**目的范围含 `rf0` ⇒ ILLI**（源 `rf0` 合法、读出完整 64 位）。浮点册的格式转换低 6 位分类由三类改为两类（15 条舍入六档 + 3 条精确 SBZ），复制族整体迁出该册。
- **`ext.uo`/`ext.so` 的扩展起始位取低 6 位**：`orrr` 形式的起始位 `hd = rdHD[5:0]`——`rdHD` 的更高位一律忽略、**不触发异常**、不置任何标志；`orri` 形式的 `immu6` 天然为 6 位。原「`hd` 大于 `N` ⇒ ILLI」作废。
- **semihosting 的服务号通道**：`immu18[17:8] == 0x3FF`（`0x3FF00–0x3FFFF`）只作 semihosting 的**固定标记**，`immu18[7:0]` **不**携带服务号；服务号由 `rd16` 给出、参数块指针在 `rb16`、返回值在 `rd8`。

**访存与原子** —— 本组明确 `ldm`/`stm` 部分生效例外的边界（地址寄存器不被传送改写），并订正 `lr` 窄读的高位口径。

- **多元素内存指令的精确性例外**：`ldm.*`/`stm.*`（含 rf 形式，SimRISC-01）**不要求**无副作用——处理多个元素的过程中触发同步异常时，此前已处理的元素允许已经生效，目的寄存器/内存可能已被部分更新；异常原因码仍须与触发元素一致、IP 仍指向该指令。寄存器类多元素指令（`rd2rd`/`rb2rb`/`rb2rd`/`rd2rb`/`ra2rd`/`rd2ra`、`rd2rf`/`rf2rd`/`rf2rf`、`ftcls`/`focls`）**不适用**该例外、仍为精确异常（非法条件在处理任何元素之前判定）；整段预检是**允许的更强行为**、软件不得依赖；单元素 `ld`/`st` 仍须精确。
- **`ldm` 的地址寄存器不得落入传送范围**：RD 形式的索引寄存器 `rdHC`、RB 形式的基址寄存器 `rbHB` 落在 `[起始, 起始+immu6)` 内 ⇒ `ILLI`（静态）；`stm` **允许**该重叠（只读传送范围、不写寄存器，行为确定）；RA/RF 形式的地址寄存器与传送范围分属不同寄存器组，结构性不可能重叠。原「允许重叠、地址按原始 `rdHC` 计算」口径作废——多元素内存指令的部分生效例外改以「地址寄存器不被传送过程改写」为前提。
- **`lr` 的窄宽度写入不定高位**：`lr.t`/`lr.w`/`lr.b` 只写目的 `rd` 的低 32/16/8 位、**高位保持原值不变**（既不零扩展也不符号扩展）；`lr.o` 写满 64 位。此口径**不同于** `ld.ub`/`ld.uw`/`ld.ut` 的零扩展，属有意为之的窄读语义。

**伪指令与形式化语义** —— 本组把伪指令正文与表集中于本册 §5、表收缩为 7 行，订正 `set.ft rf, 0` 的展开，并把形式化语义块改为节末集中。

- **伪指令正文迁入本册 §5、16 位立即数操作册按寄存器组拆分**：`set.rd`/`set.rb`/`set.ft`/`set.fo` 的逐条语义与展开示例由 `SimRISC-03` 迁入本册 §5（`SimRISC-03` 只留指针）；`SimRISC-03` 的立即数常数赋值按 `rd`/`rb`/`rf` 拆为 §1/§2/§3（分组不改内容）；§5.3 新增 `set.ft` 两种源形式的**写宽对照表**——`rf, imm32` 只写低 32 位、`rf, rf` 整 64 位（本版删除同格式纯复制、改由 `rf2rf` 承担后的**可观察变化**）。
- **§5 伪指令改为简述 + 实现表**：本册 §5 只留定性说明与「伪指令 × 源形式」8 行表（第三列「可能的实现（硬件指令）」与 `Toolchain-01 §6.1` 的展开列逐字一致）；逐条语义与展开示例迁至 `Toolchain-01 §6.2`，本册不留副本。
- **伪指令表 8 行 → 7 行：两行寄存器源形式合并为 `set.rf rf, rs`**：`set.ft`/`set.fo` 的 `rs` 形与 `set.rf` 的展开本来就相同（`rd2rf`/`rf2rf`，整 64 位复制），助记符只编码**有歧义的那一维** ⇒ 寄存器源统一按目的 bank 记作 `set.rf`，`set.ft`/`set.fo` 只留立即数形式（其 `rs` 形**非法**、**不作别名保留**）；`set.ft` 的窄写立即数与 `set.fo` 的整 64 位立即数行为逐条不变。§5 引导句、§5 表与 `Toolchain-01 §6.1` 表同步；本版 `set.ft` 写宽对照表随正文迁至 `Toolchain-01 §6.2.3`，其 `rf, rf` 写法一并改为 `set.rf rf, rs`。
- **`set.ft rf, 0` 的展开订正**（与 `Toolchain-01 §6.1` 及窄写语义对齐）：原写「展开为 `rd2rf {rf1}, {rd0}`」，但 `rd2rf` 是整 64 位搬移，会把目的高 32 一并清零，与「`set.ft` 只写低 32、高 32 保持」（本册 §2.3）矛盾；改为 2 条 `set.w`（`wp1`/`wp0` 置 0，高 32 不动）。`set.fo rf, 0` 仍为 `rd2rf {rf1}, {rd0}`（64 位清零，语义正确）。
- **形式化语义块改为节末集中 + 三级标题**：每册每个 `## N.` 节末尾集中该节全部指令的形式化语义块，配一个三级标题 `### N.M 形式化语义（IDL）`（M 接该节已有子节号）与一句导语；块内不再重复 `# id:` 行，改用块上方一行粗体 id 标注；散文正文与块内容不变，仅位置与标注形态调整。

**规范性引用** —— 本组声明浮点规范的优先级与有意偏离的标注要求。

- **浮点规范性引用**：浮点数据格式、运算结果与异常语义以 **IEEE 754-2019** 为准；本册与之冲突时以 IEEE 754-2019 为准（显式标注为有意偏离的条目除外）；有意偏离须在对应小节标注并给出理由。
````

**新发现/坑**：

- 任务书 H1 仍写 `m15-spec-002`（文件名与台账均为 `m15-spec-008`；立任务提交说明「改号避开已用的 m15-spec-002」但未改 H1）——不在本次改动范围，登记待订正。
- 全仓唯一残留 `0.5.7-rc` 在根 `README.md` 版本表：该表「已发布」列由契约投影驱动（`check-spec-drift` 要求其等于契约版本头），本任务按范围不动契约 ⇒ 登记为声明例外。
- `check-spec-archive` 预期红（缺 `SimRISC-0.5.7` 归档目录）：快照 = 末次声明 `0.5.7` 的提交，提交前无法生成；该门控只在 `check-milestone`，不入 L1。
- 本 worktree 缺 `.cache/refs/DADAO.wiki`，`check-spec-archive-verify` 报 `RuntimeError`（环境缺失，与本次改动无关）。
- **旁证门控（均与本改动无关，保留现场并登记）**：`check-isa-coverage` rc=2（`ERROR: 找不到 llvm-mc`，新 worktree 无安装根）；`check-writer-guards` rc=2（23/27，`W1a–c` 因 `binary-executed=False` 同因）；`check-temp-dirs` rc=2（`/tmp/opencode/m14-linux-024` 陈旧 11.3 h，属其它任务）；`check-milestones-fresh` rc=2（`m15-infra-009` worktree 缺任务书，属其它任务）；`check-knowledge-refs` rc=2（`milestones-m16.md:32` 指向不存在的 `contract-cache.md`，本任务未改该文件）。处置：不改本任务范围外文件，登记待主会话/对应任务处理；未重试（根因明确、非瞬态）。
- 原文顶部段内「本段之上 `0.5.7-rc` 条目」是段名自指，发布后成为陈旧引用；按「零残留」改为 `0.5.7`（仅版本串，无语义改动）。

**遗留问题**：

- 根 `README.md`（标题 + 版本表）与 `.tao/contracts/contract-isa.md`、`contract-fp.md` 版本头仍为 `0.5.6`/`0.5.7-rc`：须由契约投影任务与发布同笔更新（二者须同步，否则 `check-spec-drift` 红）。
- `check-spec-archive` 缺 `SimRISC-0.5.7` 目录：须在合入 `master` 后生成归档快照（M15 归档前完成）。
- 按任务约束未提交 git、未建 tag。

**返工（Needs Revision 第 1 轮，2026-11-20）**：

- **finding**：证据脚本判改动面/正文时用工作树（`git status`、裸 `git diff`）与 `HEAD:` ⇒ 本分支 WIP 提交后工作树干净 ⇒ C8a/C8b/C8c 假 FAIL，且 C6 与 `HEAD:` 同内容 ⇒ 恒真。
- **处置**：基线改为「本任务分支与 `master` 的分叉点」（当前即 `HEAD~1`；可用 `SPEC008_BASE` 覆盖），断言一律 `git diff <base>..HEAD` / `git show <base>:<path>`，**不看工作树**；注释写明「基线 = 上一个提交，提交后仍可跑」。
- **复验**：提交后运行期证据目录 `run.sh` ⇒ **rc=0、checks=28 fail=0**（C6/C8a/C8b/C8c 全 PASS）；`--inject` ⇒ rc=0，4 路仍各自命中 FAIL（I1/I2 changelog 红；I3 正文 +1 字符 ⇒ C6 红；I4 缺标志串 ⇒ C5c 红），4 路 md5 还原与注入前一致。
- **抽样门控**：`check-spec-changelog` rc=0、`check-manifests-guard` rc=0、`check-knowledge-refs` rc=2（`.tao/knowledge/milestones-m16.md:32` 指向不存在的 `contract-cache.md`；基线提交同处一致、本任务未改该文件，属 `m16-spec-001` 遗留）。
- **交付物未动**：13 册、`spec/.manifests.toml`、0.5.7 变更记录一字未改（本轮只改证据脚本与本任务书）。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-20）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 段名自指 `0.5.7-rc` 残留于条目正文 | ✅已修 | 该处改为 `0.5.7`（仅版本串） | C3a spec/ = 0 命中 |
| F2 合并条目可能丢事实/改语义 | ✅已核 | 仅合并同主题（2+13、6+7），事实逐条保留；原第 2 条「quiet/signaling 差别只剩 `NV`」与第 14 条重复，由「浮点比较族的异常标志」承载；未改写判据/数值 | C5c 21 标志串缺失=无；code token 113→112（缺 `0.5.7-rc`）；C6 正文零改动 |
| F3 重排后附录结构（标题/逆序/无表格/无任务号） | ✅已核 | 五组用粗体段落 + 导语，不新增标题层级 | `check-spec-changelog`/`check-spec-numbering`/`check-spec-purity` rc=0 |
| F4 13 册改册未同笔更新锁 | ✅已修 | 13 册 sha256 重算 | C7 不符=无；`check-manifests-guard` rc=0 |
| F5 根 README / 契约版本头未随发布同步 | ⏸延后 | 任务范围明示「不动契约」，README 已发布列与契约同源 | C1 `check-spec-drift` rc=0；见「遗留问题」 |
| F6 缺 `SimRISC-0.5.7` 归档 | ⏸延后 | 快照须在发布提交落地后派生 | `check-spec-archive` 唯一 FAIL = A1 0.5.7 目录缺失 |
| F7 任务书 H1 编号与文件/台账不一致 | ⏸延后 | 不在改动范围（仅状态/完成区/审阅记录） | 见「新发现/坑」 |
| F8 重排后 code token 保真（`±` 丢反引号、新增 `ext.*` 简称） | ✅已修 | 恢复 `±` 为 code span；导语改回 `ext.uo`/`ext.so` 原名 | token 对账 113→112，缺失仅 `0.5.7-rc`、新增 0 |

### 第 1 轮 reviewer 验收（2026-11-20）

**重跑记录（本人真实输出/退出码，均在仓库根执行）**

1. 门控逐条 rc=0：`check-spec-changelog`/`numbering`/`purity`/`refs`/`codeblocks`、`check-manifests-guard`、`check-idl-sync`、`check-spec-cite-targets`、`check-spec-drift`、`check-asm-list`、`check-legality-drift`；changelog 报告 `files=22 segments=58 rc_segments=9 bullets=285 simrisc_header_versions=['0.5.7']`，本人独立解析 SimRISC 附录 `-rc` 段 = **0**（9 段属 DADAO-11/12/13/21/22/23、IDL、Kaiwu、Toolchain）。
2. 册头现场统计 `count=13 unique=['0.5.7']`；13 册 sha256 逐册现算与 `spec/.manifests.toml` 全符。
3. **正文零改动（本人自写比对脚本，基线 = `HEAD~1`）**：13 册剥册头版本行（`SimRISC-00` 另剥变更记录段）后逐字节相同 `差异=无` rc=0；`git show --name-only HEAD` **恰 15 文件**，`01–12` 各 1 行、清单 13 行；无契约改动；H1 已为 `m15-spec-008`。
4. 变更记录：顶部 `### 0.5.7（2026-11-20）`；5 组各有导语；`版本号不变`/`用户 2026-11-1x` 尾巴 **0 次**；唯一 code token `113→112`、`新-旧=∅`、`旧-新=['0.5.7-rc']`；抽 6 条（含 2 组合并：NaN 2+13、溢出 6+7）逐字比对**语义未变、未新增事实**；§ 密度与改前持平（单句 §≥3 仍为原 3 处，无新增堆砌）。
5. `0.5.7-rc` 残留：`spec/`=0、`.tao/contracts/`=0、`docs/`=0；全仓例外逐条 = `.tao/archive/**` 40、`.tao/tasks/**` 28、`README.md` 1（`| SimRISC | 0.5.6 | 0.5.7-rc |`，声明遗留）。
6. **独立注入 2 路**（运行期临时树 + `cp`/md5 还原，非本任务树）：① `SimRISC-07` 册头改回 `0.5.7-rc` ⇒ `check-spec-changelog` rc **0→2**（`互锁组 simrisc-00..12 组内册头版本不一致: ['0.5.7','0.5.7-rc']`），还原 md5 OK→rc 0；② `SimRISC-05` 正文 +1 字符 ⇒ 本人正文比对 rc **0→1**（`差异=['SimRISC-05…']`）且证据脚本 C6 `PASS→FAIL`，还原 md5 OK→rc 0。证据脚本 `--inject` 4 路 `命中预期 FAIL = True`、md5 15/15 OK。

**阻断（门控/退出码）**：仓库根执行运行期证据目录内的 `run.sh`（正常模式）**rc=1、`checks=28 fail=3`**——`C8a 少=[15 文件]`、`C8b 异常=12 册`、`C8c 期望 13/13 实际 0/0`；`--inject` 模式同样 rc=1。根因：`checks.py::check_scope()` 用**裸 `git status`/`git diff`（工作树）**判改动面，本分支已由 architect WIP 提交、工作树干净 ⇒ 集合为空 ⇒ **假 FAIL**（AGENTS 明令「提交后仍须回绿、禁裸 `git diff`」）；同源缺陷：`body_diff()` 基线取 `git show HEAD:`，提交后与工作树同内容 ⇒ **C6 恒真**，其 PASS 已不能证明「正文零改动」（我方已改用 `HEAD~1` 基线独立复证通过）。**改法（只动 `checks.py`，不碰被测产物）**：`changed()`→`git diff --name-only HEAD~1 HEAD`、`numstat()`→`git diff --numstat HEAD~1 HEAD -- <path>`、`body_diff()`→`git show HEAD~1:spec/<name>`；预期 `run.sh` rc=0、`checks=28 fail=0`、`--inject` rc=0 且 4 路仍各自命中 FAIL。

**非阻断（记录，交 architect/用户裁）**：① 根 `README.md` 仍 `0.5.6/0.5.7-rc` —— **不属本发布必须闭环**：任务书「不在范围」明写不动契约、契约版本号升级须用户认可（本任务无授权原话）、`check-spec-drift` rc=0 证明 README 与契约当前自洽（单改 README 必红），且 master 已立 **m15-spec-009 SimRISC 0.5.7 发布投影（README + 契约版本头 + 规范快照）** 待本任务合入后派单；**要求**：m15-spec-009 必须紧随合入执行，否则对外「在研 0.5.7-rc」与已发布 0.5.7 长期不符且无门控可拦。② `check-spec-archive` rc=2 = `A1 目录缺失：SimRISC-0.5.7` + 本 worktree 缺 `DADAO.wiki` 只读参考（环境，`make fetch-refs` 可重建），**不阻断本任务**，属 M15 归档前置（合入后 `gen_spec_archive.py --apply`，与 0.5.6 同套路），挂 `check-milestone` 不入 L1。③ `check-knowledge-refs` rc=2 唯一悬空 = `milestones-m16.md:32 → contract-cache.md`（本任务未改该文件、master 同缺）。④ 完成区/自审 F7 称「H1 仍写 m15-spec-002、待订正」**与实际不符**——本笔已改 `# m15-spec-008`，文档级笔误不返工。⑤ 本分支落后 master 若干提交（含对本任务书「按主题重组 + 映射表 + 元话术清理」的补充要求），我方已按 master 最新版逐条核验**均满足**（5 组、5 导语、`版本号不变` 0 次、段首总述保留裁定日期、21→19 映射表齐全）；master 新增提交与 `spec/` 无交集。

**判决：Needs Revision** —— 仅因证据脚本提交后不可复现 rc=0 且 C6 基线恒真（门控/退出码类阻断）；被测交付物 7 项核心判据经我方独立重跑**全部通过**，返工面限 `checks.py` 一处。

### 第 2 轮 reviewer 验收（2026-11-20）

**重跑（本人真实输出/退出码）**

1. 运行期证据目录 `run.sh` 正常模式：**rc=0、`checks=28 fail=0`、`RESULT: PASS`**，打印 `baseline=a8644ec0（立 m15-spec-008…）..HEAD=5c7ff48c`；`--inject`：**rc=0**，I1/I2 changelog 红、**I3 正文 +1 字符 ⇒ C6 真红**（`差异=['SimRISC-05…']`）、I4 C5c 红，4 路 md5 还原一致、末轮复跑 28/0。
2. **我方独立验 C6 不再恒真**（运行期临时树，`cp`+md5）：基线 rc=0 → 给 `SimRISC-05` 正文尾 +1 字符（8352→8353）→ `run.sh` **rc=1**（`checks=28 fail=3`：C6 `差异=['SimRISC-05…']`、C7 sha256 不符、C1 manifests-guard 红）+ 我方自写脚本 **rc=1**；`cp` 还原 md5 OK → 两者 **rc=0、差异=无**、临时树 status 干净。（注入遇 2 次共享临时盘瞬时 ENOSPC、第 3 次成功；**交付物工作树全程 md5 `f0d15ae2…` 未变、status 干净**，两次事故只损临时树副本。）
3. **禁用判据 grep**：`"status"`/`porcelain`/`show HEAD:` 命中=**无**；git 调用仅 `merge-base master HEAD`、`show <base>:`、`diff --name-only|--numstat <base>..HEAD` 与打印用 `log/rev-parse`。
4. **基线选择**：分叉点（`a8644ec0`）**优于 `HEAD~1`** —— 本笔返工提交后 `HEAD~1` 已是发布提交（C6 将恒真、C8a 少 14 假红），分叉点不变；合入 squash 后 `merge-base` 仍为 `a8644ec0`（它是 master 祖先）⇒ `base..HEAD` 恰为本任务 15 文件，**合入后仍成立**。
5. **交付物未动**：`git diff 893dfb4c..HEAD -- spec/` **空**；返工提交仅任务书（证据脚本按约定不入库）；14 个交付物文件 md5 与第 1 轮**逐个相同**；`check-spec-changelog`/`check-manifests-guard` rc=0；status 干净。（注：`git diff a8644ec0..HEAD -- spec/` = 14 文件是**发布本身**，非返工改动。）
6. **合并态**：分支未碰 `.tao/knowledge/`；master 树已有 `contract-cache.md`、其 `milestones-m16.md` 已无该串 ⇒ **合入后该悬空自行消失**；本工作树 `check-knowledge-refs` rc=2 仍为同一处（`milestones-m16.md:32`），非本任务引入。

**非阻断 finding**：① 任务书返工说明「当前即 `HEAD~1`」已过时（实为分叉点 = `HEAD~2`），文档级；② `master` 不可见时脚本静默回退 `HEAD~1`（该态 C8 会红、C6 PASS 失义），建议回退 `origin/master` 或直接报错；③ C8a 依赖 `core.quotepath=false`（本仓已配、新 clone 未配 ⇒ C8a 假红，实测复现），建议 `_git()` 加 `-c core.quotepath=false`。三者均**大声失败、不产假绿**，不阻断。

**判决：Accepted** —— 上轮打回项（C8 工作树判据、C6 恒真）已修复并经我方独立注入复证；交付物 14 文件与上轮逐字节相同，核心判据仍全绿。
