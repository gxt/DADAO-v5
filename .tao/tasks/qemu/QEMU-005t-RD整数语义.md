# QEMU-005t: RD 整数语义（算术/逻辑/移位/比较/条件赋值）

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-004t`

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `QEMU-004t` 产出的 `target/dadao/translate.c`（全部 `trans_*` 存根为 ILLI）与 `insn.decode`
  - `.tao/knowledge/contract-isa.md` §1.3（rd0/rb0/rf0 约定）、§3（标量整数：算术/比较/逻辑/位操作/条件赋值/立即数设置/块赋值）、附录 A.2–A.5（MISC 子表中的整数运算）
  - `verif/opcodes.yaml`（各指令 `fields`/`legality`）、`verif/legality_rules.yaml`
- 输出：`components/qemu/patches/0003-dadao-rd-arith.patch`、`components/qemu/patches/series`
- 约束：
  - 只实现本任务列出的指令；load/store、branch/call/ret、RB 指令、浮点保持 ILLI 桩
  - 所有 ILLI 检查先于任何 TCG 写操作
  - rd0 写为 NOP（ISA §1.3.1），不额外 ILLI
  - 源操作数在写目标前全部读取（源被覆盖前已捕获）
  - 运行时异常（除零、`INT_MIN ÷ −1`）用 TCG 条件分支，不在 build 期 assert
  - `swym` 保持 NOP
  - 完成后不自行 commit

## 背景（完整）

### 目标

在 `QEMU-004t` decodetree 脚手架上，实现 M1 scope 中 **RD 数据类指令**的 TCG 语义，覆盖算术、逻辑、移位/扩展、比较、条件赋值、立即数设置与块赋值。0628 对应任务 `DL-015a` 实现 35 个 trans 函数，经评审 Accepted。

### 设计理由

- 按 oracle 实现：每条指令的语义、合法性、结果符号均来自 `contract-isa.md` §3 与 `opcodes.yaml`，不从实现反推。
- ILLI 先于写：违法操作数在生成任何 TCG 写操作前判定，保证精确异常（目标寄存器不提交）。
- 先快照后写：所有源操作数在写目标前读取，避免 `src == dst` 时用写后值。

### 关键概念 / 数据

**寄存器访问约定**：通过 `tcg_gen_ld_i64`/`tcg_gen_st_i64` + `offsetof(CPUDADAOState, rd[n])` 读写；`store_rd(0, …)` 静默忽略（rd0 硬连 0）。写目标前先做 ILLI 检查。

**指令范围（0.5.3）**：

1. **128 位加减（rrrr）** §3.1.1：`add.uo`/`add.so`/`sub.uo`/`sub.so`，`rdha:rdhb = rdhc ± rdhd`。
   - ILLI：`rdha` 与 `rdhb` 同时为 rd0；`rdha == rdhb` 且非 rd0。
   - TCG：有符号用 `tcg_gen_add2_i64`/`sub2_i64` 前先对源做符号扩展（`tcg_gen_sari_i64(hi, src, 63)`）；无符号零扩展。高字→rdha、低字→rdhb，rd0 目标跳过写。
2. **固定位宽加减（orrr，MISC-byte/wyde/tetra）** §3.1.2：`add.ub/sb/uw/sw/ut/st`、`sub.*`。结果保留 size 位、高位按符号/零扩展；ILLI：`rdhb == 0`。
3. **自增自减（riii）** §3.1.3：`add.si rdha, imms18`（全 64 位）。
4. **128 位乘法（rrrr）** §3.1.4：`mul.uo`/`mul.so`，`tcg_gen_mulu2_i64`/`muls2_i64`；ILLI 同 add/sub。
5. **固定位宽乘/除/余（orrr，MISC 子表）** §3.1.5：`mul.*`、`div.*`、`rem.*`。
   - ILLI：`rdhb == 0`；除数为零；`div.s` 中 `INT_MIN ÷ −1`（各 size 对应值）；fault 时目的不写。
   - 截断：truncate-toward-zero（C99），余数符号 = 被除数符号。
6. **比较（rrii + orrr）** §3.2：`cmp.si`/`cmp.ui`（立即数）、`cmp.ub/sb/uw/sw/ut/st/uo/so`（寄存器）。结果 −1/0/1 写目的全 64 位；ILLI：目的为 rd0 / `rdhb == 0`。
7. **逻辑（orrr，MISC-byte/wyde/tetra/octa）** §3.3：`and.*`/`or.*`/`xor.*`/`xnor.*`。仅 size 低位参与，高位保持目的原值；ILLI：目的为 rd0。
8. **移位（orrr/orri）** §3.4.1：`shl.u*`/`shr.u*`/`shr.s*`；立即数取 `immu6` 低位；ILLI：`shamt > N`。
9. **扩展（orrr/orri）** §3.4.2：`ext.u*`/`ext.s*`；`hd > N` → ILLI；高位保持。
10. **条件赋值（rrrr）** §3.5：`cs.n`/`cs.z`/`cs.p`（单值）、`cs.eq`/`cs.ne`（双值）。`movcond` 实现；ILLI 按 §3.5/§2.6（目标为 rd0 时）。
11. **立即数设置（rwii）** §3.6：`set.ow`/`set.zw`/`or.w`/`andn.w`（RD）。wyde-position 编码见 §2.3。
12. **块赋值（orri）** §3.7：`rd2rd rdhb, rdhc, immu6`。ILLI：`immu6 == 0`、`rdhb == rd0`、`rdhb + immu6 > 64`、`rdhc + immu6 > 64`；重叠时按序号递增逐对先读后写。

**不覆盖（保持 ILLI 桩）**：`ld.*`/`st.*`/`ldm.*`/`stm.*`（`QEMU-006t`）、branch/jump/call/ret/rela（`QEMU-008t`）、RB 指令（`QEMU-008t`）、§6 浮点与 `cs.*-rf`、LR/SC、特权指令。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-015a-qemu-rd-arith.md`（完整转述：寄存器访问约定、每条指令实现规格、约束、完成区与 Architecture Review）。
- DADAO-0628：`components/qemu/patches/0004-dadao-rd-arith.patch`（仅参考 TCG 风格，不复制 0.4.1 语义/编码）。

## 交付物

- `components/qemu/patches/0003-dadao-rd-arith.patch`：`target/dadao/translate.c`（替换本任务范围 `trans_*` 存根为真实 TCG）、必要的 `helper.c`/`cpu.h` 补充。
- `components/qemu/patches/series`：加入 `0003`。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **指令集合重排**：0628 的 `add`/`sub`/`muls`/`mulu`/`divs`/`divu`/`cmps`/`cmpu`/`exts`/`extz`/`shlu`/`shrs`/`shru` 在 v5 变为 `add.uo`/`add.so`/`sub.uo`/`sub.so`、`mul.uo`/`mul.so`、`div.*`/`rem.*`、`cmp.si`/`cmp.ui`、`ext.*`、`shl.*`/`shr.*`，并新增固定位宽 orrr 形式（MISC-byte/wyde/tetra）。
2. **格式变化**：`addi`(rrii) → `add.si`(riii)；`cs.*` 命名带点；新增 `set.ow`/`set.zw`/`or.w`/`andn.w`(rwii) 与 `rd2rd`(orri)。
3. **除余分离**：0.5.3 将 `div` 与 `rem` 拆为独立指令；余数/商的目标约定按 §3.1.5 与 `opcodes.yaml` 的 `fields` 确定，不沿用 0628 的「rdha=余数、rdhb=商」假设。
4. **固定位宽语义**：高位填充（符号/零扩展）与「仅 size 位参与、高位保持」规则为 0.5.3 新增，须严格按 §3.1.2/§3.3/§3.4。
5. **RB 全 64 位**：本任务不涉及 RB；但 `rd2rd` 等块赋值的 bank 边界按 §3.7。
6. **浮点条件赋值**：`cs.*-rf` 属 §6，M1 排除，保持 ILLI。

## 已知坑 / 结论

摘自 0628 `DL-015a` 完成区与 Architecture Review：

1. **双目标 ILLI**：`rdha==rdhb && rdha!=0` → ILLI；两者同时为 rd0 → ILLI（对 add/sub/mul rrrr）。
2. **源快照**：所有源在写目标前读取；`cseq` 类先读旧值再 `movcond`。
3. **rd0 写 NOP**：`store_rd(0, …)` 静默忽略，不额外 ILLI。
4. **除法运行时 ILLI**：除零与 `INT_MIN ÷ −1` 用 TCG 条件分支（见 `QEMU-011t` 的 label 顺序坑）。
5. **移位量掩码**：寄存器形式 shift amount 取 `rdhd[5:0]`（`tcg_gen_andi_i64(shamt, rdhd, 0x3F)`）；立即数形式直接传。
6. **比较三分支**：默认 1，`movcond EQ→0`，再 `movcond LT→-1`。
7. **patch 序列可应用性**：0628 曾出现补丁未 apply 到工作树、`git am` corrupt 的基础设施问题；v5 须确保 `series` 顺序 apply 干净（`INFRA-004t`）。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-015a-qemu-rd-arith.md`
- 本项目：`.tao/knowledge/contract-isa.md` §1.3、§2.3、§3、附录 A.2–A.5；`verif/opcodes.yaml`；`verif/legality_rules.yaml`
- 本项目：`.tao/tasks/qemu/QEMU-004t-Decodetree解码.md`（`trans_*` 签名与 `arg_*` 结构体）
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `components/qemu/patches/0003-dadao-rd-arith.patch` 存在且干净 apply；`series` 已加入
2. §3 中本任务范围的 RD 整数指令全部由 ILLI 桩替换为真实 TCG，语义与 `contract-isa.md` §3 一致
3. 所有 ILLI 检查先于 TCG 写；rd0 写为 NOP；源在写前快照
4. 除零与 `INT_MIN ÷ −1` 产生运行时 ILLI（TCG 条件分支），非 build 期 assert
5. 未覆盖指令仍为 ILLI 桩
6. `make build-qemu` PASS；相关语义/合法性/边界向量经「MC 汇编 → QEMU 执行 → 结果比对」与 oracle 一致（若 harness 未就绪，记录依赖并保留可复现命令）
7. 完成区含真实构建/运行输出；未自行 commit

## 完成区

**状态**：待开始
**Commit**：
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
