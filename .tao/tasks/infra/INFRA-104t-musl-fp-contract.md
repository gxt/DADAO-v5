# INFRA-104t: musl 构建加 `-ffp-contract=off`（修 `ISS-332`：`math/yn` 3 ulp）

**模块**：infra
**项目里程碑**：M9（收尾前）
**依赖**：`LLVM-123t`（FMA 收缩启用）、`LLVM-129t`（已排除自身）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**已由 reviewer 实证，勿重复推断**）

- 现象：libc-test 静态档从 `LLVM-127t` 时的 **331 pass / 0 fail** 变为 **330 pass / 1 fail**，唯一 fail = `math/yn`（差 3 ulp）。
- 排除：`LLVM-129t` 关闭 `ldm/stm` 后仍 fail，失败 TU 零 `ldm/stm`；`jn/j0/j1` 目标码开关前后逐条一致。
- **决定性实验**（reviewer 在临时树做的）：`jn.c` 加 `-ffp-contract=off` 重编 ⇒ **exit=0 回绿**。
- 假设成立：`LLVM-123t` 启用 FMA 收缩后，musl 的 libm 多项式在 `a*b+c` 处收缩为单次舍入，结果与 libc-test 的严格期望差 1–3 ulp。上游 musl 的 `configure` 会尝试加 `-ffp-contract=off`；本仓交叉构建**没有**该 flag（`tools/infra/build_musl.py` 与 `components/musl/` 均无）。

## 目标

给 musl 交叉构建加 **`-ffp-contract=off`**（与上游意图一致），使 libm 结果与收缩无关；重建静态 + 共享 musl，验证 libc-test 恢复 **331 pass / 0 fail**。

## 实现要点（不预设落点，二选一并在完成区说明）

1. `tools/infra/build_musl.py` 的编译 flag（若它直接驱动 `make`，传 `CFLAGS_EXTRA`/`CFLAGS`）；
2. 或 `components/musl/` 的构建补丁（`config.mak` / `Makefile` 片段）。

**不要**全局关掉用户的 FMA 收缩（那只影响 libc 构建）。

## 验收

1. `make build-musl` + `make build-musl-shared` 重建成功；`check-musl-freshness` rc=0。
2. libc-test 静态档：**331 pass / 0 fail**（known-fail/blocked 保持原值）；`math/yn` 单独跑 exit=0。
3. 抽查 3 个 libm 函数目标码，确认收缩已消失（`fomul`+`foadd` 存在、`fofma` 为 0，或在 FP contraction 点看 `fofma` 消失）。
4. `make check`(L1) rc=0；`make check-modules`(L2) rc=0。
5. **可达 FAIL**：去掉该 flag 重建 ⇒ `math/yn` 复现 fail（贴两次真实输出）。
6. 证据 `.work/evidence/<任务ID>/run.sh`（rc 落盘、禁 `| tee`）。

## 接口规范

- **输入**：`tools/infra/build_musl.py`、`components/musl/**`、`Makefile`。
- **输出**：构建 flag + 重建产物 + libc-test 结果。
- **约束**：不改 `spec/`、`contracts/`、LLVM/QEMU；不 commit/push；临时目录 `/tmp/opencode/INFRA-104t/`。

## 完成区
（执行后填写，≤30 行）

## 审阅记录
