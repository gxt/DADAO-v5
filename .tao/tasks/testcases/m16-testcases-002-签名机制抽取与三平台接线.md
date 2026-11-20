# m16-testcases-002: 签名机制抽取（`tests/inst` 现有实现 → 共享层）+ `tests/arch` 接线

**模块**：testcases
**项目里程碑**：M16
**依赖**：无（与 `m16-chipyard-008` 并行；本任务只改 `tests/` 与 `tools/testcases/`）
**可并行分片**：否
**预估**：6–8 h
**档位**：中改
**状态**：待开始

## 背景与判据（用户 2026-11-20 两次裁定）

> 「确实值得借鉴，tests-inst 和 tests-arch 都可以采用这个能力。」
> 「tests-inst 和 tests-arch 的底层机制我希望能尽量复用。」

**关键事实：机制已经在仓里，本任务不是"新造"，是"抽出 + 复用"。**

- `tests/inst/macros/inst_test.inc:181-186` 的 `__REC reg` 就是签名的写入口：`st.o \reg, [rb30, 0]` + `add.si rb30, 8` + 计数 `__NCHECK`；`rb30` 是结果缓冲写指针（同文件 `:54` 的保留寄存器约定）。
- 收尾 `:585` 用 `__PRINT TEST_BUF, (8 * __NCHECK)` 把整块打出（`__PRINT` 见 `:192-203`，逐字节 `SYS_WRITEC`）。
- host 侧取流与比对已在 `tests/ee-tiny/run_inst_tiny.py`：三平台各返回 `(rc, stdout_bytes, log_path)`（`:246`）、chipyard 走 `+semiout=`（`:273`）、逐平台字节数 `:332`、**字节数断言 `8×检查点数`** `:346-351`。
- 平台通道均已存在，不需要新造：chipyard `+semiout` 收 `SYS_WRITEC`/`SYS_WRITE0`/`SYS_WRITE(handle 1)` 的每个字节（`tools/testcases/lib/chipyard_engine.py:14-25`）；gem5 用 `--console-out`（`tools/gem5/compare_chipyard.py:532`）；QEMU 的 semihosting console 走 stdout 管道（`tools/testcases/lib/run_qemu_test.py:400-440`）。
- `tests/arch` 现在**只有退出码**：`tests/arch/ptw/expected.yaml` 抬头写明「guest 内自检 + `SYS_EXIT` 退出码 = 0x00 通过 / 0x01–0x7F 第 N 条断言失败」，**没有实际值**。

参考形态（`riscv-arch-test`，只借形态不借判定方式）：签名区 = `.data` 里的固定数组、预填 `0xdeadbeef`（漏跑可见）、每观测点写 8 字节并前进、末尾整块 dump、host 侧逐字节比。**该框架是"单实现合规"（gold 来自 Spike/SAIL），没有多平台差分能力**——我们的判定仍是"三方/四方互比"。

## 目标

1. **共享汇编层** `tests/shared/asm/signature.inc`（`tests/shared/README.md` 的判据：被 ≥2 个 scope 复用 ⇒ 放这里）：
   - `SIG_BEGIN count`：`.data` 里 `.p2align 4` 的 `begin_signature` + `.fill count,8,0xdeadbeef`；
   - `SIGUPD reg`：`st.o \reg, [rb30, 0]` + `add.si rb30, 8` + 计数（**与 `__REC` 同形、同寄存器约定**，`rb30` = 写指针）；
   - `SIG_DUMP`：一次 `SYS_WRITE`（`handle 1`，参数块 `{1, TEST_BUF, 8*ncheck}`）块写整段；保留 `SYS_WRITEC` 逐字节路径作为回退（不改已有镜像行为时用）。
2. **`tests/inst` 改为复用，不留第二份**：`inst_test.inc` 的 `__REC` 委托给 `SIGUPD`，收尾打印改调 `SIG_DUMP`（或保持 `__PRINT` 但由 `SIG_DUMP` 实现）——**行为必须不变**（见验收 1）。
3. **host 层** `tools/testcases/lib/signature.py`：从 `run_inst_tiny.py` 抽出
   - `parse(blob, count)`：按 8 字节切、长度断言、把 `0xdeadbeef` 槽标为"未写"；
   - `compare(got, want)`：返回首个不一致槽号 + 两侧值（16 进制），供任何 scope 直接报"槽 N 期望 X 实际 Y"；
   - `capture(platform, ...)`：三平台取流适配（qemu stdout / gem5 `--console-out` / chipyard `+semiout`）；
   - `run_inst_tiny.py` 与 `tests/arch` 都调用它，**不得留第二份解析/取流实现**。
4. **`tests/arch` 接线**：`ptw` 至少 3 条 case 的观测点（A/D 回写后的 PTE 值、`cause_info`、命中/填充计数）改用 `SIGUPD` 输出实际值，host 侧用同一 `signature.py` 判定。
5. **登记**：`tests/shared/README.md` 加一行（内容/谁用）；`tests/arch/README.md` 的「观测通道」段改为「签名流 = 唯一判据载体，退出码只作镜像级兜底」。

## 不在本任务范围

- **全量改 `tests/inst` 的期望值/载体**（那属 M17 的符合作业，且会改变指令流 → 影响已标定的周期基线）；
- 改 RTL / gem5 / QEMU 源码，改 `spec/` 与 `.tao/contracts/`；
- Vast 侧三方差分（归 `m16-chipyard-011`）。

## 验收（逐条贴真实 rc）

1. **抽取不改行为**：`make check-inst-asm` **272/272**；且抽取前后**每个镜像的签名流逐字节相同**（基线与改后各 dump 一份、逐镜像 md5 比，**非抽样**）。
2. **三平台取流一致**：同一镜像在 qemu、gem5（SE）、chipyard（**Tiny**，用现成 simulator）各取一份签名流，**逐字节相等**（≥1 条 case）。若 chipyard 侧正在被其它任务构建/占用 ⇒ 记 BLOCKED 并给替代证据（不得并发构建）。
3. **漏跑可见**：故意删一条 `SIGUPD` ⇒ 对应槽为 `0xdeadbeef`，`signature.py` 报「槽 N 未写」（不是静默当 0）。
4. **可达 FAIL ≥3 路**：① 改一个期望值 ⇒ 比对 rc=1 且报槽号 + 两侧值；② `SIG_DUMP` 长度写成 `count*4` ⇒ 长度断言红；③ 某平台流缺失 ⇒ BLOCKED 而不是 PASS。
5. **复用核验**：机制实现只有一份——`signature.inc`、`signature.py` 各 1 个文件，且 `tests/inst`、`tests/arch` 内无复制（`grep` 计数**现场派生**，不写死）。
6. **门控**：`check-inst-asm`、`check-arch`、`check-tests-index`、`check-case-ledger`、`check-index-blobs`、`check-knowledge-refs` 真实 rc；`make check-inst-macro-scope` 仍绿（`SIGUPD` 加入宏体后不得触发扫描告警）。

## 约束

- 独立 `git worktree`（分支名 = 任务号）；**禁改主工作树**；临时文件在 `/tmp/opencode/<任务ID>/`。
- **不提交 git**；术语「寄存器组」；完成区不写具体 `.work/**` 路径（写「运行期证据目录内的 `run.sh`」）。
- **不得 `make install-host` / 不得重建 QEMU/gem5/chipyard**：用现成安装根与 simulator；确需重建须先说明理由并在完成区登记。
- 失败保留现场并继续推进（自行处置：派修/绕行/有据重试并记录次数/登记后跳过），只在需用户语义裁定时留问。
