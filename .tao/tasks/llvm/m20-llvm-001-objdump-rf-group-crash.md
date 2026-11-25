# m20-llvm-001: `llvm-objdump` 对 rf 寄存器组越界崩溃（ISS-468）

**模块**：llvm
**项目里程碑**：M20
**依赖**：无（`m14-llvm-007`、`m15-spec-003` 已合入）
**可并行分片**：否（单组件补丁 + 单 lit 面）
**预估**：2–4 h
**档位**：大改（组件补丁；复核 ≤60 min）
**状态**：待开始

## 背景（M20 分诊，2026-11-25）

`ISS-468` 记录 9 个 `tests/inst/**/*_rf.S` 镜像无法生成 IP→助记符表：
组装后用 `llvm-objdump -d` 反汇编即断言崩溃。现场复核 9/9 仍复现：

```
Assertion `RegNo && RegNo < 258 && "Invalid register number!"' failed
```

定位到的触发点是测试故意构造的非法 `ldm` 原始字 `0x3EDC304A`
（`tests/inst/01-load-store/ldm.o_rrri_rf.S` 第 116 行，`rf55 + immu6=10 > 64`）。
MC 解码器接受该字并给出 `rf55`、`count=10`，打印机 `printRegGroupRange`
用 `Start.id() + Count - 1` 算结束寄存器，得到 258（越出 rf bank），撞断言。
合法用例（如 `{rf1:rf63}`、`{rf32:rf47}`）不触发。

## 目标

1. `llvm-objdump -d` 对**非法/越界组编码**不得崩溃：按 MC 层判据拒绝该编码并由
   objdump 输出可见的未知/非法指令形式，或在打印机层做不改合法输出的防御。
   具体分支在任务书「待裁定」中给出并由 reviewer 复核，不得静默截断成合法组。
2. 合法 rf 组（含 rf63 边界、`{rf32:rf47}`、`{rf1:rf63}`）反汇编输出逐字不变。
3. 9 个 `_rf.S` 镜像全部可生成反汇编；不得通过修改测试用例里的非法原始字来绕过
   （该字是合法性用例的一部分）。

## 验收（逐条贴真实 rc）

1. 9/9 `_rf.S` 组装 + `llvm-objdump -d` 全部 rc=0；崩溃数为 0；对 `0x3EDC304A`
   给出稳定、可重复的非法编码输出（记录原文）。
2. 合法 rf 组反汇编抽样 3 例（`{rf63:rf63}`、`{rf32:rf47}`、`{rf1:rf63}`）与改动前
   逐字节 `diff` 为空。
3. 新增/扩展 lit 用例：覆盖非法 `0x3EDC304A`、合法 rf63 边界和至少一个合法组；
   证明非法分支可达（注入前红/后绿），且不是恒真断言。
4. 按 `docs/Process-01` 更新 `components/llvm-project` 补丁序列并重导；`check-lit`、
   `check-patch-tree` 的 **llvm 段 0 problem**、`check-instrinfo` 真 rc。
5. 重建/安装按仓库纪律执行；完成区记录 `llvm-objdump` 与安装根 md5，证明安装根
   与构建树一致；若 `install-host` 与在途 QEMU 窗口冲突，须串行等待或按规程
   记录并补装。

## 约束

独立 `git worktree`（分支 = `m20-llvm-001`）；不提交 git；只改
`components/llvm-project/**`、对应 lit 用例与本任务书；不改 `spec/`、契约、
`Makefile`；不新增测试之外的文档。任务书不写构建树/安装树/临时目录的具体路径；
证据落在「运行期证据目录内的 `run.sh`」。
术语：`rf` 是**寄存器组**，不写「银行」。

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
