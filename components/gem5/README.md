# gem5 组件（gem5）

DADAO 的 gem5 功能参考（M11）。上游基线与补丁序列由
`manifests/components.lock.toml` 锁定；工作树由 `make fetch` +
`make apply-series` 在 `.work/source/gem5` 建立。

## 当前状态（GEM5-004t / B0 + GEM5-005t + GEM5-006t / B1 + GEM5-007t / B2 + GEM5-008t / B3 + GEM5-009t / B4 + GEM5-010t / B5 + GEM5-011t / B6）

- **解码核心**：`src/arch/dadao/**` 骨架 + 契约驱动的解码表
  （格式/字段/opcode/6 位子表分派/助记符/非法与保留编码；
  `rule_refs` + `legality` 表达式作为执行批次的合法性数据）。
- **B1 执行语义**（`exec/b1.{hh,cc}`，38 条取数存数）：RD/RB/RA/RF 的
  单/多 load/store，纯 C++（不依赖 gem5 头），由 `inst.cc` 的
  `Gem5B1Context` 适配寄存器组/内存；ILLI → `IllegalInstruction`、
  MALIGN → `MalignInstruction`（先 panic 报地址/宽度，B6 接 trap 向量）、
  内存 fault 原样返回。大端字节序与 48 位地址回绕在核内完成。
- **B2 执行语义**（`exec/b2.{hh,cc}`，8 条 rwii 立即数）：`or.w`/`andn.w`/
  `set.zw`/`set.ow` 的 RD/RB 变体与 `set.w` RF 变体，按 `entry->id` 分派
  （同名助记符 RD/RB 不混淆）；`wpN` 选择 wyde、`immu16` 无符号分片拼接、
  其余 48 位按各指令清 0/置 1/保持；RD/RB 目的 0 ⇒ ILLI（先于寄存器访问），
  `set.w rf0` 合法且按 FCSR 写掩码（`wp2`→`[33:32]`、`wp0`→`[4:0]`、
  `wp1`/`wp3` 写无效）。共享接口（`Fault`/`Bank`/`Target`/`RegAccess`/
  `fieldValue`）上移到 `exec/common.hh`，B1 语义不变。
- **B3 执行语义**（`exec/b3.{hh,cc}`，42 条 64 位运算/地址运算）：128 位
  加减乘与无进位乘（`rrrr` 双目的高低半 + 进位/借位）、18/12 位立即数算术与
  比较、位扫描/位计数（有效位上界 `hd`）、64 位逻辑与移位/循环移位、符号/零
  扩展、逐块反转、除余定值语义（除零/`INT_MIN÷−1`）与 RB 加减/比较、`aip.si`
  IP 相对寻址；按 `entry->id` 分派，静态 ILLI 先于任何寄存器读。
- **B4 执行语义**（`exec/b4.{hh,cc}`，63 条 32/16/8 位运算 +
  `rev.t/w/b`）：源先按宽度截断再运算，结果写满 64 位（`u` 零扩展、
  `s` 符号扩展），`cmp` 的 −1 为 64 位全 1；除零/`INT_MIN÷−1` 定值；
  `orrr` 移位量取 `rdhd` 低位（天然 mod W），`orri` 的 `immu6 ≥ W`
  ⇒ ILLI；`rev.t/w/b` 每块内按 one-hot `k` 反转单元顺序（`k ≥ S` ⇒ ILLI）。
  按 `entry->id` 分派，静态 ILLI 先于任何寄存器读；无访存路径。
- **B5 执行语义**（`exec/b5.{hh,cc}`，28 条块搬移/条件赋值/控制流/RAS）：
  8 条寄存器块搬移（RD/RB/RA/RF 组间与组内，64 位二进制不变；`immu6=0`/
  越界/目的 0/同组重叠 ⇒ ILLI，`rf0` 目的按 FCSR 写掩码、`ra0` 按不透明
  64 位传输）；5 条条件赋值（`cs.n/z/p` 写 `rdhb`、`cs.eq/ne` 写 `rdhc`，
  先读全部源再写、条件不成立写回原值）；10 条条件跳转 + 2 条 `jump` +
  2 条 `call` + `ret`，地址按 64 位全宽计算（`rb0 + (sext(imm)<<2)`，
  `rrii` 为 `rbha + rdhb + (sext(imms12)<<2)`），48 位截断交地址空间；
  RegRAS/MemRAS 状态机 C1/C2/C3a/C3b 与 D1/D2/D3/D4a/D4b（`RACNT`/
  `MRPTR`、递归折叠、MemRAS 大端换出/读回、RASOF/RASUF 与访存异常精确）。
- **B6 执行语义**（`exec/b6.{hh,cc}`，30 条系统/原子/屏障）：
  `swym`（no-op + `swymHint` 时延提示，`immu18` 非功能操作数）；`trap`/
  `escape`/`cfx2rd`/`cfx2rc`（cfxha 保留 6–14/19–61 ⇒ ILLI；`escape`
  `imms18[17:1] != 0` ⇒ ILLI、字节偏移仅 0/4；`cfx2rd/cfx2rc` 未建模组合 ⇒
  CFXREG、`trap` 控制转移 `trapTo`、帧错误 ⇒ CFXESC；`cfx2rd` 目的 `rd0`
  丢弃写不 ILLI）；`fence`（`immu18[17:12]` SBZ、`pred/succ` 六位掩码、
  `cfxha=0` = all cfx、`pred=succ=0` 合法 no-op，`ordering()` 为平台接入点）；
  `lr.*`/`sc.*` 各 12 条（宽度 8/4/2/1 × 存储序 nn/an|nr/ar，按 `entry->id`
  分派；`lr` 零扩展大端读并置保留、`sc` 精确地址+宽度匹配后条件写并置
  `rdHB=0/1`，无论成败清本 hart 保留；`lr` 的 `hb != rd0` ⇒ ILLI、`sc` 的
  `rdHB = rd0` ⇒ ILLI；非 `.b` 未对齐 ⇒ MALIGN；MALIGN/访存 fault 精确、
  不消费保留）。保留标记由每线程 `ISA` 单槽持有（精确地址 + 宽度，F8.1），
  `clear()` 复位、不做检查点序列化。
- **B7 未实现**：非 B1–B6 的成功解码指令仍返回
  `UnimplementedInstruction`（显式 panic）；未匹配/保留编码返回
  `IllegalInstruction`（ILLI）。不做跨批混写。
- **断言**：264 行逐条解码断言（`decode-assertions.tsv`）+ 388 条非法/保留/
  身份回归用例（`decode-negative.tsv`），由 `make check-gem5-decode` 运行；
  B1 执行断言 `exec/b1_test.cc`（38/38）由 `tools/gem5/check_b1.py`、
  B2 执行断言 `exec/b2_test.cc`（8/8、逐 wyde/立即数分片/FCSR 掩码/ILLI）
  由 `tools/gem5/check_b2.py`、B3 执行断言 `exec/b3_test.cc`（42/42、128 位
  高低半/立即数边界/one-hot/循环移位/有符号无符号比较/除余定值/64 位写满）
  由 `tools/gem5/check_b3.py`、B4 执行断言 `exec/b4_test.cc`（63/63、non-B4
  201/201、窄位宽截断/扩展/舍入/比较/移位/rev/ILLI）由 `tools/gem5/check_b4.py`、
  B5 执行断言 `exec/b5_test.cc`（28/28、non-B5 236/236、块搬移范围/重叠/
  `rf0`/`ra0`、条件边界、64 位地址、RAS C1–C3b/D1–D4b、精确异常）由
  `tools/gem5/check_b5.py`、B6 执行断言 `exec/b6_test.cc`（30/30、non-B6
  234/234、`rule_refs` 5/14/12、swym/fence 掩码 4096×2/`lr` 零扩展+MALIGN+
  hb、`sc` 成功失败+宽度截断+精确 fault、CFXREG/CFXESC、保留单槽覆盖与消费）
  由 `tools/gem5/check_b6.py` 编译运行（均不进 gem5 二进制，不改
  `tests/**`）。
- **GEM5-005t 增量**：`ftsclb`/`fosclb` 第三操作数 `rfhd/rf` → `rdhd/rd`
  （同 `orrr` 编码，SPEC-181t F5.2 C1；旧 rf 写法为负例守护）；12 条 `sc.*`
  的 `rdhb != rd0`（`dst_rd0`）合法性数据 + 28 条合法性断言（sc 目的 rd0
  ⇒ ILLI、`rdhc=rd0` 仍合法、scaleB 指数 `rdhd=0` 合法）。
- **B1–B7 边界**（GEM5-002t-REPORT §5）：38 / 8 / 42 / 63 / 28 / 30 / 55。

## 补丁集

- 形态：**树形补丁集**（`patches/<上游相对路径>.patch`，一文件一补丁），
  清单见 `series`；规范 `docs/Process-01-组件补丁组织与构建编排.md`。
- 规模（2026-11-02 现场统计）：**45 份** = 新增 43 + 修改 2
  （`src/arch/Kconfig`、`src/arch/SConscript`）。
- 解码表由 `tools/gem5/gen_decode_table.py` 从 `contracts/opcodes.yaml` +
  `GEM5-002t` 矩阵生成；`--check` 为漂移门控（不手工编辑 `.inc`）。
  生成器内置 SPEC-181t 守护：scaleB 第三操作数必须是 `rdhd/rd`（旧 `rfhd/rf`
  直接拒绝），12 条 `sc.*` 必须保留 `dst_rd0` + `rdhb != rd0`。

## 构建 / 校验

```
make build-gem5          # SCons；SCons 缺失时 rc=2（BLOCKED，不假 PASS）
make check-gem5-decode   # 264 行解码断言 + 388 条非法/回归用例
python3 tools/gem5/check_b1.py --source .work/source/gem5   # B1 执行断言（38/38）
python3 tools/gem5/check_b2.py --source .work/source/gem5   # B2 执行断言（8/8）
python3 tools/gem5/check_b3.py --source .work/source/gem5   # B3 执行断言（42/42）
python3 tools/gem5/check_b4.py --source .work/source/gem5   # B4 执行断言（63/63）
python3 tools/gem5/check_b5.py --source .work/source/gem5   # B5 执行断言（28/28）
python3 tools/gem5/check_b6.py --source .work/source/gem5   # B6 执行断言（30/30）
make check-patch-tree
```

gem5 自身只接受 `<src>/build/<variant>` 作为构建目录；
`make build-gem5` 成功后把 `.work/build/gem5` 链接到该目录，
二进制在 `.work/source/gem5/build/DADAO/gem5.opt`。
