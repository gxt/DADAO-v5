# LLVM-015m: LLVM MC 里程碑

**模块**：llvm
**项目里程碑**：M1
**状态**：里程碑
**目标**：DADAO-v5 的 LLVM MC 层完成——`dadao-unknown-elf` triple 注册，`llvm-mc` 能汇编全部 M1 指令（含 RA）、`llvm-objdump` 能反汇编回规范文本，编码字节与 `.tao/knowledge/contract-isa.md` / `contracts/opcodes.yaml` 独立推导的期望值一致，lit 字节级检查 0 failures，`make build-mc` 全绿。
**关联任务**：`LLVM-001k`、`LLVM-002t`、`LLVM-003t`、`LLVM-004t`、`LLVM-005t`、`LLVM-006t`、`LLVM-007t`、`LLVM-008t`、`LLVM-011t`、`LLVM-012t`、**`LLVM-013t`**（wyde-position 解析修复，2026-09-22）、**`LLVM-014t`**（ELF `e_flags` 修复，2026-09-22；`LLVM-010t` 已于 2026-09-21 关闭）

## 核验
- 关联任务是否均已 `已验证`
- 各任务产出的文件是否都存在：
  - `.tao/knowledge/adr-0006-llvm-baseline.md`
  - `manifests/components.lock.toml`（llvm `enabled = true` + 完整 commit）
  - `components/llvm-project/patches/0001-dadao-triple-registration.patch`
  - `components/llvm-project/patches/0002-dadao-target-skeleton.patch`
  - `components/llvm-project/patches/0003-dadao-register-info.patch`
  - `components/llvm-project/patches/0004-dadao-instrinfo.patch`
  - `components/llvm-project/patches/0005-dadao-asmparser.patch`
  - `components/llvm-project/patches/0006-dadao-disassembler.patch`
  - `components/llvm-project/patches/0007-wyde-position-operand-parser.patch`（`LLVM-013t` 产出）
  - `components/llvm-project/patches/series`
  - `tests/lit/MC/Dadao/lit.cfg.py`（`LLVM-003t` 产出）
   - `tests/lit/MC/Dadao/*.s`（含 OBJ/ASM 前缀 + 字节级 OBJ CHECK，`LLVM-008t` 产出；`LLVM-011t`/`LLVM-013t` 增补，现 **21 个**）
   - `tests/lit/MC/Dadao/wpn_operand.s`、`wpn_err_wp4.s`、`wpn_err_foo.s`、`wpn_err_range.s`（`LLVM-013t` 产出）
  - ~~smoke `.s` 修正与 E2E lit 用例（`LLVM-010t` 产出）~~（`010t` 已关闭；E2E 冒烟归 `INTEG-002t`）
  - RA 指令补丁与 lit（`LLVM-011t` 产出）
  - `tools/llvm/check_lit_bytes.py`（`LLVM-012t` 产出）
- `make build-mc` PASS（ninja 目标含 `not`，`LLVM-013t` 补）；`llvm-lit tests/lit/MC/Dadao/` 0 failures（**21 个**）
- `python3 tools/llvm/check_lit_bytes.py` exit 0（N > 0；现 **53 patterns**）
（核验通过后，主会话将 `**状态**` 置为 `里程碑`）

## 核验记录（2026-09-21，主会话执行；用户确认置里程碑）

**关联任务**：`LLVM-001k`~`008t`、`011t`、`012t` 均已 `已验证`；`LLVM-010t` 已关闭（2026-09-21，见 `changelog.md`/`deferred.md`）。

**产出文件**：全部存在（`adr-0006-llvm-baseline.md`、`manifests/components.lock.toml`、`components/llvm-project/patches/0001`–`0006` + `series`、`tests/lit/MC/Dadao/lit.cfg.py`、`tests/lit/MC/Dadao/*.s`（**17 个**）、`tools/llvm/check_lit_bytes.py`）。

**命令核验（真实输出）**：
```
$ make build-mc
build-mc: PASS

$ .work/build/llvm/bin/llvm-lit tests/lit/MC/Dadao/
Total Discovered Tests: 17
  Passed: 17 (100.00%)
  Failed:  0 (0.00%)

$ python3 tools/llvm/check_lit_bytes.py
check_lit_bytes: 41 patterns OK
  (info: 32/41 masks cover op-field only)
exit=0

$ python3 tools/llvm/test_encoding_oracle.py     # 额外
Results: 68 passed, 0 failed out of 68 tests
```

**跨模块影响核查**：`fence`（LLVM 侧 lit 缺口 + QEMU 侧实现缺失）与 `.o → .bin`/`llvm-objcopy` 缺口均已按用户裁定**登记 `deferred.md`**（处置完毕）；`INTEG-002t`（MC↔QEMU E2E 冒烟）属 **integ** 模块，非本里程碑门槛。⇒ 无未处置的跨模块影响。

**结论**：核验通过，置 `里程碑`。

## 核验记录（第 2 轮：2026-09-22，主会话执行；因 `LLVM-013t` 新增而重新核验）

**触发**：`INTEG-002t` 发现 `llvm-mc` 对 `wpN` **静默编码为 `wp0`** ⇒ 新增修复任务 `LLVM-013t`（用户裁定「增加专门任务」，里程碑不顺延）。该任务已完成并 `已验证`，故按 AGENTS.md 模块里程碑规则**重新核验**本里程碑。

**关联任务**：`LLVM-001k`~`008t`、`011t`、`012t`、**`013t`** 均已 `已验证`；`LLVM-010t` 已关闭（2026-09-21）。

**产出文件**：全部存在；新增 `components/llvm-project/patches/0007-wyde-position-operand-parser.patch` + `tests/lit/MC/Dadao/wpn_operand.s`/`wpn_err_wp4.s`/`wpn_err_foo.s`/`wpn_err_range.s`；`tests/lit/MC/Dadao/*.s` 由 17 → **21 个**。

**命令核验（真实输出，2026-09-22）**：
```
$ make build-mc
ninja: Entering directory `.work/build/llvm'
ninja: no work to do.
build-mc: PASS

$ .work/build/llvm/bin/llvm-lit tests/lit/MC/Dadao/
Total Discovered Tests: 21
  Passed: 21 (100.00%)

$ python3 tools/llvm/check_lit_bytes.py
check_lit_bytes: 53 patterns OK
  (info: 44/53 masks cover op-field only)
exit=0

$ python3 tools/llvm/test_encoding_oracle.py
Results: 68 passed, 0 failed out of 68 tests

$ python3 tools/llvm/validate_instrinfo.py
=== Result: 0 errors, 0 warnings ===
```

**跨模块影响核查**：`INTEG-002t` 报告的 `wpN` 缺陷已由 `LLVM-013t` **修复并验收**（reviewer 两轮 Accepted；`wp0`–`wp3` 编码经独立手算 16/16 一致；3 组反例注入均 FAIL + 还原）⇒ **无未处置的跨模块影响**。

**结论**：核验通过，`LLVM-015m` 维持 `里程碑`。
