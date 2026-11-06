# GEM5-021t: gem5 SE tset 基线调查（static 先行）

**模块**：gem5
**项目里程碑**：M11
**依赖**：`GEM5-014t`（已验证；SE 平台骨架）、`ADR-0048 D3/D4`（SE 复用 `tests/tset`，最终覆盖完整 tset）
**状态**：待开始

## 用户裁定（2026-11-06）

> M11 的「GEM5 == QEMU」按 **「补完整 tset（D4 字面）」** 收口。
>
> 追问后授权：**「允许加 SE 驱动（推荐）」** —— 允许在 `tools/testcases/` 加 gem5 SE 运行路径（driver 层），**不动 `tests/tset` 用例与期望**，先测出缺口。

## 现状（事实）

- gem5 SE 平台存在：`configs/dadao/se.py`（`--binary`，只接受静态 `ET_EXEC`）、`DadaoSEWorkload` + `Process` + SE TLB（`GEM5-014t`）
- SE 侧 syscall 面目前只到最小 libc 启动集（`set_tid_address`/`write`/`writev`/`exit`/`exit_group`）
- `tests/tset` 三个驱动（`run_libc_test_user_suite.py` / `run_llvm_ts_user.py` / `run_embench_user_suite.py`）都是 QEMU user 专用，**没有 gem5 SE 运行路径**
- `.dadao/tests/` 下没有任何 gem5 tset 运行目录 ⇒ 完整 tset 在 SE 上当前覆盖为 0

## 目标

1. **加 SE 运行路径**（driver 层，`tools/testcases/`）：让三类 tset 的 **static** 产物可在 gem5 SE 上执行并收集退出码/stdout；不修改 `tests/tset/**` 的用例、期望值、语料。
2. **跑出基线**：`libc-test` / `llvm-ts` / `embench` 的 static 全量（或按现场可枚举全集）在 gem5 SE 上逐一执行，记录：
   - `PASS` / `FAIL` / `SKIP` / `BLOCKED`
   - 退出码、stdout 摘要
   - `BLOCKED` 必须给**根因证据**（未实现 syscall 号/名称、`ET_DYN`/`PT_INTERP`、TLS 相关 syscall、`mmap`/`brk`、线程/futex、信号等）
3. **与 QEMU user 基线逐 case 对照**：同 case ID 比较 pass/fail/exit；输出差异清单（`gem5_only_fail` / `qemu_only_fail` / `blocked`），不得把 BLOCKED 写成 PASS。
4. **产出可复跑报告**：JSON（机器可读）+ Markdown 摘要（计数现场统计，不手写数字）；摘要落知识层（`.tao/knowledge/refs/`），运行期产物不入库。
5. 给出**缺口分类清单**（按能力分组、每组案例数与预估补做顺序），作为后续实现任务的输入。

## 范围 / 非范围

**在范围内**：`tools/testcases/lib/**`、`tools/testcases/tset/**` 的驱动层（新增 SE 模式）、`.tao/knowledge/refs/GEM5-021t-*`（摘要）、本任务书、`milestones.md`。

**不在范围**：实现缺失的 SE 能力（syscall/TLS/动态链接/线程等，另立任务）；`tests/tset` 用例与期望；QEMU/gem5 语义实现；`tests/parity/matrix-M11.md`（等完整 tset 对齐后再重生成）。

## 验收标准

1. 新增 SE 运行路径可复跑，命令写入任务书；**static 三类套件各跑一轮**并产出 JSON + 摘要。
2. 每个未通过案例都有 `BLOCKED`/`FAIL` 分类与证据；`BLOCKED` 不得计入 PASS；计数现场统计。
3. 与 QEMU user 基线逐 case 对照，输出 `gem5_only_fail`/`qemu_only_fail`/`blocked` 清单；若出现 `gem5 通过而 QEMU 未通过`，单列并标注（按 `ADR-0048 D5` 需定位）。
4. 缺口分类清单：每类给出「能力名、阻塞案例数、代表案例、所需改动面（syscall/TLB/TLS/loader）」。
5. 不改 `tests/tset/**`；`make check`（L1）rc=0；完成区 ≤30 行、无运行期路径。
6. 反例：把某个已知不可运行的产物（如 `ET_DYN`）喂给 SE 路径 ⇒ 必须记 `BLOCKED`（`PT_INTERP`/`ET_DYN`），不得 PASS。

## 说明

- 本轮只做 **static**；动态链接、TLS、线程/futex 按 `ADR-0048 D4` 属「后补但不得降级」，本轮只需**如实列入缺口**。
- 允许为了跑通 SE 路径做**最小**驱动改造（参数化 engine、产物选择、超时/日志），不得改测试语义。
- 若某套件在 SE 上连启动都不到（例如 loader 拒绝 `ET_EXEC` 以外），按 `BLOCKED` 记录并给出首个失败点（stderr/退出码）。
