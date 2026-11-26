# m16-chipyard-033: RTL `WumingRegFile` RegRAS 改环形缓冲（去搬移）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：用户当前自行修复的 `escape`（`DIV-11`）先合入（同改 chipyard RTL）
**可并行分片**：否（同改 `components/chipyard`）
**预估**：4–8 h
**档位**：大改（复核 ≤60 min）
**状态**：待验收

## 背景（用户 2026-11-25）

`spec/SimRISC-00 §2.4.3` / `ADR-0012 D7.5` 允许并推荐**环形缓冲 + 隐藏基准索引**；用户确认 RTL 不应使用搬移——`call`/`ret` 搬 62 个 64 位槽是直接的时序/面积代价。

现状：`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingRegFile.scala.patch` 中 `WumingRasOp.PUSH/SPILL` 做 `raNext(i) := ra(i+1)`（i=1..62）、`POP` 做 `raNext(i) := ra(i−1)`（i=2..63），每周期整体搬移。QEMU 的 `ras_base` + `ra_phys()` 是参考实现（`1 + (base + i) % 63`）。

## 统一环形约定（硬约束；用户 2026-11-25）

四平台必须用**同一套**隐藏布局，否则「全 64 槽按值比」会因窗口外残留不同而假红：

- 物理槽：`0` = `ra0` 元数据（`{SBZ,RACNT,MRPTR}`，不占窗口），`1..63` = 环形数据槽；
- 映射：`phys(i) = 1 + ((base + i) % 63)`，`i ∈ 1..63`；`base` 为 6 位隐藏基准（0..62，复位 0，不可架构访问）；
- 推进方向与 QEMU `ra_phys()` 一致：`call` 压栈 `base += 1`、`ret` 弹栈 `base −= 1`（模 63），写入/读出均经映射；
- 架构视图（`ld.o-ra`/`st.o-ra`/`rd2ra`/`ra2rd` 与 trace/`-d cpu` 导出）一律按映射换算。

## 要做

1. 在 `WumingRegFile` 增加隐藏基准寄存器 `rasBase`（6 位，0..62，复位 0，**不可架构访问**）；
2. 逻辑→物理映射函数；**所有** `ra1..ra63` 的架构访问走映射：`raRead()`、通用 `read()` 的 RA 分支、写回口（`ld.o-ra`/`st.o-ra`）、`rd2ra`/`ra2rd` 块赋值、`io.rasTopCount/rasTopAddr/rasOldest`；
3. `PUSH/SPILL` 改为「`rasBase` 前进一格 + 写新栈顶」，`POP` 改为「`rasBase` 后退一格」；`FOLD/DEC/REFILL/CONSUME` 仅经映射读写，判定与提交语义不变；
4. 架构视图与改前逐例一致（`ra_i` 逻辑序、`ra0` 位域、RASOF/RASUF、MemRAS 溢出/回填）；
5. `WumingTiny`/`WumingVast` 两种配置均构建 rc=0，`%Error`=0；复跑 arch 探针（`arch-hart-001/002`）、`check-idl-full` 274。

## 不做

- 不改 `escape`/cfx/monitor 等其它 RTL；
- 不改 spec/契约/版本号；不改 QEMU/gem5/IDL。

## 约束

- 独立 `git worktree`；组件补丁按 `docs/Process-01`（改隔离源树 → `make_patch.py chipyard` 重导）；不提交 git；
- 只动 `components/chipyard/patches/generators/dadao-*/…/WumingRegFile.scala.patch`（必要时 `components/chipyard/{README.md,changelog.md}`、`tests/arch/hart/` 探针）+ 本任务书；完成区 ≤30 行。

## 验证

1. `check-patch-tree` chipyard 段 0 problem；Tiny/Vast 构建 rc=0；sim md5 记录；
2. RAS 相关 arch 探针全绿；`check-idl-full` 274/274（芯片侧与改前逐例一致）；
3. **可达 FAIL ≥2 路**：① `POP` 基准不后退 ⇒ 返回地址错/探针红；② 映射写成 `% 62` ⇒ 溢出/回绕用例红；`cp`+md5 还原重建回绿；
4. 综合资源对比（可选记录）：搬移逻辑消失后的 LUT/FF 变化；
5. `git status -uall` 仅允许文件 + 任务书。

## 完成区

**测试结果**：`run.sh --base` 35/35、`--inject` 22/22，均 rc=0。架构视图逐例：`06-control-flow` 15/15（chipyard+qemu，两平台 15 份输出与改前逐字节相同）；`01-load-store` 38/38（两平台逐字节相同）；`11-cfx` 6/7 与改前同（唯一 `escape_ciii_cfx` = `DIV-18`）；`arch-hart-001` 124 槽签名数组与改前完全相同（既有 2 槽 `DIV-17`：63 vs 3）；`arch-hart-002` S/U 各 38 槽 PASS；`check-idl-full` 273/274（唯一 `escape_ciii_cfx`，与改前同；`DIV-18`）。
**修改文件**：`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingRegFile.scala.patch`、`components/chipyard/changelog.md`、本任务书。源树改在组件工作树内（base+1 commit `7b1d785`），未提交 DADAO-v5 git。
**验收结果**：Tiny 104 s / Vast 246 s，均 rc=0、`%Error`=0、`WumingRegFile` 0 条 width 警告；末版 sim md5 Tiny `71cbed98…`、Vast `0ead2519…`（同源重建 `5f5fc39e…`/`97cbf356…`，ISS-453，行为判据不取 md5）。注入：A「PUSH/POP 退回搬移」⇒ call 点 12 / ret 点 4 红；B「PUSH 不推进 base」⇒ call 点 12 红；C「POP 不后退 base」⇒ ret 点 4 红；`cp`+md5 还原并重建后 06 15/15、与基线逐字节相同。门控：`check-patch-tree` chipyard 段 0 problem（31 patches）；`--source-state` OK（HEAD=7b1d785，base+1）；`make_patch` 1 written → 0 written 幂等；`check-index-blobs`/`check-tests-index`/`check-component-changelog`/`check-no-residue`/`run_arch --self-test` rc=0；`git status -uall` 仅上述 3 个文件。
**新发现/坑**：① 隐藏布局必须与 QEMU 的 C1 特例一致——空栈 PUSH（RACNT=0）**不推进** base，C3a/C3b 才推进；否则窗口外残留位置不同。② 同源重建 sim 字节可不同（ISS-453），且共享运行期 sim 可能被其它会话的节点同步覆盖；判据只用行为/逐字节输出，md5 仅记录。③ `raPhysOf` 用 7 位和做一次条件减 63（无除法），初版 Mux 分支位宽不一致会让 Verilator 报 WIDTHEXPAND，已显式切片消除。
**遗留问题**：`DIV-17`（arch-hart-001 槽 1/7，RTL Vast 以 cfx_power 交付）与 `DIV-18`（Tiny 无 cg15 rc3 ⇒ escape_ciii_cfx）为既有登记红，本任务不关闭；可选综合资源对比未做；`ISS-m16-011` 本轮未复现。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-27）

审查范围：`WumingRegFile.scala` 的 `rasBase`/`raPhysOf`/`raRead`/RAS op/`writeRa`，逐行对照 QEMU `helper.c` 的 `ra_phys()`、C1/C3a/C3b/D3/D4b 与 `ra0` 掩码；并核对隐藏布局四平台一致。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 初版 `raPhysOf` 的 `Mux` 两支位宽不同（7 vs 8 位），生成 RTL 有 WIDTHEXPAND | ✅已修 | `(b +& idx)(6,0)` 与 `(sum - 63.U)(6,0)` 显式切片；`rasBaseInc/Dec` 同样切片 | 末版 Vast/Tiny 构建 `WumingRegFile` width 警告 = 0；功能回归全绿 |
| F2 C1 空栈 PUSH 是否应推进 base（不推进则与 QEMU 物理布局一致） | ✅已修 | PUSH 分支 `when(racnt===0)` 不推进、C3a `otherwise` 推进；对照 QEMU C1/C3a | `06-control-flow` 15/15 与改前逐字节相同；`call_iiii_ra` C1/C2/C3a/C3b 全过 |
| F3 `rasOldest` 在 RACNT=0 时的边界（旧实现读 `ra(0)`=0） | ✅已修 | `Mux(racnt===0, 0.U, ra(raPhys((64-racnt)(5,0))))` | C3b/D4b 用例全过；`11-cfx`/`01-load-store` 与改前逐字节相同 |
| F4 写回口/`rd2ra`/`ra2rd` 是否全部经映射（防漏改） | ❌不修（审查确认已覆盖） | `writeRa` 的 `else` 用 `ra(raPhys(idx))`；其余访问都走 `raRead`/`read` | `01-load-store` 的 `ld.o/st.o/ldm.o/stm.o` RA 形式 38/38、两平台逐字节相同 |
| F5 注入 A 的「搬移+映射」组合是否真能红（避免恒真） | ✅已确认 | A 保留直接索引 shift、顶经映射写，语义必错 | A 实测 call 点 12、ret 点 4 红；还原后同用例绿 |

### 第 1 轮 reviewer 验收（2026-11-27）

**重跑（全部为我本机输出；证据 = 运行期证据目录内 `run.sh`）**：
- `./run.sh --base` ⇒ `rc=0`、`35/35 checks passed`：Tiny build rc=0、Vast build rc=0（251 s）、`%Error`=0、`WumingRegFile` width 警告 0；sim md5 Tiny `71cbed98…` / Vast `0ead2519…`（与完成区一致）。
- 逐例：06 `15/15`+`compared=30 mismatch=0`；01 `38/38`+`76/0`；11 失败集恰 `escape_ciii_cfx.S`（rc=1、`14/0`）；arch-hart-001 `slots=124 identical=True`、known-red=2；arch-hart-002 smon/umon `slots=38 identical PASS`；`[idl-full] total=274 fails=escape_ciii_cfx`。
- 门控：`check-patch-tree chipyard problems=0 / 31 patches`、`make_patch` before==after（幂等）、`check-index-blobs`/`check-tests-index`/`check-component-changelog`/`check-no-residue`/`run_arch --self-test` rc=0、`git status unexpected paths=""`；`check_tasks.py` rc=0、`check_knowledge_refs.py` PASS rc=0。
- `./run.sh --inject` ⇒ `rc=0`、`22/22`：A（退回搬移）dirty=present、重建 102 s、`call_iiii_ra rc=12`/`ret_riii_ra rc=4` 真红；B（PUSH 不推进 base）`call rc=12` 红；C（POP 不后退 base）`ret rc=4` 红；三路 `restore md5=2b029ab5…`、还原后源树 clean、重建 101 s、06 `15/15`+`30/0` 回绿。注入只写被测 `WumingRegFile.scala`（`git diff` dirty 为证），测试脚本未动。

**语义核（我通读 QEMU `target/dadao/helper.c` 对照）**：`ra_phys=1+(ras_base+n)%63`；C1（`racnt==0` 分支）**不推进** base、C3a/C3b `+1`、D3 `+62≡−1`、D4b 不动 —— RTL `when(racnt===0)` 特例与 QEMU 逐条一致（任务书「call 压栈 base+=1」字面与 QEMU 冲突处按 QEMU，与 gem5-027/idl-023 同口径）；`raPhysOf` 一次条件减 63（b≤62、idx≤63 ⇒ 和≤125，结果 1..63，无除法）；`rasBase` 6 位、复位 0、无 IO/写口暴露。

**架构视图（grep 全源树）**：`ra(` 仅 12 处且全经 `raPhys`（`raRead`/`rasTopCount/Addr/Oldest`/FOLD/DEC/REFILL/PUSH/SPILL/写回口），通用 `read()` 的 RA 分支走 `raRead`，`WumingBank.RA` 只在 `read`/`writeRa`；`new WumingRegFile` 仅 `WumingCore:395`、`rasBase/raPhys` 无外部引用 ⇒ 无旁路。

**基线真实性**：`baseline/outputs.tsv` 60 对中 chipyard==qemu 59 对（唯一差 = `escape_ciii_cfx`，DIV-18 既有红）；抽查 `06 br.eq_rrii_rd=ca61fe38…`、`01 ld.o_rrii_ra=7e5529ce…` 均逐字节见于改前记录（2026-11-20 `m16-testcases-002` 基线清单）；11 套基线行 chipyard==qemu（QEMU 本任务未动）⇒ 逐字节链路成立。

**约束**：worktree `git status -uall` 恰 3 文件 = 完成区声明；主仓 clean；共享源树 HEAD `7b1d785` clean、`REGF` md5 与注入前相同；证据脚本 md5 未变；任务书无具体 `.work/**` 路径；本次新增文本无「银行」（changelog 历史条目残留属既有，不在本次改动行）。

**判决：Accepted**（以上均为我重跑的真实输出/退出码，未采信完成区转述）；遗留照旧：`DIV-17`/`DIV-18` 既有登记红、可选综合资源对比未做。

