# m20-qemu-001: QEMU cfx 寄存器与异常迁移

**模块**：qemu
**项目里程碑**：M20
**依赖**：W1（`m20-spec-002`/`m20-idl-001`/`m20-llvm-004`）；M16/M17 收口后派发
**可并行分片**：否（QEMU 组件写者）
**预估**：4–8 h
**档位**：大改（组件）
**状态**：待开始

## 背景

执行 `m20-spec-001` 已决口径：新 cg4/5/6/7、scratch 2..16、PTWFAULT/PTWFAIL、cfx 编号、UART32/33（cfxha61 异步源）、中断删除、每 cfx 五种原因。

## 范围

- `components/qemu/patches/**` 的 cfx 寄存器面/别名/异常原因/PTW/PTWFAIL/UART/time/hart/power；
- QEMU 侧异步源（UART cfxha61）与 `cfx_hart` 捕获；PTW 细节 `cfx_ptw cg8 rc4`；
- 相关 QEMU 探针/unit、changelog、补丁序列。

## 验收

1. 新 cfx 寄存器/编号/原因/UART 异步源按契约实现；旧 cg/旧名称/旧编号残留 0；不实现旧别名。
2. `check-qemu-forms`、`check-patch-tree` qemu 段 0 problem、`check-inst-asm` 代表集/QEMU 探针真 rc。
3. PTW 故障：复用现有 PTW 用例改期望为 `PTWFAULT 1<<15` + `cfx_ptw cg8 rc4` ID；不新增专用 PTWFAULT/PTWFAIL 用例。
4. 至少一条可达 FAIL；安装根/构建树 QEMU md5 一致；证据落运行期证据目录内 `run.sh`。

## 约束

独立 worktree（分支 = `m20-qemu-001`）；不提交 git；不改 `spec/`、契约、gem5/RTL/内核/LLVM；组件补丁按 `docs/Process-01` 重导。

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
