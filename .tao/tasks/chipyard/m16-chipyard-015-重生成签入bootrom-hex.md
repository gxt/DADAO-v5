# m16-chipyard-015: 重生成签入的 `bootrom.tiny.hex`（跟随 `m15-testcases-021`）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m15-testcases-021`（伪指令收口，Tiny bootrom md5 `51430087…` → `a5d78816…`）；`m16-chipyard-008`（释放 chipyard 写者）
**可并行分片**：否（改组件补丁集）
**预估**：1 h
**档位**：小改
**状态**：待开始

## 背景（缺口，由 `m15-testcases-021` 披露）

`components/chipyard` 的补丁集里签入了一个**文本 hex** 形式的 Tiny BootROM：
`generators/dadao-wuming/src/main/resources/dadao/bootrom/bootrom.tiny.hex`
（`build.sbt` 的 `resourceGenerators` 在构建时解码成 `/dadao/bootrom/bootrom.tiny.img`；见 `components/chipyard/README.md` 的 BootROM 段，`m12-chipyard-028` 起由 `tools/testcases/arch/build_tiny_bootrom.py` 重生成）。

`m15-testcases-021` 把 `power_tiny.S` 的 `LD64` 改成规范伪指令 `set.rd`（同值、同指令数、**编码顺序不同**），Tiny bootrom 的 md5 从 `514300876e…` 变为 `a5d78816…`，`tests/arch/hmon/expected.yaml` 已跟新；但**签入的 hex 仍是旧字节**。

## 目标

1. 用现行工具链重生成 hex 到该资源路径（`build_tiny_bootrom.py` 的 `--hex-out`，输出与运行期 `build-bootrom` 产物一致）；
2. 更新 `components/chipyard/README.md` 的 BootROM 段（新 md5）与 `components/chipyard/changelog.md`（按任务一条）；
3. 确认 `build.sbt` 解码后的 `.img` md5 = 新 bootrom md5。

## 验收（逐条贴真实 rc）

1. **字节一致**：签入 hex 解码后 md5 = `build-bootrom` 运行期产物 md5（现场算，不抄）；
2. **Tiny sim 不回归**：用现有 simulator 跑 Tiny 代表例（如 `check_tiny_hmon` 或 `m12-chipyard-003` 的桩核探针；若 `check_tiny_hmon` 的预存红未修，给基线对照）；`FIRRTL/SV` 不因 hex 变化而改变核逻辑；
3. **补丁树**：`check-patch-tree` chipyard 段 0 问题；`check-component-changelog` rc=0；
4. **可达 FAIL ≥1 路**：把 hex 改回旧字节 ⇒ 上述 md5 一致性断言红（`cp`+md5 还原）。

## 约束

独立 `git worktree`；不提交 git；**只动该 hex + README/changelog**，不改 RTL；术语「寄存器组」；完成区不写具体 `.work/**` 路径。
