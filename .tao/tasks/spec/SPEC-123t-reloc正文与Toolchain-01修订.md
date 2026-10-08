# SPEC-123t: reloc 正文 + `Toolchain-01 §6.1` 修订（已授权）+ 锁

**模块**：spec
**项目里程碑**：M6
**依赖**：`SPEC-122t`（reloc 体系 ADR 须 `Accepted`）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - 已 `Accepted` 的 reloc 体系 ADR（`SPEC-122t` 产出，拟 `.tao/adr/adr-0021-*.md`）。
  - `.tao/knowledge/contract-elf.md §2–§4`（reloc 投影，`ISS-154`/`ISS-151`/`ISS-161`）。
  - `.tao/adr/adr-0019-dadao-relocation-types.md`（现有 reloc 集 D1–D8；`ABS48` 数据 8B 字段）。
  - `spec/Toolchain-01-汇编语言.md §6.1`（现口径「4×`set.w`」，与 `ISS-156` 实现口径不一致）。
  - `manifests/spec-readonly.lock.toml`（只读册 `sha256` 锁）、`spec/Process-06-spec目录保护规范.md`、`spec/Process-02-合约编写规范.md`。
  - **用户授权（原话，见 `INTEG-023k §B`）**：`ISS-156` 口径 = `rd2rf rfx, rd0` + **仅非零 `wp` 的 `set.w`**（`set.fo rf,0` ⇒ 1 条）；**并同步该册 `sha256` 锁**。
- **输出**：
  1. `.tao/knowledge/contract-elf.md §2–§4`：**reloc 正文**——`REL12` + 新专用类型（`ISS-151`/`ISS-161`）+ **`ABS48` 数据 8 字节字段表示**（`ISS-154`：48 位地址、大端存储、高 16 位填 0）。
  2. `spec/Toolchain-01-汇编语言.md §6.1`：**修订** `ISS-156` 口径（`rd2rf rfx, rd0` + 仅非零 `wp` 的 `set.w`；`set.fo rf,0` ⇒ 1 条）——**限 `§6.1`（用户授权范围内）**。
  3. `manifests/spec-readonly.lock.toml`：`Toolchain-01` 段 `sha256` **同步**（同一变更内）。
- **约束**：
  - **只改授权范围**（`Toolchain-01 §6.1`）；其余只读册**不得**触碰；任何扩面须**先停下、报告、待用户授权**。
  - 只读册改动**必须**在**同一变更**内同步 `sha256` 锁（`Process-06`）。
  - 与 `SPEC-122t`/`SPEC-124t` **同改 `spec/`/锁 ⇒ 串行**。
  - 正文以 `Process-02` 合约编写规范为准；不引入 ADR 決策之外的口径。
  - 计数口径**派生自单一真源**（`contracts/opcodes.yaml` 等），**不硬编码**。

## 硬约束

- **临时目录** `/tmp/opencode/SPEC-123t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **一键证据脚本** `.work/evidence/SPEC-123t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/spec/SPEC-123t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **reloc 正文落笔**：`contract-elf.md §2–§4` 含 `REL12` + 新专用类型 + `ABS48` 数据 8B 字段表示；与已 `Accepted` 的 reloc ADR **一致**（给 `grep`/摘录）。
2. **`Toolchain-01 §6.1` 修订**：口径 = `rd2rf rfx, rd0` + 仅非零 `wp` 的 `set.w`（`set.fo rf,0` ⇒ 1 条）；给 `sed`/`grep` 真实输出。
3. **锁同步**：`manifests/spec-readonly.lock.toml` 的 `Toolchain-01` `sha256` == 实测 `sha256sum`（给真实输出）。
4. **授权范围核验**：`git diff --name-only | grep -E '^spec/'` 只允许出现 `spec/Toolchain-01-汇编语言.md`；不得有其它的 `spec/` 文件。
5. **门控**：`make check` EXIT=0（`check-spec-readonly`/`check-spec-refs`/`check-contracts` 等）。
6. **一键证据脚本**：`.work/evidence/SPEC-123t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（如改 `§6.1` 后再跑 `check-spec-readonly` ⇒ FAIL ⇒ `cp`+md5 还原 ⇒ 回绿），给真实输出与退出码。
7. **无残留**：`git status --porcelain -uall` 仅本任务应有改动（`spec/Toolchain-01` + `manifests/spec-readonly.lock.toml` + `.tao/knowledge/contract-elf.md` + 本任务书）。

> **判据修正（architect，2026-10-09 收尾）**：验收标准 4 原判据与授权范围**矛盾**（reviewer 第 1 轮指出：本任务本就授权改 `spec/Toolchain-01 §6.1`，却要求「`grep '^spec/'` 应为空」）——修正为「`git diff --name-only | grep -E '^spec/'` 只允许出现 `spec/Toolchain-01-汇编语言.md`；不得有其它的 `spec/` 文件」，即核「**无越界改其它只读册**」，而非要求 `spec/` 交集为空。

## 完成区

**测试结果**：`make check` EXIT=0（lit 62/62、check-spec-readonly 21 册、check-spec-drift、validate-vectors、repository checks PASS）；`make check-patch-tree` EXIT=0（2 组件 / 92 补丁）；`.work/evidence/SPEC-123t/run.sh` RUN_EXIT=0（含 C10/C11 注入自检）。日志见 `.work/log/spec/SPEC-123t-*.log`。

**修改文件**：`.tao/knowledge/contract-elf.md`（§2–§4 reloc 正文 + 头/附表来源标注，rev. 2026-10-09）；`.tao/adr/adr-0021-ldst-symbol-reloc.md`（D1 就地修订 + `## 修订` + 用户原话）；`spec/Toolchain-01-汇编语言.md`（§6.1，**上轮已改，本轮不动**）；`manifests/spec-readonly.lock.toml`（**上轮已改，本轮不动**）；`.work/evidence/SPEC-123t/run.sh`（证据脚本 rev. 2026-10-09，`.work` 不入 git）。

**验收结果**（rev. 2026-10-09，用户改判双类型）：
- **类型与编号（§2.2）**：`R_DADAO_REL12 = 4`（`rb0` 基址、PC 相对）／`R_DADAO_ABS12 = 5`（`rb1–rb63` 基址）／`R_DADAO_NUM = 6`（由 5 改 6）。
- **公式（§3.1）**：`REL12`：`field = S + A − P`（字节、不 `>>2`；`P` = 该访存指令地址 = `rb0` 读出值）；`ABS12`：`field = S + A`（字节、不 `>>2`）。
- **必须区分（§2.2）**：ELF `RELA` 无「基址寄存器」字段 ⇒ 汇编器按基址自动选型（`rb0`⇒`REL12`，否则⇒`ABS12`）；不得只用一个类型；linker 只看类型、不解码指令。
- **`rb0` 危险（§3.1）**：`rb0` 读出当前指令地址、随取指漂移 ⇒ 多指令形态②③④以 `rb0` 为基址会漂移；**规避（`rb2rb` 拷出 ±k×4 修正 / 避开 `rb0`）由 LLVM 定**，规范不指定、不禁止。
- **四形态（§4）**：访存偏移形态①–④**由 LLVM 依实际情形选择**；reloc 层不新增更宽类型/不 relaxation；`REL12`/`ABS12` 只服务形态①。
- **越界（§3.2）**：两类型越出 `−2048..+2047` 一律 link-time error（不截断/wrap/静默 0）。
- **`ABS48` 数据 8B 字段 / `set.fo §6.1` / 锁**：与上轮一致（未变）；锁 `sha256 = 9d6164bc…` 与实测一致。
- **授权范围**：`git diff --name-only` 中 `spec/` 仅 `spec/Toolchain-01-汇编语言.md`（**上轮遗留、未提交**）；本修订**未新增/修改任何 `spec/` 文件**（Toolchain-01 md5 / 锁未变）。

**新发现/坑**：
- **用户 2026-10-09 改判原话（原样留痕）**：(1)「四个方案是让 llvm 根据实际情况选择，没让你来选」；(2)「ld/st 指令用到的基址寄存器可以是 rb0，所以，动态运行过程中，需要考虑 rb0 自己的递增」；(3)「两种情况是并存的，rb0 表示相对地址，rb1-rb63 则是绝对地址；真实使用的时候是不是需要明确区分」；(4)「两种类型：REL12 和 ABS12」。
- 任务书「`grep '^spec/'` 应为空」**与工作树不符**：上轮 `Toolchain-01 §6.1` 改动尚未提交（`git status` 仍 ` M`）⇒ 实为「本修订未新增 `spec/` 改动」，由 Toolchain-01 md5/锁未变佐证。
- 上轮三类过期口径（`contract-asm.md §6`、`validate_mc_vectors.py` set.fo 特例断言、`rela.s` 注释仅 4 类）**仍未改**（超范围）。

**遗留问题**：
1. 实现侧（LLVM/LLD `DADAO.def`/`DADAO.cpp`）仍旧 4 类 / `NUM=4`，未含 `ABS12` 与 `rb0` 自动选型；归 `LLVM-065t`（spec 先行）。
2. 上述三类过期口径。
3. 任务书「验收标准 1/6」措辞仍指单一 `REL12`（未同步双类型）——正文已按双类型落笔，措辞待主会话收尾/后续任务同步。

## 审阅记录

#### 第 1 轮 engineer 自审
（自主逐行审查 `contract-elf.md §2–§4`、`Toolchain-01 §6.1`、锁、证据脚本；判决：finding 已全部处置，可置「待验收」。）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `REL12` 公式（`S+A` vs `S+A−P`）属 ADR 未定层 | ✅已决（显请复核） | 取 `S+A`（基址相对、非 PC），§3.1/§3.2 落笔并注明备选被否 | `run.sh` C3/C4 PASS；完成区「验收结果」 |
| F2 spec（NUM=5）与实现（DADAO.def NUM=4）临时不一致 | ✅预期（非缺陷） | §2.2 明确编号；实现归 `LLVM-065t` | `make check` EXIT=0（无门控比对 reloc 编号） |
| F3 `contract-asm.md`/`validate_mc_vectors.py`/`rela.s` 过期口径 | ⏸延后 | 未改（超任务输出范围） | ——（登记「遗留问题」2） |
| F4 计数不写死（reloc 行数 / 指令条数） | ✅合规 | 正文无硬编码门控计数；`NUM` 为 enum 规范值 | `run.sh` 用 grep 模式、无计数断言 |
| F5 证据脚本 C7 因 git `quotepath` 误判 CJK 路径 | ✅已修 | 加 `git -c core.quotepath=false` | 改前 C7 FAIL → 改后 `run.sh` RUN_EXIT=0 |

#### 第 2 轮 engineer 自审（rev. 2026-10-09）

（用户改判 `REL12` 为双类型后返工；自主逐行审查 `contract-elf.md §2–§4`、`adr-0021`、证据脚本；判决：finding 已全部处置，可置「待验收」。）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| G1 上轮 `REL12` 写成「基址相对、`S+A`」（与用户改判冲突） | ✅已修 | §2.2 拆 `REL12`(4,rb0)+`ABS12`(5)、`NUM`→6；§3.1 `REL12`=`S+A−P`、`ABS12`=`S+A`；§3.2 两类型越界 | `run.sh` C1a/b/c、C3a/b PASS；`RUN_EXIT=0` |
| G2 上轮否定了 PC 相对（Q1 反问）——用户裁定由 LLVM 选四形态 | ✅已修 | §4 加「形态①–④由 LLVM 依实际情形选择」；ADR-0021 `## 修订` ⑤ | `run.sh` C3e PASS |
| G3 `rb0` 为基址会随取指漂移（Q2）未记 | ✅已修 | §3.1 加 `rb0` 危险段（规避由 LLVM，规范不指定/不禁止）；ADR-0021 修订 ④ | `run.sh` C3d/C3d2 PASS |
| G4 两公式混淆风险（Q3「是否需明确区分」） | ✅已修 | §2.2 加「两类型必须区分」段（汇编器按基址选型、linker 只看类型）；ADR-0021 D1 扩展注记 | `run.sh` C3c PASS |
| G5 ADR-0021 未就地修订 | ✅已修 | 标题/状态 rev + D1 扩展注记 + `## 修订`（含用户 4 条原话）+ 状态说明补记 | `grep`/审阅本文；门控不受 ADR 影响 |
| G6 证据脚本未覆盖新内容 | ✅已修 | 重写 `run.sh`：编号 4/5/`NUM`=6、`REL12` `−P`、`ABS12` 存在、`rb0` 危险、四形态句；注入 A（删 `ABS12` 行+改回 `S+A`⇒FAIL）+ 注入 B（Toolchain 口径⇒门控 FAIL）；结尾 `rc` | `run.sh` RUN_EXIT=0；C10*/C11* 全 PASS；前后 md5 相等 |
| G7 任务书「`spec/` diff 应为空」与工作树不符（上轮改动未提交） | ✅披露（非缺陷） | 未回退未提交改动；以「本修订未新增 `spec/` 改动」核验 | `run.sh` C6（md5=锁）/C7 PASS；完成区「新发现/坑」 |

#### 第 1 轮 reviewer 验收（rev. 2026-10-09）

**重跑**：`bash .work/evidence/SPEC-123t/run.sh` EXIT=0，31 项全 PASS（C1a/b/c、C2、C3a/b/c/d/d2/e、C4a/b、C5a/b、C6、C7、C8、C9、C10a–f、C11a–e）。

**独立注入**：`sed` 删 `contract-elf.md` 的 `ABS12` 行 → md5 变化（`f4083…→02c3e…`）→ 脚本报 3 FAIL（C1b/C10a/C10e）RUN_EXIT=1 → `sed -i` 还原 → md5=`f4083…`（相等）→ 脚本 RUN_EXIT=0。

**门控**：`make check` EXIT=0；`make check-patch-tree` EXIT=0。

**独立复核（①–⑨）**：① `REL12`=4、`ABS12`=5、`NUM`=6 ✅；② `REL12`=`S+A−P`（字节）、`ABS12`=`S+A`（字节）✅；③ 「两类型必须明确区分／汇编器按基址自动选型／linker 只看类型不解码指令」✅；④ `rb0` 危险说明 +「规避由 LLVM 定」✅；⑤ 「形态①–④由 LLVM 依实际情形选择／reloc 层不新增更宽类型不做 relaxation」✅；⑥ 两类型越界均 link-time error（不截断/wrap/静默 0）✅；⑦ `ABS48` 数据 8B（大端/高 16 位=0）、`set.fo` 口径（`rd2rf rf,rd0` + 仅非零 wp 的 `set.w`）、锁 sha256=`9d6164…` 与实测一致 ✅；⑧ ADR-0021 D1/D2/D3 未删 + 用户 4 条原话留痕 + `## 修订` ✅；⑨ `spec/` 交集仅 `Toolchain-01` ✅。

**`git status`**：5 个 ` M`（`contract-elf.md`、`adr-0021-*.md`、`Toolchain-01`、`spec-readonly.lock.toml`、任务书），无残留。

**任务书判据缺陷**：验收标准 4「`grep '^spec/'` 应为空」与授权范围矛盾——本任务授权改 `Toolchain-01 §6.1`，工作树有该文件未提交的 ` M` 是正常状态；正确判据 =「`git diff --name-only | grep '^spec/'` 只允许出现 `Toolchain-01`，不得有其它 `spec/` 文件」。建议 architect 修订任务书措辞。

**判决**：**Accepted**。证据脚本合格（FAIL 路径真实、注入非空可还原、无 `tee`）、重跑全绿、独立注入验证通过、门控双绿、9 项独立复核全部符合。
