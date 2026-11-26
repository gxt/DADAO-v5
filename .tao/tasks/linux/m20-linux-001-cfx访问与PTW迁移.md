# m20-linux-001: Linux/SEE cfx 访问与 PTW 迁移

**模块**：linux
**项目里程碑**：M20
**依赖**：W2（QEMU 实现稳定）；M16/M17 收口后派发
**可并行分片**：否（linux 内核写者）
**预估**：4–8 h
**档位**：大改（内核）
**状态**：待开始

## 背景

执行 `m20-spec-001` 已决口径：cfx 寄存器/原因/PTWFAULT/PTWFAIL/UART32/33、中断删除、每 cfx 五种原因。Linux 需要能读 `cfx_ptw cg8 rc4`（仅 smon 通过 delegation；hmon hypv 直读），并适配新编号。

## 范围

- `components/linux/patches/**` 的 `arch/dadao`：cfx 访问常量、cause 解码、PTW 故障、UART32/33、time=62、hart/power 变更；
- SEE/SBI 映射与内核头/uapi；相关 Linux 探针/单测；changelog/补丁序列。

## 验收

1. 内核使用新 cg/编号/原因；旧编号/旧名称残留 0；`cfx_ptw cg8 rc4` 只在允许的 monitor 路径读取。
2. `check-linux-k0/k1/k2/k5/k6`（按范围）真 rc；`check-patch-tree` linux 段 0 problem；K6/LTP 代表例不回归。
3. PTW 故障按 `PTWFAULT` + `cfx_ptw cg8 rc4` 解码；不新增专用 PTWFAULT/PTWFAIL 用例。
4. 至少一条可达 FAIL；证据落运行期证据目录内 `run.sh`。

## 约束

独立 worktree（分支 = `m20-linux-001`）；不提交 git；不改 `spec/`、契约、qemu/gem5/RTL/LLVM；组件补丁按 `docs/Process-01` 重导；内核优先走通用路径，DADAO 特有只做 arch 适配。

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
