# M1 阶段已关闭 Issue（≤ 2026-09-22）

> **来源**：Step 3（2026-10-04）从 `.tao/knowledge/issues.yaml` 提取——**M1 阶段（≤ 2026-09-22）已 `closed` 的 issue**。
>
> **判据**：M1 达成 = **2026-09-22**（commit `348dbd3`，`INTEG-004m` 置里程碑）。**灰区不计**——2026-09-23~09-30 的「M1 范围收窄」（如 `fence` 移出 M1、`rela.si` 删除）属 **M1→M2 过渡**，不计 M1 阶段（用户裁定 2026-10-04）。
>
> **未提取**：post-M1（≥ 2026-09-23）的 `closed` issue 仍在活台账 `.tao/knowledge/issues.yaml`。

**共 8 条**（按原 `issues.yaml` 顺序）。

| id | title | scope | resolved_by |
| --- | --- | --- | --- |
| `ISS-001` | ISA 归一化完成里程碑（原 `SPEC-005m`）已移除——意义由 `SPEC-002t/003t` + `SPEC-011m` 覆盖 | spec | `SPEC-001k` 任务重排移除独立 m 标记（2026-09-10） |
| `ISS-012` | `opcodes.yaml` L5 注释与 `ADR-0004` D5.1 措辞歧义——已由 `QEMU-004t` 修正（UNDI→ILLI） | spec | `QEMU-004t` N-1 修正（2026-09-19） |
| `ISS-036` | validator 缺 legality 类 `expected_fault` 非 null 守卫——已由 `TESTCASES-008t` 消解 | testcases | `TESTCASES-008t`（2026-09-18） |
| `ISS-037` | 跨模块影响（testcases 重排）：`QEMU-012t`/`017t`/`001k` 表中陈旧引用已同步修正 | testcases, qemu | 2026-09-16 规划级复审同步修正 |
| `ISS-033` | 数据级覆盖率缺口 154 项（`009t` 发现）→ 由 `TESTCASES-010t+011t` 消解，gap=0 后方可置 `012m` 里程碑 | testcases | `TESTCASES-010t`（114 条）+ `TESTCASES-011t`（35 条）消解，`012m` 已置里程碑（2026-09-21） |
| `ISS-034` | `012m` 阻断（用户裁定 B1）：数据级覆盖率缺口未消解前 `TESTCASES-012m` 不得置里程碑 | testcases | `TESTCASES-010t+011t` 消解缺口，`012m` 已置里程碑（2026-09-21） |
| `ISS-048` | `QEMU_BUILD` 未使用 / 构建落点不一致——已消解（`QEMU-003t` 改 out-of-tree） | qemu | `QEMU-003t`（2026-09-19） |
| `ISS-059` | `QEMU-008t` 验收遗漏：`stm.o-rb` 被误标 PASS——已由 `QEMU-010t` 补实现+验证 | qemu | `QEMU-010t`（2026-09-20） |

## 原始 YAML（提取前逐条）

```yaml
- id: ISS-001
  title: "ISA 归一化完成里程碑（原 SPEC-005m）已移除——意义由 SPEC-002t/003t + SPEC-011m 覆盖"
  status: closed
  scope: [spec]
  blocks: []
  resolved_by: "SPEC-001k 任务重排移除独立 m 标记"

- id: ISS-012
  title: "opcodes.yaml L5 注释与 ADR-0004 D5.1 措辞歧义——已由 QEMU-004t 修正（UNDI→ILLI）"
  status: closed
  scope: [spec]
  blocks: []
  resolved_by: "QEMU-004t N-1 修正（2026-09-19）"

- id: ISS-033
  title: "数据级覆盖率缺口 154 项（009t 发现）→ 由 TESTCASES-010t+011t 消解，gap=0 后方可置 012m 里程碑"
  status: closed
  scope: [testcases]
  blocks: []
  resolved_by: "TESTCASES-010t（114 条）+ TESTCASES-011t（35 条）消解，012m 已置里程碑（2026-09-21）"

- id: ISS-034
  title: "012m 阻断（用户裁定 B1）：数据级覆盖率缺口未消解前 TESTCASES-012m 不得置里程碑"
  status: closed
  scope: [testcases]
  blocks: []
  resolved_by: "TESTCASES-010t+011t 消解缺口，012m 已置里程碑（2026-09-21）"

- id: ISS-036
  title: "validator 缺 legality 类 expected_fault 非 null 守卫——已由 TESTCASES-008t 消解"
  status: closed
  scope: [testcases]
  blocks: []
  resolved_by: "TESTCASES-008t（2026-09-18）"

- id: ISS-037
  title: "跨模块影响（testcases 重排）：QEMU-012t/017t/001k 表中陈旧引用已同步修正"
  status: closed
  scope: [testcases, qemu]
  blocks: []
  resolved_by: "2026-09-16 规划级复审同步修正"

- id: ISS-048
  title: "QEMU_BUILD 未使用 / 构建落点不一致——已消解（QEMU-003t 改 out-of-tree）"
  status: closed
  scope: [qemu]
  blocks: []
  resolved_by: "QEMU-003t（2026-09-19）"

- id: ISS-059
  title: "QEMU-008t 验收遗漏：stm.o-rb 被误标 PASS——已由 QEMU-010t 补实现+验证"
  status: closed
  scope: [qemu]
  blocks: []
  resolved_by: "QEMU-010t（2026-09-20）"
```
