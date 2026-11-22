# m15-testcases-023: ansibench 四件在 Tiny 上跑通（picolibc 实际应用验证）

**模块**：testcases
**项目里程碑**：M15
**依赖**：`m15-testcases-021`（测试资产命名收口）、`m18-linux-001`（K6 shell，提供 Tiny 启动面）
**可并行分片**：否
**预估**：3–5 h
**档位**：中改（新驱动 + 四件构建/运行 + picolibc 能力验证）
**状态**：待开始

## 背景（用户 2026-11-22）

embench 不再拆 freestanding/picolibc 两套；改用 **ansibench 四个「总占用 <64 KiB」的基准**作为 **picolibc 的实际应用验证**。当前 picolibc 只有冒烟/自测，没有真实应用跑通。

实测（picolibc + Tiny lds，`-O2`，text+data+bss）：`coremark` 33.7 KB、`dhrystone` 42.1 KB、`linpack` 24.4 KB、`whetstone` 30.4 KB。

**范围外**：`stream`（默认数组 bss 809 KB）、`hint`（fopen 文件）、`nbench`（popen/pipe）、`tripforce`（OpenSSL）。

## 目标

1. 新驱动 **`tests/ee-tiny/run_ansibench_tiny.py`**，并更新 `tests/ee-tiny/.manifests.toml`（新增文件必须登记，否则 `check-manifests-guard` 红）。
2. 四件构建 + 在 Kaiwu-Tiny 上运行：
   - 链接契约：安装版 `lib/picolibc_noflash.ld` + `lib/crt0-semihost.o`（`_start` 重命名为 `_picolibc_start`）+ `tests/ee-tiny/crt0_tiny_picolibc.S` 栈桩 + `libc.a`/`libm.a`/`libsemihost.a`；
   - 参数按 Tiny 规模缩小（coremark 迭代、dhrystone runs、linpack N、whetstone n），目标单件 <2 min。
3. **picolibc 能力验证（本任务重点）**：每件实际使用并断言到的能力：
   - `printf`（含 `%f`：whetstone/dhrystone 的结果行）；
   - `malloc/free`（coremark/dhrystone/linpack）；
   - `libm`：`sin/cos/atan/log/exp/sqrt`（whetstone）、`fabs`（linpack）；
   - `clock()`：Tiny 上若不可用/不准确，**不得静默绕过**——要么接 `cfx_time` 的最小适配（披露），要么登记为缺口并说明断言如何降级。
4. 断言：四件 `exit 0` + 关键输出行（CoreMark `Correct operation validated`、dhrystone/linpack/whetstone 的结果行）；计时数字只记录不断言。

## 验收（真实 rc）

1. `python3 tests/ee-tiny/run_ansibench_tiny.py` rc=0，逐件打印 exit/关键输出/耗时；
2. **可达 FAIL ≥2 路**（`cp`+md5 还原 + 重建）：① 改一条期望输出 ⇒ 红；② 破坏 `crt0_tiny_picolibc.S`（如不设 SP）⇒ 红；
3. `check-manifests-guard`、`check-tests-index`、`check-dirs` rc=0；
4. 不回归：`test-picolibc-smoke`、`run_picolibc_tests_tiny.py --stage fast` rc=0；
5. 完成区 ≤30 行；状态 → `待验收`。

## 约束

独立 worktree；不提交 git；只动 `tests/ee-tiny/**`（新驱动 + manifest）、必要证据脚本与任务书；不改 `components/**`（ansibench 是 patchless 语料，源树只读）；术语「寄存器组」；`cp`+md5 还原；不写运行期路径。
