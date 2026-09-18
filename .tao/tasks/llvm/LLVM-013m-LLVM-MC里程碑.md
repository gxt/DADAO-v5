# LLVM-013m: LLVM MC 里程碑

**模块**：llvm
**项目里程碑**：M1
**状态**：待开始
**目标**：DADAO-v5 的 LLVM MC 层完成——`dadao-unknown-elf` triple 注册，`llvm-mc` 能汇编全部 M1 指令（含 RA）、`llvm-objdump` 能反汇编回规范文本，编码字节与 `.tao/knowledge/contract-isa.md` / `contracts/opcodes.yaml` 独立推导的期望值一致，lit 字节级检查 0 failures，`make build-mc` 全绿。
**关联任务**：`LLVM-001k`、`LLVM-002t`、`LLVM-003t`、`LLVM-004t`、`LLVM-005t`、`LLVM-006t`、`LLVM-007t`、`LLVM-008t`、`LLVM-010t`、`LLVM-011t`、`LLVM-012t`

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
  - `components/llvm-project/patches/series`
  - `tests/lit/MC/Dadao/lit.cfg.py`（`LLVM-003t` 产出）
   - `tests/lit/MC/Dadao/*.s`（含 OBJ/ASM 前缀 + 字节级 OBJ CHECK，`LLVM-008t` 产出）
  - smoke `.s` 修正与 E2E lit 用例（`LLVM-010t` 产出）
  - RA 指令补丁与 lit（`LLVM-011t` 产出）
  - `tools/llvm/check_lit_bytes.py`（`LLVM-012t` 产出）
- `make build-mc` PASS；`llvm-lit tests/lit/MC/Dadao/` 0 failures
- `python3 tools/llvm/check_lit_bytes.py` exit 0（N > 0）
（核验通过后，主会话将 `**状态**` 置为 `里程碑`）