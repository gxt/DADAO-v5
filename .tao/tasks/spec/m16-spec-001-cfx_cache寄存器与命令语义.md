# m16-spec-001: `cfx_cache`（cfx5）寄存器与命令语义（A 方案：重定义 `cg8 rc9`）

**模块**：spec
**项目里程碑**：M16
**依赖**：无
**可并行分片**：否（改 `spec/` 与 `.tao/contracts/`）
**预估**：3–4 h
**档位**：大改（spec + 契约 + 测试机约定）
**状态**：已验证

## 用户已定口径（2026-11-20，不得自决）

- **重定义 `cg8 rc9`**（旧的 bit0/1/2 数值编码作废；`cfx5` 在 `contract-see` 里是「已分配未实现」，无实现依赖）；
- **选择位在 `[15:14]`**：bit15 = I-cache（1 选中）、bit14 = D-cache（1 选中）⇒ `11` = 全选；
- 操作与范围沿用 TLB 控制字的风格：`[1:0]` 操作、`[3:2]` 范围；
- **不加 ASID**（cache 以 PA 为键，非 VIVT）；
- **`invalidate` 丢弃脏数据不写警告**（DMA 场景这是正确操作）。

## 目标

1. **`spec/DADAO-12 §4.6 cfx_cache`**：
   - `cg8 rc0 cache_exist`（RO）：**bit0 = I、bit1 = D**，其余保留 0；
   - `cg8 rc8 cache_enable`（RW）：**bit0 = I、bit1 = D**，复位值 = exist；`exist=0` 的位置写 1 无效果（读回 0）；
   - `cg8 rc9 cache_ctrl`（WO）：`[1:0]` 操作 = `00=none/01=clean/10=invalidate/11=flush`；`[3:2]` 范围 = `00=all/01=PA 单行/10=PA 区间/11=reserved`；`[15:14]` 选择（bit15=I、bit14=D）；其余保留 0；
   - `cg8 rc10 cache_addr_start`（RW）：`PA[41:0]`；`cg8 rc11 cache_addr_size`（RW）：字节数；
2. **语义写死**：
   - `op=none` 或 `[15:14]=00` ⇒ no-op，且不检查范围编码与 `size`；
   - `scope=all` 忽略 start/size；`PA 单行` 只匹配包含 start 的行；`PA 区间` 匹配与 `[start, start+size)` 相交的行；
   - **I 侧**：`clean` = no-op；`invalidate` = 丢弃；`flush` = 等价 `invalidate`；
   - **D 侧**：`clean` = 写回并清 dirty；`invalidate` = 丢弃（脏数据丢失，**不写警告**）；`flush` = 写回后丢弃；
   - 两侧全选时判序 **I 表先、D 表后**；命令**同步完成**；
   - `cache_enable` 对应位 = 0 ⇒ 该侧命令 no-op；对不可缓存/MMIO 的 PA 无效果、不报异常；
   - **per-hart**；不改 `cfx_cache` 的异常表。
3. **新建 `.tao/contracts/contract-cache.md`**：按 `contract-tlb` 的体例（编号断言 + 来源标注 + 判序/失败语义），覆盖上述全部语义；
4. **`spec/Kaiwu-测试机运行环境.md`**：`cfx5` 从「已分配未实现」改为 **Vast 实现**（Tiny 不实现），补 `§3.x` 测试机约定（同步完成、per-hart、I/D 选择位与「I 先 D 后」）；
5. 版本号**不升**（`DADAO-12` 与 `Kaiwu` 均保持现值），只在各自变更记录加条目（用户认可后再升）。

## 验收（逐条贴真实 rc）

1. **交叉一致**：`DADAO-12 §4.6` 的寄存器表、`contract-cache.md` 的断言、`Kaiwu` 的实现范围三处**逐项对应**（寄存器名、位定义、语义），给一张对应表；
2. **旧编码已废**：全仓 `grep` 旧句「bit0=invalid icache」= 0；`contract-see` 里 `cfx5` 的「未实现」表述已改；
3. **门控**：`check-spec-changelog`、`check-spec-numbering`、`check-spec-purity`、`check-spec-refs`、`check-spec-codeblocks`、`check-manifests-guard`（`spec/` 与 `.tao/` 的 sha256 同步）、`check-contracts-dir`、`check-contract-relocs`、`check-knowledge-refs` 全 rc=0；
4. **可达 FAIL ≥2 路**（临时树/`cp`+md5）：① 删契约里一条断言的来源标注 ⇒ 对应门控红；② 把某一寄存器位定义改错（如 `[15:14]` 的 I/D 对调）⇒ 三处对应表核验红；
5. 补丁/清单纪律：`spec/.manifests.toml`、`.tao/.manifests.toml`（若需）同笔更新。

## 不在本任务范围

不实现 RTL / QEMU / gem5 的 `cfx5`（后续实现任务）；不动 `tests/arch` 的 cache 探针。

## 约束

独立 `git worktree`；不提交 git；术语「寄存器组」；完成区不写具体 `.work/**` 路径；**版本号不得自行升级**。

## 完成区

**测试结果**：通过 **50/50**（运行期证据目录内 `run.sh` rc=0：三处逐项对应 **37 项** + 旧编码作废 3 项 + 门控 9 项 + 脚本自身 rc 1 项）；注入自检 `run.sh --inject` rc=0（**三路**反例——契约来源标注、`[15:14]` I/D、`enable` 行（rc8）I/D——均真实判红后回绿）。
**修改文件**：`spec/DADAO-12-SEE-主管系统运行环境.md`（§4.6 重写 + `0.7.3-rc` 变更条目）、`spec/Kaiwu-测试机运行环境.md`（§3 实现范围条目 + 新增 §3.2 + `0.4.7-rc` 变更条目）、`spec/.manifests.toml`（两册 sha256 同笔）、新增 `.tao/contracts/contract-cache.md`（CACHE-01…30）、`.tao/contracts/contract-see.md`（§3 的 cfx5 口径 + §7 变更记录）、`.tao/contracts/README.md`（索引行）；版本号均未升（DADAO-12 仍 `0.7.3-rc`、Kaiwu 仍 `0.4.7-rc`）。本轮返工只动 4 个文件（`contract-cache.md`、`DADAO-12`、`spec/.manifests.toml`、本任务书）；提交范围 = 上列 6 个实现文件 + 本任务书 = **7 个**。
**验收结果**（真实 rc）：
① 三处逐项对应 = **37 项全 OK**：regname（`cg8 rc0/8/9/10/11`）、exist 行（rc0）与 enable 行（rc8）**各自**解析的 bit0 = I、bit1 = D、`[15:14]`（bit15 = I、bit14 = D）、`addr_start` 承载 `PA[55:0]`（`[63:56]` 读 0、无 `PA[41:0]` 残留）、`[1:0]` 四操作、`[3:2]` 四范围，加 12 条语义（no-op 不查范围/`size`、I 侧 `clean` = no-op、D 侧 `invalidate` 丢脏不写警告、`enable=0`、不可缓存/MMIO 无效果、`PA 单行`/`PA 区间`、两侧全选 I 先 D 后、同步完成、per-hart）在 spec ↔ 契约一致（Kaiwu 只引上游）。
② 旧编码作废：`invalid icache` 在 spec/.tao 契约/components/tools/tests/docs = **0 命中**；`contract-see` §3 无「已分配未实现」且指向 `contract-cache.md`。
③ 门控 rc=0：`check-spec-changelog`/`numbering`/`purity`/`refs`/`codeblocks`、`check-manifests-guard`、`check-contracts-dir`、`check-contract-relocs`、`check-knowledge-refs`（另 `check-spec-drift`、`check-contracts-pending`、`check-tasks`、`check-dirs`、`check-no-residue` 亦 rc=0；`check-milestones-fresh` 整跑仅 M15 台账两条兄弟任务违规，`--file` 单跑 m16 台账 PASS）。
④ 可达 FAIL 3 路（`cp` 备份 + md5 对账）：① 删 CACHE-06 来源标注 ⇒ `check-spec-refs` rc=2（注入前 rc=0）；② §4.6 `[15:14]` I/D 对调 ⇒ 核验 rc=1（`expected=('I','D') actual=('D','I')`）；③ §4.6 enable 行（rc8）bit0/bit1 对调 ⇒ 核验 rc=1（`[FAIL] spec enable 行（rc8）bit0/bit1 = I/D: expected=('I','D') actual=('D','I')`）；三路还原后 md5 与注入前相等且回绿。
**新发现/坑**：① `cache_addr_start` 按用户 2026-11-20 裁定扩为**完整 56 位 PA**（`PA[55:0]`、`[63:56]` 读 0），范围匹配按 56 位逐位比较、不截断；② 现存实现与探针仍按「Vast 的 `cfx5` 未实现 ⇒ `CFXREG`」（QEMU/gem5/chipyard 的 cfx 集不含 5；`tests/arch` 的 `integ042t cfx5_cache_cfxreg`、`integ049t unimpl_cfx`、`integ050t regress_unimpl_cfx`）⇒ 新口径须由后续实现/测试任务回归。
③ Kaiwu `§6.3.4`「cache / LLC 不引入、不假设一致性」与 `§6.3.5` 首句在有 cache 后需复核（未改）；④ `check-knowledge-refs` 开工前即红（台账已引 `contract-cache.md` 而文件不存在），新增契约后转绿；⑤ 契约版本按 `contract-tlb` 体例取 README 版本表的 SEE / SBI **已发布**版 `0.7.1`（上游正文 `0.7.3-rc` 在研）以过 `check-spec-drift`；⑥「不查范围编码/`size`」只适用 `[15:14]=00` 与 `op=none`，`enable=0` 不抑制编码校验（任务书只列两条不检查项）；⑦ 契约「变更记录」段若用「保留/必须」等词会触发 `check-spec-refs` Check 2（该段无来源标注）⇒ 该段措辞改为「读 0」（本轮实测 rc=2 → 改后 rc=0）。
**遗留问题**：上段 ②③ 两项待后续/待裁定，均不在本任务范围；无其他未完成项。

## 审阅记录

### 第 1 轮 engineer 自审

自主逐行审查（本深度无嵌套子代理）：spec §4.6 判序分支（选择 → 操作 → 范围/操作数）与各 no-op 情形的
互相排斥性、两侧语义表与 `enable=0` 的关系、Kaiwu §3.2 与 §3 实现范围条目的互指、契约 30 条断言的来源标注
与判序/失败语义、证据脚本的反例路径与还原纪律。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 契约 CACHE-03 只写短名（`cache_exist` 等）⇒ 三处 regname 覆盖核验会假红/假绿 | ✅已修 | 改全 regname（`cfx_cache_*`）+ `cg8 rc0/8/9/10/11` 显式列出 | `run.sh` A 段「CACHE-03 覆盖 5 个寄存器名/cg8 rc」两项 OK |
| F2 核验脚本 `code_pairs` 用单一 dict 收 `00…11` 编码 ⇒ 操作维被范围维覆盖（恒空） | ✅已修 | 拆成 (操作维, 范围维) 两个 dict | `run.sh` A 段 spec/契约「操作编码」「范围编码」四项 OK（32 项 PASS） |
| F3 反例① 的「非空注入」判据用 `git diff --name-only`，对**未跟踪**的新契约恒空 ⇒ 假 FAIL | ✅已修 | 改判「注入前后 md5 已变」，并打印 `git status -uall` 行数说明 | `--inject` 段「非空注入防护（字节内容已变）」OK、两路 rc 期望均达成 |
| F4 `contract-see` 的「cfx5 未实现」检查过粗（§7 变更记录合法叙述旧值） | ✅已修 | 收窄到 §3 段（`## §3`–`## §4`）+ 另查指向 `contract-cache.md` | 「§3 无「已分配未实现」」OK、`run.sh` rc=0 |
| F5 契约变更记录仍写旧英文拼法（会被更宽的旧句扫描命中） | ✅已修 | 改中文叙述；旧句扫描面放宽为 `invalid icache` | 旧句 0 命中（spec/.tao 契约/components/tools/tests/docs） |
| F6 spec 把 `enable=0` 写成「该侧命令 no-op（不报异常）」⇒ 与「只有两处不查范围编码」冲突 | ✅已修 | 改「该侧不被维护；编码与 `addr_size` 校验不受使能影响」；契约 CACHE-08/23 同步 | 门控 `check-spec-refs` rc=0；语义项「enable=0」三处 OK |
| F7 「不适用地址」未交代内存窗口（无 `cg7` 描述）的可缓存性 | ✅已修 | spec 与 CACHE-22 均补「内存窗口的可缓存性由实现决定」 | `check-spec-refs` rc=0；CACHE-22 语义项 OK |
| F8 二次编辑 Kaiwu 后 `spec/.manifests.toml` sha256 失配 ⇒ `check-manifests-guard` rc=2 | ✅已修 | 现场 `sha256sum` 重算并同笔更新两册条目 | `check-manifests-guard` rc=0（`run.sh` C 段） |

**约束核验**：worktree `git status -uall` = 6 改 + 1 新增（实现文件 5 改 + 1 新增，另有本任务书自身）；`git diff --stat` = 6 files / +86 −8；未改 RTL/QEMU/gem5、未动 `tests/arch`、未升任何版本号、未提交 git；术语用「寄存器组」；本记录与本任务书均无运行期具体路径。
**判决**：**待验收**（全部 finding 已修，无未修项）。

### 第 1 轮 reviewer 验收

**重跑记录（我自己的命令与真实输出/退出码）**
- 运行期证据目录内 `run.sh`：`结果: PASS（32 项逐项一致）`、9 门控全 `[OK]`，`EXIT=0`；`run.sh --inject`：两路反例判红（`check-spec-refs rc=2`、三处核验 `rc=1` 且首条 `[FAIL] spec [15:14] 选择位 I/D … actual=('D','I')`）→ 还原 md5 相等 → 回绿，`EXIT=0`。
- 我独立重跑 11 门控全 `rc=0`：`check-spec-changelog/numbering/purity/refs/codeblocks`、`check-manifests-guard`、`check-contracts-dir`、`check-contract-relocs`、`check-knowledge-refs`、`check-spec-drift`、`check-contracts-pending`。
- 我独立注入 3 路（`cp` 备份 + md5 对账，未用 git 还原）：① 删 CACHE-06 来源标注 ⇒ `check-spec-refs rc=2`，还原 md5 `da701e49…` 相等且 `rc=0`；② §4.6 选择位对调 ⇒ 核验 `rc=1`；③ Kaiwu §3.2 选择位对调 ⇒ 核验 `rc=1`；三路还原后 md5 与审查前快照逐一相等、`git status -uall` 空。
- 旧编码：全仓 `grep "invalid icache"`（排 `.git`）仅命中运行期证据脚本与本任务书（引用该检索式），现行 spec/契约 0 命中；`contract-see §3` 无「已分配未实现」且指向 `contract-cache.md`（我逐段核）。
- 范围/版本：`git show --name-only HEAD` = **7 文件**（完成区声明 6 + 任务书自身，非「恰 6」，系计数口径差异、无越界文件）；未动 QEMU/gem5/chipyard/tests；`DADAO-12` 仍 `0.7.3-rc`、`Kaiwu` 仍 `0.4.7-rc`（与 HEAD~1 同行逐字相同）。
- 判据 1 十项我人工逐条核：`[15:14]`、`[1:0]` 四操作、`[3:2]` 四范围、两处无条件 no-op、I `clean`=no-op、D `invalidate` 丢脏不警告、`enable=0`、不可缓存/MMIO、I 先 D 后、同步完成、per-hart —— spec §4.6 与 contract-cache 同值；Kaiwu §3.2 载选择位/判序/同步/per-hart/`exist=0b11`，其余以上游引用式覆盖、无矛盾。
- 判据 3 语义自洽：`op=none`/选择 `00` ⇒ no-op 且不查范围与 `size`（spec 与 CACHE-12/13 一致）；`[3:2]=11` 明写为**非法编码 ⇒ `CFXREG`**（仅在需校验时），非 no-op、非未定义，明确；`enable=0` 两处均「该侧不被维护、编码与 `addr_size` 校验不受使能影响」= 不抑制编码校验，Kaiwu 引用上游、不冲突。

**发现**
- ❌ 阻断：证据脚本的「`cache_enable` 位定义」**无可达 FAIL 路径**——我注入「§4.6 `rc8` 行 bit0/bit1 对调」与「契约 CACHE-07 位定义对调」两路，三处核验均 `rc=0`（`check-spec-refs/purity/drift` 亦 `rc=0`）；脚本该项标签写 `exist/enable`，实际只解析首个 `bit0/bit1`（exist 行），CACHE-07 未被解析 ⇒ 完成区把「exist/enable 位」计入已核 32 项属超报。
- ⚠️ 文档级（不阻断）：12 条语义行标「三处一致」而 Kaiwu 列为 `-`（实为 spec↔契约两处 + Kaiwu 引用上游）；`DADAO-12` 变更条目仍写「该侧命令 no-op」，正文已按 F6 改「该侧不被维护」。
- 设计问题（记录、不阻断，终裁归用户）：`cache_addr_start` 仅 `PA[41:0]`（4 TiB）而本册 PA 56 位。**判为可接受的实现范围限制**：Vast RAM 仅 `[0, 2 GiB)`、`cg7`/核内偏移同为 42 位，高位 PA 在本测试机不可达；但架构上页表可映射 >4 TiB PA，`[63:42]` 写忽略 ⇒ 高位丢弃、该行永不可被「单行/区间」选中。建议由用户裁定：扩 `PA[55:0]`，或在 §4.6/CACHE-18 补一句范围限制。

**判决**：**Needs Revision** —— 失败项 = 上列阻断（`cache_enable` 位定义断言缺可达 FAIL 路径，属证据脚本不合格）。修法：三处核验增解析 §4.6 `| 8 | 8 |` 行与契约 CACHE-07 的 `bit0/bit1`，与规范值 `bit0=I/bit1=D` 比对，并在反例段加一路「rc8 行对调 ⇒ 核验非 0」；顺带把语义行标签改「spec↔契约（Kaiwu 引用上游）」。修后重跑 `run.sh` 与 `run.sh --inject`。其余约束均守住（范围、版本号未升、术语「寄存器组」、未提交 git、本记录无运行期路径）。

### 第 2 轮 engineer 返工（回应第 1 轮 reviewer Needs Revision）

| reviewer finding | 处置 | 改了什么 | 复验证据 |
|------------------|------|---------|---------|
| R1（阻断）证据脚本的 `cache_enable` 位定义无可达 FAIL 路径：只解析 §4.6 首个 `bit0/bit1`（exist 行），`rc8` 行与 CACHE-07 未解析 | ✅已修 | 核验脚本改为**按 rc 逐行解析** §4.6 表（`rc0`→exist、`rc8`→enable 各自比对），新增 `CACHE-07` 断言项；反例段加第三路「`rc8` 行 bit0/bit1 对调 ⇒ 核验非 0」 | `run.sh`：37 项 PASS、rc=0；`run.sh --inject` 第三路真实判红：`[FAIL] spec enable 行（rc8）bit0/bit1 = I/D: expected=('I','D') actual=('D','I')`，还原 md5 `6ae9edfc…` 相等并回绿 |
| R2（文档级）12 条语义行标「三处一致」而 Kaiwu 列为 `-` | ✅已修 | 标签改为「spec ↔ 契约一致（Kaiwu 引用上游，不重编码）」，段标题同步 | `run.sh` A 段段标题与 12 行标签均为新措辞、全 OK |
| R3（设计，终裁归用户）`cache_addr_start` 仅 `PA[41:0]` | ✅已修（用户 2026-11-20 裁定扩宽） | §4.6 `rc10` 改「完整 `PA[55:0]`；`[63:56]` 读 0、写忽略」，三档范围补「按 56 位 PA 逐位比较」；CACHE-03/16/17/18 同步；`DADAO-12` 变更条目同步；核验加「`PA[55:0]` 承载」「无 `PA[41:0]` 残留」两项 | `run.sh` 两项宽度断言 OK；`run.sh` rc=0 |
| 上一轮 F6 遗留：`DADAO-12` 变更条目仍写「该侧命令 no-op」（正文已为「该侧不被维护」） | ✅已修 | 变更条目改为「该侧不被维护（编码与 `addr_size` 校验不受使能影响）」 | `grep` 该册无「该侧命令 no-op」；`check-spec-changelog` rc=0 |
| 本轮自发现：契约「变更记录」用「保留」触发 `check-spec-refs` Check 2（该段无来源标注） | ✅已修 | 该段「`[63:56]` 保留」→「`[63:56]` 读 0」 | 现场 rc=2 → 改后 `check-spec-refs` rc=0 |

**计数口径更正**：上一轮完成区的「32 项」为**误报**（`enable`/CACHE-07 未真正解析）；本轮按实际断言数重算为 **37 项**，`run.sh` 打印与完成区一致。
**约束核验**：本轮仅动 4 个文件（`contract-cache.md`、`DADAO-12`、`spec/.manifests.toml`、本任务书）；`git diff --stat` 相对 base WIP 提交 = 4 files / +48 −16；未改 RTL/QEMU/gem5、未动 `tests/arch`、未升版本号、未提交 git。
**判决**：**待验收**（R1–R3 + 两条遗留全部已修，无未修项）。

### 第 2 轮 reviewer 验收

**重跑（我自己的命令与真实输出/退出码）**
- 运行期证据目录内 `run.sh`：`结果: PASS（37 项逐项一致）`、`[OK]` 行计数 **50**、9 门控全 OK，`EXIT=0`；`run.sh --inject`：三路全红后回绿（`check-spec-refs rc=2`；`[15:14]` 路 `rc=1`；`enable` 路 `rc=1`，首条 `[FAIL] spec enable 行（rc8）bit0/bit1 = I/D … actual=('D','I')`），`EXIT=0`。
- 我独立复现阻断项的可达 FAIL（`cp` 备份 + md5）：§4.6 `| 8 | 8 | cache enable` 行 bit0/bit1 对调 ⇒ 核验 **rc=1**（打印同上 FAIL 行），还原 md5 `6ae9edfc…` 相等、回 **rc=0**；另抽 2 路宽度探针（rc10 行回退 `PA[41:0]`、契约 CACHE-18 回退）⇒ 均 **rc=1**（`cache 侧不再残留 PA[41:0] 截断 … 仍有`），还原后回绿；注入期间 `check-spec-refs/purity/drift` 仍 `rc=0` ⇒ 红来自核验脚本本身，非门控凑绿。
- 门控我独立抽样 7 项全 **rc=0**：`check-spec-refs`/`purity`/`drift`/`changelog`、`check-manifests-guard`、`check-contracts-dir`、`check-knowledge-refs`。
- `PA[55:0]` 五项抽核三处同值：spec §4.6 rc10 行「完整 `PA[55:0]`；`[63:56]` 保留、读 0、写忽略」、spec 三档范围「一律按 56 位物理地址逐位比较」、契约 CACHE-03、CACHE-16/17「按 56 位 PA 比较」、CACHE-18「`[63:56]` 保留、读 0、写忽略…不做任何截断」；`[63:56]` 口径 spec 与契约一致；§4.6 与 contract-cache 内 `41:0` **0 残留**（并有门控断言）；Kaiwu §3.2 无宽度表述（声称属实）。
- 两处修订落地：12 条语义行标签已改「spec ↔ 契约一致（Kaiwu 引用上游，不重编码）」；变更记录已改「该侧不被维护（编码与 `addr_size` 的校验不受使能影响）」，与正文同口径。
- 范围/版本：`git show --name-only HEAD` = **4 文件**（`contract-cache.md`、本任务书、`spec/.manifests.toml`、`DADAO-12`）、`+48 −16`；`DADAO-12` 仍 `0.7.3-rc`、`Kaiwu` 仍 `0.4.7-rc`；`git status --porcelain -uall` 空；完成区计数更正（32→37 项、50/50、三路）与我实测一致。

**判决**：**Accepted** —— 上轮阻断项（`cache_enable` 位定义无可达 FAIL 路径）已修且我独立复现「注入判红 → 还原回绿」；`PA[55:0]` 扩展三处一致、无 `PA[41:0]` 残留；其余抽样无回归，约束（不改代码、未提交 git、本记录无运行期路径）均守住。
