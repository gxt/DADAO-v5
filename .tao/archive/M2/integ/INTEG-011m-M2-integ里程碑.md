# INTEG-011m: M2 integ 里程碑

**模块**：integ
**项目里程碑**：M2
**状态**：里程碑
**目标**：集成验证层随 M2 收口——跨模块接口契约机械核对（LLVM/QEMU/opcodes/inventory，去硬编码并接入门控）、`validate_encoding` no_overlap 修复、以及 **最小 FP E2E smoke**（`llvm-mc → llvm-objcopy → QEMU`，期望值独立派生）；`check-interface` 80/80、`make check` 全绿。
**关联任务**：`INTEG-005t`、`INTEG-006t`、`INTEG-007t`、`INTEG-008t`、`INTEG-009t`（5 个）

> **注**：`INTEG-010t`（M2 归档与回顾）同属项目里程碑 M2，但按 `SPEC-090k` 属 **M2 达成后**执行的收尾任务（依赖「M2 各模块 `m` 均已核验为 `里程碑`、门槛 5 条均满足」），**不计入本 `m` 的达成分解**。

## 核验
- 关联任务是否均已 `已验证`
- 各任务产出是否存在：`tools/integ/check_interface_alignment.py`、`tests/e2e/smoke_fp.s`、`tests/lit/E2E/smoke_fp.test`
- `check-interface` 80/80；最小 FP smoke 经 `make check-lit` 通过

## 核验记录（2026-10-04，architect 核验）

**关联任务**：`INTEG-005t`~`INTEG-009t`（5/5）全部 `已验证`（`009t` = M2 门槛④的最小 FP smoke）。

**命令核验（真实输出，2026-10-04）**：
```
$ python3 tools/integ/check_interface_alignment.py ; echo rc=$?
  总计: 80 项 | PASS: 80 | FAIL: 0 | MANUAL: 0
  rc=0

$ make check   → `check-lit`: DADAO-E2E :: smoke_fp.test PASS（31/31 全绿）；EXIT=0
```
`smoke_fp` 组成：`rd2rf` 入 RF → `ftadd`（1.5+2.25=3.75）→ `ft2it`（向零截断 = 3）→ `cmp.so` + `br.nz` → exit port；期望值由宿主 `struct`/`math` 独立派生（**不调用** LLVM/QEMU），反例注入 A/B 均「注入→FAIL→还原+重建→回绿」。完整输出见 `.work/log/integ/M2-milestone-make-check.log`。

**门槛④（FP 实现侧）**：执行层 60/60 + `dst_rd0@FP` + 本模块最小 smoke 三件齐备（详见 `milestones.md` M2 达成核验记录）。

**跨模块影响**：`INTEG-005t` 发现的 `check_interface_alignment.py` 非递归 glob 已修复；`INTEG-009t` 记录的 f→i 舍入口径已由 `ISS-126` 覆盖（FP 开放点固定取值）⇒ 无未处置项。

**结论**：核验通过，置 `里程碑`。
