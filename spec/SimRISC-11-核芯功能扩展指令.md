# SimRISC核芯功能扩展指令

> **版本：0.5.8-rc**（与 SimRISC-00 一致）
> **分类：核芯功能扩展** — trap/escape/cfx2rd/cfx2rc/fence

## 1. 指令域与执行条件

`trap`/`escape`/`cfx2rd`/`cfx2rc` 指令可以在任意运行模式下执行，具体是否允许由各核芯功能扩展的 cfx mask 寄存器和指令类型 cfx mask 寄存器控制。详细异常路由规则见 SEE。

核芯功能扩展指令用于访问各核芯功能扩展的寄存器与异常入口，为应用程序提供完备的运行环境，并用于资源管理和状态配置等功能。

一个32位的指令会被分解为5个部分：8/6/6/6/6，即op/ha/hb/hc/hd，其中ha专门用来指定核芯功能扩展编号。

指令中核芯功能扩展编号可以有两种写法：
- `cfx<cfxha>`：直接使用编号，如 `cfx63`、`cfx0`
- `cfx_<cfxname>`：使用名称，如 `cfx_power`、`cfx_umon`

汇编器对两种写法等价处理，均编码为 6 位的 cfxha。

`cfxHA` 指向保留核芯功能扩展时，本章所有指令均触发 ILLI 异常；保留 cfxha 的具体分配由 SEE（DADAO-12）定义。

## 2. 陷入指令

陷入指令用于将控制权转移到相应核芯功能扩展的异常向量地址。

操作数类型为：`ciii`

```simrisc
trap    cfxHA, immu18
```

其中，cfx_<cfxname> 指定核芯功能扩展名称；immu18指定具体功能编号。

### 2.1 形式化语义（IDL）

本节各指令的形式化语义由 `idl/SimRISC-11.idl` 生成，逐条如下：

<!-- IDL:trap_ciii_cfx BEGIN -->
<!-- 本块由 IDL 源生成，禁手改；生成器见 `idl/tools/` -->
**`trap_ciii_cfx`**
```idl
if (cfx_is_reserved(cfxHA)) {                 # 保留核芯功能扩展 ⇒ 进当前运行模式 monitor
  raise(ExceptionCode::Illegal, mode(), ip());
} else if (cfx_trap_denied(cfxHA)) {          # 目标 cfx 的 cfxtrap 掩码拒绝源 cfx
  raise(ExceptionCode::CfxPerm, mode(), ip());
} else {                                      # CFXTRAP：计数 → 现场 → 模式/目标 → 向量
  cfx_trap_enter(cfxHA, immu18);
}
```
<!-- IDL:trap_ciii_cfx END -->

## 3. 退出指令

退出指令用于退出异常、将控制权交还给出口意图指定的现场。同步与异步**共用**该出口：同步进入的出口意图在目标 cfx 的 `cg5 rc8`–`rc11`，异步进入的在 `cfx_hart cg5 rc8`–`rc11`（见 `DADAO-12 §5.1`/`§5.3`/`§5.4`）。

操作数类型为：`ciii`

```simrisc
escape  cfxHA
```

其中，`cfxHA` 指定核芯功能扩展名称，必须是**当前执行的 cfx**。编码字段 `imms18` 必须为 **0**（SBZ），手工编码非 0 ⇒ ILLI；旧的 `+0`/`+4` 偏移与 `cg9` 帧选择位作废。返回的运行模式、cfx 与指令指针取自当前 cfx `cg5` 的出口意图 `rc8`–`rc11`，返回地址精确取 `rc10`；目标运行模式不得升权、目标 cfx 未实现或目标模式没有对应 monitor ⇒ 当前 cfx 的 `CFXESC`。不设“帧有效位”；`escape_num` 每次执行 +1。完整语义见 `DADAO-12 §5.1`/`§5.3`。

### 3.1 形式化语义（IDL）

本节各指令的形式化语义由 `idl/SimRISC-11.idl` 生成，逐条如下：

<!-- IDL:escape_ciii_cfx BEGIN -->
<!-- 本块由 IDL 源生成，禁手改；生成器见 `idl/tools/` -->
**`escape_ciii_cfx`**
```idl
# 步骤 0（DADAO-12 §5.1/§5.3）：`escape cfxHA` 只提供 cfxha，`imms18` 编码必须为 0
# （SBZ），非 0 ⇒ ILLI；保留 cfxha ⇒ ILLI。`cfxHA` 必须是当前 cfx，否则 ⇒ 当前 cfx
# 的 CFXESC（切换任何状态之前）。不设帧有效位（`cg5 rc4 == 0` 也可返回）。
if (imms18 != 0) {                            # imms18 为 SBZ，非 0 ⇒ ILLI
  raise(ExceptionCode::Illegal, mode(), ip());
}
if (cfx_is_reserved(cfxHA)) {                 # 保留核芯功能扩展 ⇒ ILLI
  raise(ExceptionCode::Illegal, mode(), ip());
}
if (cfxHA != inner_cfx_code()) {              # cfxha 必须是当前 cfx，否则 ⇒ CFXESC
  raise(ExceptionCode::CfxEsc, mode(), ip());
}

# 步骤 1–3：按当前 cfx 的出口意图 cg5 rc8–rc11 恢复运行模式与当前 cfx（rc8/rc9）、
# escape_num++、跳转 rc10，并把 rc11 整字写入目标模式 monitor 的 cg15 rc3（与切模式/
# 切 cfx/跳转原子完成）。目标模式不得升权、目标 cfx 必须已实现且目标模式有 monitor，
# 否则在切换任何状态前报当前 cfx 的 CFXESC；这些检查与整字恢复由语义库函数按 SEE 完成。
cfx_escape_enter(cfxHA);
```
<!-- IDL:escape_ciii_cfx END -->

## 4. 寄存器传输指令

这类指令用于核芯功能扩展的寄存器与rd寄存器之间进行相互赋值。

操作数类型为：`crrr`

```simrisc
cfx2rd    cfxHA, cgHB, rcHC, rdHD
cfx2rc    cfxHA, cgHB, rcHC, rdHD
```

其中，cfx_<cfxname> 指定核芯功能扩展名称，cgHB和rcHC指定该核芯功能扩展的寄存器组和寄存器号。
cfx2rc 是将 rdHD 的值设置到 cfx_<cfxname>_cgHB_rcHC 中。
cfx2rd 是将 cfx_<cfxname>_cgHB_rcHC 的值设置到 rdHD 中。

读写不存在的 cfx_<cfxname>_cgHB_rcHC 组合时触发 CFXREG 异常；cfx_<cfxname> 为 reserved 核芯功能扩展时触发 ILLI 异常；读写权限不匹配时，触发非法核芯功能扩展寄存器访问异常（CFXREG）。

> **注意**：cfx2rd/cfx2rc 的数据通路仅连接 rd 寄存器组。若需要将 rb 或 rf 寄存器的值写入核芯功能扩展寄存器，须先通过 `rb2rd rd, rb, 1` 或 `rf2rd rd, rf, 1` 中转至 rd 寄存器。汇编器提供 `set.rd rd, rs` 伪指令简化此操作（展开为 `rb2rd`/`rf2rd`/`rd2rd`）。

为简化汇编代码的编写，寄存器传输指令支持一种简化的操作数写法，将 `cfx_<cfxname>, cgHB, rcHC` 三个参数合并为 `cfx_⟨cfxname⟩_regname` 的形式，其中 `regname` 为寄存器名称（即 SEE 文档 regname 列中的名称）。汇编器会根据寄存器名称自动查找对应的 cg 和 rc 编号，展开为标准的三个操作数格式。

```simrisc
@@ 简化写法（推荐）
cfx2rd  cfx_umon_excp_cause_ip, rd2    @@ 读取 cfx_umon 的 excp_cause_ip
cfx2rc  cfx_power_ctrl, rd2             @@ 写入 cfx_power 的 power_ctrl

@@ 等价的标准写法
cfx2rd  cfx_umon, cg5, rc3, rd2
cfx2rc  cfx_power, cg8, rc1, rd2
```

这种简化写法使代码更具可读性，程序员无需记忆每个寄存器的cg和rc编号，直接通过寄存器名称即可定位目标寄存器。

### 4.1 形式化语义（IDL）

本节各指令的形式化语义由 `idl/SimRISC-11.idl` 生成，逐条如下：

<!-- IDL:cfx2rd_crrr_cfx BEGIN -->
<!-- 本块由 IDL 源生成，禁手改；生成器见 `idl/tools/` -->
**`cfx2rd_crrr_cfx`**
```idl
if (cfx_is_reserved(cfxHA)) {                 # 保留核芯功能扩展 ⇒ ILLI
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 读 cfx_<cfxname>_cgHB_rcHC 到 rdHD；存在性与读写权限（HW/RO/保留 ⇒ CFXREG）由 SEE 的寄存器表
# 描述、cfxreg 来源掩码拒绝（⇒ CFXPERM）由 §5.2 的表描述：operation 只表达访问（T6 裁定）
rd[rdHD] = cfx_read(cfxHA, cgHB, rcHC);
```
<!-- IDL:cfx2rd_crrr_cfx END -->

<!-- IDL:cfx2rc_crrr_cfx BEGIN -->
<!-- 本块由 IDL 源生成，禁手改；生成器见 `idl/tools/` -->
**`cfx2rc_crrr_cfx`**
```idl
if (cfx_is_reserved(cfxHA)) {                 # 保留核芯功能扩展 ⇒ ILLI
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 把 rdHD 的值写到 cfx_<cfxname>_cgHB_rcHC；存在性与读写权限（HW/RO/保留 ⇒ CFXREG）由 SEE 的
# 寄存器表描述、cfxreg 来源掩码拒绝（⇒ CFXPERM）由 §5.2 的表描述：operation 只表达访问（T6 裁定）
cfx_write(cfxHA, cgHB, rcHC, rd[rdHD]);
```
<!-- IDL:cfx2rc_crrr_cfx END -->

## 5. 屏障指令

屏障指令用于约束本 hart 对所选 cfx 资源域的访问顺序。

操作数类型为：`ciii`

```simrisc
fence   cfxHA, immu18
```

其中，`cfxHA` 指定资源域：

- `cfx0` / `cfx_umon`：表示 **all cfx**（不是只作用于 umon 本地资源）；
- `cfx1`–`cfx63`：表示指定的 cfx。

`immu18` **整体书写，不拆成三段操作数**；其位域为：

| 字段 | 位 | 含义 |
| --- | --- | --- |
| `hb` | `immu18[17:12]` | SBZ，必须为 0 |
| `pred` | `immu18[11:6]` | 前序（predecessor）访问类型掩码 |
| `succ` | `immu18[5:0]` | 后序（successor）访问类型掩码 |

`pred`/`succ` 的位含义相同：

| 位 | 名称 | 访问类型 |
| --- | --- | --- |
| bit0 | `cr` | cfx memory read |
| bit1 | `cw` | cfx memory write |
| bit2 | `ci` | cfx IO input |
| bit3 | `co` | cfx IO output |
| bit4 | `mr` | system memory read |
| bit5 | `mw` | system memory write |

汇编器为上述 12 个位提供同名宏，可直接用 `|` 组合，组合结果整体作为 `immu18` 书写：

| 宏 | 值 | 访问类型 |
| --- | --- | --- |
| `PRED_CR` | `1 << 6` | cfx memory read |
| `PRED_CW` | `1 << 7` | cfx memory write |
| `PRED_CI` | `1 << 8` | cfx IO input |
| `PRED_CO` | `1 << 9` | cfx IO output |
| `PRED_MR` | `1 << 10` | system memory read |
| `PRED_MW` | `1 << 11` | system memory write |
| `SUCC_CR` | `1 << 0` | cfx memory read |
| `SUCC_CW` | `1 << 1` | cfx memory write |
| `SUCC_CI` | `1 << 2` | cfx IO input |
| `SUCC_CO` | `1 << 3` | cfx IO output |
| `SUCC_MR` | `1 << 4` | system memory read |
| `SUCC_MW` | `1 << 5` | system memory write |

例如 `fence cfx0, PRED_CR|SUCC_CR|SUCC_CW` 与 `fence cfx0, 67` 编码相同。

`pred = 0` 且 `succ = 0` 是合法的 no-op。

屏障只保证**本 hart** 对所选 cfx 的对应访问顺序/可见性；不跨 hart，不等待 DMA
完成，也不负责 TLB / icache 维护。

异常规则：

- `hb != 0` ⇒ ILLI；
- `cfxHA` 为保留核芯功能扩展 ⇒ ILLI（保留 cfxha 的分配由 SEE/DADAO-12 定义）；
- 正常屏障不产生异常。

### 5.1 形式化语义（IDL）

本节各指令的形式化语义由 `idl/SimRISC-11.idl` 生成，逐条如下：

<!-- IDL:fence_ciii_cfx BEGIN -->
<!-- 本块由 IDL 源生成，禁手改；生成器见 `idl/tools/` -->
**`fence_ciii_cfx`**
```idl
if (immu18[17:12] != 6'd0) {                  # hb = immu18[17:12] 为 SBZ，非零 ⇒ ILLI
  raise(ExceptionCode::Illegal, mode(), ip());
}
if (cfx_is_reserved(cfxHA)) {                 # 保留核芯功能扩展 ⇒ ILLI
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 屏障：pred = immu18[11:6]、succ = immu18[5:0]（各 6 位访问类型掩码，bit0–5 = cr/cw/ci/co/mr/mw），
# cfx0 = all cfx、cfx1–cfx63 = 指定 cfx；只约束本 hart，不跨 hart、不等待 DMA、不维护 TLB/icache。
# 顺序/可见性语义由实现提供，IDL v0 不建模（T7 裁定）；零掩码是合法 no-op
cfx_fence(cfxHA, immu18[11:6], immu18[5:0]);
```
<!-- IDL:fence_ciii_cfx END -->

<!-- ASSEMBLY_LIST_START -->
## 附录 A：汇编指令速查

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `cfx2rc` | `crrr` | `cfx` | `cfx2rc cfxHA, cgHB, rcHC, rdHD` | `cfx2rc_crrr_cfx` |
| `cfx2rd` | `crrr` | `cfx` | `cfx2rd cfxHA, cgHB, rcHC, rdHD` | `cfx2rd_crrr_cfx` |
| `escape` | `ciii` | `cfx` | `escape cfxHA` | `escape_ciii_cfx` |
| `fence` | `ciii` | `cfx` | `fence cfxHA, immu18` | `fence_ciii_cfx` |
| `trap` | `ciii` | `cfx` | `trap cfxHA, immu18` | `trap_ciii_cfx` |

<!-- ASSEMBLY_LIST_END -->

<!-- LEGALITY_START -->
## 附录 B：合法性检查

* `encode_sbz`：SBZ 非零 → ILLI — `escape_ciii_cfx`, `fence_ciii_cfx`（2 条）
* `encode_cfx_reserved`：保留 cfxha（具体分配由 SEE/DADAO-12 定义）→ ILLI — `cfx2rc_crrr_cfx`, `cfx2rd_crrr_cfx`, `escape_ciii_cfx`, `fence_ciii_cfx`, `trap_ciii_cfx`（5 条）
<!-- LEGALITY_END -->
