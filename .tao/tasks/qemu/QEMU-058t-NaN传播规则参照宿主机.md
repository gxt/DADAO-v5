# QEMU-058t: NaN 2-NaN 传播规则（参照宿主机实测）

**模块**：qemu
**项目里程碑**：M7
**依赖**：无（同改 `components/qemu/patches` ⇒ 与其它 qemu 侧任务串行）
**状态**：待开始

> 立项来源：用户 2026-10-12 裁定「先在 M7 内做解锁件再归档」+ 本轮讨论（**从易到难第 5 项**）；依据 `ISS-195`（QEMU softfloat `float_2nan_prop_rule == none` ⇒ assert ⇒ blocked **5**）。

## 用户裁定（2026-10-12，**原话/选项标签**）

- 议题：DADAO 的 2-NaN 传播规则取哪条（`s_ab` / `ab` / `x87` / …）。
- 选项：A「`s_ab`（IEEE 754-2019 推荐）+ 实证」／B「`ab`」／C「先查 test 期望再定」。
- **用户选择 = 「参照当前宿主机的实现」**（= **实测宿主机行为，选与之匹配的 softfloat 规则**）。
- 取得渠道：**经主会话问答**取得（2026-10-12）。

## 目的 / 根因（事实）

- `components/qemu/patches/**` 的 `fp_status_init`（或等效）**从未设** `float_2nan_prop_rule` ⇒ 走默认 `float_2nan_prop_none` ⇒ QEMU 在 `parts64_pick_nan` **assert/abort**（architect 已 gdb 定位：`helper.c:550 ftdiv → float32_gen2 → parts64_div → parts64_pick_nan`）⇒ `ISS-195` **5 条** test blocked（如 `test-remquo-quo` rc=−6）。
- 上游规范（`SimRISC-07`/`contract-fp`）只规定「**NaN 传播 payload**」+「**sNaN 作算术输入 ⇒ 置 NV 且结果 qNaN**」+「符合 IEEE 754」⇒ **payload 选谁属实现定义**。
- IEEE 754-2019 §6.2.3 推荐：任一为 sNaN 则传播它，否则传播 quiet，同优先级按 a→b。

## 接口规范

- **输出**：
  1. **实测宿主机行为（必做、先做）**：在**宿主机**（本机 x86_64）用 `sNaN/qNaN × sNaN/qNaN` 组合构造用例（C 或 Python/`numpy` 皆可，须**记录** payload 位、quiet/signaling、符号），得出「**宿主机在 2-NaN 情形取谁的 payload**」的**实测结论**（留档）。
  2. **设置匹配的 softfloat 规则**（`components/qemu/patches/**`）：按实测结果选 `float_2nan_prop_{s_ab,s_ba,ab,ba,x87}` 之一（**给依据：实测结论 ↔ 规则名**）；若实测**无法**与任一规则一一对应 ⇒ **停下报告**。
  3. **重建 QEMU**（增量；申报耗时；`setsid`/`XXX_EXIT`/`JOBS=8`/`124` 判 FAIL 规则同上）+ **跑那 5 条 test**（真实退出码）。
  4. **全量 test**：`make check-picolibc-tests-full` ⇒ **四分类 before/after**（before：`pass 152 / fail 0 / excluded 18 / blocked 65`）+ 解锁清单。
  5. `.tao/knowledge/milestones.md` 流水更新 `QEMU-058t` 行（状态 `待验收`，`完成时间` `—`）。
- **约束**：
  - **不得**改 DADAO 的上游语义主张（只补"实现定义"的那一格）；
  - ⚠️ **若"宿主机实测"与那 5 条 test 的期望冲突**（test 期望 ≠ 宿主行为）⇒ **停下报告**（需用户裁定"以谁为准"，`lessons §3.17`）；
  - **不改** `spec/`、`contracts/`、`tests/vectors/`；**计数不写死**。

## 验收标准

1. **宿主机实测留档**：用例 + 真实输出（payload/quiet 位），并给出**结论**（宿主机等价于哪条规则）。
2. **规则已设**：`git diff` 显示 `float_2nan_prop_rule` 被设为**与实测匹配**的值（给依据）。
3. **那 5 条 test**：before（blocked/abort）→ after（**真跑 rc=0**，真实输出）；**`fail` 仍须 0**。
4. **全量 test**：`pass` **上升**、`blocked` **下降**（before/after 现场统计 + 解锁清单）。
5. **门控**：`make check`、`check-patch-tree`、`check-no-residue`、`check-picolibc-tests`（快档）各 EXIT=0。
6. **反例可失败**：注入（回退该规则 ⇒ 复现 assert/abort）⇒ 断言/门控 **FAIL** ⇒ `cp`+md5 还原 ⇒ 回绿。
7. **完成区**（≤30 行）与真实输出逐条对齐。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/QEMU-058t/`；**命令一律在 workdir（= 仓库根）内、相对路径；禁 `cd` 出界**；禁仓库内临时文件。
2. **不提交 git**；补丁导出纪律（写 `/tmp`、行数下限、**非空 blob**、`check-patch-tree` 断言⑥、`.work/source/qemu` 状态与 `series` 一致）。
3. 完成区与真实输出逐条对齐；**禁 `cmd | tee` 吞码**。
4. 只动任务范围（`components/qemu/patches/**`、任务书、`milestones.md` 行）；越界须披露。
5. 失败保留现场并继续推进；**只在需用户语义裁定**时**停止并报告**（禁自拟自答）。
6. 任务书/记录中**不得写字面 `.work/<具体路径>`**（用 `<>` 占位）。
7. 一键证据脚本落 `.work/evidence/<任务ID>/`（能失败、可达 FAIL、结构断言、计数不写死、捕获退出码）。
8. 反例注入还原**禁** `git checkout`/`restore`/`stash`；一律 `cp` + md5 对账。
9. **计数不写死**。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
