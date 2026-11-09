# m12-chipyard-005: 解码器 + 整数 ALU + 寄存器堆

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-004`（semihosting 已通，可观测输出）
**可并行分片**：否（单核实现，单写者）
**状态**：已验证

## 背景

- `m12-chipyard-002`~`004` 已完成：骨架、Tiny 地址图、bootrom+loadmem、harness semihosting。
- 当前 `WumingCoreStub` 只覆盖 **5 类指令**（`set.zw`/`or.w`/`jump` 等），是为跑通闭环的最小执行器；真核从本任务开始。
- 本任务只做**整数执行的最小可用集**：解码、整数 ALU、寄存器堆；访存/控制流在 `006`，位操作/原子/杂项在 `007`。

## 目标

1. **寄存器堆**：`rd`（64 位）、`ra`/`rb` 双 bank。**`rd0` 恒读 0**（作为目的：`rrrr` 双目的允许其一为 `rd0` 并丢弃该半结果，但不能同时为 `rd0`；其余格式目的为 `rd0` ⇒ ILLI）。**`rb0` = 当前正在执行的指令地址（`IP`，非下一条）**，只读；**作为显式目的 ⇒ ILLI**（`spec/SimRISC-00 §2.2`）。
2. **解码器**：至少覆盖 `orrr`/`orri`/`rrrr` 三种格式与 `SimRISC-04`（64 位数据运算）、`SimRISC-08`（32 位）、`SimRISC-05`（地址运算）中的**算术/逻辑/移位**指令。
   - **合法性**：**保留编码 ⇒ UNDI**、**非法组合 ⇒ ILLI**（按 `contracts/legality_rules.yaml` 的 `excp_undi` / ILLI 规则，不得静默当 NOP）。
3. **整数 ALU**：加/减/与/或/异或/移位/比较；**溢出与进位语义按 `spec/SimRISC-04`**（不套用 RISC-V）。
4. **接入**：替换 `WumingCoreStub` 中对应的 5 类指令桩，保持 bootrom→应用→semihosting 闭环不回归。

## 验收标准

1. `tests/inst` 中**本任务覆盖的指令族**在 chipyard 上逐例与 QEMU `dadao-tiny` 一致（状态/退出码；不比时序）
2. 覆盖的用例数按 `inst_sweep.py list` 子命令现场统计并与报告一致（不写死）
3. `rd0`/`rb0` 的读 0 / 写丢弃有专门断言（含「写 rd0 后再读」）
4. **保留编码 ⇒ UNDI**（`legality_rules.yaml` 的 `excp_undi`）；**非法组合 ⇒ ILLI**（`dst_rd0`/`dst_rb0`/`dst_dual_same`/`encode_sbz`/未实现）；两类各有至少 3 例注入式验证
5. Verilator 构建 rc=0（**主控机**，用户 2026-11-10：chipyard 后续构建/调试在主控机）；有界运行不崩；bootrom→loadmem→semihosting 闭环不回归
6. `make apply-series` / `check-source-state` / `check-patch-tree` / L1 / L2 rc=0
7. 一键证据脚本（运行期证据目录下的 `run.sh`，含可达 FAIL 注入）
8. 完成区 ≤30 行、无运行期路径

## 非范围

- 访存（`006`）、控制流/RAS（`007`）、位操作/原子/杂项（`007`）
- FP（`008`–`012`）
- T0/T1 冒烟（`013`/`014`）
- 不实现 cfx（Tiny 无 cfx；`trap` 仅 semihosting）

## 说明

- 参考实现 `.cache/refs/DADAO/SOC-chipyard/` 的 `wuming_1stage/{dpath,cpath,regfile,consts}.scala` 可作结构参考（**只读溯源，非执行依赖**）。
- **构建与调试在主控机**（用户 2026-11-10）；仓库修改在主控机；若上节点则事后 `make sync-node-repo`。

## 完成区

**测试结果**：一键证据脚本（运行期证据目录下 `run.sh`，未入库）**PASS=49 FAIL=0**（rc=0；C 段改主控机后 48→49：+elab rc +build rc +「二进制非陈旧」−节点可达 −节点同步）；`--self-test-inject` **5/5 注入均 FAIL + `cp`/md5 还原后 PASS**；返工新增的 `sub.uo` 借位用例先打红后回绿（旧 RTL 红、修复后 169 B 逐字节 == QEMU）。

**修改文件**（累计 11 项；第 2 轮改动为其中 5 项 = 本任务书、`components/chipyard/{README.md,changelog.md}`、`.../WumingALU.scala.patch`、`tools/chipyard/inst_sweep.py`，与 `git status -uall` 逐项一致）：① 本任务书；② `components/chipyard/README.md`；③ `components/chipyard/changelog.md`；④ `components/chipyard/series`；⑤ 删除 `.../WumingCoreStub.scala.patch`；⑥ 改 `.../WumingTile.scala.patch`；⑦–⑩ 新增 `.../WumingCore.scala.patch`、`WumingDecoder.scala.patch`、`WumingALU.scala.patch`、`WumingRegFile.scala.patch`；⑪ `tools/chipyard/inst_sweep.py`。任务 worktree 内无临时产物。（本任务书 diff 另含并行复核 reviewer 追加的「第 1 轮 reviewer 验收」记录，非本轮撰写、未改动其结论。）

**验收结果**：
① 覆盖 **273** 例（`inst_sweep.py list` 现场统计：semantic/boundary/encoding **210** + fault 63；另 3 保留编码 + 3 专门注入 ⇒ 69 个 fault 镜像）。
② 非故障 210 例：chipyard 输出 1240 B == YAML 期望 == QEMU **逐字节一致**（md5 三者同为 `2d4d9465…`）。
③ rd0/rb0 专程序 169 B == 期望 == QEMU：`rrrr` 高/低半丢弃 `rd0` 后仍读 0、`rb0` 读自身 IP（`aip.si`/`add.o`）、`or.w` 保 OR 语义、`SYS_WRITEC` 回写 `rd8=0xdeadbeef`；第 2 轮加 `rrrr` 高半三态探针：`sub.uo` 借位（`a<b`/`a==b`/`a>b`/`0 vs 全 1`）+ `sub.so`/`mul.uo` 高半。
④ 69 个故障：QEMU 退出码 ILLI `0xF8` / UNDI `0xF9`；chipyard 逐例打印 `PRE`、无 `POST`，`fault ... inst=<word> ILLI|UNDI` 与 `faults.json` 逐条一致；ILLI 含 `dst_rd0`/`dst_rb0`/`dst_dual_same`/`encode_sbz`；「已定义合法但未实现」的 `ld.ub` 在 QEMU 上正常执行（PRE+POST、rc=0）而 chipyard 上 ILLI（PRE、无 POST），证明不是静默 NOP；3 例保留编码按合约 ⇒ UNDI。
⑤ 构建/运行在**主控机**（用户 2026-11-10 裁定；第 2 轮复验）：`make verilog` ELAB=0、`make CONFIG=WumingTinyConfig` BUILD=0、两份日志 `%Error`=0、生成 `WumingCore/ALU/Decoder/RegFile.sv`、二进制新于 applied ALU 源；有界运行不崩；闭环：`semihost_smoke.elf` 与 QEMU stdout 逐字节同、`tiny_smoke.elf` 有界 halt 且 UNDI。（原节点（server208）记录：ELAB/BUILD=0、`%Error`=0、同一闭环结论；**已按 2026-11-10 裁定改主控机复验**。）
⑥ `apply-series`/`check-source-state`/`check-patch-tree` rc=0（9 patch set / 327 patches）；L2 rc=0；L1 红仅 `check-temp-dirs`（他人临时目录，只报告不删除）；⑦–⑨ 证据脚本含可达 FAIL 注入、本区 ≤30 行无运行期路径、只用主控机（原节点同步项已删）。

**新发现/坑**：
- `rb0` 按 `spec/SimRISC-00 §2.2` 读出为**当前指令地址**（只读，写 ⇒ ILLI），不是 0；任务书「rb0 读恒 0」与规范冲突，按 spec 落地。
- 保留编码按 `legality_rules.yaml` 的 `excp_undi` ⇒ **UNDI**，非法操作数/组合 ⇒ ILLI；任务书「保留编码 ⇒ ILLI」的字面口径按合约修正，两类均验证。
- `aip.si` 向量期望依赖参考 harness 的装载段长度（IP 基址），生成器按参考 loader 复算并平移到实际指令地址。
- 任务 worktree 的 `.work` / `.cache` / `.dadao` 是指向主树安装根与缓存的本地符号链接（均未入库）；收尾清理时勿沿符号链接递归删除主树 `.work`。
- Chisel Bundle 字段名 `width` 与本版本 `Data.width` 冲突；改 `opWidth`。ROL 初版把 `rotR` 写成移位后的值而非移位量；由 rol 向量+QEMU 暴露。`SYS_WRITEC/WRITE0` 返回标量须由核写回 `rd8`（004 契约），初版漏写、smoke 不依赖返回值故未暴露，已补专测。
- 主控机 chipyard conda env **缺 `firtool`**（台账 §11.2 称已装）⇒ elab 直接 `Error: firtool not found in PATH`（rc=2）；取空闲节点的**同版本**二进制（md5 `bdfd7ff5…`）放回 env 后 ELAB=0。
- **向量覆盖缺口**：`tests/inst` 的 5 条 `sub.uo` 无一 `a<b`，故 210 例全绿也没抓到借位错；「高半值域 0/1」这类语义必须在专测里覆盖三态（`a<b`/`a==b`/`a>b`）。
- 同类模式核查（对照 QEMU `trans_arith.c.inc`）：`add.uo`=`setcond LTU`（ZX 128 位加天然得 0/1）、`add.so/sub.so`=`add2/sub2`（符号扩展 128 位高半）、`mul.*`=`mulu2/muls2`（完整 128 位积）⇒ 只有 `SUB128_U` 一处「整宽回绕当高位」。
- 本分支实测**不在 master 祖先中**（master 的 005 任务书仍是派单前版本、`components/chipyard` 无 ALU 补丁）⇒ 合并待办。

**遗留问题**：⏸ 本任务分支未合入 `master`（合并后消除台账行与 L1 差异）；⏸ L1 `check-temp-dirs` 为他人临时目录（只报告不删除）；⏸ 访存全宽度/块复制/控制流/RAS 归 `006`/`007`，现编码明确 ILLI。

## 审阅记录

#### 第 1 轮 engineer 自审

自审方式：自主逐行审查（engineer 深度 1，无嵌套子代理）；范围 = 4 个新 Scala 源（Core/Decoder/ALU/RegFile）导出补丁、Tile 接线、测试生成器与证据脚本。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 新核 `sSemi` 只 `IP+=4`，未把 semihosting 标量写回 `rd8`（004 契约） | ✅已修 | 写回端口增加 `sSemi && resp.valid` 分支，数据=`resp.value`、目的=rd8 | rd0rb0 专测 `SYS_WRITEC` 返回 `rd8=0xdeadbeef`；QEMU/chipyard/期望三者一致 |
| F2 `semiRetReg` 在写回 mux 之后定义 ⇒ elaboration NPE | ✅已修 | 提前到状态机声明之后 | 节点 `make verilog` 由 Error 转 ELAB=0 |
| F3 ROL 的 `rotR` 误写成 `aW >> amount`（值）而非移位量 | ✅已修 | `rotR = (nBits - sh)(5,0)` | rol.o/rol.t 全部向量 + QEMU 逐字节一致 |
| F4 `div.ut` 除零定值写 `0x0000FFFF`（应为 32 位 `0xFFFF_FFFF` 零扩展） | ✅已修 | 改 `h00000000ffffffff` | `div.ut` 向量由 QEMU 回绿（全 210 例唯一差异） |
| F5 QFC 空白行 0x08–0x0F 被当 ILLI（实际 reserved） | ✅已修 | 删除该分支；`opcDefined` 精确到 0x10-0x1A/0x20-0x32/0x38-0x3F 等 | 保留编码 0x08040001 节点诊断 `UNDI`，QEMU rc=249 |
| F6 stub 的 `or.w` 为「替换 wyde」，SimRISC-03 规定「wyde 内 OR」 | ✅已修 | ALU `OR_W = a | (imm<<shift)`，其他 wyde 不变 | rd0rb0 专测：`0xFFFF` + OR `0x1234` @wp1 → `0x1234FFFF`，再 OR `1` → `0x1235FFFF` |
| F7 `aip.si` 向量期望依赖参考 loader 布局（IP=参考基址），直接生成必假红 | ✅已修 | 生成器复算参考 loader 字数并平移 IP 期望到实际指令地址 | aip.si semantic/boundary 全部由 QEMU/chipyard 一致通过 |
| F8 `width` 字段名与 Chisel `Data.width` 冲突（`UInt(2.W)` 类型错误） | ✅已修 | 三处改 `opWidth` | 节点 `sbt compile` [success] |
| F9 故障程序把 PRE/POST 放在未装载 SRAM，`SYS_WRITE0` 扫到随机内存（300 s 超时） | ✅已修 | 标记字符串固化在镜像 `ENTRY+0x400`，代码后填充 | 故障程序秒级结束，PRE 可见、无 POST |
| F10 rd0rb0 的缓冲长度把"早期 `st.o` 写指针"也计入 ⇒ 多打印 8 B | ✅已修 | `buf_bytes = len(expected) - 1`（扣掉早期直接输出的 `'A'`） | 期望 73 B == QEMU == chipyard |
| F11 L1 的 `check-temp-dirs` 红来自他人临时目录；不能删除且不应掩盖 | ✅已修（显式断言） | 证据脚本允许 ledger + temp-dirs，但若 `VIOLATION: /tmp/opencode/` 命中本任务号即 FAIL | 全量证据 `PASS=48 FAIL=0`；`series` 注入仍使 `apply-series`/`check-patch-tree` 变红 |

#### 第 1 轮 reviewer 验收

**重跑记录**（全部 reviewer 本人执行；原始输出在运行期证据目录 `m12-chipyard-005-reviewer/`）
1. `python3 tools/chipyard/inst_sweep.py list` → **rc=0**：`covered=273 semantic_set=210 fault_cases=63`（任务书写的 `--list` 不存在 → rc=2；CLI 是子命令 `list`）。
2. 一键证据脚本（运行期证据目录下 `run.sh`，第 1 次）→ `PASS=47 FAIL=1`，唯一红 = L1 `check-run-artifacts` 142 条，逐条核对**全部**为 reviewer 落在运行期日志目录的临时文件文件名违规（非 reviewer 文件 0 条）⇒ 移入运行期证据目录；该次 A–E 各项本体全 PASS。
3. `run.sh --self-test-inject` → **rc=0**：5/5 注入均 FAIL、`restore md5 matched`、`restore -> PASS`。
4. 独立强制重建（server208：删 `.classpath_cache/chipyard.jar` + verilator Mdir，显式 `PATH`/`RISCV`）→ `ELAB_EXIT=0`、`BUILD_EXIT=0`、两份日志 `grep -c '^%Error'`=0、二进制重链（10113704 B）；节点 applied 源 5 文件 md5 == 本树（`5ba6fc4c… a1291464… a5ea3a7b… 72b9a470… c8734b97…`）。
5. 覆盖：210 例 `expect==QEMU==chipyard` 逐字节 1240 B、md5 `2d4d94651346`、manifest 210 条 0 切片差异；抽 **21** 例（`rrrr` 双目的、`aip.si` 读 IP、`div.ut`/`rem.st`/`mul.so` 边界、移位/比较/rol）YAML 独立重算 == 三方。
6. 故障：`faults.json` 69 = 66 ILLI + 3 UNDI；抽 6 例（`dst_rb0_addo`/`sbz_shlt_imm32`/`reg-arith_3`/`reg-arith_4`/`reserved_08040001`/`unimpl_ldub`）QEMU rc=248(0xF8)/249(0xF9) 且仅 `PRE\n`，chipyard `fault … inst=<word> ILLI|UNDI` 逐条同；`unimpl_ldub` QEMU rc=0 + `PRE\nPOST\n` 而 chipyard ILLI 无 POST ⇒ 非静默 NOP。
7. **独立反例注入**（engineer 5 例之外）：改节点 applied `WumingDecoder.scala` 删 `bbd` 的 `dst_rb0` ILLI ⇒ 退化为静默执行，md5 `a1291464→cac22ace`，重建 `ELAB/BUILD=0` → 同一 `run.sh` → **`RUN2_INJECT_EXIT=1`、`PASS=46 FAIL=2`**（`chipyard fault cases actual=3`、`fault kinds actual=1`，其余 46 项含 QEMU 侧全绿）⇒ `cp -p .preinject` 还原 md5 回 `a1291464`、重建 → **`RUN3_RESTORED_EXIT=0`、`PASS=48 FAIL=0`**。

**约束核验**：11 文件 == 完成区「修改文件」（`git status` 逐项一致；期间 architect 于 00:16 建 WIP `c16961bd`，含且仅含该 11 文件，内容 md5 与验收起始快照逐个相同）；`spec/`/`contracts/`/`tests/` 零改动；无 `scratch`/`*_tmp`/`_gate`/`*.orig` 残留；完成区 22 行（≤30）且无运行期路径；本轮审阅 ≤40 行；reviewer 未 commit/push、未改共享台账；`sync-node-repo` rc=0、`dirty=0`。

**判决：Needs Revision**
- **F1（阻断·语义 + 代码行为）`sub.uo` 借位高半错**：`spec/SimRISC-04 §1.1`「`add.uo/sub.uo`（ZX）… `rdHA` 为进位/借位（0 或 1）」，QEMU `target/dadao/insn_trans/trans_arith.c.inc` 用 `setcond LTU`；`WumingALU.scala.patch` 的 `SUB128_U → hi := subU(127,64)` 在 a<b 时给 `0xFFFF…F`。19 例独立探针（同镜像 QEMU vs chipyard）**唯一差异**：`sub.uo rd1,rd2,rd3,rd4 (5-7)` QEMU `hi=0x0000000000000001` / chipyard `hi=0xFFFFFFFFFFFFFFFF`（`lo` 两者均 `0xFF…FE`），其余 18 例逐字节同；`tests/inst` 5 条 `sub.uo` 无一 a<b ⇒ 210 例绿灯掩盖；README/changelog 自称「高半是进位/借位」与代码亦不符。**改法**：`WumingALU.scala.patch` 的 `SUB128_U` 高半改 `Mux(io.a < io.b, 1.U, 0.U)`，并在 `inst_sweep.py` 专测（或向量）补借位用例后重跑证据脚本。
- **F2（文档·不阻断）**：本 worktree 任务书正文仍写「`rd0`/`rb0` 读恒 0」「保留编码 ⇒ ILLI」「`--list`」；master 已由 `6303e4fd` 修正但**非本分支祖先**（分支 19:21:54 早于该提交）⇒ 合并须保留 master 口径；`--list` 实为子命令 `list`。
- **F3（文档·不阻断）**：L1 `check-milestones-fresh` 3 条 VIOLATION 全因分支缺台账提交（005 行仍在「待开始」、006 行未列），`check-temp-dirs` 2 个陈旧目录属 m13-testcases-001/002；run.sh 只放行这两项，第 1 轮放行表外的 `check-run-artifacts` 即红 ⇒ 放行非恒真。

#### 第 2 轮 reviewer 验收（对 `8e04daf8`；接本 reviewer 第 1 轮）

**重跑记录**（全部本人执行；原始输出在运行期证据目录 `m12-chipyard-005-reviewer/`）
1. **F1 静态核验**：`WumingALU.scala.patch` = `SUB128_U) { hi := Mux(io.a < io.b, 1.U(64.W), 0.U(64.W)); lo := subU(63,0) }`；补丁 `+` 行重建 md5 `4735c143…` == applied 源 md5、`git hash-object` = `1443fa168e…` == 补丁 `index 0000000..1443fa1`、202 行 == 202 行；`python3 tools/infra/make_patch.py chipyard` → **rc=0、`0 written, 19 unchanged`**（补丁集逐文件 md5 前后相同）⇒ 确为导出、非手改。
2. **全量重验（稳定树）**：`run.sh` full → **`R2_BASELINE_EXIT=0`、`PASS=49 FAIL=0`**（elab rc / build rc / `%Error` / 二进制非陈旧 / `sub.uo borrow high half` 全 PASS；L1 放行实测仅 `check-temp-dirs`）。
3. **独立反例注入 + 先红后绿**：applied `WumingALU.scala` 的 `SUB128_U` 高半回退为旧实现（`cp -p` 备份，md5 `4735c143→3750fb84`），删 `chipyard.jar` + verilator Mdir 强制真重建 → 同一 `run.sh` → **`R2_INJECT_EXIT=1`、`PASS=42 FAIL=7`**：`sub.uo borrow high half actual=2`（4 探针恰红 `a<b`、`0 vs 全1` 两例，与 engineer「旧 RTL 红 2/4」独立吻合）、`chipyard rd0/rb0 state == expected/QEMU` 红而 `QEMU rd0/rb0 == expected` 仍绿（期望对、DUT 错）、`apply-series`/`check-source-state`/`check-patch-tree` 红 = 门控侦出源树漂移；该轮日志含 40 处 `Compiling/firrtl` + `verilator --main` ⇒ 注入真进了 DUT。`cp -p` 还原 md5 回 `4735c143…`（`.preinject` 已删）→ 删 jar+Mdir → **`R2_RESTORED_EXIT=0`、`PASS=49 FAIL=0`**（链：源 00:54 → jar 01:51:33 → `WumingALU.sv` 01:51:53 → 二进制 01:52:19）。
4. `run.sh --self-test-inject` → **`R2_SELFTEST_EXIT=0`**：5/5 注入均 FAIL + `restore md5 matched` + `restore -> PASS`。
5. **断言可达**：`sub.uo borrow high half` 读 `$WORK/chipyard-rd0.out`（DUT 输出），期望由 `1 if a<b else 0`、`(a-b)&0xFF…F` 现算（不读期望文件）⇒ 旧 RTL 必红（实测 2）。
6. **稳定树复算**：`list` → `covered=273 semantic_set=210 fault_cases=63`；sweep 1240 B 三方 md5 `2d4d94651346…`；rd0rb0 169 B 三方 md5 `b4807146…`；`faults.json` 69 = 66 ILLI + 3 UNDI；`check-patch-tree` `9 patch set / 327 patches`。
7. **构建（主控机）**：`run.sh` 内无 `ssh`/`rsync`/节点引用 ⇒ 本任务未占用节点（208 现负载属他人 016/017 长仿真，本轮只读核过一次 md5）；日志 02:03 晚于最终源 00:54，且我两轮强制重建证明管线会真编译 ⇒ 第 1 轮「日志早于源码」已消除。
8. **firtool 环境事件**：主控机 `.conda-env/bin/firtool` md5 `bdfd7ff5f922e1bba7ee035182dde9bb` == server208 同名文件；`firtool --version` = `CIRCT firtool-1.75.0` + `LLVM 19.0.0git` == `nodes.md §11.1`；`verilator 5.022`/`openjdk 20.0.2` 亦与台账同；`nodes.md §11.2①` 本就写明「firtool 不在 conda 依赖、需装 CIRCT 静态包」⇒ 来源可追溯、版本同源；缺件表现为 elab rc=2，现由 `chipyard elaboration rc` 断言兜住。

**约束核验**：第 2 轮改动 = 5 文件（`git diff --stat 4e8619d0..8e04daf8` = 任务书/README/changelog/ALU 补丁/`inst_sweep.py`）== 完成区「修改文件」；`spec/`、`contracts/`、`tests/` 零改动；工作树 `git status` 干净（注入产物与 `.preinject` 已清）；完成区 26 行 ≤30、运行期路径 0 条；本 reviewer 第 1 轮与并行 reviewer 第 1 轮记录均在、结论未改（仅 `.work` 路径措辞按 `check-knowledge-refs` 改写，G6 只披露并行一条、实为两条）；本轮 reviewer 未 commit/push、未改共享台账。

**判决：Accepted**
- F1 已真修且**先红后绿**（见 3）；覆盖缺口由 4 例 `sub.uo` 三态探针 + DUT 侧语义断言补齐；同类自查（`sub.so`/`mul.uo`/`add.uo` 探针）与 QEMU `trans_arith.c.inc` 一致；README/changelog/验收 2/完成区⑤⑥ 口径已按 spec 与主控机裁定修正。
- 遗留（不阻断，交 architect）：① 任务书 `**依赖**：m12-chipyard-005`（自依赖）与背景漏 `001` 源自 master 派单版本（`check_tasks.py` 不解析该字段），合并/收尾时改；② 主控机 env 无门控校验 `firtool`，建议 `make doctor` 或 `nodes.md §10.1` 补一条；③ 节点 applied ALU 仍为返工前 `a5ea3a7b…`，下次上节点须按 `nodes.md §10.1` 重放（主控机改→导出→同步→apply-series→重建）。

#### 第 1 轮 reviewer 验收（并行独立复核，对 `c16961bd`；不替换上节已提交记录）

**重跑记录**（全部本 reviewer 亲自执行；证据落运行期证据目录 `m12-chipyard-005-reviewer/`）
1. 覆盖现场复算 `inst_sweep.py list` → rc=0：`covered=273 semantic_set=210 fault_cases=63`；按 class 重算 = semantic 92 + boundary 50 + encoding 68 = 210，legality 57 + overlap 6 = 63；覆盖 id 的 spec_cite 仅 `SimRISC-04/05/08`（无 09/10 的 `.w/.b`，无 `ld/st`、跳转、FP），未越界。
2. 独立 emit → rc=0：`covered=273 semantic_set=210 dumped_bytes=1240 fault_images=69`；`faults.json` = 66 ILLI + 3 UNDI（`reserved_08040001/1B040001/58040001`），`qemu_executes` 仅 `unimpl_ldub`。
3. 三方差分（自跑）：QEMU 输出 == YAML 期望 == chipyard 输出，1240 B 同为 md5 `2d4d94651346ef673c5a855e024c1489`（QEMU rc=0；chipyard rc=0 且 `SYS_EXIT … host exit status 0`）；rd0rb0 专程序 73 B 三方同 `cd48d1528af5ebdd9189b1b752fd86b1`。
4. 故障批次（自跑）：QEMU 69/69 → ILLI rc=248、UNDI rc=249 且仅 `PRE\n`（`unimpl_ldub` 例外 rc=0+`PRE\nPOST\n`）`bad=0`；chipyard 69/69 → rc=0 + `PRE` + 无 `POST` + 有 fault 诊断，`inst=… ILLI|UNDI` 与 `faults.json` 比对 `seen=69 mismatch=0`（ILLI 66/UNDI 3）。
5. 门控（自跑）：`check-source-state` rc=0；`check-patch-tree` rc=0（`9 patch set(s), 327 patches OK`）；L1 中被声明为外因的三项逐个亲跑——`check-knowledge-refs` rc=0（两次，另一轮的同名红未复现，判并发瞬时）、`check-milestones-fresh` rc=0（合入 master 后已转绿）、`check-temp-dirs` rc=2 但 2 条 VIOLATION 均属 m13-testcases-001/002、命中本任务号 0 条 ⇒ 确为外因。`apply-series`/L1 全量/L2 未在稳定树上由本 reviewer 跑通（见下）。
6. 节点一致性：server208 applied 源 5 文件 md5 == 本树（`5ba6fc4c… a1291464… a5ea3a7b… 72b9a470… c8734b97…`），节点仓库 HEAD 干净；二进制重链时间晚于源码、`chipyard.jar` 与 `.sv` 生成时间；但完成区引用的 elab/build 日志早于最终源码，属证据滞后（后续由强制重建补上）。
7. 完成区纪律：23 行 ≤30、无运行期路径；`git show --stat c16961bd` = 11 文件与「修改文件」逐项一致；`spec/`、`contracts/`、`tests/` 未被本任务改动。

**约束核验**：`rd0` 恒读 0、`rb0` = 当前指令地址（只读，作显式目的 ⇒ ILLI）按 `SimRISC-00 §2.1/§2.2` 与 `legality_rules.yaml`（`dst_rd0`/`dst_rb0`/`dst_dual_same`/`encode_sbz` = ILLI、`excp_undi` = UNDI）落地成立，`WumingRegFile`/`WumingDecoder` 与 QEMU 行为一致；任务书旧口径已由 master 修正，合并时须保留。

**判决：Needs Revision**
- **F1（阻断，独立复现）** `sub.uo` 借位高半错：本 reviewer 自建 4 组同镜像探针（QEMU vs chipyard）——`a<b(5-7)` spec/QEMU `hi=0x0000000000000001`、chipyard `hi=0xFFFFFFFFFFFFFFFF`（md5 `e00a0f2b…` vs `9b7190ae…`）；`a>b`、`a==b`、`add.uo` 进位三组两者一致 ⇒ 唯一差异即 F1；静态同源 `SUB128_U → hi := subU(127,64)`。`tests/inst` 的 5 条 `sub.uo` 无一 a<b ⇒ 210 例绿灯掩盖。改法同上节 F1。
- **未完成项（环境，非放行理由）**：`run.sh` 全量重跑在第 298 行因脚本被并发改写报 `syntax error`（`MINE_RUN1_EXIT=2`），`--self-test-inject` 与本 reviewer 自选反例注入未执行——工作树自 00:51 起处于返工（ALU 借位修复、`inst_sweep.py` +51 行借位探针、README/changelog、run.sh 重写均未提交），对共享跟踪文件注入会与在写者并发冲突，按「不与在写者并发写共享文件」推迟至第 2 轮重验。
- **并发现象**：存在另一 reviewer（其第 1 轮记录已由 `fe7e5a86` 提交，结论同为 Needs Revision，F1 与本节互为独立复现）；HEAD 已移至 `4e8619d0`（合入 master 任务书口径），本节仅对 `c16961bd` 有效。

#### 第 2 轮 engineer 返工（对第 1 轮 F1）

自审方式：自主逐行审查（engineer 深度 1，无嵌套子代理）；范围 = `WumingALU` 补丁 `SUB128_U`、`inst_sweep.py` 专测、证据脚本 C 段（节点→主控机）、任务书/README/changelog 文档项。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| G1 F1 `sub.uo` 借位高半 = 128 位回绕 | ✅已修 | `SUB128_U` 高半 `subU(127,64)` → `Mux(io.a < io.b, 1.U(64.W), 0.U(64.W))`；补丁由 `make_patch` 重导出（非手改，E1 收敛回 base+1） | 旧 RTL 首差第 74 字节 `hi=0xFF…FF` vs QEMU `1`；修复后 169 B「期望==QEMU==chipyard」逐字节同 |
| G2 覆盖缺口（`tests/inst` 5 条 `sub.uo` 无一 `a<b`） | ✅已修 | 专测新增 (f) 4 例：`a<b`/`a==b`/`a>b`/`0 vs 0xFF…FF`，期望按 §1.1 独立派生（非 QEMU 回填） | 旧 RTL 红 2/4；修复后全绿；证据脚本加语义断言 `sub.uo borrow high half`（读 DUT 输出，旧 RTL 可达 FAIL） |
| G3 同类模式自查（`rrrr` 其他变体） | ✅已核 | 对照 QEMU `trans_arith.c.inc`：`add.uo`=`setcond LTU`、`add.so/sub.so`=`add2/sub2`、`mul.*`=`mulu2/muls2`；专测补 (g) `sub.so`、(h) `mul.uo` 高半探针 | (b) `add.uo` 进位与 (g)(h) 在**旧** RTL 上即绿 ⇒ 该错误仅存在于 `SUB128_U` |
| G4 F2/F3 文档项 | ✅已修 | 验收 2 与完成区①改 `inst_sweep.py list`；完成区⑤改主控机并保留节点记录+注明；README/changelog 口径精确化为「无符号加减高半 0/1、有符号高半=128 位高 64、乘法=完整积高半」 | `check-knowledge-refs`/`check-component-changelog` rc=0；`check-patch-tree` 327 patches OK |
| G5 证据脚本仍按节点跑（用户 2026-11-10 改主控机） | ✅已修 | C 段改主控机本地 `make verilog` + `make CONFIG=…` + 本地仿真，新增 elab/build rc、`%Error`、二进制非陈旧断言；E 段（节点同步）删除 | full `PASS=49 FAIL=0`（rc=0）；`--self-test-inject` 5/5 注入 FAIL + 还原 PASS |
| G6 审阅记录内具体 `.work` 路径致 L1 `check-knowledge-refs` 红 | ✅已修 | 第 1 轮并行复核「重跑记录」第 2 条改运行期措辞（结论不变） | L1 该项回绿；L1 放行表收缩为仅他人 `check-temp-dirs` |

环境项（非 finding，已在「新发现/坑」登记）：主控机 chipyard conda env 缺 `firtool`，取空闲节点同版本二进制放回后 ELAB=0（旧 RTL 红测、修复后各一次）。

#### 收尾（architect，2026-11-10 02:16）

- 第 1 轮 two reviewer 独立复现同一阻断（`sub.uo` 借位高半 128 位回绕）；第 2 轮 **Accepted**（`PASS=49 FAIL=0`，独立注入 ⇒ `PASS=42 FAIL=7` ⇒ 还原回绿）。
- 修复：`SUB128_U` 高半 `Mux(a<b, 1, 0)`，`make_patch` 重导出（非手改）；`inst_sweep.py` +4 借位探针（`a<b`/`a==b`/`a>b`/`0 vs 全1`），旧 RTL 上可达 FAIL（`actual=2`）。
- 三方差分：sweep 1240 B md5 `2d4d9465…`；rd0/rb0 169 B md5 `b4807146…`；69 故障镜像 QEMU 248/249 与 chipyard `ILLI|UNDI` 逐条一致。
- **构建改主控机**（用户 2026-11-10）：elab/build 日志晚于最终源，证据滞后已消除；未占用节点。
- `firtool` 缺件已从同版本二进制补入 conda env（md5 `bdfd7ff5…`，与 208 一致，`CIRCT firtool-1.75.0`）；建议后续加 env 校验门控。
- 遗留（不阻断）：任务书自依赖已改 `004`；节点 applied ALU 仍是返工前版本，下次上节点按 `nodes.md §10.1` 重放。
