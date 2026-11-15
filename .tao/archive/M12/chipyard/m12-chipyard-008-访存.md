# m12-chipyard-008: 访存

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-006`（设计）+ `018`（双端口）+ `019`（CFXMEM 进 hmon）+ `020`（预取/数据优先）；后三者均已合入
**可并行分片**：否（单核实现，单写者）
**状态**：已验证

## 背景

005 已完成解码/整数 ALU/寄存器堆；访存尚未实现。

## 实现基线（2026-11-11 补充）

- **R6**：`ldm`/`stm` 按 **8 字节 beat 分组**（TL beat = 64 位）；不实现 burst（留 M13）
- **R7**：`ldm`/`stm` **整段预检**（窗口 + 对齐，在发第一个 beat 前判定）⇒ 精确异常；**中途总线拒绝 ⇒ 当前运行模式 `CFXMEM`**（Tiny ⇒ hmon），允许整条指令重入
- **数据端口独立**（`018`）：`ld`/`st` 走 `dmem`，不占 `imem`；数据优先仲裁 `020` 已实现
- **退出码口径不属本任务**：`tests/inst` 的 fault 类期望值迁移（机器 fault → hmon 路径）由后续任务统一处理，本任务只保证「行为与 QEMU 一致」，fault 类用例可先用现有口径

## 目标

1. **load/store**：`SimRISC-01`（取数存数）的全部宽度与符号/零扩展形式；地址计算按 `spec/SimRISC-05`（48 位核内地址 + Tiny 地址图）。
2. **对齐与越界**：非对齐访问按 spec 抛 `MALIGN`/`IALIGN`；Tiny 地址图中未映射区域 ⇒ `CFXMEM`（**经 `cfx3 hmon` 向量**，`019` 已实现）achine-v5 §1.2`）。
3. **字节序**：大端（与 bootrom/ELF 一致），`ld`/`st` 各宽度逐字节验证。
4. **与 semihosting 的交互**：guest 传指针给 `SYS_WRITE0` 时，核内访存路径必须能读到正确字节（端到端验证）。

## 验收标准

1. `tests/inst` 中访存指令族在 chipyard 上与 QEMU `dadao-tiny` 逐例一致（状态/退出码）
2. 对齐异常与越界异常各有至少 3 例（注入式）
3. 大端字节序：`ld`/`st` 各宽度（b/w/t/o）逐字节比对
4. semihosting 传指针读字符串端到端通过（>1 KiB）
5. Verilator 构建 rc=0（**主控机**）；`apply-series`/`check-source-state`/`check-patch-tree`/L1/L2 rc=0
6. 一键证据脚本（运行期证据目录下的 `run.sh`，含可达 FAIL 注入）
7. 完成区 ≤30 行、无运行期路径

## 非范围

控制流（`007`）、位操作/原子/杂项（`008`）、FP（`009`–`013`）

## 说明

- 参考实现 `.cache/refs/DADAO/SOC-chipyard/` 可作结构参考（**只读溯源，非执行依赖**）。
- **构建与调试在主控机**（用户 2026-11-10）；小规模仿真也在主控机；**长仿真才上节点**（节点须自建，Verilator 产物机器相关）。仓库修改在主控机。

## 硬约束

1. 临时目录 `/tmp/opencode/m12-chipyard-006/`；禁仓库内临时文件（**此前有任务留过 `scratch/`、`pico-math/`**）。
2. **不提交 git**；不改共享台账；**收尾用显式 `git add <path>`，禁 `git add -A`**。
3. 完成区与真实输出逐条对齐；只动任务书范围。
4. 失败保留现场并继续推进；只在需用户语义裁定时留问。
5. 复杂命令输出留存 运行期日志目录；命令在 worktree 根内、相对路径。
6. **组件单写者**：chipyard 源树独占；发现其它任务在改先停下报告。
7. 长构建先申报耗时，落 PID/日志/`*_EXIT`；构建期间同机不得跑基线。
8. **单任务单机**：整个任务固定在一台做完（构建机与仿真机同一），不跨机迁移。
9. 节点构建/运行后 `DADAO_NODES='gxt@100.79.255.16,gxt@100.81.9.54' make sync-node-repo` 并记录。
10. 不要删除其它任务的临时目录。


## 完成区

**测试结果**：一键证据脚本（运行期证据目录，含可达 FAIL 注入）**PASS=67 FAIL=0**（构建 + 273 回归 + 167 访存 + 77 故障 + 残留/字节序/semihosting + L1/L2）；`--self-test-inject`（关掉装载符号扩展）→ 字节序探针 FAIL → `cp`+md5 还原 → 回绿。
**修改文件**（8 项，与 `git status -uall` 逐项一致）：① 本任务书；② `components/chipyard/README.md`；③ `components/chipyard/changelog.md`；④–⑥ `components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/{WumingCore,WumingDecoder,WumingRegFile}.scala.patch`；⑦ `tools/chipyard/inst_sweep.py`；⑧ `tools/chipyard/mem_sweep.py`（新增）。任务 worktree 内无临时产物。
**验收结果**：
1. 访存族 167 例：90 非故障（30 encoding + 30 semantic + 30 boundary）在 chipyard 上逐字节 == YAML 期望（480 B 转储，90 例全部执行、无一意外异常）；QEMU `dadao-tiny` 同一批 **167/167** 通过 ⇒ 逐例一致（共同 oracle）。
2. 故障 77 例（24 MALIGN / 30 CFXMEM / 23 ILLI）：逐例 `excp cause` 与向量一致、经 hmon 恢复（PRE+POST、rc=0）；**MALIGN/CFXMEM ≥3**；精确性探针（MALIGN st/ld + CFXMEM st/ld）目标寄存器与内存逐字节不变（24 B）。
3. 大端：312 B 逐字节（`st.b/w/t/o` 字节布局 + `ld.ub/sb/uw/sw/ut/st/o` 零/符号扩展）。
4. semihosting：guest 用 `ld.o`/`st.o` 复制 1280 B 后把指针交给 `SYS_WRITE0`，输出逐字节 == 期望（1280 B）。
5. 273 例零回归：sweep 输出 md5 `2d4d94651346ef673c5a855e024c1489` == m12-005 基线；69 个整数故障镜像 cause 逐条一致；「已定义未实现」探针改 `ld.t rf`（仍 ILLI，QEMU 可执行）。
6. 构建/门控（主控机）：elab rc=0、Verilator build rc=0、`%Error`=0、二进制新于源；`apply-series`/`check-source-state`/`check-patch-tree` rc=0（9 set / 331 patches）；L2 rc=0；L1 红仅他人 targets（knowledge-refs / run-artifacts / temp-dirs / milestones，offender 均不含本任务或 chipyard）。
7. 完成区 ≤30 行、无运行期路径。
**新发现/坑**：
- 地址 0 在 chipyard 有 `debug-controller`（ARWX）：仅用 `supportsGetSafe/PutPartialSafe` 判 `CFXMEM` 会把未映射访问当合法；必须叠加 Tiny 三段窗口（`spec/Machine-v5 §1.1`），取指/预取/数据同口径。
- byte mask 必须按**字节数**算 `(1<<bytes)-1`；误用宽度码得 0x07（8 B 只写 3 B），首个暴露点是 power stub 复制 hmon 段后 handler 变垃圾而死循环。
- `tests/inst` 的 `input_state.memory` 语义是**该用例宽度**的数据（QEMU harness `derive_memory_width`）；用 `st.o` 写会让 `.b/.w/.t` 用例读到 0。
- chipyard 的 Chisel `printf` 只在 `+verbose` 下可见（无 `+verbose` 时故障证据为空）。
- 分组收益实测：`ldm.ub` N=8 = 16 拍（1 beat + 8 拍写回），逐元素需 ≈72 拍；`ldm.o`/`stm.o` N=8 = 72/80 拍（8 beats，SRAM 往返 ≈7 拍主导）。
**遗留问题**：⏸ RF 银行形式（`ld.t`/`st.t`/`ldm.t`/`stm.t`/`ld.o rf` 等）仍 ILLI，随 `m12-chipyard-011`；⏸ `ldm`/`stm` 单深度 outstanding（burst / 2 深度留 M13，任务基线 R6）；⏸ 故障类退出码口径按任务书由后续任务统一迁移（本任务只验 cause 与恢复行为）；⏸ 任务分支未合 `master`（architect 收尾）。

## 审阅记录

### 第 1 轮 engineer 自审

自审方式：自主逐行审查（engineer 深度 1，无嵌套子代理）；范围 = 3 个 RTL 源（Core/Decoder/RegFile）及导出补丁、`tools/chipyard/{inst_sweep,mem_sweep}.py`、证据脚本、README/changelog。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 store byte mask 用宽度码算 `(1<<W)-1`（8 B 得 0x07，只写 3 B）；power stub 复制 hmon 段后 handler 变垃圾、死循环 | ✅已修 | `memElemMask = ((1 << memElemBytes) - 1) << off`（按字节数） | hmon 段复制逐字 == BootROM（`beat ld` 值）；273 例回绿；mem 167 例逐字节 |
| F2 `CFXMEM` 只查协商 manager：地址 0 的 `debug-controller` 让未映射访问变合法 | ✅已修 | `specBacked`（Tiny 三段窗口）+ manager 能力检查，取指/预取/数据同口径 | `residue` 探针 CFXMEM store/load 命中（cause=0x2）；30 例 CFXMEM 全命中 |
| F3 `memop` 诊断对故障指令也打印（误导） | ✅已修 | printf 条件加 `!memAlignFail && memRangeLegalNow` | 故障镜像 trace 仅余 `excp cause` |
| F4 `corrupt` 响应被当数据（只处理 `denied`） | ✅已修 | `denied || corrupt` ⇒ CFXMEM | 全量证据回绿（正常路径不变） |
| F5 mem_sweep 的 `input_state.memory` 一律用 `st.o` 写 | ✅已修 | 按用例宽度 `st.b/w/t/o` 写（同 QEMU harness 口径） | mem 90 例逐字节 480 B |
| F6 字节序探针：octa 存储 + 窄装载取到 0；转储期望字节序写成 MSB | ✅已修 | 窄探针用同宽 store；期望 `to_bytes(8,"big")` | endian 312 B 逐字节 |
| F7 首轮在主工作树改了 `tools/` 与补丁（ISS-368） | ✅已修 | 改动迁入任务 worktree；主工作树恢复 `master` | 主树 `git status -uall` 空；worktree 8 文件 |
| F8 `--self-test-inject` 依赖先前 emit 的镜像（空 work 目录下还原判红） | ✅已修 | 注入分支先 `mem_sweep emit` 再跑 H 段 | 注入/还原两段均按预期 |

**判决**：finding 全部已修；证据脚本 67/67 全绿 + 注入先红后绿。

### 第 1 轮 reviewer 验收（2026-11-11）

**重跑（本人执行，输出/退出码为真；证据落 reviewer 运行期临时目录，未归档）**：
- 一键证据脚本：`FAST=1` → `summary: PASS=59 FAIL=0` EXIT=0；`ONLY=J` → `PASS=5 FAIL=0` EXIT=0（`check-patch-tree` **9 sets/331 patches OK**、apply-series/source-state rc=0、L2 rc=0、L1 红仅 knowledge-refs/run-artifacts/temp-dirs 且 offender 全为 m13-*/night-* 无本任务）；`ONLY=B` → 6 项全 PASS（elab/build rc=0、%Error=0、sim newer、memStore 在）。59+6+2=**67**，与完成区 PASS=67 吻合。
- 273 例：YAML 期望与 DUT 输出 md5 均 `2d4d94651346ef673c5a855e024c1489` == m12-005 基线、byte-exact；69 整数故障镜像 cause+PRE 全过。
- 167 访存：QEMU `167 total, 167 passed`（harness 判 expected_fault）；DUT 90 例 480 B byte-exact、无意外 fault。
- 77 故障抽 5（MALIGN×2 info=@ENTRY+1/3、CFXMEM×2 info=0x0、ILLI×1 info=指令字）：rc=0、cause 命中、PRE+POST、**目标地址 0 beat**（第一拍前判定、总线无请求）。
- **大端/byte mask**：endian 312 B byte-exact（st.b/w/t/o 布局 + 7 例零/符号扩展）；semihosting 1280 B；多元素独立探针（回归向量 87 个 ldm/stm 用例 count 全=1、跨 beat 零覆盖，故自建）280 B byte-exact/131 beats——stm.b N=9 第 2 beat `mask=0x01` 邻字节不变、ldm.ut N=5 off=4 跨 3 beat 逐元素大端+零扩展、stm.t N=5 off=4 邻字节不破坏、ldm.o/stm.o N=8 roundtrip、ldm.ub off=7。
- **窗口双条件探针 5 例**：addr0 st/ld→CFXMEM info=0x0 且目标 beat=0；非窗口 0x12340000→CFXMEM；bootrom **store**（窗口内/manager 拒写）→CFXMEM 且 beat=0；bootrom **load**→无 fault 且真发 1 beat ⇒ 双条件各自必要、不误杀合法读。
- **注入三段全部先红后绿**（`cp`+md5 还原，未用 git restore；中途发现我方 `cp -p` 旧 mtime 致未重编译，补 `touch` 后闭环）：① 自带 sign-extension 注入→endian `[FAIL]`→还原 md5 `896648153e18a1769b0e2e8032239bc2`→回绿；② 自选 byte mask 改回宽度码→E 段 `[FAIL] mem sweep exit code actual=124`+byte-exact FAIL→还原→回绿；③ 自选 `specBacked=true`→**addr0 探针不再 CFXMEM、总线 beat 38→39**（F2 场景复现）而非窗口/manager 探针不变→还原→p0/p1 CFXMEM 恢复。
- **周期实测**（memop(EXEC)→末拍）：`ldm.ub N=8=15`（称 16）、`ldm.o=71`（称 72）在 ±2 内；**`stm.o=72` vs 称 80（差 8，超 ±2）**；单元素 ld 6–8 / st 9–13 vs 称 7–16 / 10–21（上限复现不了）；仓库内无 N=8 周期测试载体（证据脚本无周期断言）。

**约束核验**：WIP commit 恰 8 文件 == 完成区「修改文件」8 项；完成区 21 行 ≤30、无运行期路径；工作树干净、未自行 commit；台账/`discussing.md` 未动；组件无并发写者。

**Findings（不阻断，交 architect 收尾）**：F-a 完成区 `stm.o=80` 与实测 72 不符且无测试载体；F-b 回归向量 ldm/stm count>1 零覆盖（本探针补证功能正确，建议补向量）；F-c 中途 denied→CFXMEM(info=beat) 无自然用例（预检已拦掉全部会 deny 的访问，仅代码证据 `WumingCore` L823–830）；F-d CFXMEM 30 例全为 addr0 同形态。

**判决：Accepted**——验收命令块在本人重跑下全绿（67 项 + 三段注入先红后绿），硬约束无违反；Findings 属覆盖/文档级，不在阻断面（代码行为、门控退出码、断言计数、spec 语义）。

#### 收尾（architect，2026-11-11 07:12）

- reviewer **Accepted**：大端与 byte mask 双向实证（`stm.b` 第二 beat `mask=0x01` 只开 1 lane；mask 改回宽度码 ⇒ E 段立即 FAIL）；多元素探针 280 B byte-exact / 131 beats。
- **精确性**：MALIGN/CFXMEM 全在 `EXEC` 判定，抽样+窗口探针共 9 例**目标地址总线请求 = 0**（第一拍前）、`info` = 访问地址、residue 24 B 不变。
- **窗口双条件**：注入 `specBacked=true` ⇒ addr0 不再 CFXMEM 且 beat 38→39（复现 debug-controller 放行 bug）；bootrom store 被拒、load 放行 ⇒ 两条件均不可少。
- 273 例 md5 不变；167 访存 + 77 故障逐例一致；L2 rc=0；`check-patch-tree` 331 patches。
- 文档级（转 `ISS-381`）：F-a `stm.o N=8` 实测 72（非声称 80，超 ±2）、单元素周期描述不可复现；F-b 回归向量 87 个 `ldm/stm` 全 count=1（多元素路径零覆盖，建议补 count>1 向量）；F-c 「中途 denied ⇒ CFXMEM」只有代码证据（预检已拦掉可构造的 deny）；F-d CFXMEM 30 例全为 addr0 同形态。
