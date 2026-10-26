# SPEC-177t: 删除 SBI 保留值 `0x3FFFF`（ISS-334 / ADR-0038 D3）

**模块**：spec
**项目里程碑**：M10
**依赖**：ADR-0038（D1/D2/D4/D5 已 Accepted；D3 本次定）
**状态**：待验收

## 背景（用户 2026-10-26 选 B）
semihosting 已迁至 `0x3FF00–0x3FFFF`；`DADAO-22:863` 的保留值 `0x3FFFF` 正落在该区间，若将来用于「SBI 协议版本协商」会被 semihosting 短路。用户在 A（移到 `0x3FEFF`）/ B（删除）/ C（收窄区间）中选 **B：删除该保留约定**。

## 改动
1. `spec/DADAO-22-SBI-主管系统二进制接口.md:863`：删除「保留 `immu18` 值 `0x3FFFF`（最大）用于将来可能的 “SBI 协议版本协商” 功能。」一句；保留前半句（新增 cfx 时新增章节/功能码表）。
   - **不要**改 SBI 里其它 `0x3FFFF`（那些是 `set.rd rd3, 0x3FFFF` 的 immu18 掩码常量）。
2. 版本：SBI `0.7.2` → **`0.7.3-rc`**；SEE 同步 **`0.7.3-rc`**（`check-spec-changelog` 的 SEE↔SBI 互锁）；两册附录新开 `### 0.7.3-rc（未发布）`，SBI 条目写「删除 `0x3FFFF` 保留值（与 semihosting 区冲突，ADR-0038 D3）」。
3. `ADR-0038`：在 D3 处补「**D3 决议（2026-10-26，用户选 B）**：删除保留值；ISS-334 由 SPEC-177t 关闭」。
4. `issues.yaml`：ISS-334 `closed`，`resolved_by: SPEC-177t`。
5. 锁：`manifests/spec-readonly.lock.toml` 头补授权（用户原话「B」）；重算 DADAO-22、DADAO-12 sha256。

## 约束
- 只改上述 2 册 + ADR-0038 + issues + 锁 + 任务书/`milestones.md`；不改 semihosting 判定、不改其它 `0x3FFFF` 掩码。
- 临时目录 `/tmp/opencode/SPEC-177t/`；不提交。

## 验收
- `make check` rc=0；`check-spec-readonly`、`check-spec-changelog`、`check-contracts-*` rc=0。
- grep：`DADAO-22` 中「SBI 协议版本协商」= 0；`0x3FFFF` 掩码常量数量不变；SBI/SEE 册头/附录段一致。
- ISS-334 closed + resolved_by 正确。

## 完成区

**测试结果**：`make check` **rc=0**（尾行 `repository checks (L1): PASS`）；`check-spec-readonly`（21 册 OK）/`check-spec-changelog`（`files=21 segments=45 rc_segments=7`，see-sbi 互锁一致）/`check-contracts-dir`/`check-contracts-pending`/`check-contract-relocs` 均 **rc=0**；证据 `bash .work/evidence/SPEC-177t/run.sh` → **checks=31 failures=0，rc=0**（含 3 组注入→预期 FAIL→`cp`+md5 还原→回绿）。

**修改文件**：`spec/DADAO-22-SBI-主管系统二进制接口.md`（§14 删句 + 册头/附录 → 0.7.3-rc）、`spec/DADAO-12-SEE-主管系统运行环境.md`（册头/附录 → 0.7.3-rc，正文不变）、`.tao/adr/adr-0038-semihosting-tag-range.md`（D3 决议 + 决策来源/遗留同步）、`.tao/knowledge/issues.yaml`（ISS-334 `closed` / `resolved_by: SPEC-177t`）、`manifests/spec-readonly.lock.toml`（头授权原话「B」+ 2 册 sha256）、`.tao/knowledge/milestones.md`（状态）、本任务书；证据 `.work/evidence/SPEC-177t/{run.sh,checks.py}`（`.work/**` 不入 git）。

**验收结果**：
- grep：`DADAO-22` 中「SBI 协议版本协商」= **0**、「保留 immu18 值 0x3FFFF」= **0**；掩码常量 `set.rd   rd3, 0x3FFFF` = **7 行**，与基线（`38f8e230`）**逐行相同**（基线现场取，不写死）。
- 版本：SBI/SEE 册头均 `0.7.3-rc`；两册附录顶段 `### 0.7.3-rc（未发布）`、次段 `### 0.7.2（2026-10-26）`；互锁一致。
- 锁：DADAO-22 `002e056a…`、DADAO-12 `3c788509…`（现场重算 = 锁内值；其余 19 册未动）。
- ADR-0038 D3 已补「**D3 决议（2026-10-26，用户选 B）**：删除保留值；`ISS-334` 由 `SPEC-177t` 关闭」。
- 注入反例（证据脚本内）：回填待删句 ⇒ c01/c02 FAIL；删 1 行掩码 ⇒ c03 FAIL（7→6）；SEE 单册回退 0.7.2 ⇒ c04 FAIL；三次 `cp` 还原后 md5 全等（`MD5-RESTORE-OK`）且回绿。

**新发现/坑**：
- 附录**不得含** `ADR-`/`ISS-`/任务号（`check-spec-changelog` 断言 6）⇒ 任务书原拟条目「（与 semihosting 区冲突，ADR-0038 D3）」**去掉 ADR 号**落笔，决策指针归 ADR-0038 + 锁头授权段。
- 版本常量（SBI `0x00070002` ×4、SEE `supv_global_version`）按 SPEC-176t 惯例**不动**（发布时同步，无门控要求与 `-rc` 册头相等）。
- `check_spec_changelog` 的 `-rc` 段判据：数值须 = 下一段 z+1 且必须在首位 —— 0.7.3-rc 压 0.7.2 正好。

**遗留问题**：根 `README.md`「在研版本」列未同步 SBI/SEE `0.7.3-rc`（非本任务允许文件集）；`ADR-0038`「关联」行仍只列 `SPEC-176t` 为落点（未改）。

## 审阅记录

### 第 1 轮 engineer 自审（2026-10-26）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 锁头初稿写「其余 8 处 `0x3FFFF`」，实际剩余掩码 7 处（基线 8 = 7 掩码 + 1 保留句） | ✅已修 | 改为「其余 7 处」 | `grep -c` 现场 7；证据 03 `expected=7 actual=7` |
| F2 任务书原拟附录条目带 `ADR-0038 D3`，会被 `check-spec-changelog` 断言 6 判红 | ✅已修 | 条目去 ADR 号，只写语义 | `check-spec-changelog` rc=0；证据 12 rc 段命中 0 |
| F3 SBI 册头 `-rc` 与正文「当前 0.7.2 = `0x00070002`」并存，是否同步升常量 | ❌不修 | 未改常量 | 依 SPEC-176t 惯例（发布时同步）；无门控要求；已在「新发现」说明 |
| F4 证据 03 若基线取错（掩码 0 行）会「0 行 == 0 行」恒真 | ✅已修 | `checks.py` 基线为空即 FAIL | 注入②：删 1 行 ⇒ `expected=7 actual=6` 如期 FAIL |
| F5 c12 初版 rc 段提取逻辑混用（heading 判断与跳出条件交叉） | ✅已修 | 重写 `rc_section()` 取段函数 | 证据 12 PASS；注入① 下仍 0 命中 |
| F6 台账/任务书状态与完成区是否对账 | ✅已修 | 顶层 `**状态**` → `待验收`；`milestones.md` 行同步 | `check-milestones-fresh` 在 `make check` 内 rc=0 |
| F7 注入断言 `expect_fail` 初版只判 `rc≠0`，脚本自身用法错（rc=2）也会被当作「如期 FAIL」 | ✅已修 | 收紧为必须 `rc==1`，rc=2 计 FAIL；补 R4 还原后锁哈希复验 | 三轮注入 I1b/I2b/I3b 均 `rc=1`；R4 MATCH；`checks=31 failures=0` |

**自审判决**：改动逐行核对（删句仅限 §14 该句、7 条掩码常量逐行同基线、两次 sha256 与锁一致、附录逆序/无任务号、互锁一致、ADR/issue 指针齐备）；未修项 F3 有明文先例且不阻断门控。**可标「待验收」**。

