# m20-gem5-005: gem5 cfx 寄存器与异常迁移

**模块**：gem5
**项目里程碑**：M20
**依赖**：W1（`m20-spec-002`/`m20-idl-001`/`m20-llvm-004`）；M16/M17 收口后派发
**可并行分片**：否（gem5 组件写者）
**预估**：4–8 h
**档位**：大改（组件）
**状态**：待开始

## 背景

执行 `m20-spec-001` 已决口径：新 cg4/5/6/7、scratch 2..16、PTWFAULT/PTWACCERR、cfx 编号、UART32/33（cfxha61 异步源）、中断删除、每 cfx 五种原因。

## 范围

- `components/gem5/patches/**` 的 `node_cfx`/`tiny_cfx`/`fs_machine`/PTW/TLB/cause/别名；
- UART32/33 异步源、`cfx_hart` 捕获；PTW `cfx_ptw cg8 rc4`；time/hart/power；
- 相关 gem5 unit/探针、changelog、补丁序列。

## 验收

1. 与 QEMU 同口径；旧 cg/旧名称/旧编号残留 0；不改 QEMU/RTL/Linux。
2. `check-gem5-decode`、`check-patch-tree` gem5 段 0 problem、代表集真 rc；安装根/构建树 md5 一致。
3. PTW 用例按既有 PTW 路径适配为 `PTWFAULT 1<<15` + `cfx_ptw cg8 rc4` ID；不新增专用 PTWFAULT/PTWACCERR 用例。
4. 至少一条可达 FAIL；证据落运行期证据目录内 `run.sh`。

## 约束

独立 worktree（分支 = `m20-gem5-005`）；不提交 git；不改 `spec/`、契约、qemu/RTL/内核/LLVM；组件补丁按 `docs/Process-01` 重导。

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
