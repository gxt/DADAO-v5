# ADR-0062: 异常原因编码扁平化（PTW 权限/访存故障脱离 `CFXPERM`/`CFXMEM` 大类）

**状态**：Accepted（2026-11-24；D1–D6 经用户逐条确认，收尾按用户 2026-11-24 补充裁定补 D6 与版本口径）
**日期**：2026-11-24
**关联**：`ADR-0056`（Accepted；其 **D2/D3 的「大类 + wyde 子原因」两级编码与 D4 的 `CFXPERM`/`CFXMEM` 混合语义由本 ADR 取代/修订**；D1 的低 16 位 one-hot 表、D5 退出码、D6/D7 的同步义务继续有效。**本 ADR 不改 `adr-0056` 原文**）；`ADR-0045 D6`（cfx 两轴权限）；`ADR-0061`（异步源标识，`[31:16]` 不属本 ADR）；`ISS-469`；`spec/DADAO-12 §1/§2.2.5/§2.2.6/§3.6/§4.1–§4.6/§5.2`、`spec/DADAO-13`、`spec/Kaiwu §1.2/§7.1`；`contract-see §6.1/§6.1.1`；`contract-tlb §8`；`m17-spec-001`（本 ADR）、`m17-spec-002`（正文改动）

## Context（背景）

`ADR-0056` 把 `excp_cause_id` 定成**两级**：`[15:0]` 置一个大类（`CFXPERM` = `1 << 7`、`CFXMEM` = `1 << 1`），原因细则放进该大类独占的 16 位 wyde（`CFXPERM` → wyde2 `[47:32]`、`CFXMEM` → wyde3 `[63:48]`）。该模型铺开到三实现与内核后暴露四个结构问题（用户 2026-11-24 指出并要求扁平化）：

1. **大类同名不同义**：`CFXPERM` 同时表示「PTW 页权限拒绝」与「cfx 来源掩码拒绝」；`CFXMEM` 同时表示「页表未映射 / A/D 回写失败」与「核内非法访存」。handler 必须「先看大类、再按 wyde 移位」两级解码。
2. **子原因位本身已足够**：`[32]`–`[38]` 单独即可说明权限原因，`[48]`–`[55]`/`[56]` 单独即可说明访存原因；大类位不含额外信息。
3. **`[39] NCFXPERM`/`[57] NONPTW` 是「否定位」**：它们只把「不属于页表路径」这件事再编码一遍，却要求所有生成侧（三实现 + Linux 头 + 各校验器）维护「wyde 归属互斥」这条跨字段不变量。
4. **扩展成本**：每加一个 PTW 原因都要同时维护大类与「另一 wyde 必须全 0」，校验器只能按两级结构写。

用户裁定改为**扁平位图**：一条异常只置**一位**（该位所属位图中的恰一位），大类位只在 D3 的两个专属场合使用。

## Decision（决策）

### D1 扁平位图模型

`excp_cause_id`（64 位）**不再区分「大类 + 子原因」两级**；位号直接给出原因：

- `[15:0]`：同步 cause one-hot，11 项**编码与位索引一字不改**（`CFXTRAP`=0 … `IALIGN`=13）；其中 `CFXMEM`（`1 << 1`）/`CFXPERM`（`1 << 7`）的语义收窄见 D3。
- `[31:16]`：异步源/未来大类段，**不属本 ADR 范围**（异步源身份口径见 `ADR-0061`）。
- `[39:32]`：**权限类位图**，有效位 `[32] NUPERM`–`[38] NXPERM`；`[39]` 删除（保留 0）。
- `[47:40]`：保留（必须 0）。
- `[55:48]`：**访存/缺失类位图**，`[48] IGPTRAP`–`[55] DSPFTRAP`；`[56] ADWBFAIL`；`[57]` 删除（保留 0）；`[63:58]` 保留（必须 0）。
- **独立性**：高位位图**可在 `[15:0]` 全 0 时独立成立**（PTW 故障即此形态，低位 cause 为 0）；`cause_id == 0` 表示无异常。
- **不变式（供校验器机械判定，取代旧「wyde 归属互斥」）**：
  1. 64 位内**恰一位**为 1（或整体为 0）；
  2. `CFXPERM`/`CFXMEM` 置位时 `[63:32]` **必须全 0**；
  3. `[32..38]` 任一置位时 `[15:0]` 必须全 0；`[48..56]` 任一置位时 `[15:0]` 必须全 0；
  4. `[39]`、`[47:40]`、`[57]`、`[63:58]` **恒 0**。

### D2 两类权限正交

- **cfx 来源掩码层**（`<mode>_cfxtrap`/`cfxmem`/`cfxreg`/`cfxexe` 掩码、`cg3 rc12` deleg 声明）⇒ **只置 `CFXPERM`（`1 << 7`），`[63:32]` 全 0**。
- **PTW 层**（页权限：HSJU 位不符、R/W/X 不符）⇒ **只置 `[32]`–`[38]` 之一，`[15:0]` 全 0**。
- 两层在编码上**互斥**：不存在「一个 `CFXPERM` 混着两种权限来源」的形态；内核按「`[15:0]` 是否非 0」即可分流权限来源。

### D3 删除 `[39]`/`[57]`，两类 cause 单一含义

- `CFXPERM`（`1 << 7`）= **仅**「cfx 访问被来源掩码拒绝」；置位时 `[63:32]` 全 0。
- `CFXMEM`（`1 << 1`）= **仅**「非 PTW 的核内访存故障」（核内地址空间非法访问/取指、未实现 cfx 的普通 `ld/st`、核内存储块故障、`ptw_enable = 0` 的访存）；置位时 `[63:32]` 全 0。
- **删除 `[39] NCFXPERM` 与 `[57] NONPTW`**（位保留、恒 0）；**不新增任何 cause 位**（同步 11 项不变）。
- **迁移映射（旧 → 新；`A|B` = 两位同置，`2^n` 即 `1 << n`）**：
  - `CFXPERM | 2^n`（`n ∈ 32..38`）→ `2^n`；
  - `CFXPERM | 2^39` → `CFXPERM`；
  - `CFXMEM | 2^n`（`n ∈ 48..55`）、`CFXMEM | 2^56` → `2^n`；
  - `CFXMEM | 2^57` → `CFXMEM`；
  - 其余 cause 的编码**不变**。
- **过渡**：允许实现在迁移期**同时接受**新旧两种形态（仅用于旧镜像过渡），但契约与测试的**断言**一律按新编码；迁移完成即删旧路径，不做长期双轨。

### D4 `cause_info` 口径

一个 cause/一组位只有**一种** `info` 类型；`info` 只承载地址类信息：

- `CFXPERM`（cfx 来源掩码拒绝）= **触发指令的地址**（与 `excp_cause_ip` 同值）；
- `CFXMEM`（非 PTW 核内访存）= **被访问的核内地址**；
- `[32..38]`（PTW 权限拒绝）= **访问的 VA**；
- `[48..55]`（PTW 缺失类）= **访问的 VA**；
- `[56] ADWBFAIL` = **PTE 物理地址**。

> 细分待 `m17-spec-002` 定稿：`cfxexe` 拒绝的 `info`（现行 = 目标 `IP`）与 `cfxmem` 轴拒绝的 `info`（现行 = 访存地址）是否沿用 `ADR-0056 D4`——两者同属 `CFXPERM`。本 ADR 只定粗口径，细分不在此处裁定（见「未定」3）。

### D5 影响面与迁移顺序

前一步落地并过门控才进下一步：

1. **spec/contract**（`m17-spec-002`）：`DADAO-12 §1/§2.2.5/§2.2.6/§3.6/§4.1–§4.6/§5.2`、`DADAO-13`、`Kaiwu §1.2`；`contract-see §6.1/§6.1.1`、`contract-tlb §8`（TLB-34/36/41 + §11 探针）。契约是 oracle 源头（校验器现场解析它）。
2. **QEMU**（Vast 可达面最全，参考实现）：`cpu.h` 的 `DADAO_SUB_*` 表、`helper.c` 的 raise 点与 `cause_id` 校验器。
3. **gem5**：`fs_machine.hh` 的 `CauseSub`/`checkCauseId` + `node_tlb`/`fs_tlb`/`node_cfx`/`tiny_cfx` 的 raise 点。
4. **RTL（chipyard）**：`GewuFile` 常量与校验器、`Wuming{Core,Ptw,Tlb}` 判定点传参；Tiny 结构性不可达 PTW 位，只改表与默认值。
5. **IDL**：`idl_exec.py` 的 `CFXMEM` 置位。
6. **测试**（`tests/arch`、`tests/unit`、`tools/`）：从契约解析位号的校验器、期望表、探针镜像与 `--self-test`。
7. **Linux**：`cause-sub.h` 名表、`fault.c` 分类、`pgtable.h`/`process.c` 注释与自检。

### D6 Vast 的 PTW 故障路由与退出码（用户 2026-11-24 补充裁定）

- **Vast 的 PTW 权限/缺失故障按当前运行模式进对应 monitor**：`user` → `cfx_umon`、`jail` → `cfx_jmon`、`supv` → `cfx_smon`、`hypv` → `cfx_hmon`，与普通同步异常同规则（`DADAO-12 §5.2`）。扁平化**只改编码，不改路由**；Tiny 无 PTW，不受影响。
- **Vast 的退出码不沿用** `Kaiwu §7.1` 的 `0xF0 | bit3:0` 形态（该形态是 **Tiny 测试机专有**）：Vast 的 PTW 故障测试**直接读 `cfx_<mode>_excp_cause_id`** 判因，不经 monitor 退出码编码。
- 含义：`Kaiwu §7.1` 的「monitor 位索引」表在 Vast 上**不承载** PTW 故障；两机型因此无编码冲突（Tiny 无 PTW、Vast 不走该退出码）。

逐文件清单见**附录 A**（2026-11-24 现场 `grep` 核实）。本 ADR **不改**任何 spec/contract 正文、平台代码与测试，**不升版本号**。

## Rationale（理由）

- **一位一义**：扁平后 handler 只按位区间取值，不再需要 `(cause_id >> 32)` / `(>> 48)` 两套移位加大类判定；`Kaiwu §7.1` 的 `bit3:0 = 异常位索引` 在「`[15:0]` 非 0」时完全不变。
- **删否定位**：`[39]`/`[57]` 携带的就是「大类位自己」；扁平后大类位不再兼指两类来源，否定位失去对象，保留反而与「`CFXMEM` 只表示非 PTW」矛盾。
- **不加 cause 位**：现有 11 个同步 cause 已覆盖全部异常种类（用户 2026-11-24）；加位会触碰 `Kaiwu §7.1`「编码冻结、不得重排」。
- **位布局不动**：`[32..38]`/`[48..56]` 位号沿用 `ADR-0056`，三实现、Linux 头、探针的位号表**无需重排**，只改置位规则、删两位、改校验器口径——迁移面可控。
- **保留 `CFXPERM`/`CFXMEM` 两个名字**：cfx 掩码拒绝与非 PTW 核内故障仍需独立的同步 cause（`Kaiwu §7.1` 退出码按低位索引编码）；改名会连带退出码与全部 handler，收益仅止于措辞。

## Consequences（影响）

- **必改**：`DADAO-12`（§1/§2.2.5/§2.2.6/§3.6/§4.1–§4.6/§5.2 + 变更记录，逐处见 A1）、`DADAO-13`（A2）、`Kaiwu`（§1.2 与 §4.4 路由见 A3；§7.1 退出码在 Vast 不适用，见 D6）；`contract-see §6.1/§6.1.1`（删两行 + 改归属段）、`contract-tlb`（TLB-33/34/36/41 + §11 三条探针）。
- **校验器改指**：现有脚本现场解析 `contract-see §6.1.1` 与 `adr-0056` 位表；`adr-0056` 原文不改（任务约束），故这些脚本必须**改指 `contract-see`/`ADR-0062`**，并把判定从「大类 + wyde 互斥」改为「64 位扁平 one-hot」。
- **风险**：旧镜像/旧期望表按两级编码断言，迁移期必红；测试侧须与实现同批切换（D5 第 1–2 步先行，测试在第 6 步统一改）。
- **不改**：`adr-0056` 原文（另立后续任务补「已被 0062 取代」注记）、`components/*/changelog.md`（历史记录）、`.tao/archive/**`、`docs/DDLN/**`。

## 已定（2026-11-24 用户裁定；原「未定 1/2」落定，正文改动归 `m17-spec-002`）

- **Vast 的 PTW 故障 monitor 路由**：见 **D6**——按当前运行模式进对应 monitor（`user`→`umon`、`jail`→`jmon`、`supv`→`smon`、`hypv`→`hmon`）。
- **Vast 的退出码**：见 **D6**——不沿用 `0xF0 | bit3:0`（Tiny 专有），测试直接读 `cause_id`。
- **版本号**：**不升号**。`spec/DADAO-12` 的改动并入现有**未发布** `0.8.0-rc` 段（不新开版本、不另起发布）；`contract-see` 内容随上游不升，改动只追加在 §7 变更记录；`contract-tlb` **不设版本号**（删除头部版本段，来源改指本 ADR，改动记录走文内条目）。

## 未定（待用户裁定；仅 1 条）

1. `CFXPERM` 的 `cause_info` 细分：`cfxexe` 拒绝的目标 `IP`、`cfxmem` 轴拒绝的访存地址是否沿用 `ADR-0056 D4`（本 ADR D4 只定「cfx 掩码 = 指令地址」粗口径）。

## 附录 A：影响清单（逐文件，2026-11-24 现场 `grep` 核实）

> 每条末尾「核实」给出该文件存在性与命中数（`grep -c`；首行 = 首次命中行号）。行号对应本 ADR 起草时的 `HEAD = 862b6f56`。

**spec（3 条）**

- A1 `spec/DADAO-12-SEE-主管系统运行环境.md`：§1 L41（路由句「未映射与 A/D 回写失败归 `CFXMEM`，权限拒绝归 `CFXPERM`」）；§2.2.5 L251；§2.2.6 L287/L289（第 1 步 `CFXMEM`+`[57]`）/L297（第 6/7 步与末段「wyde 归属」）；§3.6 L401/L407/L413–L426（两张 wyde 表，删 `[39]`/`[57]`）/L441–L445（归属互斥 → 扁平不变式）/L447–L451（info 口径）；§4.1 L503/L506；§4.2 L522；§4.3 L532；§4.4 L544；§4.5 L593；§4.6 L635；§5.2 L888（`CFXPERM` 行）/L893/L895/L900–L908（monitor 位索引表）/L916/L947/L951/L963；变更记录 L1152。—— 核实：`grep -c NCFXPERM` = 3，首行 L297。
- A2 `spec/DADAO-13-HEE-超管系统运行环境.md`：L13（hmon 同表 + 子原因指针）、L33/L34（`CFXPERM` 原因与 info 收敛）。—— 核实：`grep -c 子原因` = 1，首行 L13。
- A3 `spec/Kaiwu-测试机运行环境.md`：L56/L58/L60–L62/L64（Tiny/Vast 的 `CFXMEM`/`CFXPERM` 路由）、L94/L101–L102（两层次权限）、L119（A/D 回写失败）、L167/L171/L177（五类同步异常与 `info` 范围）、L475/L496/L498（`§7.1` 退出码位索引）。—— 核实：`grep -c CFXPERM` = 8，首行 L61；L475/L496/L498 的改动按 D6 写清「Tiny 专有、Vast 不适用」。

**contracts（2 条 + 1 条无改动核对）**

- A4 `.tao/contracts/contract-see.md`：§6.1 标题 L85（「11 项 cause + 18 位子原因」）、L87（`[15:0]` 分层表述）、L93（`CFXMEM` 行）、L96（`CFXPERM` 行）、L107–L109（wyde 归属 / handler 取值 / info）；§6.1.1 L111–L134（删 `[39]` 行 L124、`[57]` 行 L134，改 L113 取值形态）；§7 追加变更记录（L194 起）；头部来源 L5。—— 核实：`grep -c NCFXPERM` = 3，首行 L96。
- A5 `.tao/contracts/contract-tlb.md`：TLB-16 L41、TLB-33 L70、TLB-34 L71（wyde 归属 + 含 `NCFXPERM`/`NONPTW`）、TLB-35 L72、TLB-36 L73（退出码取低位索引，**与扁平模型冲突，须改写；Vast 不适用该码，见 D6**）、TLB-41 L84；§11 L90（取值口径）、L94（表头「大类 + 子原因位」）、L104（⑨a `NONPTW`）、L108（⑫ `NONPTW`）。—— 核实：`grep -c NONPTW` = 4，首行 L71。
- A6 `contracts/*.yaml`（机器可读数据）：**无需改**——`grep -rn 'CFXPERM|CFXMEM|cause' contracts/*.yaml` 仅命中 `contracts/linux-boot.yaml:23`（`required_terms` 里出现 `CFXMEM` 术语），不涉及位编码。—— 核实：命中 1 处，首行 L23。

**QEMU（2 条）**

- A7 `components/qemu/patches/target/dadao/cpu.h.patch`：L311–L346 的 cause/sub-cause 宏（`DADAO_CAUSE_WYDE2/WYDE3`、`DADAO_SUB_NUPERM`…、`DADAO_SUB_NCFXPERM` L346、`DADAO_SUB_NONPTW`）；注释 L325–L335（两级编码说明）。—— 核实：`grep -c DADAO_SUB_NCFXPERM` = 1，首行 L346。
- A8 `components/qemu/patches/target/dadao/helper.c.patch`：raise 点 L254（`CFXMEM|NONPTW`）、L264（`CFXPERM|NCFXPERM`）、L817–L842（PTW 权限）、L1039–L1097（缺失类/权限）、L1290/L3809（`ADWBFAIL`）、L2475（cfx 掩码拒绝）；校验器 L2356–L2385（大类↔wyde 归属）。—— 核实：`grep -c DADAO_SUB_NCFXPERM` = 2，首行 L264。

**gem5（5 条）**

- A9 `components/gem5/patches/src/arch/dadao/fs_machine.hh.patch`：L74–L96（`enum CauseSub`：`SubNcfxPerm` L84、`SubAdwbFail` L95、`SubNonPtw` L96）、L99–L100（wyde 掩码）、L104–L106（`checkCauseId` 口径）。—— 核实：`grep -c SubNcfxPerm` = 1，首行 L84。
- A10 `components/gem5/patches/src/arch/dadao/fs_machine.cc.patch`：`checkCauseId()` 实现（回写点调用处校验）。—— 核实：`grep -c checkCauseId` = 1，首行 L100。
- A11 `components/gem5/patches/src/arch/dadao/node_tlb.cc.patch`：L98（cfx 掩码拒绝）、L147–L167（missing/frag/hsju 子原因）、L254–L270（权限）、L308（`ADWBFAIL`）、L378/L486/L496/L514–L515（`NONPTW`）、L415–L443（缺失类）。—— 核实：`grep -c SubNonPtw` = 5，首行 L378。
- A12 `components/gem5/patches/src/arch/dadao/fs_tlb.cc.patch`：L52（`NONPTW`）、L68（`NCFXPERM`）。—— 核实：`grep -c SubNonPtw` = 1，首行 L52。
- A13 `components/gem5/patches/src/arch/dadao/node_cfx.cc.patch` + `tiny_cfx.cc.patch`：`NCFXPERM` 置位点（node L1247/L1330/L1335/L1407/L1412、tiny L383/L451/L488）与 `ADWBFAIL`（node L1470）。—— 核实：`grep -c SubNcfxPerm` node = 5（首行 L1247）、tiny = 3（首行 L383）。

**RTL / chipyard（6 条）**

- A14 `components/chipyard/patches/generators/dadao-gewu/src/main/scala/gewu/GewuFile.scala.patch`：L126–L150（编码注释）、L157–L176（`PERM_*` 与 `MEM_*` 常量，删 `PERM_NCFXPERM` L164 与 `MEM_NONPTW` L176）、L186、L218–L220（校验器规则）、L587（`enterCfx` 判序注释）。—— 核实：`grep -c PERM_NCFXPERM` = 1，首行 L164。
- A15 `components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingCore.scala.patch`：L62/L71（`NONPTW` 说明）、L1400–L1415（`enterHmonMem` 默认子原因）、L1441/L1452/L1511（`ptw_enable=0` 与非页表路径）、L1591–L1594/L1948（`NCFXPERM` 置位）、L2074/L2139（`ADWBFAIL`）、L2159（存储块故障）。—— 核实：`grep -c MEM_NONPTW` = 1，首行 L1406。
- A16 `components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingPtw.scala.patch`：L35/L63/L93（`ADWBFAIL` 说明）、L305（HSJU 子原因）、L417/L425/L451/L458（`MEM_NONPTW` 响应）、L491–L507（`ADWBFAIL`）。—— 核实：`grep -c MEM_NONPTW` = 4，首行 L417。
- A17 `components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingTlb.scala.patch`：L72（PTE PA 注释）、L323（`hsjuSub = PERM_NUPERM + runMode`）。—— 核实：`grep -c PERM_NUPERM` = 1，首行 L323。
- A18 `components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingParams.scala.patch`（L72）+ `.../chipyard/src/main/scala/config/DadaoConfigs.scala.patch`（L159）：Tiny 无 PTW ⇒ 全 `CFXMEM [57] NONPTW` 的注释与默认值。—— 核实：各 1 处，首行 L72 / L159。
- A19 `components/chipyard/README.md`：L227（编码段）、L230（Tiny 可达面「每一处 `CFXMEM` 都是 `[57] NONPTW`」）、L251/L262（A/D 回写失败）、L255/L267（探针判据）、L375（cache 脏行回写失败）。—— 核实：`grep -c NONPTW` = 2，首行 L227。

**IDL（1 条）**

- A20 `idl/tools/idl_exec.py`：L87–L88（`NONPTW_SUBCAUSE = 1 << 57`）、L182（`CFXMEM` 判定）、L594–L596（置位点）、L740（`CFXPERM` info 注释）。—— 核实：`grep -c NONPTW_SUBCAUSE` = 2，首行 L88。

**测试 / 工具（9 条）**

- A21 `tests/arch/ptw/check_ptw_regs.py`：L9/L93–L109（解析 `contract-see §6.1.1` + `adr-0056` 互校）、L237（`--self-test` 位号清单）。—— 核实：`grep -c adr-0056` = 2，首行 L9。
- A22 `tests/arch/ptw/check_ptw_walk.py`（L8 `adr-0056` 互校）、`check_ptw_tlb.py`（L6/L53）。—— 核实：各 1/2 处（首行 L8 / L6）。
- A23 `tests/arch/ptw/ptw_carrier_tlb.py`：L127–L137（wyde 解析注释）、L1371–L1372（子原因名表含 `NCFXPERM`）。—— 核实：`grep -c NCFXPERM` = 1，首行 L1372。
- A24 `tests/arch/ptw/expected.yaml`：L155/L160/L225/L230（`subcause: NONPTW`）、L133 起（`ADWBFAIL` 期望）。—— 核实：`grep -c NONPTW` = 4，首行 L155；`ADWBFAIL` 3 处，首行 L133。
- A25 `tests/arch/ptw/ptw_regs.S`（L22–L23/L152/L170）、`ptw_sig.S`（L343/L353）、`rtl-coverage.yaml`（L63/L82）、`gen_ptw_sig_tables.py`（L246）。—— 核实：`NONPTW` 各 4/2/2/1 处，首行 L22/L343/L63/L246。
- A26 `tests/arch/umon/`：`check_mode_entry.py`（L8/L62–L69 从契约解析 `NCFXPERM` 位）、`mode_entry.S`（L12）、`README.md`（L87）、`m5_perm_mask_cfxperm.S`（L19）。—— 核实：`NCFXPERM` 各 7/1/1/1 处，首行 L8/L12/L87/L19。
- A27 `tools/chipyard/excp/causeid.S`（L27）+ `check_causeid.py`（L46–L47 `NONPTW` 期望）、`tools/chipyard/dcache/check_vastdcache.py`（L6 `adr-0056` 三方互校）。—— 核实：各 1/2/1 处，首行 L27/L46/L6。
- A28 `tools/testcases/arch/`：`min_rom_probe_049t.py`（L194–L198 `SUB_NONPTW` 等 8 处）、`min_rom_probe_integ040t.py`（L169）、`min_rom_probe_integ042t.py`（L124）、`min_rom_probe_integ048t.py`（L96–L100 `NCFXPERM`，13 处）、`min_rom_probe_integ039t.py`（L159–L163 HSJU 位）。—— 核实：`NONPTW` 8/3/4 处（首行 L194/L169/L124）；`NCFXPERM` 13 处（首行 L96）；`NUPERM` 2 处（首行 L159）。
- A29 只引用位号/ADR 的脚本（改注释或自检即可）：`tests/unit/linux/k4_cow_probe.py`（L31/L278 `§6.1.1`，7 处）、`tools/testcases/arch/min_rom_probe_045t.py`（L127）、`min_rom_probe_integ046t.py`（L362）、`min_rom_probe_integ007t.py`（L56）。—— 核实：`6.1.1` 7 处（首行 L31）；`ADR-0056` 各 1 处。

**Linux（3 条）**

- A30 `components/linux/patches/arch/dadao/include/asm/cause-sub.h.patch`：L15–L16（段注释）、L52–L72（`DADAO_SUB_*` 宏，删 `NCFXPERM` L59 与 `NONPTW` L72）、L125（区间判断 `pos <= DADAO_SUB_NCFXPERM`）、L146–L163（名表）。—— 核实：`grep -c DADAO_SUB_NONPTW` = 2，首行 L72。
- A31 `components/linux/patches/arch/dadao/mm/fault.c.patch`：L34（分类注释）、L625（`NUPERM…NCFXPERM` 分类）、L933–L947（`ADWBFAIL`/`NONPTW` 先于 VMA 查找的分支）。—— 核实：`grep -c DADAO_SUB_NONPTW` = 1，首行 L947。
- A32 `components/linux/patches/arch/dadao/include/asm/pgtable.h.patch`（L110 注释）+ `kernel/process.c.patch`（L477–L483）+ `kernel/k4_switch_selftest.c.patch`（L558）：`CFXPERM + NCFXPERM` 的注释与自检路径。—— 核实：`NUPERM` 1 处（L110）；`NCFXPERM` 2/1 处（首行 L477/L558）。

**明确不改（记录，不入清单）**：`components/{qemu,gem5,chipyard,linux}/changelog.md`（历史记录，按 `AGENTS.md` 只追加不改写）、`components/chipyard/chipyard-diff-vs-rocket.md`（与 rocket 的差异盘点，属历史分析）、`tests/arch/vast-arch-inventory.md`（盘点文档，随实现批次更新）、`docs/DDLN/**`、`.tao/archive/**`、`adr-0056` 原文。

## 状态说明

2026-11-24 由 `m17-spec-001` 起草。用户当日裁定「权限异常编码扁平化」：PTW 权限拒绝只置 `[32]`–`[38]` 之一、PTW 访存/页缺失只置 `[48]`–`[55]` 之一或 `[56]`、`CFXPERM`/`CFXMEM` 各只表示一种来源、删除 `[39]`/`[57]`、不新增 cause 位。2026-11-24 用户确认 D1–D5 并补裁定 D6（Vast 路由/退出码）与版本口径 ⇒ 置 `Accepted`；收尾只改本 ADR 与任务书（不改 `spec/`、`contracts/` 正文与平台代码）；附录 A 为影响清单；正文改动归 `m17-spec-002`；仅剩 `cause_info` 细分 1 条未定。
