# m20-chipyard-002: RTL cfx 寄存器与异常迁移

**模块**：chipyard
**项目里程碑**：M20
**依赖**：W1（`m20-spec-002`/`m20-idl-001`/`m20-llvm-004`）；可与 W2 并行，验收排后
**可并行分片**：否（RTL 组件写者）
**预估**：8–12 h
**档位**：大改（RTL）
**状态**：待开始

## 背景

执行 `m20-spec-001` 已决口径：新 cg4/5/6/7、scratch 2..16、PTWFAULT/PTWACCERR、cfx 编号、UART32/33（cfxha61 异步源）、中断删除、每 cfx 五种原因。

## 范围

- `components/chipyard/patches/**` 的 Gewu/Cfx 寄存器组、decoder、cause 位图、PTW/TLB；
- UART32/33、time=62、uart=61、power、hart；IPI/UART 中断/power 后三项删除；
- `tests/arch` 的 RTL 代表探针、changelog、补丁序列。

## 验收

1. RTL 与 spec/契约一致；旧 cg/旧编号/旧名称残留 0；资源/时序变化有记录。
2. Verilator/`check-arch` RTL 代表集真 rc；`check-patch-tree` chipyard 段 0 problem。
3. PTW 用例按既有 PTW 路径适配为 `PTWFAULT 1<<15` + `cfx_ptw cg8 rc4` ID；不新增专用 PTWFAULT/PTWACCERR 用例。
4. 至少一条可达 FAIL；证据落运行期证据目录内 `run.sh`；RTL 长构建按节点/本地已有流程。

## 约束

独立 worktree（分支 = `m20-chipyard-002`）；不提交 git；不改 `spec/`、契约、qemu/gem5/内核/LLVM；组件补丁按 `docs/Process-01` 重导。

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
