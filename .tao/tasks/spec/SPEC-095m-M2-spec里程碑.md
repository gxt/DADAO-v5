# SPEC-095m: M2 spec 里程碑

**模块**：spec
**项目里程碑**：M2
**状态**：里程碑
**目标**：规范与接口冻结（Normative Freeze）完成——`spec/`（SimRISC 0.5.4 + v5 自定 `Toolchain-01`/`Process-0x`）→ 投影（`contracts/*` 机器数据、`.tao/knowledge/contract-*.md` 叙述合约）→ checker（`make check`）三层**机械一致**；投影表「缺口」清零或显式 deferred；`check-spec-refs` 违规清零；上游↔v5 偏离台账（6 项）成型；FP **实现侧**收口（执行层 60/60 + `dst_rd0@FP`）。为 M3 codegen 提供稳定契约。
**关联任务**：`SPEC-012k`、`SPEC-013t`、`SPEC-014t`、`SPEC-016t`、`SPEC-018t`、`SPEC-019t`、`SPEC-021t`、`SPEC-022t`、`SPEC-023t`、`SPEC-024t`、`SPEC-026t`、`SPEC-027t`、`SPEC-028t`、`SPEC-029t`、`SPEC-030t`、`SPEC-031t`、`SPEC-033t`、`SPEC-034k`、`SPEC-035t`、`SPEC-036t`、`SPEC-037t`、`SPEC-038t`、`SPEC-039t`、`SPEC-040t`、`SPEC-041t`、`SPEC-042t`、`SPEC-043t`、`SPEC-044t`、`SPEC-045t`、`SPEC-046t`、`SPEC-047t`、`SPEC-048t`、`SPEC-049t`、`SPEC-050t`、`SPEC-051t`、`SPEC-052t`、`SPEC-053t`、`SPEC-054t`、`SPEC-055t`、`SPEC-056t`、`SPEC-057t`、`SPEC-058t`、`SPEC-059t`、`SPEC-060t`、`SPEC-061t`、`SPEC-062t`、`SPEC-063t`、`SPEC-064t`、`SPEC-065t`、`SPEC-066t`、`SPEC-067t`、`SPEC-068t`、`SPEC-069t`、`SPEC-070t`、`SPEC-071t`、`SPEC-073t`、`SPEC-074t`、`SPEC-075t`、`SPEC-076t`、`SPEC-077t`、`SPEC-078t`、`SPEC-079t`、`SPEC-080t`、`SPEC-081t`、`SPEC-082t`、`SPEC-083t`、`SPEC-084t`、`SPEC-085t`、`SPEC-086t`、`SPEC-087t`、`SPEC-088t`、`SPEC-089t`、`SPEC-090k`、`SPEC-091t`、`SPEC-092t`、`SPEC-093t`、`SPEC-094t`（77 个；已删号 `015t`/`017t`/`032t`/`072t` 略；过渡期旧里程碑 `SPEC-020m`/`SPEC-025m` 不计入）

## 核验
- 关联任务是否均已 `已验证`
- 各任务产出是否存在：`.tao/knowledge/contract-*.md`（含 `contract-asm.md`、`contract-fp.md`）、`contracts/{opcodes,legality_rules,fp_semantics}.yaml`、`spec/README.md`（投影表）、`.tao/knowledge/MEMORY.md`（偏离台账节）
- 门槛②：投影表 4 项缺口（`contract-asm`/`sbi`/`exception`/`mmu`）清零或显式 deferred
- 门槛③：`make check-spec-refs` Check1/Check2 = 0
- 门槛⑤：偏离台账恰好 6 项（`MEMORY.md`）

## 核验记录（2026-10-04，architect 核验）

**关联任务**：77/77 全部 `已验证`（其中 `SPEC-020m`/`SPEC-025m` 为旧过渡期里程碑，不计入本 M2 `m`）。

**门槛②（投影缺口清零 / 显式 deferred）——`spec/README.md` 实测**：
```
$ ls -l .tao/knowledge/contract-asm.md                 → 存在（SPEC-091t）
$ grep -nE '^\| `(DADAO-12|DADAO-13|DADAO-22|DADAO-23)' spec/README.md
  DADAO-12/13/22/23 ①叙述合约列 = `deferred`（contract-sbi/exception/mmu；归属 M3+，触发条件）
$ grep -nE 'contract-(sbi|exception|mmu)\.md' spec/Process-02-合约编写规范.md
  三者状态 = **deferred**（SPEC-092t）
```
⇒ 门槛②的 **4 项**（`contract-asm` 已补齐；`sbi`/`exception`/`mmu` 显式 deferred）**均满足**。
**caveat（非阻断，供主会话复核）**：投影表仍存 3 处字面 `缺口`——`SimRISC-07` 行 ④列 `缺口`（oracle/向量待建，见 `docs/fp-oracle-design.md`；FP 独立 oracle/向量按 `milestones.md` 明确属 **M3**，但未加 `deferred` 字样）、`DADAO-12` 行 ②④列 `缺口（据实）`（表示「据实、无需独立投影」）。按 `SPEC-090k` 对门槛②的 4 项界定为满足；若要字面清零，建议将 `SimRISC-07 ④` 改标 `deferred（M3）`（需改 `spec/README.md`，超出本核验写范围，交主会话）。

**门槛③（`check-spec-refs` 76→0）**：
```
$ make check-spec-refs ; echo EXIT=$?
  Check 1 — 引用有效性：总引用数 680，成功解析 680，失败 0
  Check 2 — 无引用规范断言：命中数 0
  结果: PASS (0 violations)
EXIT=0
```
（`ISS-086` 已 closed；日志 `.work/log/spec/M2-milestone-check-spec-refs.log`。）

**门槛⑤（偏离台账 6 项）**：
```
$ awk '...' .tao/knowledge/MEMORY.md   # `## 上游 ↔ v5 偏离台账`
  表格数据行 = 6（# 1 exit port / 2 fence SBZ / 3 测试机地址映射+复位值 / 4 ra0(MemRAS) / 5 e_flags / 6 M1-M2 排除口径）
```
6 项均带 ADR/契约指针（`SPEC-093t` 已验证）。

**门槛①（`make check` 全绿）**：见 `milestones.md` M2 达成核验记录与 `.work/log/integ/M2-milestone-make-check.log`（EXIT=0，lit 31/31）。

**跨模块影响**：无未处置项（`issues.yaml` open 项无一 `scope: M2`）。

**结论**：核验通过，置 `里程碑`。
