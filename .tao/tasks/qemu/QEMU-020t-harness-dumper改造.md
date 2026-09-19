# QEMU-020t: harness dumper 改造（D1 修法 a 落地）

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-014t`、`QEMU-006t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `QEMU-014t` 交付的 `tests/scripts/build_test_binary.py`（含 `build_dumper_section`、`build_exit_section`）
  - `QEMU-014t` 交付的 `tests/scripts/run_qemu_test.py`（含 `QMPClient`、`--dump` 模式）
  - `QEMU-006t` 实现的 `jump-rrii`/`br.nz` 语义（trampoline/exit 可用）
  - `.tao/knowledge/adr-0010-qemu-task-restructure.md` D1 修法 a（普通模式不 emit dumper）
  - `.tao/knowledge/adr-0009-qemu-harness-methodology.md` D2/D7（guest 内比较 / state-dump 机制）
- 输出：修改后的 `tests/scripts/build_test_binary.py`（dumper emit 条件化）、`tests/scripts/run_qemu_test.py`（模式联动）
- 约束：
  - 不改 harness 的 loader/exit/比较逻辑
  - 不改 QEMU 补丁
  - `--dump` 模式行为不变（仍 emit dumper + 自旋 + QMP pmemsave）
  - 普通模式（无 `--dump`）不 emit dumper 段，使 harness 在 `006t` 后可端到端跑 RD-only 向量
  - 完成后不自行 commit

## 背景（完整）

### 目标

按 ADR-0010 D1 修法 a 改造 harness：普通模式不 emit dumper 段（因 dumper 用到 `st.o-rb`/`rb2rd`，属 `008t`），使 harness 在 `006t` 完成后即可端到端跑 RD-only 向量。`--dump` 诊断模式保持原有行为（emit dumper + 自旋 + QMP pmemsave）。

### 设计理由

- D1 修法 a 的核心洞察：普通模式（D2）pass/fail 判定只看 `$?`（guest 内 XOR+ORR 比较 → 写 exit port），**不需要 dumper 段**。
- dumper 段用到 `st.o-rb`（写 RB 值到 dump region）和 `rb2rd`（读 rb0/PC），这些指令属 `QEMU-008t` 范围。
- 去掉普通模式的 dumper 后，harness 只需 `005t`（loader/比较指令）+ `006t`（`st.o` exit port + `jump`/`br.nz`）即可端到端跑。

### 关键概念 / 数据

**改造方案**：

1. `build_test_binary.py` 的 `build_dumper_section()` 调用改为条件化：
   ```python
   if dump_mode:
       build_dumper_section(out, case)  # 需要 rb2rd/st.o-rb（008t）
   # 普通模式：不 emit dumper 段
   ```

2. `build_exit_section()` 中的 `br.nz` + `jump` 结构不变（已在 `006t` 实现）

3. `run_qemu_test.py` 的 `--dump` 参数联动：`dump_mode=True` 时传递给 `build_test_binary`

**验证**：
- `006t` 完成后：`python3 tests/scripts/run_qemu_test.py tests/vectors/isa/reg-arith.yaml` 应全量 PASS（无 dumper，只靠 exit code 判定）
- `008t` 完成后：`python3 tests/scripts/run_qemu_test.py tests/vectors/isa/reg-arith.yaml --dump` 应能导出 state-dump

### 上游引用

- 本项目：`.tao/knowledge/adr-0010-qemu-task-restructure.md` D1 修法 a
- 本项目：`.tao/knowledge/adr-0009-qemu-harness-methodology.md` D2/D7

## 交付物

- 修改后的 `tests/scripts/build_test_binary.py`：dumper emit 条件化
- 修改后的 `tests/scripts/run_qemu_test.py`：模式联动
- 完成区附 `006t` 后端到端 RD-only 向量 PASS 证据

## 已知坑 / 结论

1. **`--dump` 模式仍需 `008t`**：dumper 段用 `rb2rd`/`st.o-rb`，`--dump` 模式在 `008t` 前不可用。
2. **普通模式不需要 dumper**：D2 guest 内比较 → exit code，host 只看 `$?`。
3. **`expected_fault` 优先**：legality 用例在 `--dump` 下仍走 fault 路径写 exit port，不自旋（`build_exit_section` 中 `expected_fault` 分支优先于 `dump_mode` 分支）。

## 参考

- 本项目：`.tao/knowledge/adr-0010-qemu-task-restructure.md` D1
- 本项目：`.tao/tasks/qemu/QEMU-014t-QEMU语义harness.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

| # | 验收项 | 现在可跑 / BLOCKED | 说明 |
|---|--------|-------------------|------|
| 1 | `build_test_binary.py` 普通模式不 emit dumper 段（diff 确认 `build_dumper_section` 调用被 `if dump_mode:` 保护） | 现在可跑 | 代码审查 |
| 2 | `run_qemu_test.py` 的 `--dump` 参数正确传递给 `build_test_binary` | 现在可跑 | 代码审查 |
| 3 | `006t` 完成后：`python3 tests/scripts/run_qemu_test.py tests/vectors/isa/reg-arith.yaml` 全量 PASS（RD-only 向量，无 dumper） | BLOCKED | 原因：需 `QEMU-006t` 完成后方可验证。替代：在 `005t` 已验证 + `006t` 补丁 apply 后验证 |
| 4 | `--dump` 模式行为不变（仍 emit dumper + 自旋 + QMP pmemsave） | 现在可跑 | 代码审查（行为逻辑未变，只是条件化调用） |
| 5 | 既有 legality 用例（`expected_fault`）在普通模式下仍正确路由 | 现在可跑 | `run_qemu_test.py tests/vectors/isa/misc.yaml --case 2` |
| 6 | `make build-qemu` 不受影响（本任务只改 harness 脚本） | 现在可跑 | |
| 7 | 完成区含真实运行输出；未自行 commit | 现在可跑 | |

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录