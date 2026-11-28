# m19-qemu-002: QEMU 侧 `swym` 的 SBZ/ILLI 功能语义

**模块**：qemu
**项目里程碑**：M19
**依赖**：`m19-spec-001`、`m19-qemu-001`、`m19-testcases-001`
**可并行分片**：否
**预估**：2–4 h
**档位**：小改
**状态**：待开始

## 背景

`m19-spec-001` 定了 `swym N`：`N = immu18[11:0]`，`immu18[17:12]` 为 SBZ、非 0 ⇒ `ILLI`；总时延 `1 + N`。

`m19-qemu-001` 只迁移了几何与装载，**没有**实现这条功能语义：QEMU 的 `trans_swym_oiii_imm` 仍是无条件 NOP，高位非零也照常执行。`m19-testcases-001` 的完整载体因此在 QEMU 上 `rc=12`（4 条 `ILLI` 用例全部落空），其功能子集（去故障例）三平台 88 B 签名逐字节一致。

QEMU 不承担周期（`NOP` 时延保持），但 **SBZ/ILLI 是功能维度**，参考模型必须与 spec 一致，否则三平台一致性没有基线。

## 目标

1. 在 QEMU 的 `swym` 译码/执行路径加入 `immu18[17:12] != 0 ⇒ ILLI`（与被删的 `fence`/`ret` 同类静态判据的风格一致），非法时不产生任何副作用。
2. 保持 `swym N` 合法编码仍为 NOP（QEMU 不做 1+N 时延）。
3. 同步 QEMU 侧解码表/断言（如 `insn.decode` 或 `check_qemu_trans` 的非法用例）与组件 changelog/README。
4. 不引入新补丁文件；只改既有补丁（`target/dadao/insn_trans/*`、必要时 `helper.c`）。

## 验收（逐条贴真实 rc）

1. `make build-qemu` rc=0；`make check-qemu-trans`（或等价）rc=0，含高位非零 ILLI 用例。
2. `m19-testcases-001` 的完整载体（含 4 条故障例）在 QEMU 下 rc=0；签名流与 gem5/chipyard 的 88 B 逐字节一致。
3. **可达 FAIL ≥2 路**：① 去掉 SBZ 检查 ⇒ 4 条故障例全落空、rc≠0；② 把合法 N 也判 ILLI ⇒ 功能例红；均 `cp`+md5 还原回绿。
4. `check-patch-tree` qemu 段 0 problem（须在共享源树同步后）；`check-component-changelog` rc=0。
5. 不改 gem5/chipyard/testcases 资产；版本号未升。

## 约束

独立 `git worktree`；**不提交 git**；只动 `components/qemu/**` 与必要门控；不接板；完成区不写具体 `.work/**` 路径。
