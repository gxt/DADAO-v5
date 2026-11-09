# GEM5-032t: 定位 `math_test` 238→0 的根因（B7 注销前置）

**模块**：gem5
**项目里程碑**：M11
**依赖**：`INTEG-059t`（已验证，记录了「现引擎 0 errors」）
**可并行分片**：否（单引擎重建/对比，单写者）
**状态**：已验证

## 背景（事实）

- `GEM5-015t`（2026-11-04）：`picolibc math_test` 在 gem5 FS 上 **238/76404 errors**（QEMU 0 errors），归因 **B7 浮点数值差异**，登记为已知 BLOCKED（`PICOLIBC_KNOWN_BLOCKED`）。
- `INTEG-058t`（2026-11-06 20:01，`3de11cac`）：**重写 `components/gem5/patches/src/arch/dadao/exec/b7.cc.patch`（137 行）** + `b7.hh`，即 FP 执行单元（含 `convert_f2i` 六档舍入迁移）。
- `INTEG-059t`（2026-11-09）：reviewer 亲跑 `math_test` ⇒ QEMU/gem5 **均 0 errors**（`Tested 76404 functions, 0 errors`），`run_parity` 报 `blocked masquerade`（登记与现状矛盾）。

## 目标

**确认 238→0 的根因**，为「缺陷关闭式重登记」提供依据（不是就地改写 BLOCKED）。

1. **候选根因**：`INTEG-058t` 的 `b7.cc` 重写（FP 执行 / 六档舍入）。请用证据确认或排除。
2. **验证方式（二选一或都做）**：
   - **A. 二进制对比**：分别用 `3de11cac^` 与 `3de11cac` 的 gem5 补丁集构建 gem5（`build-gem5`，两次），用**同一个** `math_test` ELF/argv 各跑一次，比对 errors 数。
   - **B. 单元/语义对比**：跑 `check-b7`（`tools/gem5/check_b7.py`）与 `b7_ref.py` 在 `3de11cac^`/`3de11cac` 两个补丁集下的结果；对 `b7.cc` 的语义 diff 逐处说明「旧实现错在哪、新实现如何修正」。
3. **排除测试条件变化**：确认两次跑的 ELF/argv/镜像/预算一致（若不一致，结论作废）。
4. **给出结论**：
   - 若是真修复 ⇒ 写「可注销 `PICOLIBC_KNOWN_BLOCKED`」的证据与建议（含根因 commit/文件/语义点）
   - 若不是 ⇒ 写明「测试条件变化」或其它原因

## 验收标准

1. 根因明确到 **commit + 文件 + 语义点**（如「`b7.cc` 的 `convert_f2i` 舍入方向」）
2. 至少 **2 个数据点**（修复前 / 修复后）用同一 ELF 跑出的 errors 数对比，命令与输出入完成区
3. 若用 A 方式：两次 `build-gem5` 的二进制 md5 不同、`check-gem5-decode`/`check-b7` 均 rc=0
4. 若用 B 方式：`check-b7` 在两个补丁集下各跑一次，结果差异逐条解释
5. `make check`（L1）rc=0（并发红须核实）
6. 一键证据脚本（运行期证据目录下的 `run.sh`，含可达 FAIL 注入）
7. 完成区 ≤30 行、无运行期路径

## 非范围

- **不改** `PICOLIBC_KNOWN_BLOCKED`（注销由后续任务/architect 按结论执行）
- 不改 `math_test` 用例与期望
- 不改 spec/contracts

## 说明

- 重建 gem5 会占用 `.work/source/gem5` 与 `.work/build/gem5`，属**组件单写者**；开工前确认无其它 gem5 任务在跑。
- 长构建先申报耗时，落 PID/日志/`*_EXIT=$rc`。
- 结论必须区分「真修复」与「测试没跑到」——后者不算注销依据。

## 完成区

**测试结果**：一键证据 `run.sh` 9/9 绿（rc=0）；`--inject` 3 项预期 FAIL（rc=3）。`check-b7`/`check-gem5-decode` 新旧补丁集各一次（旧 rc=1，新 rc=0）。L1 3 红均非本任务（见遗留）。
**修改文件**：本任务书。代码/证据未入库（运行期取证目录）。
**验收结果**：
1. 数据点（同 argv / Tiny 镜像 / `math_test` 源码）：`3de11cac^` 补丁集引擎 + 11-05 旧 ELF（md5 `bd3571b8…`）→ `238 errors` rc=1；`12b0064c` 补丁集引擎 + 现 ELF（md5 `db796237…`）→ `0 errors` rc=0。
2. 同 ELF 隔离：现 ELF 仅 24 条 f2i 的 immu6 `0x04→0x01`(RNE) → `235 errors` rc=1；失败行是 238 的**严格子集**（差 3 行 = `copysignf:40/46`、`fabsf:304` 的 NaN payload）。
3. 交叉组合均 ILLI rc=248（旧 ELF×现引擎 / 现 ELF×旧引擎）⇒ 跨编码变更无法"同一 ELF"直比，第 2 条即合法隔离。
4. 两次 `build-gem5` 二进制 md5 不同（`9f497d7d…` vs `67e4f7c6…`）；gem5 内嵌编译时间 ⇒ md5 每次重建即变，身份按补丁集/树哈希。
5. `check-b7` 旧补丁集 rc=1（1045 条 oracle mismatch：旧实现把 immu6 当 count 并写多寄存器），新 rc=0；`check-gem5-decode` 旧 drift rc=1（旧表配新 contract，预期），新 rc=0。
**结论**：
- Q1 是 058t 引起：证据 1/2 + `git log`（11-05 起触及 `components/llvm-project/patches` 的只有 `3de11cac`）⇒ 两 ELF 工具链差异只有 058t；只改 058t 重定义的 f2i 字段即 0→235。
- Q2 真修复（非测试条件变化）：旧引擎对 C 强制转换用 `rf0[33:32]` 动态舍入（默认 RNE）而非 RTZ，违反 `contract-fp` / SimRISC-07；用例、argv、镜像、预算未变。
- Q3 根因 = commit `3de11cac`；文件 `b7.cc.patch`（`runConvertF2I` 改 `modeFromCode(immu6)` 单寄存器）、`DADAOCodeGen.td.patch`+`DADAOISelDAGToDAG.cpp.patch`（C 转换发 `0x04` RTZ）、`fp_soft.cc.patch`（RNA/溢出）；语义点 = **f2i 舍入方向**。
- 建议：**可注销 `PICOLIBC_KNOWN_BLOCKED`**（缺陷关闭式）；picolibc 段重生成、README/`GEM5-015t` 同步由后续任务执行。
**新发现/坑**：跨编码变更（immu6 语义重定义）不能用同一 ELF 跨新旧引擎比较（双方 ILLI），正确隔离 = 同 ELF 只改被变更字段；gem5 二进制内嵌编译时间，md5 不能作"同一二进制"证据；058t 同时改 decode 表 ⇒ 旧补丁集配新 contract 必 drift（预期）；旧补丁集窗口内其它会话的 L1 会看到该 drift（gate lock 曾见 stale `check` 持有者）。
**遗留问题**：
- L1 3 红，均已核实非本任务：① `check-patch-tree` chipyard 断言⑨（主工作树 `12b0064c` 同红复现）；② `check-milestones-fresh` R1（本 worktree 分支台账仍"待开始"，master 已移"进行中"；任务禁改 milestones，合并后自消）；③ `check-temp-dirs`（他任务陈旧目录，只报告）。
- `sync-node-repo` 未执行：两节点 13 项脏文件是 `m12-infra-003` 的 submodule 补丁基建 WIP（主控机无对应文件），`reset --hard`+`clean -fd` 会销毁其 WIP，留待该任务收口后由主会话同步。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 首轮 0-err 用的是重建前二进制（md5 `d51a…`），与最终树可能不一致 | ✅已修 | 重建后（`67e4…`/`5d019b23…`）重跑 math_test | 两次均 `0 errors` rc=0 |
| `gem5_run` 内 `RUN_RC=$?` 使调用方 `$?` 恒 0，检查形同虚设 | ✅已修 | 调用方改 `rc=$RUN_RC` | `run.sh` 9/9 绿；`--inject` 3 红 rc=3 |
| `patch_f2i.py` 硬编码工具链绝对路径 | ✅已修 | 由 repo root 推导 `.dadao/cross-toolchain/bin` | 重跑 24 字节/24 条指令校验通过 |
| 仅凭 errors 数不能排除"LLVM 其它改动" | ✅已修 | 查 git log 并只翻转 058t 重定义的字段 | 唯一 LLVM patch commit = `3de11cac`；0→235 |
| 3 例 NaN payload（copysignf/fabsf）机制未深挖 | ⏸延后 | — | 属 238−235 的 3 行，与 f2i 无关；新配置 0 errors，不影响注销 |
| 共享 `.work/source/gem5` 上切旧补丁集期间，其它会话 L1 可能误红 | ✅已披露 | 完成区"新发现/坑"+ 核实 L1 红非本任务 | 主工作树 `12b0064c` 复现 chipyard 红；milestones 红由分支基线解释 |

#### 收尾（architect，2026-11-09 15:44）

- 判决：engineer 自审 + 证据链闭合（无 reviewer 轮；本任务为**只读定位**，不改源码，结论由 architect 复核后接受）。
- **根因确认**：`INTEG-058t`（`3de11cac`）的 `b7.cc` `runConvertF2I` 由「count + rf0 动态模式」改为 `modeFromCode(immu6)`，C 强制转换改发 `0x04`(RTZ) ⇒ 违反 `contract-fp`/SimRISC-07 的旧实现被修正。
- **决定性隔离**：同一现 ELF 只把 24 条 f2i 的 immu6 从 `0x04` 翻回 `0x01`(RNE) ⇒ **235 errors**，失败行是 238 的严格子集。
- **B7 注销**：结论为「可注销（缺陷关闭式）」；**待用户裁定**后另立执行任务（删除 `PICOLIBC_KNOWN_BLOCKED` + picolibc 段现场重生成 + README/`GEM5-015t` 口径同步）。
- `sync-node-repo` 未执行（节点 13 项脏 = `m12-infra-003` WIP，待其收口后同步）。
- 坑：跨编码变更不能用同一 ELF 跨新旧引擎直比（双方 ILLI）；gem5 二进制 md5 内嵌编译时间，不能作「同一二进制」证据。
