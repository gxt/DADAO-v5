# m13-gem5-012: `ext.uo`/`ext.so` orrr 的 `hd` 取 `rdHD[5:0]`（删 ILLI 路径）

**模块**：gem5
**项目里程碑**：M13
**依赖**：`m13-spec-008`（口径真源与契约先行；本任务依据其 §2.2 措辞与「用户裁定」段）
**可并行分片**：否（gem5 单组件单写者；可与 `m13-qemu-010` 并行，与其它 gem5 任务串行）
**状态**：待开始

**预估**：2–3 h（含 gem5 增量重建 10–25 min，开工前申报实际耗时）

## 用户裁定（2026-11-13）

> 「`ext.*` 的 orrr 形式，`rdHD` 取**低 6 位**作起始位 `hd` 后继续执行，**不抛 ILLI**。」

- **渠道**：用户 2026-11-13 裁定，由主会话转达；原话登记于 `ISS-422`（`.tao/knowledge/issues.yaml`）。
- **口径**：`hd = rdHD & 0x3F`；`rdHD` 高位忽略、不抛异常。`orri` 形式的 `immu6` 天然 6 位、行为不变。

## 背景（现状与缺陷）

- `components/gem5/patches/src/arch/dadao/exec/b3.cc.patch`：
  - `extendStartBit()` 注释自陈「orrr = the full 64-bit rdhd *register value*, so >63 is checkable; contract-isa §6.4.2」——把「可检查」当成了「须报错」。
  - `case B3Op::ExtUo/ExtSo` 内：`const uint64_t start = extendStartBit(inst, ctx);` 后紧跟 `if (start > 63) return Fault::Illegal;`（注释「orrr takes the whole register value, so 64..2^64-1 is ILLI」），再 `hd = start`、`mask = lowMask(hd + 1)`、符号位取 `(value >> hd) & 1`。
  ⇒ `rdHD=64` 等取值被判 ILLI（实测退出码 `0xF8`=248），与 chipyard 相反（`ISS-422`）。
- `components/gem5/patches/src/arch/dadao/exec/b3_test.cc.patch` **把旧行为钉成了期望**：「orrr hd comes from the whole rdhd register value: 64 and 2^64-1 are illegal, and nothing is written.」，`badHds[] = {64, 65, 0xFFFFFFFFFFFFFFFF, 1<<40}` 逐个断言 `Fault::Illegal` + `writes.empty()` ⇒ 本任务必须同步改这组断言，否则 `check_b3.py` 必红。
- chipyard RTL 对照（只读溯源，非执行依赖）：`WumingDecoder.orrrShift` 把 `rdHD` 值送 ALU 的 6 位 `shamt` 端口 ⇒ 天然截低 6 位。

## 范围（只改 gem5 组件）

1. **`.../exec/b3.cc.patch`**：`ExtUo`/`ExtSo` 分支删 `if (start > 63) return Fault::Illegal;` 与其理由注释；`hd` 改为截低 6 位——**二选一**（实现须自洽、注释同步改述为「`hd = rdHD[5:0]`，高位忽略（spec §2.2 / `ISS-422`）」）：
   - 甲：`hd = static_cast<unsigned>(start & 0x3F)`（调用点掩码）；
   - 乙：`extendStartBit()` 内 orrr 分支返回 `value & 0x3F`（若该函数**仅** ext 使用；先 `grep` 确认调用者，若另有 shamt 使用者则只能取甲）。
   `dst == 0 ⇒ Fault::Illegal` 保留不变。
2. **`.../exec/b3_test.cc.patch`**：把「`badHds ⇒ Illegal` + 无写」一组**替换**为截低 6 位口径，并与「高位被忽略」互证：
   - `rdHD=64` ⇒ 与 `hd=0` **同值**、**恰一次写**；`65 ⇒ hd=1`；`0xFFFF_FFFF_FFFF_FFFF ⇒ hd=63`；`1<<40 ⇒ hd=0`；`0x43(67) ⇒ hd=3`；
   - 期望由 spec 口径在测试内独立手算：`mask = lowMask((start & 63) + 1)`、`result = value & mask`、`ExtSo` 且 `(value >> (start & 63)) & 1` 为 1 时 `|= ~mask`；每个新用例附 `spec_cite`（`SimRISC-04: ext.uo` / `ext.so`）与「低 6 位」依据；
   - `dst rd0 ⇒ Illegal`、`orri immu6` 既有断言保持不变。
3. `components/gem5/changelog.md` 记一条。
4. **oracle 向量（独立派生）**：新增/改动的期望**不得**由被测实现输出反填；除 harness 断言外，另建一组 ≥6 条的 oracle 表（覆盖 `ext.uo`/`ext.so` × `hd∈{0,3,63}` × 源值「全 1」「bit_hd=1 的最小数」），逐条写出「位段复制 + 符号/零扩展」的手算过程，落完成区或证据脚本注释。
5. **增量重建**：`make build-gem5`（改单文件，预计 10–25 min；开工前申报，完成后记录实测墙钟）。

**非范围**：不改 `tests/inst/**`（归 `m13-testcases-033`）、不改 spec/合约（归 `m13-spec-008`）、不改 qemu/chipyard、不改 B3 之外的 `exec/*.cc`。

## 验收标准（可执行、可失败）

1. **组件 harness**：`python3 tools/gem5/check_b3.py` `rc=0` —— `B3 coverage 42/42`、harness 与 live 集合双向差集为空、`PASS` 计数现场值（较施工前增加新用例数、`FAIL=0`；施工前计数先抄一份做对照）。
2. **真实 gem5 二进制（非 harness）**：`.S` 探针经 `tools/testcases/inst/run_asm_suite.py --platforms gem5`（或等价 SE/FS 单例）执行 —— `rdHD=64` 与 `hd=0` 结果**逐字节相同**，`rdHD=67 ≡ hd=3`、`rdHD=63 ≡ hd=63`；**不再出现 ILLI**（旧为 `0xF8`）。
3. **旧行为可达 FAIL**：施工前 gem5 二进制（`md5`/构建 commit 钉住并抄进完成区）跑同一探针 ⇒ ILLI；改后 ⇒ 正常。若旧二进制已被覆盖无法复原 ⇒ 用「注入 ② 恢复 `start > 63 ⇒ Illegal`」作为等价 FAIL 路径，并在完成区说明替代理由（禁写「推定」）。
4. **回归**：`make check-gem5-decode` rc=0（264 行 decode 断言不退化）；`python3 tools/gem5/check_b7.py` rc=0（FP 族不受影响，作回归项；ext 不属 B7）。
5. **可达 FAIL 注入（≥2 路；`cp` 备份 + md5 对账 + `touch` 还原 ⇒ 回绿；禁 `git checkout/restore/stash`）**：
   ① 掩码改恒等（`hd = start`，且 ILLI 已删）⇒ `check_b3.py` 红（`rdHD=64` 期望不符 / 移位量越界）；
   ② 恢复 `if (start > 63) return Fault::Illegal;` ⇒ 新用例红（`64/65/0xFFFF…/1<<40` 四条 Fault 不符）。
6. **门控**：`check-patch-tree` 的 **gem5 子集 problem=0**（整树红若来自并行任务在飞，须现场归因并给子集判据）；`check-component-changelog` rc=0；`check-source-state` 的 **gem5 OK**（`base+N`、`clean=True`）。
7. **脚本与对账**：一键证据脚本 `rc=0`；完成区 ≤30 行、无运行期路径；「修改文件」与 `git status -uall` 对账。

## 说明

- gem5 侧「B 组探针」指 **B3 断言 harness（`exec/b3_test.cc` + `tools/gem5/check_b3.py`）**；`check_b7.py` 是浮点 B7 的门控、与 `ext` 无关，只作回归。
- 组件补丁须走 `make_patch`（一文件一补丁）导出；`check-patch-tree` 保持 problem=0。
- 重建期间 `free -g` 可用内存 < 8 GiB ⇒ 降 `JOBS` 并记录次数；禁 `-j$(nproc)`。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号），**动手前 `git rev-parse --show-toplevel` 自证**；禁改主工作树；组件源树改动收敛为 `base+1` 且干净（不入本仓库）。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；计数取现场值；「修改文件」与 `git status -uall` 对账。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需用户语义裁定写进任务书「待裁定」段返回主会话。
6. 一键证据脚本；反例注入「注入 → FAIL → 还原（`cp`+md5）→ 回绿」。
7. 禁 `reset --hard`/`checkout -- .`（`ISS-402`）。
8. 命令作用域 = workdir（仓库根），用相对路径；临时文件放 `/tmp/opencode/<任务ID>/`。

## 审阅记录

（待填）
