# gem5 组件（gem5）

DADAO 的 gem5 功能参考（M11）。上游基线与补丁序列由
`manifests/components.lock.toml` 锁定；工作树由 `make fetch` +
`make apply-series` 在 `.work/source/gem5` 建立。

## 当前状态（GEM5-004t / B0 + GEM5-005t + GEM5-006t / B1 + GEM5-007t / B2 + GEM5-008t / B3 + GEM5-009t / B4）

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
- **B5–B7 未实现**：非 B1/B2/B3/B4 的成功解码指令仍返回
  `UnimplementedInstruction`（显式 panic）；未匹配/保留编码返回
  `IllegalInstruction`（ILLI）。不做跨批混写。
- **断言**：264 行逐条解码断言（`decode-assertions.tsv`）+ 388 条非法/保留/
  身份回归用例（`decode-negative.tsv`），由 `make check-gem5-decode` 运行；
  B1 执行断言 `exec/b1_test.cc`（38/38）由 `tools/gem5/check_b1.py`、
  B2 执行断言 `exec/b2_test.cc`（8/8、逐 wyde/立即数分片/FCSR 掩码/ILLI）
  由 `tools/gem5/check_b2.py`、B3 执行断言 `exec/b3_test.cc`（42/42、128 位
  高低半/立即数边界/one-hot/循环移位/有符号无符号比较/除余定值/64 位写满）
  由 `tools/gem5/check_b3.py`、B4 执行断言 `exec/b4_test.cc`（63/63、non-B4
  201/201、窄位宽截断/扩展/舍入/比较/移位/rev/ILLI）由 `tools/gem5/check_b4.py`
  编译运行（均不进 gem5 二进制，不改 `tests/**`）。
- **GEM5-005t 增量**：`ftsclb`/`fosclb` 第三操作数 `rfhd/rf` → `rdhd/rd`
  （同 `orrr` 编码，SPEC-181t F5.2 C1；旧 rf 写法为负例守护）；12 条 `sc.*`
  的 `rdhb != rd0`（`dst_rd0`）合法性数据 + 28 条合法性断言（sc 目的 rd0
  ⇒ ILLI、`rdhc=rd0` 仍合法、scaleB 指数 `rdhd=0` 合法）。
- **B1–B7 边界**（GEM5-002t-REPORT §5）：38 / 8 / 42 / 63 / 28 / 30 / 55。

## 补丁集

- 形态：**树形补丁集**（`patches/<上游相对路径>.patch`，一文件一补丁），
  清单见 `series`；规范 `docs/Process-01-组件补丁组织与构建编排.md`。
- 规模（2026-11-02 现场统计）：**39 份** = 新增 37 + 修改 2
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
make check-patch-tree
```

gem5 自身只接受 `<src>/build/<variant>` 作为构建目录；
`make build-gem5` 成功后把 `.work/build/gem5` 链接到该目录，
二进制在 `.work/source/gem5/build/DADAO/gem5.opt`。
