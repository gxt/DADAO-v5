# SPEC-131t: 过渡 oracle 约定 + semihosting `cfxha` 口径收口（规范/合约/锁）

**模块**：spec
**项目里程碑**：M7
**依赖**：无（同改 `spec/`/锁 ⇒ 与其它 `spec` 任务串行）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - 用户裁定（2026-10-11；`INTEG-033k §裁定汇总 #7`）：**过渡 oracle 采用**——宿主机结果作参照 + **明确边界**（端序／`long double`=f64 vs 宿主 80-bit／`fenv`／UB／实现定义），**登记为「非判据真源」**（将来 `GOLDEN-*` 替换）。
  - 用户裁定（2026-10-11；`INTEG-033k §裁定汇总 #9`）：semihosting 用 `trap cfx3, 0x30000`；**须核 M6 探针 `cfx_umon` 是否为 cfx3，不一致要登记**。**cfxha 口径已裁定**（用户 2026-10-11 追加：「**写成任意 cfxha**」）——semihosting 用哪个 `cfxha` **不指定**、**与 `cfxha` 取值无关**；**保留现状 `cfx_umon`(cfx0)、`cfx3` 等效、不改实现**；口径表述已落 `contract-semihosting §1`（`INTEG-034t`，2026-10-11）。
  - 实测事实（本 `k`）：`cfx_umon` = **cfxha 0**；`cfx3` = `hmon`（`spec/DADAO-12 §1`）；v5 `tests/scripts/codegen_crt0.s` 与 `tools/qemu/min_rom_probe_049t.py` 均用 `trap cfx_umon, 0x30000`；`contract-semihosting §1` 与 QEMU 实现（`trans_ctrl.c.inc`）均**只查 `immu18[17:16]`、与 `cfxha` 无关**。
  - 现行正文：`docs/Process-05-里程碑TDD规范.md §2`（L3「独立 oracle（host 侧按 IR/spec 语义派生）」）；`spec/Machine-01 §5.1`；`.tao/knowledge/contract-semihosting.md §1`；`.tao/knowledge/contract-see.md`。
- **输出**：
  1. **过渡 oracle 约定**：在 `docs/Process-05-里程碑TDD规范.md`（§2 或其下新增小节）写入「**过渡 oracle**」——宿主机结果**仅作参照**、**非判据真源**；边界清单（**端序** big-endian vs 宿主 / **`long double`** = f64（`sizeof=8`）vs 宿主 80-bit / **`fenv`**（v5 `machine/fenv.h` 退化为 `FE_TONEAREST`）/ **UB / 实现定义**）；标注将来由 `GOLDEN-*` 里程碑替换。
  2. **semihosting `cfxha` 口径**（**已裁定，2026-10-11**）：`contract-semihosting §1` / `spec/Machine-01 §5.1` 明确「tag 判定与 `cfxha` 无关」的现行口径；`cfx3` vs `cfx_umon`(cfx0) **不一致已处置**——用户裁定「**写成任意 cfxha**」⇒ **任意 `cfxha` 等效、不改实现**、保留现状 `cfx_umon`(cfx0)；口径表述已由 `INTEG-034t` 落 `contract-semihosting §1`。**本任务不再改动该口径**（若仍需正文侧补充，另行裁定）。
  3. 相关 `spec/` 册 `sha256` 锁同步（`spec/*.md` 若纳入锁）。
- **约束**：
  - **Spec-first**：正文以 `spec/` 与 `contract-*` 为准；ADR 不承载正文（`Process-03`）。
  - **不改上游只读册**（`SimRISC-*`/`DADAO-*`）；本任务只改 v5 自定册/合约（`Machine-01`/`Process-05`/`contract-*`）。
  - **`cfxha` 口径已裁定**（用户 2026-10-11：「**写成任意 cfxha**」）：任意 `cfxha` 等效、与取值无关、**不改实现**；口径表述已由 `INTEG-034t` 落 `contract-semihosting §1`，本任务不再改动（`AGENTS.md`「最小安全设计」：不猜测、不自行改契约）。
  - **计数不写死**；只动任务范围，越界须披露。

## 验收标准

1. **过渡 oracle 正文**：`docs/Process-05 §2`（或新增小节）含「宿主机结果 = 参照、**非判据真源**」+ **四类边界**（端序/`long double`/`fenv`/UB-实现定义）+ `GOLDEN-*` 替换指针（`grep` 真实输出）。
2. **semihosting 口径**（**已裁定**）：`contract-semihosting §1` 明确「tag 判定与 `cfxha` 无关」且「任意 `cfxha` 等效」；`cfx3` vs `cfx0` 不一致**已处置** = 保留现状 `cfx_umon`(cfx0)、不改实现（用户 2026-10-11 裁定；`INTEG-034t` 落盘）。
3. **锁同步**：`make check-spec-readonly`（或等价）EXIT=0；被改册 `sha256` 锁同步。
4. **门控**：`make check` EXIT=0；`check-spec-refs` 无新增违规。
5. **反例门控**：对新增/修改断言可注入反例 ⇒ FAIL ⇒ `cp`+md5 还原 ⇒ 回绿（若有可注入点）。
6. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**测试结果**：一键证据脚本 `.work/evidence/<任务ID>/run.sh` **27/27 PASS，EXIT=0**（含 3 门控）；`--inject`（把 §2.1 的 `FE_TONEAREST` 改写为 `FE_RNE_ONLY`）⇒ **恰 1 FAIL（`p05-fenv`）/ TOTAL=27** ⇒ `cp`+md5 还原（`eea9e133bf10…` 复原）⇒ 回绿 **27/27**，`EXIT=0`；注入前后 md5 相异（非空注入）。
**修改文件**：
- `docs/Process-05-里程碑TDD规范.md`（§2 下新增 `### 2.1 过渡 oracle（宿主机参照；非判据真源）`，**+15 行**）；
- `.tao/knowledge/milestones.md`（`SPEC-131t` 行状态 `待开始`→`待验收`，**+1/−1**）；
- 本任务书（完成区/审阅记录/状态）；
- 非入库：`.work/evidence/<任务ID>/run.sh`（证据脚本）。
**验收结果**：
- ① 过渡 oracle 正文（`grep -F` 真实输出均 present）：小节 `### 2.1 过渡 oracle`；「仅作参照」「非判据真源」；四类边界「端序/大端」、「long double/f64/80-bit」、「fenv/FE_TONEAREST/machine/fenv.h」、「UB/实现定义」；「使用规约/差分/禁止」；替换指针「GOLDEN-*」。
- ② semihosting 口径**只核不改**：`sed -n '/^## §1/,/^## §2/p'` 抽 §1 区块（8 行，非空）含「任意 `cfxha` 等效」「与 `cfxha` 取值无关」「与 `cfxha` 无关」；`spec/Machine-01 §5.1`（line 109）含「与 `cfxha` 无关」；`cfxha` 口径**未改**（`contract-semihosting`/`Machine-01` 零改动）。
- ③ 门控：`make check-spec-readonly` **rc=0**、`make check-spec-refs` **rc=0**、`make check` **rc=0**（三者均 EXIT=0）。
- ④ `spec/` 未触：`git status --porcelain -uall -- spec/` 空 + `git diff --name-only master..HEAD -- spec/` 空。
**新发现/坑**：
- **注入须有鉴别力**：`grep -F "FE_TONEAREST"` 会命中 `FE_TONEAREST_X`（子串）⇒ 首版注入 `FE_TONEAREST→FE_TONEAREST_X` **假绿**；注入值须**不含**被检 token（改用 `FE_RNE_ONLY`）。属 `lessons §2.10`「注入无鉴别力」实例。
- `fenv` 边界所依「v5 `machine/fenv.h` 退化为仅 `FE_TONEAREST`」当前**无仓内文件可证**（全仓 `grep FE_TONEAREST` 仅命中裁定/文档，`components/picolibc` 无 `fenv.h` 补丁）——出处 = 用户裁定 `INTEG-033k #7`；已按「标来源」落纸，未臆造。
**遗留问题**：无。（`§输出 3` 的 `spec/` 册 `sha256` 锁同步：本任务未改 `spec/`，`check-spec-readonly` rc=0，**不适用**。）

## 审阅记录

### 第 1 轮 engineer 自审

- **逐行审查 `docs/Process-05` §2.1 新块**：位置正确（`## 2.` 与 `## 3.` 之间）；四类边界逐条齐全、与 `INTEG-033k #7` 一致；「非判据真源/仅作参照/使用规约/禁止」与 `AGENTS.md`「Independent oracle」对齐；`GOLDEN-*` 替换指针显式（含去留 = 废止）。引 `INTEG-033k #7` 标来源，未臆造。
- **规范等级用词**：沿用册内 MUST/SHOULD 体系（「必须/可以/不得/禁止」），未引入新等级；未改 §2 表格与 §1/§3 既有正文（`git diff` 仅新增 +15 行）。
- **防造假**：所有断言均 `grep -F`/`sed` 真实执行、逐项打印 rc；覆盖计数现场统计；无 `tee` 吞码。
- **判决**：无未修 finding ⇒ 可标「待验收」。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 注入 `FE_TONEAREST→FE_TONEAREST_X` 因子串命中致假绿 | ✅已修 | 证据脚本注入值改 `FE_RNE_ONLY` | `--inject`：恰 1 FAIL（`p05-fenv`）/TOTAL=27 → 还原 md5 `eea9e133…` → 回绿 27/27，EXIT=0 |
| F2 `machine/fenv.h` 无仓内文件可证 | ⏸延后（非缺陷） | 完成区「新发现」标注出处=用户裁定 `INTEG-033k #7` | 全仓 `grep -rl FE_TONEAREST` 仅命中裁定/文档；按裁定原文落纸，未臆造 |

#### architect 交叉复核 + 提交（2026-10-12）

- **如实披露**：本任务**未跑独立 reviewer**（主会话判定 = 纯文档 + 门控全绿 + 自审含反例的低风险改动）。故由 architect 代行**独立重跑**门控与交付物存在性核验，**不设 reviewer 轮次、不伪造 reviewer 记录**。
- **门控独立重跑**：`make check` rc=0；`make check-spec-readonly` rc=0；`make check-spec-refs` rc=0；`make check-no-residue` rc=0；`check_issues.py` rc=0（21 open / 7 closed / 0 blocking）。
- **交付物 grep**：`docs/Process-05` 含「非判据真源」（L23/L25）、四类边界（端序 L29、`long double` L30、`fenv` L31、UB-实现定义 L32）、`GOLDEN-*` 指针（L25/L36）。
- **`spec/` 未触**：`git status --porcelain -uall -- spec/` **空**。
- **反例独立重跑**（architect 亲手执行）：`run.sh --inject` ⇒ **恰 1 FAIL（`p05-fenv`）/ TOTAL=27**；md5 `eea9e133…`→`d00ac0ca…`（实注入）⇒ `cp` 还原 ⇒ md5 复原 `eea9e133…` ⇒ **27/27 绿**；常态 `run.sh` **27/27 rc=0**；注入前后工作树与 `git status` 一致。
- **上提交遗留修正**：`milestones.md` 候选行已是 `lessons §2.11`（原 `§5.1` 悬空引用），由主会话于本任务分支内修正，随本提交**一并**落地（提交信息中说明）。
- **文件集对账**：staged 3 项 = 完成区「修改文件」（`docs/Process-05` / `milestones.md` / 本任务书）+ 主会话 `milestones.md` 修正；**0 漏提 / 0 多提 / 0 越界**；排除 2 份并行任务书（`INFRA-065t`/`SPEC-134t`，未跟踪、不提交）。

