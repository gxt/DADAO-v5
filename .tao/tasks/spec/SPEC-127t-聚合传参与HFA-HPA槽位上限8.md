# SPEC-127t: 聚合传参/HFA/HPA 约定收口 + HFA/HPA 槽位上限 8

**模块**：spec
**项目里程碑**：M6
**依赖**：`SPEC-124t`（调用约定契约收口 `contract-abi §6`，`已验证`）、`SPEC-126t`（返回 `rd8`，`已验证`）；与所有改 `spec/`/锁任务**串行**（同改 `spec/DADAO-21` + `manifests/spec-readonly.lock.toml`）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 用户裁定（原话）

> **「hfa/hpa也调整为：最多消耗 8个寄存器槽位（64字节）」**（2026-10-09）。

- 授权范围 = **`spec/DADAO-21 §传参 §聚合类型参数` 的 HFA/HPA 槽位上限 `4 → 8`**（含「计数检查」「示例表」「不是 HFA/HPA」示例）。
- **不立 ADR**（延续用户既定：本族为规范正文口径收口，非跨模块合约决策）。

## 变更边界（授权内 / 待裁定 / 不含）

1. **授权内（本任务落）**：`spec/DADAO-21 §传参 §聚合类型参数`——**HFA/HPA** 的槽位上限由 **4 个寄存器槽位（32 字节）→ 8 个寄存器槽位（64 字节）**；HFA（RF bank）/ HPA（RB bank）各叶子字段仍占 1 槽位、自 `16` 起递增。
2. **待用户裁定（**不擅改**）**：**通用聚合（非 HFA/HPA）** 是否同步由 4 槽位（32 B）改 8 槽位（64 B）——见下「待用户裁定」节。
3. **不含实现**：`components/**`/`tools/**`/`tests/**` 归 `LLVM-062t`（整数聚合）/ `LLVM-066t`（HFA/RF）；本任务 `git diff` 与实现侧交集为空。

## 通用聚合 4 vs 8：**已裁定 = B**（2026-10-09）

> **用户原话（逐字留痕，2026-10-09）**：
> - 「**hfa/hpa也调整为：最多消耗 8个寄存器槽位（64字节）**」
> - 追问「通用聚合（非 HFA/HPA）是否同步 4 → 8」后，用户答：「**B，补充spec**」

**裁定 = 选项 B（取代原默认 A）**：**全部聚合（通用 / HFA / HPA）统一为「最多消耗 8 个寄存器槽位（64 字节）」**；**连带阈值**：`≤ 64 字节` ⇒ 拆 `1–8` 个 8 字节块入 RD bank，**`> 64 字节` ⇒ 间接指针**（原 `>32B` ⇒ 间接指针）；**补充 `spec/`**（用户已预先授权改只读册 + 同一变更内同步 `sha256` 锁）；**不立 ADR**。

> 下述 A/B 选项表为**裁定前**记录，**选项 A 已被 B 取代**（保留供溯源）。

| 选项 | 口径 | 影响 |
|---|---|---|
| A（原默认，**已被取代**） | 仅 **HFA/HPA → 8**；**通用聚合仍 4 槽位（32 B）** | — |
| **B（已裁定）** | 通用聚合**也**改 **8 槽位（64 B）**（`≤64B` 拆 8 块、`>64B` 走指针） | `>32B 且 ≤64B` 的聚合由「指针间接」变为「8 个 RD 块」，**`LLVM-062t` 整数聚合传参按 8 块实现** |

## 接口规范

- **输入**：
  - `spec/DADAO-21-ABI-应用程序二进制接口.md §传参 §聚合类型参数`（现「最多消耗 4 个寄存器槽位（32 字节）」「计数检查：叶子字段总数 ≤ 4」+ HFA/HPA 示例表与「不是 HFA/HPA」表）。
  - **用户授权原话**（见上「用户裁定」；`DADAO-21` 为**上游只读册**，改册须用户事先授权 + **同一变更**内同步 `sha256` 锁，`Process-06`）。
  - `.tao/knowledge/contract-abi.md`（现 §5 表把 HFA/HPA/聚合传参标 `Excluded from M3`（→ M4）；§6.1 已收口聚合返回/多返回值 M6 口径）。
  - `contracts/abi.yaml`（`deferred_to_m4` 索引含 `hfa`/`hpa`/`aggregate_arguments`；机器可读投影）。
  - `manifests/spec-readonly.lock.toml`（`DADAO-21` 段 `sha256`）。
- **输出**：
  1. `spec/DADAO-21 §传参 §聚合类型参数`：**HFA/HPA 槽位上限** `4 → 8`（64 B）——「计数检查」`≤4 → ≤8`；示例表与「不是 HFA/HPA」表相应更新（补 8 槽位正例、负例阈值改 `>8`）；使「最多消耗 4 个寄存器槽位（32 字节）」的表述在 **HFA/HPA** 与 **通用聚合** 之间**不自相矛盾**（**最小改动**：把 4 槽位限定为「非 HFA/HPA 聚合」，HFA/HPA 明示 8）。
  2. `.tao/knowledge/contract-abi.md`：把 **HFA / HPA / 聚合传参** 由 `Excluded from M3`（→ M4）**提升为 M6 口径**——§5 表状态列 + §6 新增/扩展聚合传参口径（HFA/HPA ≤8 槽位 + 通用聚合取选项 A）+ 头部「`Excluded from M3`」行同步；实现归属标 `LLVM-062t`（整数聚合）/ `LLVM-066t`（HFA/RF）。
  3. **派生投影**：`contracts/abi.yaml`（`deferred_to_m4` 索引中 `hfa`/`hpa`/`aggregate_arguments` 的 M6 口径注记；若存在 ABI 投影生成器则重跑，以实测为准）。
  4. `manifests/spec-readonly.lock.toml`：`DADAO-21` 段 `sha256` **同步**（改毕 `sha256sum` 实测）。
- **约束**：
  - **只动授权范围**：`spec/` 仅允许 `DADAO-21`；其余只读册**一字不改**（`git diff --name-only | grep '^spec/'` 仅 `DADAO-21`）。
  - **不改通用聚合**（选项 A）：不得把「非 HFA/HPA」的 `4 槽位/32 B` 改为 8；除「使表述自洽」所必需的最小限定外，不扩义。任何越出 HFA/HPA 的改动 ⇒ **停下报告、待用户裁定**。
  - 只读册改动**必须同一变更**内同步 `sha256` 锁（`Process-06`）。
  - 与 `SPEC-123t`/`SPEC-124t`/`SPEC-126t` **串行**（同改 `spec/`）。
  - 计数口径**派生自单一真源、不硬编码**（`ISS-148` 教训）。
  - 与 `SPEC-124t §6.1`（聚合返回 K=8）**一致**：HFA/HPA 传参上限 8 与返回上限 8 口径统一。

## 硬约束

- **临时目录** `/tmp/opencode/SPEC-127t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **一键证据脚本** `.work/evidence/SPEC-127t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁** `tee`。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/spec/SPEC-127t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **HFA/HPA 上限 8**：`DADAO-21 §传参 §聚合类型参数` 中 HFA/HPA 的计数检查 == `≤ 8`、示例含 8 槽位正例、负例阈值 == `> 8`（给 `grep`/摘录真实输出）；HFA（RF）/HPA（RB）仍各占 1 槽位、自 `16` 递增。
2. **通用聚合未改**：非 HFA/HPA 聚合的「`≤32B` 拆 RD 块 / `>32B` 指针间接」**逐条未变**（给 `git diff` 该段 `-`/`+` 对账，证明未改通用语义）。
3. **表意自洽**：不存在「HFA/HPA 8 槽位」与「聚合最多 4 槽位」并存的矛盾表述（给相关句子摘录）。
4. **contract-abi 同步**：`§5` 中 HFA/HPA/聚合传参状态 == M6 口径；`§6` 含聚合传参口径（HFA/HPA ≤8 + 通用聚合选项 A）；实现归属标注 `LLVM-062t`/`LLVM-066t`。
5. **派生投影同步**：`contracts/abi.yaml` 相应注记与 `contract-abi.md` 一致。
6. **锁同步**：`DADAO-21` 段 `sha256` == 实测；`make check-spec-readonly` EXIT=0；**未改册** `sha256` **逐条未变**（`git diff` 中既有 `sha256` 行 `-`/`+` 计数仅 1/1）。
7. **授权范围**：`git diff --name-only | grep '^spec/'` 仅 `spec/DADAO-21-ABI-应用程序二进制接口.md`。
8. **门控**：`make check` EXIT=0（含 `check-spec-refs`/`check-spec-readonly`/`check-contracts`）。
9. **一键证据脚本**：`.work/evidence/SPEC-127t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（如把 `≤ 8` 改回 `≤ 4` ⇒ 断言 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿），给真实输出与退出码。
10. **无残留**：`git status --porcelain -uall` 仅本任务应有改动（`spec/DADAO-21-ABI-应用程序二进制接口.md` + `manifests/spec-readonly.lock.toml` + `.tao/knowledge/contract-abi.md` + `contracts/abi.yaml` + 本任务书）；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**测试结果**：`make check` EXIT=0（含 `check-spec-readonly`/`check-spec-drift`/`check-patch-tree`）；`make check-spec-refs` EXIT=0；`make check-patch-tree` EXIT=0；证据脚本 `.work/evidence/SPEC-127t/run.sh` RUN_EXIT=0。
**修改文件**：
- `spec/DADAO-21-ABI-应用程序二进制接口.md`（§传参 §聚合类型参数：统一 8 槽位/64B；计数检查 ≤8；阈值 ≤64B/>64B 间接；HFA/HPA 各补 8 槽位正例 + 负例 >8）
- `manifests/spec-readonly.lock.toml`（DADAO-21 sha256 同步，1/1 行）
- `.tao/knowledge/contract-abi.md`（头部范围/Excluded 行、§3、§4.10、§5 状态列、§6 新增 §6.4、附录 A）
- `contracts/abi.yaml`（头部注 + `deferred_to_m4` M6 注记）
- 本任务书；`.work/evidence/SPEC-127t/run.sh`（`.work/` 不在 git）
**验收结果**（真实输出，见 `.work/log/spec/SPEC-127t-*.log`）：
- `check-spec-readonly: 21 read-only spec volume(s) OK`（EXIT=0）
- `check-spec-refs`：`结果: PASS (0 violations)`
- `make check` 末行：`repository checks: PASS`
- 证据脚本：`RUN_EXIT=0 (all checks passed)`；Phase B 注入（8/64→4/32）：`INJ1`/`INJ2`/`INJ3(check-spec-readonly 非零)` 如期 FAIL；`C RESTORE md5 与注入前相等`（`cp`+md5），Phase C 回绿。
**用户裁定（原话留痕，2026-10-09）**：「hfa/hpa也调整为：最多消耗 8个寄存器槽位（64字节）」；追问通用聚合后答「B，补充spec」⇒ B = 全聚合统一 8 槽位/64B。**不立 ADR。**
**新发现/坑**：任务书验收 #2「通用聚合未改（≤32B/>32B）」与裁定 B **冲突**，已按 B 覆盖为「≤64B/>64B」；原「待用户裁定」节已更正为「已裁定=B」。
**遗留问题**：无（整数聚合/HFA 实现归 `LLVM-062t`/`LLVM-066t`，不在本任务；`components/**`/`tools/**`/`tests/**` 未碰）。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：`spec/DADAO-21 §传参 §聚合类型参数` 全文、`manifests/spec-readonly.lock.toml`、`contract-abi.md §3/§4.10/§5/§6/附录 A`、`contracts/abi.yaml`；对照用户裁定 B。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 任务书验收 #2「通用聚合未改」与裁定 B 冲突 | ✅已修（按 B） | 通用聚合阈值 `≤32B/>32B` → `≤64B/>64B`；任务书「待裁定」节更正为「已裁定=B」 | 脚本 C6a/C6b（≤64B/>64B）PASS；`make check` EXIT=0 |
| 锁 `sha256` 与实测一致性 + 仅 DADAO-21 变 | ✅已修 | 改册后实测 sha256 写回锁 | 脚本 C8 `锁 sha256==实测` PASS；`git diff -U0` 锁 `sha256` 行 `-`/`+` 各 1 |
| §可变参数「32 字节 struct 占四个连续 slot」是否需同步 | ❌不修 | 未动 | 任务显式要求「变参 >8B 拆分不动」；该句为栈内存 slot（32B=4 slot 恒真），与寄存器槽位上限无冲突 |
| contract-abi §6.1「返回 K=8」与传参 8 槽位口径 | ✅已修（登记一致） | §6.4 明示「与返回口径一致（§6.1 K=8）」；标注实现归属 `LLVM-062t`/`LLVM-066t` | 目视 §6.4；`check-spec-refs` PASS |
| 注入还原是否污染工作树 | ✅已修（验证） | 用 `cp`+md5（trap 兜底），禁 `git checkout/restore` | 脚本后 `md5sum` = 注入前 `a34b50bb…`；`grep -c '8 个寄存器槽位（64 字节）'=1`、`'4 个…'=0` |

#### 第 1 轮 reviewer 验收

**证据脚本审核**：`run.sh` 28/28 断言全部 PASS，EXIT=0。FAIL 路径存在（C1–C8 逐项判 0/1，INJ1/2/3 检测注入后非零），无 `tee`，`rc=$?` 捕获退出码，`cp`+md5 还原 + trap 兜底。**合格**。

**重跑证据**（真实输出 `/tmp/opencode/SPEC-127t-review/run.log`）：Phase A 全 PASS → Phase B 注入有效(md5变) → INJ1/2/3 如期 FAIL → Phase C md5 还原相等 → 回绿全 PASS。`RUN_EXIT=0`。

**独立注入**：`cp` 备份(md5=`a34b50bb…`) → python3 改 `8→4`/`64→32` 四处 → md5=`33d20427…`(注入有效) → 脚本 `INJ_EXIT=1`(10项FAIL) → `cp` 还原 → md5=`a34b50bb…`(相等) → 脚本 `EXIT=0` 回绿。

**① DADAO-21 内容**：L171「最多消耗 8 个寄存器槽位（64 字节）」✓；L177「叶子字段总数 ≤ 8」✓；HFA 8×double/RF16-23 正例(L189) ✓；HPA 8×int*/RB16-23 正例(L210) ✓；负例「叶子字段 > 8」(L199/L218) ✓；通用聚合 ≤64B/>64B(L221-222) ✓。展开/flatten/union/对齐规则未被误改。L260「32字节struct占四个slot」为**栈 varargs 内存 slot**（非寄存器槽位），不受影响。

**② 全仓残留扫描**：`grep -rnE '4 ?个寄存器槽位|32 ?字节|>32 ?B|≤32' spec/DADAO-21*.md .tao/knowledge/contract-abi.md contracts/abi.yaml` → 仅命中 L260（栈 varargs，非聚合传参主题）。**无残留**。

**③ 锁 sha256**：实测=`1db71655…` = 锁文件 L105 ✓；`git diff` 仅 1 行 sha256 `-`/`+`（DADAO-21）✓。

**④ contract-abi.md**：§5 表 HFA/HPA/聚合传参已标「M6 已定口径，见 §6.4」✓；§6.4 统一 8 槽位/64B + §6.1 K=8 一致 ✓；实现归属 `LLVM-062t`/`LLVM-066t` ✓。`contracts/abi.yaml` YAML 可解析 ✓。

**⑤ 任务书**：验收 #2「通用聚合未改」与裁定 B 冲突**已披露**（完成区L100），仅追加更正、未改写完成区/审阅记录 ✓。

**⑥ 越界**：`git status` 仅 5 文件：`spec/DADAO-21-*` + `manifests/spec-readonly.lock.toml` + `.tao/knowledge/contract-abi.md` + `contracts/abi.yaml` + 本任务书。无 `components/`/`tools/`/`tests/`，无 `_tmp/_orig/_rej/_preinject` ✓。

**门控**：`make check` EXIT=0（62 tests PASS）✓；`make check-patch-tree` EXIT=0（92 patches OK）✓。

**判决：Accepted**

#### 提交留痕（architect，2026-10-09）

- **档位**：reviewer 判决 **Accepted** ⇒ **正常提交**（无 `WIP:` 前缀）。
- **提交号**：`ac19fce`（`SPEC-127t: 聚合传参收口…+ DADAO-21 与锁同步 + contract-abi §6.4`）；**只 commit、未 push**。
- **文件集对账**（显式 staging，逐个路径，禁 `git add -A`）；`git diff --cached --name-only` = `spec/DADAO-21-ABI-应用程序二进制接口.md` / `manifests/spec-readonly.lock.toml` / `.tao/knowledge/contract-abi.md` / `contracts/abi.yaml` / 本任务书 —— 与「修改文件」**逐条相等**（**无漏提 / 无多提 / 无越界**）。
- **交叉复核**：DADAO-21 统一「8 槽位（64 字节）」+ `>64B ⇒ 间接指针`；锁 `sha256` 实测 = 锁文件（`1db71655…`），`git diff` 仅 1 行 `sha256` 变；contract-abi §6.4 / `contracts/abi.yaml` 注记一致；全仓无聚合槽位残留（仅 `DADAO-21` L260 栈 varargs「32 字节 struct 占四个 slot」，非聚合传参主题）。**限长**：完成区 17 行 ≤30、审阅每轮 ≤40。
