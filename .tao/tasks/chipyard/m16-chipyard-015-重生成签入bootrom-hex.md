# m16-chipyard-015: 重生成签入的 `bootrom.tiny.hex`（跟随 `m15-testcases-021`）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m15-testcases-021`（伪指令收口，Tiny bootrom md5 `51430087…` → `a5d78816…`）；`m16-chipyard-008`（释放 chipyard 写者）
**可并行分片**：否（改组件补丁集）
**预估**：1 h
**档位**：小改
**状态**：待验收

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

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

**范围**：签入 hex 补丁（组件源树重生成 → amend → `make_patch` 重导）、`components/chipyard/README.md` 的 BootROM 段、`components/chipyard/changelog.md` 的 M16 条目、运行期证据目录的 `run.sh`。逐行读 diff 并逐项比对真实输出；期望值取自 `spec/Kaiwu §6.1/§6.2` 布局与 m15-021 的运行期产物（`make build-bootrom`），不从签入 hex 反推。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 证据脚本 E4 用 QEMU **stdout** 比对 ⇒ 假红（QEMU 的 semihosting 输出落 stderr，stdout 只有 monitor banner 63 B） | ✅已修 | 改比 `qemu.err`，注释写明落点 | E4 `rc=0`，sim/qemu 各 1136 B 逐字节相同；默认模式 15/15 |
| F2 注入脚本翻补丁字节时误取注释行 `+# ` ⇒ `int('# ')` 异常、G6 假红 | ✅已修 | 跳过 `+#`/`+@` 行，只翻数据行 | `flipped 4c -> 4d`，G6 解码 `95876ef5…` ≠ 目标；`--inject` 23/23 |
| F3 TLROM 反解初版按「逆序 + 字内大端」⇒ md5 `79628e6d…` 不匹配 | ✅已修 | 实测 firtool 为「末字在前 + 字内小端」，改用 `to_bytes(8,"little")` | D1 反解镜像 md5 `a5d78816…` |
| F4 README 的 BootROM bullet 重复写了 `.classpath_cache` 坑（下一行已有） | ✅已修 | 删掉新增的重复句 | README 该条只剩 md5/power 292 B 的新事实 |
| F5 未对**旧**生成物逐文件 diff（旧 `generated-src` 已删） | ❌不修（附理由） | 无 | hex 只经 `resourceGenerators` 变成 ROM init（`BootROM.scala:84` 读 classpath 资源、`TLROM` 常量）；因此以「TLROM 反解逐字节 == 镜像」+「Tiny 代表例行为一致」代替 |

判决：F1–F4 已修复验，F5 附结构性理由不修；状态 → `待验收`。

### 第 1 轮 reviewer 验收

**重跑（我自己的执行）**：运行期证据目录内 `run.sh` 默认模式 `PASS=15 FAIL=0`、`EXIT=0`；关键行 `[A1] patch -> image md5 = a5d78816a95469766639fa658b647ef3`、`[E4] cmp sim stdout vs qemu stderr: rc=0 (sim=1136 B, qemu=1136 B)`、`[F1] check_patch_tree rc=0: 0 problem line(s); chipyard: 25 patch(es)`。
**独立解析（不复用脚本）**：自写解析器抽签入补丁新文件体 → 64 KiB 解码 md5 = `a5d78816a95469766639fa658b647ef3`（= `tests/arch/hmon/expected.yaml:46` = 运行期 `bootrom_tiny.bin` md5），文本与运行期 hex `cmp` rc=0（文本 md5 `9334a87e…`）。
**段长度**：old→new 差异字节 275 个全在 power 段（offset ≤340）；power 内容 341→289 B（4 B 对齐即 344→292，与 `m15-testcases-021` 的「344→292」一致）；hmon 段（偏移 57344 起）与中段 old/new 逐字节相同、表项 48 B 对齐（镜像末 57392）⇒ 跟随 m15-021、非误改。
**判别例读了新 hex**：sim 二进制 md5 `25c1d3f4…`，含新镜像独有 16 B 模式、不含旧镜像同位模式；jar 与 sim 重建时间均晚于 hex。
**可达 FAIL（我独立注入）**：签入补丁 `cp` 备份（md5 `bb764434…`）→ 换回 `HEAD^` 旧字节（解码 `51430087…`）→ 重跑同一脚本 `FAIL=3`（A1/A2/F1）、`EXIT=1`；`cp` 还原 md5 相等、重跑 `PASS=15 FAIL=0`、`EXIT=0`。
**门控**：`check-patch-tree` rc=0（444 OK、chipyard 25、0 problem）、`check-index-blobs` rc=0、`check-component-changelog` rc=0；`make_patch chipyard` 连跑两次均 `0 written, 25 unchanged`、树干净。
**范围**：`git show --name-only HEAD` = 4 文件；内层补丁仅 `new file` 该 hex 资源，未动 RTL。
**amend 判定（不影响合入）**：共享组件源树 `HEAD=9b80759`，其 tree == `expected_tree(base+新补丁集+gitlink)`（实测 match=True）；主工作树（master、旧补丁集）跑 `apply_series --component chipyard` 实测 rc=1「refusing to apply」且源树 HEAD/status 未变 ⇒ 合入前只是**只读安全失败**，`merge --squash` 不经过 apply-series；合入后补丁集=新集 ⇒ tree 匹配 ⇒ 打印 skipped 幂等绿。建议合入后主树复跑 `apply_series --component chipyard` 确认 skipped。
**判决：Accepted**（写入后复跑 `check-knowledge-refs` rc=0）

## 完成区

**测试结果**：一键证据脚本（运行期证据目录内 `run.sh`）默认模式 `PASS=15 FAIL=0`、`--inject` `PASS=23 FAIL=0`，两者 `EXIT=0`。

**修改文件**：① `components/chipyard/patches/generators/dadao-wuming/src/main/resources/dadao/bootrom/bootrom.tiny.hex.patch`（**唯一**重导出的补丁，其余 24 份 `unchanged`）；② `components/chipyard/README.md`；③ `components/chipyard/changelog.md`；④ 本任务书。组件源树 `git status --porcelain` 空、`HEAD=9b80759`（base `0acc1e1` + 1）。

**验收结果**：
- 字节一致：`make build-bootrom` rc=0 ⇒ `bootrom_tiny.bin` md5 **`a5d78816a95469766639fa658b647ef3`**、`bootrom.tiny.hex` 文本 md5 `9334a87e05340044ab3ee2dd665591d2`；签入补丁独立解析解码 md5 同值（65 536 B），与运行期 hex `cmp` rc=0。
- 资源解码：`sbt wuming/Compile/resources` rc=0 ⇒ `resourceGenerators` 产出的 `bootrom.tiny.img` md5 **`a5d78816…`**。
- 仿真不回归：重 elaborate 的 `gen-collateral/TLROM.sv` 反解镜像 md5 `a5d78816…`；`semihost_smoke.elf` 在 chipyard rc=0、QEMU `kaiwu-tiny` rc=0，semihosting 输出 **1136 B 逐字节相同**；sim 重建 rc=0（`make verilog` + `make`，`JOBS=32`，`.conda-env`）⇒ 新 md5 `25c1d3f4b84816c2b42e1ebc34f17ab7`。
- 门控：`check_patch_tree` rc=0（444 patches OK；chipyard 25 份 0 问题）、`check_index_blobs` rc=0、`check_component_changelog` rc=0；`check_patch_tree --source-state` chipyard OK（count=1、clean）。
- 可达 FAIL（2 路，`cp`+md5 还原）：① 源树 hex 改回旧字节 ⇒ 解码 md5 `51430087…`、与运行期 hex `cmp` rc=1；② 签入补丁翻 1 字节（4c→4d）⇒ 解码 `95876ef5…`；还原后源树 hex `9334a87e…`、补丁 `bb764434…`、解码回 `a5d78816…`。

**新发现/坑**：① QEMU 的 semihosting 输出落 **stderr**（`-nographic` 的 stdout 只有 monitor banner），跨平台逐字节比对必须取 stderr；② firtool 的 ROM 字面量是**末字在前 + 字内小端**，反解按「逆序 + 大端」必错（`79628e6d…`）；③ 只换 hex 资源不会让 `.classpath_cache/chipyard.jar` 失效（删 jar + `generated-src/<cfg>` 后才进新固件，旧坑自证）。

**遗留问题**：① 共享组件源树已 amend 到 `9b80759`（base+1，内容 = 本分支补丁集）⇒ 合入前主工作树的 `apply-series` 会因 HEAD 内容 ≠ 其旧补丁集而拒绝，需先合入本分支；② sim 二进制已重建（`25c1d3f4…`，只 ROM 常量变），MEMORY 的 sim md5 基线需主会话更新；③ 旧生成物未逐文件 diff（F5）。
