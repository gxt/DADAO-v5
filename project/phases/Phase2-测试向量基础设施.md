# Phase 2：测试向量基础设施

> 对应 DADAO-0628 的 DL-001c/019a/019b/020a（向量 schema + 编码向量 + 语义向量）

## 目标

创建独立于任何实现的测试向量系统。向量直接从 wiki 规范派生，不从 LLVM 或 QEMU 生成。这是实现独立 oracle（independent oracle）原则的基础。

## 输入文件

| 来源 | 文件 | 用途 |
|------|------|------|
| DADAO-v5/wiki | 全部 11 份文档 | 测试预期的规范来源 |
| Phase 1 输出 | `contracts/isa/spec.md` | 归一化后的 ISA 规范 |
| Phase 1 输出 | `verif/opcodes.yaml` | 编码 mask/value |
| Phase 1 输出 | `verif/legality_rules.yaml` | 合法性规则 |
| DADAO-0628 | `tests/vectors/schema.md` | 向量 schema 模板 |
| DADAO-0628 | `tests/vectors/inventory.md` | 覆盖矩阵模板 |
| DADAO-0628 | `tests/vectors/isa/*.yaml` | 测试向量示例 |

## 输出文件

```
DADAO-v5/
├── tests/
│   ├── vectors/
│   │   ├── README.md             # 向量说明
│   │   ├── schema.md             # YAML schema 定义
│   │   ├── inventory.md          # 覆盖矩阵
│   │   └── isa/
│   │       ├── rd-arith.yaml           # RD 算术：add/sub/mul/div/rem/addi
│   │       ├── rd-logic.yaml           # RD 逻辑：and/or/xor/xnor
│   │       ├── rd-shift-extend.yaml    # RD 移位：shl/shr/ext
│   │       ├── rd-compare.yaml         # RD 比较：cmps/cmpu
│   │       ├── rd-cond-assign.yaml     # RD 条件赋值：csn/csz/csp/cseq/csne
│   │       ├── rd-wyde-block.yaml      # RD wyde/块：setzw/setow/orw/andnw/rd2rd/rd2rb/rb2rd/rb2rb
│   │       ├── rd-load-store.yaml      # RD 存取：ld/st 单/多
│   │       ├── rb-ops.yaml             # RB 操作：cmp/add/sub/addi/rela/ldo/sto/ldmo/stmo
│   │       ├── ra-ops.yaml             # RA 操作：ldo/sto/ldmo/stmo/rd2ra/ra2rd
│   │       ├── rf-ops.yaml             # RF 操作：ldt/stt/ldo/sto/ldmt/stmt/ldmo/stmo
│   │       ├── rf-float.yaml           # RF 浮点运算：fadd/fsub/fmul/fdiv/...
│   │       ├── rf-convert.yaml         # RF 格式转换：ft2fo/ft2it/...
│   │       ├── rf-block.yaml           # RF 块操作：rf2rd/rd2rf/rf2rf
│   │       ├── control-flow.yaml       # 控制流：br/jump/call/ret
│   │       ├── misc.yaml               # 杂项：swym/illi
│   │       ├── system.yaml             # 系统指令：fence/lro/sco
│   │       └── cfx.yaml                # 特权指令：trap/escape/cfx2rd/cfx2rc
```

## 子代理分解

### Agent C1：向量 Schema 与基础设施

**职责**：创建 schema、README、inventory 和框架

**提示词**：
```
你是 DADAO-v5 的测试基础设施工程师。创建测试向量的 schema 定义和框架文件。

基于 DADAO-0628/tests/vectors 的类似文件，但针对 SimRISC 0.5.3 更新。

1. 创建 `tests/vectors/README.md`：
   - 说明向量来源（wiki 规范，非 LLVM/QEMU）
   - 5 类 class 定义（encoding/legality/semantic/boundary/overlap）
   - 文件组织说明
   - 新增：branch_behavior 标记（taken/not_taken），用于控制流测试

2. 创建 `tests/vectors/schema.md`：
   - 每个向量 tuple 字段定义
   - encoding.word（32 位指令字 hex）
   - input_state（rd/rb/rf/ra/pc/mem 初始状态）
   - expected_state（执行后的状态）
   - expected_fault（预期异常）
   - 新增：purpose 字段（区分不同测试意图）
   - branch_behavior 控制流字段

3. 创建 `tests/vectors/inventory.md`：
   - 覆盖矩阵表，按 opcode identity 索引
   - 每行：opcode_identity、mnemonic、所在文件、各 class 覆盖（✓/✗）
   - 对比 DADAO-0628 （87 条）扩展到 ~150+ 条
   - 标注新增加指令

4. 创建空的 YAML 文件占位（在 tests/vectors/isa 下）

参考 DADAO-0628 对应文件，但 schema 要适应 SimRISC 0.5.3 新增特性：
-brri 格式的  参数
- 浮点寄存器状态（rf[64]）
- 返回地址栈（ra[64]）
- 系统指令的 cfxcode 字段
```

### Agent C2：核心指令向量

**职责**：创建 RD/RB/RA 核心指令的测试向量

**提示词**：
```
你是 DADAO-v5 的测试向量工程师。基于 SimRISC-01/02 和 contracts/isa/spec.md 创建核心指令的测试向量。

按以下模式为每条指令创建测试向量：

**encoding class**（1 个/指令）：
- 从 opcodes.yaml 获取正确编码
- 无 expected_state，无 expected_fault
- 验证 word 与 mask/value 一致

**semantic class**（2-3 个/指令）：
- 正常操作用例
- 输入值覆盖正常范围、零、±1
- 有状态的完整前后快照

**legality class**（1-2 个/指令）：
- 每种 ILLI 条件一个向量
- 如 rd0 目的、immu6=0、range overflow

**boundary class**（1 个/指令）：
- 立即数 min/max
- 地址空间边界

**overlap class**（1 个/指令）：
- src 与 dst 寄存器重叠

### 必须覆盖的指令列表（按文件分）

**rd-arith.yaml**（RD 算术）：
add-rd-orrr, sub-rd-orrr, add-rd-rrrr, sub-rd-rrrr,
addi-rd-rrii,
mulu-rd-orrr, muls-rd-orrr, mulu-rd-rrrr, muls-rd-rrrr,
divu-rd-orrr, divs-rd-orrr, remu-rd-orrr, rems-rd-orrr,

**rd-compare.yaml** 扩展（RD 比较）：
cmpu-rd-orrr, cmps-rd-orrr, cmpu-rd-rrii, cmps-rd-rrii

**rd-logic.yaml**（RD 逻辑，注意格式改为 brrr）：
and-rd-orrr, orr-rd-orrr, xor-rd-orrr, xnor-rd-orrr

**rd-shift-extend.yaml**（RD 移位/扩展）：
shlu-rd-orrr, shrs-rd-orrr, shru-rd-orrr,
shlu-rd-orri, shrs-rd-orri, shru-rd-orri,
exts-rd-orrr, extz-rd-orrr,
exts-rd-orri, extz-rd-orri

**rd-cond-assign.yaml**（条件赋值）：
csn-rd-rrrr, csz-rd-rrrr, csp-rd-rrrr, cseq-rd-rrrr, csne-rd-rrrr
注意：按照 SimRISC 0.5.3，第一类 csn/csz/csp 的语义为：if (rdha is N/Z/P) rdhb = rdhc; else rdhb = rdhd

**rd-load-store.yaml**（加载/存储）：
ldbs/lbu/ldws/ldwu/ldts/ldtu/ldo-rd-rrii,
stb/stw/stt/sto-rd-rrii,
ldmbs/ldmbu/ldmws/ldmwu/ldmts/ldmtu/ldmo-rd-rrri,
stmb/stmw/stmt/stmo-rd-rrri

**rb-ops.yaml**（RB 操作）：
ldo-rb-rrii, sto-rb-rrii, ldmo-rb-rrri, stmo-rb-rrri,
cmp-rb-orrr, add-rb-orrr, sub-rb-orrr,
addi-rb-rrii, rela-rb-riii,
setzw-rb-rwii, orw-rb-rwii, andnw-rb-rwii

**ra-ops.yaml**（RA 操作 - 新增）：
ldo-ra-rrii, sto-ra-rrii, ldmo-ra-rrri, stmo-ra-rrri,
rd2ra-orri, ra2rd-orri

**control-flow.yaml**（控制流）：
brn-riii, brnn-riii, brz-riii, brnz-riii, brp-riii, brnp-riii,
breq-rrii, brne-rrii,
jump-iiii, jump-rrii,
call-iiii, call-rrii,
ret-riii

重要：控制流测试使用 "branch-over-poison" 模式——分支越过 unimp 指令，如果分支 taken 则跳过 poison 正常退出，否则触发 ILLI。

**rd-wyde-block.yaml**（块操作）：
rd2rd-orri, rd2rb-orri, rb2rd-orri, rb2rb-orri,
setzw-rd-rwii, setow-rd-rwii, orw-rd-rwii, andnw-rd-rwii

**misc.yaml**（杂项）：
illi-oiii, swym-iiii

创建每个向量时，确保：
- input_state 中的 rd/rb/rf 值使用完整 64 位 hex（如 "0x0000000000000001"）
- 预期结果明确标注
- wiki_cite 引用具体 spec 章节
- branch_behavior 仅在控制流测试中需要
```

### Agent C3：浮点/系统指令向量

**职责**：创建 RF 浮点和系统指令的测试向量

**提示词**：
```
你是 DADAO-v5 的测试向量工程师。基于 SimRISC-03/04 和 contracts/isa/spec.md 创建浮点和系统指令的测试向量。

### 必须覆盖的指令列表

**rf-ops.yaml**（RF 存取 - 新增到 SimRISC 0.5.3）：
ldt-rf-rrii, stt-rf-rrii, ldo-rf-rrii, sto-rf-rrii,
ldmt-rf-rrri, stmt-rf-rrri, ldmo-rf-rrri, stmo-rf-rrri
注意：单精（ft）使用 ldt/stt，双精使用 ldo/sto

**rf-block.yaml**（RF 块操作 - 新增）：
rf2rd-orri, rd2rf-orri, rf2rf-orri

**rf-float.yaml**（RF 浮点运算 - 新增的 ~40 条指令）：
对于 M1 scope，浮点运算可以标为 status: deferred（推迟），但 encoding 类向量必须创建：
- ftadd/ftsub/ftmul/ftdiv/ftrem/ftsclb/ftsgnn/ftsgnj-orrr（单精运算，8 条）
- foadd/fosub/fomul/fodiv/forem/fosclb/fosgnn/fosgnj-orrr（双精运算，8 条）
- ftqcmp/ftscmp-orrr, foqcmp/foscmp-orrr（浮点比较，4 条）
- ftcls/focls/fclog/folog/ftroot/foroot（其他浮点操作，6 条）
- csp1-rf-rrrr, csnp1-rf-rrrr（浮点条件赋值）

**rf-convert.yaml**（RF 格式转换 - 新增）：
ft2fo-orri, fo2ft-orri,
ft2it/ft2io/ft2ut/ft2uo-orri,
it2ft/io2ft/ut2ft/uo2ft-orri,
fo2it/fo2io/fo2ut/fo2uo-orri,
it2fo/io2fo/ut2fo/uo2fo-orri
（共 20 条转换指令）

**system.yaml**（系统指令 - 新增）：
fence-oiii（内存屏障）
lro_nn/lro_nr/lro_an/lro_ar-orrr（LR 指令）
sco_nn/sco_nr/sco_an/sco_ar-orrr（SC 指令）

**cfx.yaml**（特权指令 - 新增）：
cfx2rd-crrr, cfx2rc-crrr（寄存器传输）
cfxld-crii, cfxst-crii（SRAM 块传输）
trap-ciii（陷入）
escape-ciii（退出）

对于 cfx 指令，使用最小的合法 cfxcode（如 cfx_power=63），确保输入状态正确。

### 浮点测试特殊注意事项
- rf0 = FCSR，初始值包含 QuietNaN 模式位 + 舍入模式
- 单精数据只使用 rf 寄存器的低 32 位
- IEEE 754 标准浮点值使用 hex 表示（如 0x3FF0000000000000 = 1.0 double）
- 浮点指令不触发异常，异常状态记录在 rf0[4:0] 中

对于所有浮点指令，先创建 encoding 类向量确认编码正确。semantic 类向量可以留到 M3（浮点支持阶段）补充。
```

## 阶段验证

- `validate_encoding.py` 对每个 YAML 中的 `encoding.word` 与 `opcodes.yaml` 做匹配验证
- 每个 opcode 至少有一个 encoding 类向量
- 各 legality-class 向量与 `legality_rules.yaml` 对应规则匹配
- `inventory.md` 准确反映覆盖情况

## 依赖关系

- 依赖 Phase 1（opcodes.yaml、legality_rules.yaml）
- 是 Phase 3（Golden Model 验证）的输入
