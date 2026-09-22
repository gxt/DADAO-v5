# INTEG-004m: M1 集成里程碑

**模块**：integ
**项目里程碑**：M1
**状态**：里程碑
**目标**：DADAO-v5 的 M1 集成闭环达成——「MC 汇编 → objcopy → flat → QEMU 执行 → 结果比对」的端到端链路打通并可重复回归，跨模块接口契约机械核对一致，形成 MC↔QEMU 集成闭环。
**关联任务**：`INTEG-002t`、`INTEG-003t`

## 核验

- 关联任务是否均已 `已验证`
- 各任务产出的文件是否都存在：
  - `tests/e2e/*.s`、`tests/lit/E2E/*`（`INTEG-002t`）
  - `docs/integ-interface-alignment.md` + `tools/integ/check_interface_alignment.py`（`INTEG-003t`）
- 集成验收：`llvm-lit tests/lit/E2E/` 全 PASS；接口对齐核对零不一致
- 项目里程碑联动：`knowledge/milestones.md` 中 M1 行的 `integ` 列 = `INTEG-004m`

（核验通过后，主会话将 `**状态**` 置为 `里程碑`）

## 核验记录（2026-09-22，主会话执行；用户确认置里程碑）

**关联任务**：`INTEG-002t`、`INTEG-003t` 均已 `已验证`。

**产出文件**：全部存在——`tests/e2e/{smoke_arith,smoke_add,smoke_jump}.s`、`tests/lit/E2E/{lit.cfg.py,smoke_arith.test,smoke_add.test,smoke_jump.test}`、`docs/integ-interface-alignment.md`、`tools/integ/check_interface_alignment.py`。

**命令核验（真实输出，2026-09-22）**：
```
$ .work/build/llvm/bin/llvm-lit tests/lit/E2E/
Total Discovered Tests: 3
  Passed: 3 (100.00%)

$ python3 tools/integ/check_interface_alignment.py ; echo $?
总计: 80 项 | PASS: 80 | FAIL: 0 | MANUAL: 0
0                       ← 接口对齐零不一致

$ make check ; echo $?
repository checks: PASS
check_issues: 66 open, 8 closed (0 blocking M1-gate: 0)
0
```

**项目里程碑联动**：`knowledge/milestones.md` 中 M1 行的 `integ` 列 = `INTEG-004m` ✅ 里程碑。

**跨模块影响核查**：`INTEG-002t` 发现的 `wpN` 静默误编码已由 `LLVM-013t` 修复；`INTEG-003t` 发现的 ELF `e_flags` 不一致已由 `LLVM-014t` 修复（均 `已验证`）；`fence` 保持 `deferred`（用户裁定「deferred ⇒ 不阻断里程碑」，`ISS-056` `blocks: []`）。⇒ **无未处置的跨模块影响**。

**结论**：核验通过，置 `里程碑`；`milestones.md` 的 M1 置 `达成`。
