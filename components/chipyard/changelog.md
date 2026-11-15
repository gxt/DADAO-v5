# chipyard 组件变更记录

> 粒度：**按任务一条**，追加式。**体例 = 列表式（不用表格）+ 按里程碑分节**：每条 = `- **<日期> <任务号或 —>**`，**摘要另起缩进行** `  - 摘要：<摘要正文>`；节 = `## M<k>`（节序 M1→M2→…）。补丁集的生成/应用/校验规范见 `docs/Process-01-组件补丁组织与构建编排.md §10`。

## M12

- **2026-11-14 文档补齐（`ISS-421`）**
  - 摘要：`m12-chipyard-027` 新增的合法性规则 `mreg_range_addr_overlap`（`ldm`/`stm` 的**地址寄存器**落入传送范围 ⇒ ILLI；`stm` 允许、RA/RF 不适用）此前只在 RTL 与补丁里落地，本 README 的合法性清单漏列，现补入；规则真源见 `contracts/legality_rules.yaml` 的 `mreg_range_addr_overlap` 与 `spec/SimRISC-01`。
  - 执行者：architect（文档补齐）

- **2026-11-14 `m12-chipyard-028`**
  - 摘要：**签入 BootROM hex 由新 builder 重生成，hmon 与 QEMU/gem5 同版**（`ISS-410`）。旧 hex 仍是 `escape +4` 的 120 B hmon，与共享 `bootrom_tiny.bin`（槽 `0xF8`、48 B）不同 ⇒ `tests/inst` 只能靠运行期自装处理器对齐三方，现已撤除该 workaround。新 hex：解码镜像 md5 `514300876ea66ec108396334f3ef2b0f`（65536 B）、文本 md5 `c499803ae452d21f372acdb5cad12f4e`、hmon 代码 44 B/表项 `size=48`、`flags=0x3`、`off=0x2000`。补丁集只重导出该 1 份补丁（20 unchanged）。**坑**：`sims/verilator` 的 jar 只依赖 Scala/Verilog 源，资源（hex）变更不会使 `.classpath_cache/chipyard.jar` 失效 ⇒ 必须先删该 jar 再 `make verilog`，否则 elaboration 静默沿用旧固件。
  - 执行者：engineer

- **2026-11-13 `m12-chipyard-029`**
  - 摘要：**融合乘加溢出按 IEEE 舍入方向 + 严重/轻微之分**（`spec/SimRISC-07 §2.5` = IEEE 754-2019 §7.4，`m13-spec-006` 定稿）。结论先行：`WumingMulAddRecFN` 的溢出**本就**由共享舍入原语按 `rf0[33:32]` 决定（本族从未有 `forceInfOnOverflow` 覆写），实测 96 格（ft/fo × 12 形状 × 双符号 × 四档）与条款逐格一致 ⇒ **RTL 行为无需改动**；只补 `WumingMulAddRecFN` 的条款注释（写明 RNE/正向 RUP/负向 RDN ⇒ `±Inf`、其余三格 ⇒ `±max`、轻微溢出只置 `NX`，并注明禁止再加 Inf 覆写）。模型 `fp_ref.fma_exact` 同一套规则（`round_dyadic`），文档注明轻微溢出口径。工具：单元台新增 `fma ovf` 96 例（12 形状：`max×2` 严重溢出 / `max` 上方 1/4 ulp 轻微溢出 / RNE 中点上下 / 恰为 `max` / 精确 `2^128`·`2^1024`，各双符号 × 四档；期望值按条款逐格抄写成常量表，与 RTL、hardfloat、oracle 四方对照）；`fp_sweep` 的 `arith_fma_ft`/`arith_fma_fo` 各增 12 个溢出三元组（同形状，四档 × 双符号），核上 `rd` 与 `rf0` 逐字节。
  - 执行者：engineer

- **2026-11-13 `m12-chipyard-030`**
  - 摘要：**结果 NaN 统一 canonical quiet NaN + `rootn(±0,2)=+0`**（`spec/SimRISC-07 §1.4`/§2.2，用户 2026-11-13 裁定 R1/R2）。`WumingFP.scala`：舍入原语 `WumingRoundAnyRawFNToRecFN` 不再复制输入 payload（`nanFract` → 只置 quiet 位，删 `payload`）；`WumingAddRecFN`/`WumingMulRecFN`/`WumingRemRecFN`/`WumingDivSqrtRecFN` 删除 `nanSrc`/`nanSig`/`nanSigZ` 的 payload 注入，NaN 结果只由原语按 `isNaN`/`invalidExc` 生成（符号恒 0、payload 全零）；`WumingDivSqrtRecFN` 的 root 零结果 `sign = rawA.sign && !rawA.isZero` ⇒ `rootn(±0,2)=+0`、不置标志。不适用面保持：`ft2ft`/`fo2fo` 复制、signaling compare 的 sNaN 位型、min/max 单 NaN 返回数。模型 `fp_ref`：`round_bits`/`round_exact` 的 NaN 分支取 canonical、`add/mul/div/rem/sqrt_exact` 的 qNaN 分支取 canonical、`sqrt_exact` 零分支返回 `+0`、`selfcheck` 增 NaN 位级 canonical 断言。工具：`fp_unit/unit_run` 增 `spec points` 20 例（期望值逐条抄条款），`sqrt` 组对 hardfloat 只容忍零符号差（`squareRoot(-0)=-0`）；`fp_sweep` 增 `cvt_nan` 18 例、扩 `arith_nan`（ft + 负号 qNaN）与 `divrem_nan`（root ±0 四档）；`QEMU_GROUPS` 注明 qNaN 结果与 softfloat 的 payload/符号差异（QEMU 侧归 `m13-integ-010`，汇总归 `m13-testcases-032`）。
  - 执行者：engineer

- **2026-11-12 `m12-chipyard-024`**
  - 摘要：**quiet compare 遇 sNaN 置 `NV`（跟 IEEE 754-2019 §5.11）**。用户裁定「改为置 NV（跟 IEEE）」后，`WumingFP.scala` 的 `WumingCompareRecFN` 的 `NV` 条件由 `Mux(io.signaling, unordered, false.B)` 改为 `Mux(io.signaling, unordered, rawA.isSigNaN || rawB.isSigNaN)`：signaling（`ftscmp`/`foscmp`）仍对**任何**无序（含 qNaN）置 `NV`（§5.6.1），quiet（`ftqcmp`/`foqcmp`）**仅**在 sNaN 输入时置、qNaN 输入不置 —— 与 hardfloat `CompareRecFN` 的 `isSigNaNRawFloat(a) || isSigNaNRawFloat(b) || (signaling && !ordered)` 逐位一致，单元台因此取消 quiet 的 sNaN 容差（`hf-flag-diff` 改为严格）。工具：`fp_ref.cmp_exact` 同步同一口径；`fp_sweep` 的 `cmp_nan` 组按模型自动跟随；`tests/inst/fp/arith.yaml` 补 10 例（quiet 的 sNaN/qNaN × 两个操作数方向 × ft/fo，加 ft/fo 的 signaling 对照：qNaN ⇒ `NV`、有序 ⇒ 不置）。比较仍为组合逻辑，拍数不变。

- **2026-11-12 `m12-chipyard-026`**
  - 摘要：**修复 `m12-chipyard-025` 的实现未落 master（`ISS-405`）**：补丁从共享源树重导 —— 实质变化只有 `WumingFP.scala.patch` 与 `WumingFPUnitHarness.scala.patch`（其余 19 + 2 条补丁逐字未变），`WumingFP.scala.patch` 内 `forceInfOnOverflow` 由 5 处降为 **0**。模型侧补回 `025` 的口径：`fp_ref.f2f_exact` 删除 `force_inf_on_overflow` 参数与「恒 ±Inf」覆写（溢出只用舍入原语的 `_round_mag` 那一套方向规则）；`fp_sweep` 的 `cvt_ff` 改为按方向期待，`cvt_flags` 的 `flags_of_uf_nx` 不再写死 `+Inf` 字面量（改为由 oracle 导出，原字面量编码的正是旧规则），并新增 `cvt_ff_ovf` 38 例（severe / 中点上方 1 ulp / 中点 tie 各 5 档 × 双符号 = 30，加动态 `0x20` 四码 × 双符号 8）；`fp_unit/unit_run` 的 `f2f` 组去掉 hardfloat 结果的后处理，新增 `f2f fo2ft ovf` 40 例 —— 8 形状（最大 double / 中点上方 1 ulp / 中点 / 恰为 `ft_max`，各双符号）× 5 档，期望值按条款**逐格抄写**成常量表，与 RTL、hardfloat、oracle 四方对照。
  - 执行者：engineer

- **2026-11-12 `m12-chipyard-025`**
  - 摘要：**`fo2ft` 溢出按 IEEE 舍入方向**（`spec/SimRISC-07 §1.4` = IEEE 754-2019 §7.4）。`WumingFP.scala` 的 `WumingF2F` 删除 `forceInfOnOverflow` 覆写，改由舍入原语以**无界指数**判溢出：`common_overflow = sRoundedExp >> (outExpWidth − 1) >= 3`，`pegMaxFiniteMagOut = overflow && !overflow_roundMagUp` ⇒ RNE/RNA、正向 RUP、负向 RDN 给 `±Inf`，其余三格给 `±ft_max`，两种情况都置 `OF|NX`（轻微溢出在把幅值舍下来的方向上只置 `NX`）；`WumingFPUnitHarness` 不再对 hardfloat 的 `fo2ft` 结果做后处理，hardfloat 自身结果即参考。模型 `fp_ref.f2f_exact` 同步去掉「恒 ±Inf」覆写（实现补入由 `m12-chipyard-026` 完成）。
  - 执行者：engineer

- **2026-11-12 `m12-chipyard-014`**
  - 摘要：**FP 除法 / 开方 / 取余**（`spec/SimRISC-07 §2.1/§2.2`）。`WumingFP.scala` 增 `WumingDivSqrtRecFN`（除法与开方共用每拍一位的数字迭代状态机，`N = sigWidth+2` 步、耗时常数）、`WumingRemRecFN`（restoring 长除，`sigWidth + (ea−eb)` 步，`ea−eb < 0` 不进循环）与选择器 `WumingFpSlow`（`DIV`/`SQRT`/`REM` × ft/fo，**只 start 被选中的那一个实例**）。除法把手算的**精确截断商** `Q = floor(|a|/|b|·2^N)` 与余数非零标志一起交同一舍入原语（仍单次舍入）；开方逐位 restoring、radicand 按奇偶 `p` 对偶数指数；取余由 `2·rem` 与 `|b|` 及商奇偶定就近取偶，**结果精确、不置 `NX`/`OF`/`UF`**。`DZ` 由本族首次在指令级产生：`±Inf` 值走 `in.isInf`、`DZ` 位走 `infiniteExc`，两者同拍置（`0/0`、`Inf/0`、`NaN/0` 均不置 `DZ`）；`0/0`、`Inf/Inf`、`sqrt(负数)` ⇒ canonical qNaN + `NV`；qNaN 传播 payload（符号清 0，同 hardfloat；softfloat 保留符号——一例模型only）、sNaN ⇒ canonical + `NV`；`forem` 三边界（`rfHC`±Inf、`rfHD`±0、sNaN）⇒ `NV`+qNaN，`rfHD`±Inf/`rfHC`±0 ⇒ 原样返回。`WumingDecoder` 解 6 条（`orrr` 4 + `orri` 2，`foroot`/`ftroot` 仅 n = 2，其他 ILLI；目的 `rf0` ⇒ ILLI）；`WumingCore` 增第 14 态 `sFpSlow`（`EXEC` 发 `start`、`done` 拍写回并送标志）。周期实测：fo 的 div/sqrt **56 拍**（`sigWidth+3`，与操作数无关）、`forem` = `sigWidth+(ea−eb)+1`（d = 1/10/100/1000 → 55/64/154/1054）。工具：`fp_ref` 增 `round_ratio`/`round_prefix` 与三条精确 oracle + `divrem` 性质自检（Fraction 精确比对）、`fp_unit` 增 6 个 clocked op（div/sqrt 与 hardfloat `DivSqrtRecFN_small` 双对照）、`fp_sweep` 增 7 组 + `divrem_nan`（模型only）+ 10 条合法性镜像，新增 `tests/inst/fp/divrem.yaml`（32 例，本核 == YAML == QEMU）。
  - 执行者：engineer

- **2026-11-11 `m12-chipyard-013`**
  - 摘要：**FP 算术族（加/减/乘、融合乘加、比较、最小最大）**。`WumingFP.scala` 增 `WumingAddRecFN` / `WumingMulRecFN` / `WumingMulAddRecFN` / `WumingCompareRecFN` / `WumingMinMax` 与选择器 `WumingFPArith`：三种舍入运算都先把**精确**结果做成定点整数（加/减在对齐窗口内、乘法用 `2*sigWidth` 位精确积、FMA 用 `2*sigWidth+guard` 位窗口把精确积与加数对齐），再经**同一**舍入原语一次舍入 —— FMA 因此是**单次舍入**（`spec/SimRISC-07 §2.5`），与「先乘后加」在 spec 反例及其 fo 类比上结果不同（`tests/inst/fp/arith.yaml` 各留一例对照）。NaN 口径：加/减/乘传播第一个 qNaN 的 payload（`§1.4`）、FMA 恒 canonical qNaN（`§2.5`）、sNaN/`0×Inf`/`Inf−Inf` ⇒ `NV`，且 NaN 乘数下 Inf 因子不构成无穷积（`qNaN×Inf+(−Inf)` 不置 `NV`）；比较的无序结果按 quiet/signaling 取 qNaN/sNaN（符号位 0），signaling 形式对任何无序（qNaN 或 sNaN）置 `NV`、quiet 形式不置（`§4`，IEEE 754-2019 §5.7.1）；最小最大按 `§2.4`（`−0<+0`、单 NaN 返回数、双 NaN canonical qNaN、sNaN⇒`NV`）。`WumingDecoder` 解 14 条 `orrr` + 2 条 `rrrr`（`opc 0x5E/0x5F`，单目的）；`WumingCore` 把算术标志送 `rf.io.fflags`（**首次由算术抬起 `OF`/`UF`/`NX`**）。工具：`fp_ref` 增五个精确 oracle（`round_dyadic` 统一入口）、`fp_unit` 增 16 个 op（含 hardfloat `AddRecFN`/`MulRecFN`/`MulAddRecFN`/`CompareRecFN` 对照）、`fp_sweep` 增 12 个 `arith_*` 组 + `cmp_nan` 组（均入 QEMU 三方对照）+ 12 条合法性镜像，新增 `tests/inst/fp/arith.yaml`（28 例，本核 == YAML == QEMU）。
  - 执行者：engineer

- **2026-11-11 `m12-chipyard-012`**
  - 摘要：**FP 转换族接入（浮点↔整数 / 浮点↔浮点 / 复制）**。`WumingFP.scala` 增三个单元并合成 `WumingFPConvert`：`WumingRecFNToIN`（f2i，饱和 + `NV`，`NX` 与 `NV` 互斥）、`WumingINToRecFN`（i2f，整数规格化后走同一舍入原语，只可能 `NX`）、`WumingF2F`（`ft2fo` 精确 / `fo2ft` 六档且**溢出恒 ±Inf + `OF`**，与 IEEE 按方向取最大有限值不同——`spec/SimRISC-07 §1.4`/`contract-fp §2`）。`WumingDecoder` 解 20 条转换：15 条六档（`encode_onehot`）、3 条 SBZ（`encode_sbz`）、2 条窗口复制（复用 `sCopy`，`rf0` 作目的 ⇒ ILLI）；`WumingCore` 每拍接入转换单元并把其标志送 `rf.io.fflags`（**首次由硬件抬起 `NV`**；`DZ` 通道在单元台单独验证，其真实生产者属除法），`WumingRegFile` 增 `fcsrMode` 输出供 `immu6=0x20` 读 `rf0[33:32]`。工具：`fp_ref` 增三条精确转换 oracle、`fp_unit` 增 11 个 op（含 hardfloat `RecFNToIN`/`INToRecFN` 对照与 `infiniteExc`/DZ 通道）、`fp_sweep` 增 9 组镜像（281 例/23 故障）、新增 `tools/chipyard/inst_case_run.py`（把 `tests/inst` 向量文件驱动到本核，与 QEMU 同镜像比对）。
  - 执行者：engineer

- **2026-11-11 `m12-chipyard-011`**
  - 摘要：**FP 基础设施（recFN / 六档舍入 / 异常标志 / 分类）**。新增 `wuming/common/WumingFP.scala`：recFN 编解码（`recFNFromFN`/`fNFromRecFN`/`rawFloatFromFN`/`rawFloatFromRecFN`，语义对齐 berkeley-hardfloat，未引入其依赖）、单一舍入原语 `WumingRoundAnyRawFNToRecFN`（RNE/RTZ/RDN/RUP/RNA 五档 + `immu6` 六档解码、tininess 按 spec 取**舍入后**、`rf0[4:0]` 顺序的异常标志、qNaN payload 传播）、`classifyRaw`（`SimRISC-07 §5` 位序，bit0 sNaN … bit9 +Inf）、`signInject` 与 `WumingFcsr`（sticky 标志、`[33:32]`/`[4:0]` 写掩码、只读 qNaN 位）。`WumingRegFile` 打开 `rf` 银行并把 `rf0` 接到 `WumingFcsr`；`WumingDecoder` 解 `ld/st/ldm/stm` 的 rf 形式、`set.w rf`、`cs.* rf`、`rd2rf`/`rf2rd`、`ftcls`/`focls`、`ftsgnj`/`ftsgnn`/`fosgnj`/`fosgnn`；`WumingCore` 新增块分类状态 `sCls`（每拍一个元素）并修正 `cs.*` 第一类「恒写两值之一」的语义（第二类才条件写）；`WumingALU` 增 `SET_W`/`SGNJ`/`SGNN`。另增仅用于单元验证的 `WumingFPUnitHarness.scala`（旁挂一个 hardfloat 实例做 RTL/RTL 逐例对照，不进 SoC）。工具：`tools/chipyard/fp_ref.py`（独立模型 + 精确有理数 oracle）、`tools/chipyard/fp_sweep.py`、`tools/chipyard/fp_unit/`（Verilator 单元台）。
  - 执行者：engineer

- **2026-11-11 `m12-chipyard-010`**
  - 摘要：**位操作 + 原子 + 杂项（收齐非 cfx 指令）**：`rev.o/.t/.w/.b`（块内单元反序，`k` one-hot 且 `< S`）、`rol` 四位宽（`orrr`/`orri`）、`ctpop`/`ctlz`/`cttz`（`hd` = 有效位上界，全 0 ⇒ `hd+1`）、`clmul.o`（GF(2) 128 位积）；`lr`/`sc` 全部 24 条形式（保留标记 = 精确地址 + 宽度，`sc` 另比对 8 字节字值 ⇒ 与 QEMU 字粒度行为一致；`sc` 的 `rdHB = rd0` ⇒ ILLI、`lr` 的 `rdHB` 是 SBZ）；`swym`/`fence` 合法即 no-op（`fence` 的 `hb != 0` 或保留 `cfxha` ⇒ ILLI）；`cs.n/.z/.p/.eq/.ne` 条件赋值与 `rd2rd`/`ra2rd`/`rd2ra`/`rb2rb`/`rd2rb`/`rb2rd` 块赋值（新增 `sCopy` 状态）；`OPC-tetra/wyde/byte` 子表的算术/比较/移位补齐（窄位宽值语义 + 按宽度的除法定值）。新增 `tools/chipyard/bit_sweep.py`（964 条 `tests/inst` 向量分三组镜像 + QEMU 同镜像比对 + 3 条保留标记探针 + 周期探针）。
  - 执行者：engineer

- **2026-11-11 `m12-chipyard-022`**
  - 摘要：**修复预取回归（`ISS-382`）**：`WumingCore` 的预取地址合法性改判**待发** beat 的地址（`pfNextAddr = Cat(0, pfBeat, 0)`），不再用已锁存的 `pfReqAddr`/`pfReqBeat`（复位值 0 ⇒ 地址 0 不在 Tiny 三段窗口 ⇒ `pfWanted` 恒假、预取从未发起）。400 条直线 `or.o`：应用段 `prefetch` 0 → 218、需求取指 212 → 1，跨 beat 中位 8 → 1 拍（199 次全为 1）；数据优先仍为 `fetch_requests_after_data_request=0`；273 例 md5 不变。`fetch_probe` 的 `xbeat`/`timing` 程序改以 `SYS_EXIT` 收尾（`m12-009` 起 `UNDI` 会进 hmon 异常路径，不再 halt）。
  - 执行者：engineer

- **2026-11-11 `m12-chipyard-009`**
  - 摘要：**控制流全形式 + 返回地址栈**（`spec/SimRISC-06`、`spec/SimRISC-00 §2.4`）：解码器补 `br.eq`/`br.ne`（`rrii`）、相对 `jump`（`iiii`）、`call`（`iiii`/`rrii`）与 `ret rdHA, imms18`（`rd0` 配非零立即数 ⇒ ILLI）；`WumingRegFile` 把 `ra` 银行升级为 RegRAS（`ra1`–`ra63` + `RACNT`/`MRPTR`，`ra0` 读出 `{SBZ,RACNT,MRPTR}`、写入拆分、`[63:54]` 写无效），新增单周期 RAS 操作（PUSH/FOLD/SPILL/POP/DEC/REFILL/CONSUME）；`WumingCore` 在 `EXEC` 组合完成 C1/C2/C3a 与 D1/D2/D3，C3b 溢出走数据端口 8 字节存储、D4b 下溢走 8 字节读取，两者都先判定后修改（精确异常）；新增 `RASOF`/`RASUF`（`1<<10`/`1<<11`）进 hmon。返回地址 = 当前 `call` 地址 + 4。
  - 执行者：engineer

- **2026-11-08 `m12-chipyard-001`**
  - 摘要：**chipyard 首次进入 v5 补丁集**（`ADR-0024 D1` 就地修订，用户裁定 B）：新增 `generators/dadao-wuming/**`（`WumingTile extends BaseTile`、自声明 `TLClientNode`/`TLIdentityNode`、`WumingCoreParams` 不继承 `CoreParams`、桩核）、`generators/chipyard/src/main/scala/config/DadaoConfigs.scala`（`WumingTinyConfig`）、根 `build.sbt` 的 `wuming` 项目与 chipyard 依赖、`PeripheralFragments.WithBootROM` 的 BootROM 资源名参数。
  - 执行者：engineer

- **2026-11-09 `m12-chipyard-002`**
  - 摘要：**落地 `Machine-v5-Tiny` 48 位核内地址图**（`spec/Machine-v5 §1.1`）：新增 `WithDadaoTinyAddressMap` fragment（BootROM `0xffff_ffff_0000`/64 KiB/复位向量=起始、SRAM `0xffff_ff00_0000`/8 MiB 经 `BankedScratchpadKey` 落到 MBUS、`ExtMem`/`ExtTLMem` 关掉、BootROM 不附 DTB），`WumingTinyConfig` 改用该 fragment 并把 BootROM 镜像名指向 `/dadao/bootrom/bootrom.tiny.img`；Tiny bootrom 以文本 hex（`bootrom.tiny.hex`）+ `build.sbt` 的 `resourceGenerators` 解码入库（补丁集不能带二进制）；桩核改为「复位向量取指 + SRAM 写读回」三拍探针，`testAddress` 由 `0x8000_0000` 改为 SRAM 基址。
  - 执行者：engineer

- **2026-11-09 `m12-chipyard-003`**
  - 摘要：**BootROM → SRAM `+loadmem` 最小闭环**：`WumingCoreStub` 由三拍探针改为最小启动执行器（`set.zw`/`or.w`/`jump`/`ld.o`/`st.o` 子集，IP=当前指令地址、rb0/rd0 约定按 `spec/SimRISC-00`），到达子集外编码即 halt → `reportCease`；新增 `WumingLoadMem`（tile 内 TileLink 主端口加载器，自带大端 ELF64 `PT_LOAD` 解析、`p_memsz` 零填、SRAM 窗口校验、逐字回读比对，回读通过才释放核；不用 stock `SimDRAM`——Tiny 无 SimDRAM 实例、其 `+loadmem` 只写 host backing，且 fesvr 大端受限）；`WumingCoreParams` 新增 `loadMemBase/loadMemSize`（无默认，`WumingTinyConfig` 从地址图传入）；新增最小程序 `tests/shared/bootrom/tiny_smoke.{S,lds}`（`make build-bootrom` 产出 ELF）；新增 `iobinders/WumingSuccess.scala`（把 tile cease 接到 TestDriver `$stop`——chipyard 默认不连）。
  - 执行者：engineer

- **2026-11-09 `m12-chipyard-004`**
  - 摘要：**harness 侧 semihosting 应答者（最小 5 服务）**：核内 `WumingCoreStub` 识别 `trap` 的 semihosting tag（`immu18[17:8]==0x3FF`）并把 `(op, rb16, rd8, IP)` 经 **DPI 导出端口**抬到 tile 边界（核内无宿主调用）；新增 `WumingSemi`（LazyModule + TileLink 读引擎）、`wuming/vsrc/WumingSemi.v`（DPI 桥）、`wuming/csrc/WumingSemi.cc`（table-driven 宿主模型：WRITEC/WRITE0/WRITE/CLOCK/EXIT，未实现服务号显式报错，`SYS_EXIT` 以进程退出码实现有界停机）。另新增 `tests/shared/bootrom/semihost_smoke.{S,lds}` + 消息 include 与四个 `--defsym` 变体（三平台 smoke、guest FAIL、未实现服务、`SYS_WRITE`）。
  - 执行者：engineer

- **2026-11-09 `m12-chipyard-005`**
  - 摘要：**真核起点：寄存器堆 + 解码器 + 整数 ALU**。`WumingCoreStub` 由 `WumingCore` 替换（`WumingRegFile` / `WumingDecoder` / `WumingALU` 三个子模块）：`rd`/`rb` 双 bank，`rd0` 读 0、`rb0` 读当前 IP（只读），`rrrr` 双目的；解码 `orrr`/`orri`/`rrrr`/`riii`/`rrii`/`rwii` 六种格式，覆盖 SimRISC-04（64 位算术/逻辑/移位/扩展/比较/乘除）、SimRISC-05（`add.o`/`sub.o`/`cmp.uo` dbb、`add.si`/`aip.si`）与 SimRISC-08（32 位同族）；`ld.o`/`st.o`/`jump rrii`/semihosting `trap` 沿用而不回归。非实现编码不再静默：已定义未实现 ⇒ ILLI，QFC/子表空白 ⇒ UNDI（`contracts/legality_rules.yaml`），并实现 `dst_rd0`/`dst_rb0`/`dst_dual_same`/`encode_sbz` 合法性检查。ALU 口径按 `spec/SimRISC-04 §1.1`：`rrrr` 无符号加减的高半是**进位/借位（0 或 1）**、有符号加减的高半是 128 位和/差的高 64 位、乘法的两个变体都是完整 128 位积的高半。
  - 执行者：engineer

- **2026-11-10 `m12-chipyard-007`**
  - 摘要：**Tiny 固定 BootROM 固件 + `power → hmon → 应用` 移交**。新增 `tests/shared/bootrom/tiny/{power.S,hmon.S,*.lds}`（power 校验 image index table → 逐 8 字节复制 hmon 段到 `0x0fff_0000_0000` → 幂等写 `cg3 rc10` → `trap cfx_hmon, 0x30001` → hmon 校验 `CFXTRAP`+magic → `escape ...,+4` → 跳固定入口；hmon handler 共 56 B）与 `tools/testcases/arch/build_tiny_bootrom.py`（64 KiB 镜像：power 8 KiB / hmon 8 KiB / 保留 40 KiB 全零 / 表 8 KiB，链接断言 + 构建期校验，超限即失败），镜像以稀疏文本 hex 入库、`build.sbt` 资源生成器解码；应用侧新增 `tiny_crt.S`（入口设 SP，与测试程序同一 ELF）。SoC：hmon SRAM 为第二个独立 TL 从设备（64 KiB，`ARWXC`），`WumingLoadMem` 增装载契约（`e_entry` 必须 = 固定入口、`PT_LOAD` 命中 BootROM 或 hmon SRAM ⇒ 显式失败）；核内补最小 cfx_hmon 移交面（`br.*`/`trap→CFXTRAP`/`escape`/`cfx2rd`/`cfx2rc`、cause 帧、`excp_vector`），五类同步异常与完整寄存器组仍归 `m12-019`。
  - 执行者：engineer

- **2026-11-10 `m12-chipyard-018`**
  - 摘要：**取指/访存拆成两个 TileLink 客户端 + 8-beat 取指队列 + 12 态状态机骨架**。`WumingTile` 新增 `fetchMasterNode`/`dataMasterNode`（各 `IdRange(0, 3)`，都进 tile 内 `portXbar`），`WumingCore` 改为 `imem`/`dmem` 两个 `TLBundle`（A/D 通道与请求状态各自独立）；`WumingCoreParams` 新增 `fetchDepth = 8`，核内改为 8-beat 环形取指队列 + 顺序预取（source 0 需求、1/2 预取槽，命中 1 拍、投机 `denied` 不报错）；状态机按 `m12-006 §5.1` 落 12 态（`IDLE/FREQ/FWAIT/EXEC/TRAP/SEMI/EXC/MREQ/MWAIT/SLOW/FAULT/HALT`），R1 = C（移位/位域走 `SLOW` 2 拍、简单算术 1 拍），`EXC` 暂只记 cause 后进 `FAULT`（cfx 帧/向量归 `m12-019`）；诊断 `printf` 增 `cycle=`。273 例与 `m12-005` 逐字节一致（md5 `2d4d9465…`）。
  - 执行者：engineer

- **2026-11-10 `m12-chipyard-020`**
  - 摘要：**取指预取优化：4 个预取槽 + 数据优先仲裁 + SRAM 往返延迟计数**。`WumingTile` 取指客户端 `IdRange(0, 3)` → `IdRange(0, 5)`（1 需求 + 4 预取；`fetchDepth` 仍 8，source 回收/flush-stale 语义不变），`WumingCore` 的预取槽由 A/B 两个具名寄存器改为 4 槽 `Vec`（源 ID = 槽号 + 1，回复按源匹配）；**数据优先**：`MREQ`/`MWAIT`（数据端口有未完成请求）期间不发起新预取，已发出的不清空、回复仍入队；发射条件由 `qCount =/= 0 && !waitBeat` 放宽为 `qCount =/= 0 || waitBeat`（FWAIT 等已在途 beat 时继续填充槽位，否则 4 槽无效）；新增需求取指往返延迟计数器（A 握手 → D 回包拍数，`fetchresp`/`prefetch ... lat=` 诊断可见）。实测跨 beat 代价中位 8 → 1 拍（注入回 2 槽：中位 5、102/204 次 > 2 拍），SRAM 往返 4/6 拍 ⇒ 4 槽（需求 3）足够；273 例 md5 不变。
  - 执行者：engineer

- **2026-11-11 `m12-chipyard-019`**
  - 摘要：**cfx 寄存器组 + 五类同步异常进 hmon**。`WumingCore` 实现 `cfx_hmon`(cfx3)/`cfx_power`(cfx63) 的 `cg3`（四类同步 mask、`cfx_intr_mask`、`switch_run_mode` 恒 3、`excp_vector` 写忽略低 2 位）、`cg5`（`excp_prev_run_mode`、cause 帧）、`cg7`（16 块空间描述，只读写 `CFXREG`）与 `cg8 rc1`（未实现 ⇒ `CFXREG`）；`cg3` 仅 hypv 可访问，其它运行模式 ⇒ `CFXREG`；`CFXMEM`/`ILLI`/`UNDI`/`MALIGN`/`IALIGN` 五类同步异常写 `excp_cause_*` 并跳到 `excp_vector`（不再进 `FAULT`），`escape` 恢复 `excp_prev_run_mode`；未 backing 的访存/取指按 `TLEdge` 的 **safe** 合法性判 `CFXMEM`（fast 版对未映射地址会误报合法）。
  - 执行者：engineer

- **2026-11-11 `m12-chipyard-008`**
  - 摘要：**访存族：全宽度 `ld`/`st` + `ldm`/`stm`**。`WumingRegFile` 增加 **`ra` 银行**（第三组 64×64，`ra0` 可读写；RAS 语义归 `009`），读写口改为 2 位 bank 选择（rd/rb/ra）；`WumingDecoder` 覆盖 `SimRISC-01` 全部整数宽度（`ld.{ub,uw,ut,sb,sw,st}`/`st.{b,w,t}` + `ld.o`/`st.o` 的 rd/rb/ra 银行）与 `ldm`/`stm`（`rrri`，`mreg_zero`/`mreg_range_overflow`/`dst_rd0`/`dst_rb0` 合法性）；`WumingCore` 新增统一访存序列：**8 字节 beat 分组**（`stm` 逐元素打包 + byte-mask `Put`，`ldm` 逐元素提取写回）、**整段预检**（对齐 + Tiny 三段窗口，第一拍前）⇒ 精确 `MALIGN`/`CFXMEM`，中途 `denied`/`corrupt` ⇒ `CFXMEM` 进 hmon（可重入）；地址合法性改为 **Tiny 三段窗口**判定（`spec/Machine-v5 §1.1`），不再只看协商 manager 集合（否则地址 0 的 debug-controller 会把未映射访问变合法）。`tools/chipyard/mem_sweep.py` 驱动 `tests/inst/base/mem-*.yaml`（167 例：90 语义/边界 + 77 故障），`inst_sweep.py` 的「已定义未实现」探针改到 RF 银行形式（`ld.t rf`，FP 归 `011`）。
  - 执行者：engineer

- **2026-11-09 `m12-infra-003`**
  - 摘要：**子模块补丁集试点（testchipip）**：`generators/testchipip` 新增子模块补丁集 `submodules/testchipip/{series,patches/}`——`SimDRAM.cc` 的 `loadmem_memif_t::get_target_endianness()` 改为由 `+loadmem_be` plusarg 显式返回 `endianness_big`（默认 little 不变，stock RISC-V 配置行为不动），`SimDRAM.v` 的 `MEM_BASE` 默认值改为 `64'h0`（原无位宽 32 位推断会截断 48 位基址）；组件补丁集与子模块补丁集的分工/声明/门控见 `docs/Process-01 §14`。
  - 执行者：engineer

- **2026-11-12 `m12-chipyard-015`**
  - 摘要：**FP 取整 / 缩放 / 符号收尾（FP 47 条指令全部落地）**。`WumingFP.scala` 新增 `WumingFpRound`（`roundToIntegral`：`2|x|` 定点化取整数部分 + round/sticky 位，六档方向由核解析，`|x| ≥ 2^p` 原样返回、`±0` 保留符号、NaN 归一为 canonical qNaN、只有 `0x20` 且结果 ≠ 输入才置 `NX`）与 `WumingFpScale`（`scaleB`：只搬 recoded 指数再交给**同一个**舍入原语一次舍入，`n` 为 `rd` 组 64 位有符号整数并按上下界饱和，`OF`/`UF`/`NX` 全由该原语的 IEEE 判据给出）；两者合成 `WumingFpMisc`（1 拍）。`WumingDecoder` 补 `ftrnd`/`fornd`（`immu6` 六档 one-hot，`encode_onehot` 合法性）与 `ftsclb`/`fosclb`（第三操作数取 **rd 银行**，`rd0` = 指数 0）；`WumingCore` 下发/写回/累积标志；单元台新增 op 47–50（`roundToIntegral` 无 hardfloat 对应模块 ⇒ 只对精确 oracle，`scaleB` 对 `2^n` 可表示范围的 `MulRecFN`）。`tests/inst/fp/{roundint,sign}.yaml` 新增、`scaleb.yaml` 补 `fosclb rd0`。
  - 执行者：engineer

## M13

- **2026-11-15 `m13-chipyard-003`**
  - 摘要：**删 `ft2ft`/`fo2fo`、加同组块复制 `rf2rf`**（`spec/SimRISC-02 §1` + `contracts/opcodes.yaml::rf2rf_orri_rf`，`m13-spec-010`）。`WumingDecoder`：`0x44/0x02`（`ft2ft`）与 `0x44/0x0A`（`fo2fo`）两条译码与 `fpCopy` 删除，两条编码回到空置槽位 ⇒ **UNDI（`0xF9`）**（与 QEMU `insn.decode` 空白单元格 ⇒ UNDI、gem5 `FaultUNDI` 同口径）；`0x40/0x3C`（OPC-octa `111-100`）新增 `rf2rf`，复用 `sCopy` 块复制执行路径（每拍一个元素、`w0Data = rf.r0Data`、`w0Ft` 不置 ⇒ **整 64 位逐位搬移**、不换算不舍入不置标志）。合法性与既有同组复制同集（`mreg_zero`/两处 `mreg_range_overflow`/`mreg_range_overlap` 含完全重合），另加 **`dst_rf0`**：`blockCopy` 新增 `forbidRf0Dst` 参数（目的窗口自 `hb` 升序 ⇒ 含 `rf0` 当且仅当 `hb == 0`），`rd2rf`/`rf2rd` 仍允许 `rf0` 作目的、`rf2rf` 的源 `rf0` 合法且读出完整 64 位；六类非法全在译码组合逻辑里判定，`EXEC` 的 `execFault` 先于进入 `sCopy` ⇒ **任何寄存器写之前进入异常、目的未被修改**。子表位图同步（`octaRows` 行 7 `0x6F→0x7F`、`rfRows` 前两行 `0x4F→0x4B`）。**sim 重建**（`make verilog` 67 s + Verilator 增量重编 44 s，`JOBS=32`）：新 md5 `4e072a711afdca8a36788f9a9958e896`（旧基线 `079ae015…` 作废）。**验证**：`tests/inst/02-reg-copy/rf2rf_orri_rf.S` 三平台 7/7 镜像（链例 11 点/88 B 三方 rc=0 且字节流全等；6 个故障例三方 rc=0xF8）；chipyard 侧 n=3 探针（三元素逐位 + 源不变）三方 48 B 全等；退役编码三平台探针 `0x44080000`/`0x44280000` 三方 rc=0xF9。注入 3 路（放行目的 `rf0` ⇒ 点 12 红；重叠放宽为「仅完全重合」⇒ 点 16 红；位图 `rfRows` 复原 `0x4F` ⇒ 退役编码 `0xF9` 失效红）均为真实重编后观测、`cp`+md5 还原后回绿；`check-patch-tree`（chipyard 段 0 问题）/`--source-state`（chipyard OK）/`check-component-changelog`/`check-no-residue`/`check-inst-asm` 全绿。
  - 执行者：engineer

- **2026-11-14 `m13-chipyard-002`**
  - 摘要：**`sc` 保留判据严格按 spec 去掉「整字值比较」**（`spec/SimRISC-12 §1`「保留机制」；用户 2026-11-14 裁定「ISS-435：严格按spec来」）。`sc` 成败只由「`resvValid` 仍持有 + 键匹配（`lr` 的**精确地址 + 访问宽度**）」决定：删除 `resvWord` 寄存器与其比较路径、`scCheckFail` 写回路径（`w0En`/`w0Idx`/`w0Bank`/`w0Data`）与 `word-changed` 跟踪打印；`sc` 命中后的预写拍读只保留读写能力预检，**其值不参与判据**。清除事件保持 spec 口径：另一条 `lr`、`sc` 自身（成败都清）、异常/中断进入；**同 hart 普通 store 不清除**（同址同宽写后 `sc` 仍成功）。同一份 9 点探针：改前（word 值判据）`P1`（同字另一字节）/`P2`（同字其余字节）/`P3`（同址同宽写）后 `sc` 均为 1（失败），改后均为 0；`P4`–`P9`（另一条 `lr`、自消费、二次 `sc`、异宽、异址、异常/中断进入）两版一致。`tests/inst/12-misc` 的 24 个 `lr.*`/`sc.*` id × 三平台 66/66 镜像逐字节一致；`check-inst-asm` 897/897。**GAP**：多 hart 对同一 (addr,width) 的 store 清除依赖一致性事件，`WumingTinyConfig` 单 hart 无观测载体，不造用例。补丁从共享源树整体重导出（同时带出同树已提交的 `m12-chipyard-016` semihosting 改动）。
  - 执行者：engineer

- **2026-11-14 `m13-chipyard-001`**
  - 摘要：**单精（ft）写入宽度收口：ft 结果只写 `[31:0]`、`[63:32]` 保持**（`spec/SimRISC-01 §4` 注 + `spec/SimRISC-07 §1.3` + `contract-fp §1`，用户 2026-11-14 裁定）。`WumingRegFile` 的 w0 写口新增 `w0Ft`（`sf(idx) := Cat(sf(idx)(63,32), data(31,0))`），`WumingFcsr` 新增 `writeFlagsOnly`（ft 写 `rf0` 只落到 `[4:0]`，舍入模式 `[33:32]` 不动）；`WumingDecoder` 逐族置位：`ld.t`/`ldm.t`（并去掉 tetra 装载的符号扩展）、`ftadd/ftsub/ftmul`、`ftfma`、`ftdiv/ftrem/ftroot`、`ftrnd`、`ftsclb`、`ftmin/ftmax`、`it2ft/io2ft/ut2ft/uo2ft`、`fo2ft`、`ftsgnj/ftsgnn` 与 `ft2ft`（`fpCopy(false)`，只搬低 32 位）；`fo2fo`（`fpCopy(true)`）、`rd2rf`/`rf2rd`、`ld.o`/`ldm.o`、`ft2fo` 保持 64 位。工具：`fp_sweep.py` 新增 `ftwidth` 组 29 例（每例先把目的高半填非零图案，含 `ld.t rf0 ⇒ 0x7FF8_0000_7FC0_001F`、`ft2ft` 单例/三元素块、以及 5 个 64 位反向对照），并修掉一处**镜像自毁**隐患：`DATA` 原在 `ENTRY+0x2000`，当组的代码长大越过 4 KiB（本组的 29 例已越过）时运行期 seed 会写坏程序尾部的 `SYS_WRITEC` 循环 ⇒ 移到 `ENTRY+0x30000` 并在 `build_group` 加「镜像不得触到 DATA」断言；`rfmem`/`sign`/`divrem`/`rnd` 等组的 ft 目的先清零高半，使旧期望在新写入宽度下仍成立。同一镜像旧实现 24/29 红、新实现 29/29 绿。
  - 执行者：engineer

## M16

- **2026-11-16 `m16-chipyard-002`**
  - 摘要：**cfx 独立为 `generators/dadao-gewu/`（sbt 项目 `gewu`）generator**（`ADR-0053 D1–D7`）。`WumingCore.scala` 的 cfx 状态与判权/分发（9 组寄存器、cg3/cg5/cg7 读写判据、`escape` 合法性、异常帧写入、运行模式）整体搬进 `GewuFile`（`GewuFileIO` 19 个字段：读写地址/数据/许可、异常入口、`escape`、`redirect`、`monitorHa`/`vector`/`frameValid`/`cause*`/`prevMode`/`runMode`/`intrMask`）；根 `build.sbt` 三处接线（新增 `gewu` 项目 `dependsOn(rocketchip)`、`baseProjects` 加入、`wuming` 改 `dependsOn(rocketchip, gewu)`），`generators/dadao-gewu/` 内 `wuming` 出现 0 次。D4：`Gewu` 只出 `redirectValid`/`redirectTarget`，`ip`/flush 仍由核驱动（异常入口用 `gewu.io.vector`、`escape` 提交用 `redirect.target`；两者不可共用一个受 `excp.valid` 影响的 mux，否则 `escape` 目标 IALIGN 失败那拍会跳错地址并把 `finish` 的取值与 `excp` 事件接成组合环）。D5：新增 `GewuParams`（cfx 序列 + 帧归属 + 位宽 + 运行模式编码），由 `WumingGewuParams` 从地址图注入，`gewu` 内无机器常量。D6/D7：寄存器名仍 `cfx_*`、`spec/` 不改名；`WumingDecoder.scala` 的 cfx 解码留在核内（35 行/42 处不变）。**sim 重建**（`make verilog` + `make`，`JOBS=32`）：新 md5 `bd5e75b3a64044b4cb69d20c298f080d`（旧基线 `4e072a71…` 作废），两次独立重建字节相同。**验证**：改前/改后两版同一批 29 镜像（`trap_ciii_cfx`/`escape_ciii_cfx`/`cfx2rc_crrr_cfx`/`fodiv_orrr_rf`/`add.so_rrrr_rd`）的 `semi.out` 逐字节、退出码、每条 `cycle=` 值全等；注入 5 路（`cfxVector` 写回 +4 ⇒ 1 例红、`escape` 去掉当前-cfx 判据 ⇒ 红、`GewuParams` 帧归属改 `cfx_power` ⇒ 红、`runModeReset` 改 1 ⇒ 红、`redirectTarget` 接 0 ⇒ 红）+ 1 路不可观测项（`escape` 的「帧有效」判据：帧无清零路径，与用例自记 GAP ③ 一致），每路 `cp`+md5 还原并重建后回绿；`make_patch.py` 幂等（23 patches / 二次 0 写入）、`check-patch-tree` chipyard 段 0 问题、`check-source-state` chipyard OK。
  - 执行者：engineer
