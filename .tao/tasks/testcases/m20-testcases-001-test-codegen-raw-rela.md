# m20-testcases-001: 修复 `test-codegen` raw 单 TU 的未解析 RELA（ISS-509）

**模块**：testcases
**项目里程碑**：M20
**依赖**：无（`m14-llvm-007` 的「同节 global 仍发重定位」行为已合入）
**可并行分片**：否（单驱动脚本 + 单门控）
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：待开始

## 背景（M20 分诊，2026-11-25）

`ISS-509` 记录 `check-unit` 的 `test-codegen` 基线红：raw single-TU 组装 19/19 报
`SHT_RELA present`，`Results: 0/19 passed`。本次现场复核仍复现：

- 用当前工具链跑驱动脚本的 `--build-only`，19 例全部失败，理由均为
  `raw single-TU object is not fully resolved: SHT_RELA present`。
- 根因不在 QEMU，也不在 LLVM 语义：`llc` 输出的程序带 `.globl main`，
  `llvm-mc` 对同节 global 符号仍发 `R_DADAO_REL26`（`m14-llvm-007` 有意保留
  该重定位，供链接器使用）；而 raw 管线把 crt0 与程序拼成一个 TU，没有链接器，
  `llvm-objcopy` 不会施加重定位。
- 受控验证：把 raw 合并文本里的 `.globl main` 改为 `.local main` 后重汇编，
  `llvm-readelf -r` 输出 `There are no relocations in this file`。

## 目标

1. raw 管线在**只改测试驱动**的前提下，让 crt0 对 `main` 的调用在汇编期解析：
   合并文本中程序侧 `main` 必须按 TU 内局部符号处理（`m14-llvm-007` 的 global
   重定位行为不得改）。
2. 19/19 用例在 QEMU Tiny 上按 `expected.yaml` 的退出码通过；不得删除或放宽
   「raw 对象必须无 RELA」断言。
3. 不改变 linked-ELF 管线（`test-elf`）与既有多 TU 语义。

## 验收（逐条贴真实 rc）

1. `run_codegen_e2e.py --build-only`：19/19 通过、0 条 `SHT_RELA present`。
2. 完整 `test-codegen`（或 Makefile 目标的等价命令）：19/19 pass，退出码 0；
   若当前有在途 QEMU 任务占用 `install-host` 窗口，允许用 `make -n test-codegen`
   解析工具路径后直跑同一驱动，并在完成区写明未跑 `make` 目标的原因。
3. **可达 FAIL**：把本次「局部化 `main`」改动还原为原始 `.globl main` ⇒
   build-only 回 0/19（`SHT_RELA present`）；`cp` + md5 还原后回 19/19。
4. `check-inst-asm`、`check-tests-index` 真 rc；`check-patch-tree` 只要求
   **llvm/testcases 未被本任务改坏**，总 rc 受在途 qemu/musl 漂移影响时按分段披露。
5. 完成区记录实际工具 md5（`llc`/`llvm-mc`/`llvm-objcopy`）与 QEMU md5，证明
   验的是同一批二进制。

## 约束

独立 `git worktree`（分支 = `m20-testcases-001`）；不提交 git；只改
`tools/testcases/unit/run_codegen_e2e.py`（必要的最小范围）与本任务书；不改
`components/**`、`spec/`、契约、`Makefile`；不新增运行期文档。任务书不写
构建树/安装树/临时目录的具体路径，证据统一落在「运行期证据目录内的 `run.sh`」。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（待填）

#### 第 1 轮 reviewer 验收
（待填）
