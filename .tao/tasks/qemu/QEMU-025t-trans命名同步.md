# QEMU-025t: QEMU trans_* 命名同步到 0.5.4 id

**模块**：qemu
**项目里程碑**：M1→M2
**依赖**：无
**状态**：已验证

## 问题描述

`tools/integ/check_interface_alignment.py` 的 `QEMU trans ↔ opcodes.yaml` 检查报 **FAIL（0/254）**：

```
MISSING: ld.ub_rrii_rd -> trans_ld_ub_rrii_rd [M1]
MISSING: cmp.uo_orrr_rd -> trans_cmp_uo_orrr_rd
...
```

根因：**QEMU 补丁的 `trans_*` 函数命名与 0.5.4 的 `opcodes.yaml` id 期望不一致**：

- QEMU 侧实际命名（旧风格）：`trans_cmp_uo`、`trans_ld_ub` 等（`mnemonic` 级）
- 检查器期望（新 id 风格）：`trans_cmp_uo_orrr_rd`（`id` 级，含 format/feature）

即 `check_qemu_trans.py` 按 `opcodes.yaml` 的 `id`（`mnemonic_format_feature`）拼期望函数名，而 QEMU 补丁的 trans 函数未随之更新。

**注**：此检查只读 `opcodes.yaml` + QEMU 补丁（**不需 QEMU 二进制**），属 pre-existing 跨模块缺口（0.5.4 id 化后的遗留）。

## 目标

使 QEMU 的 `trans_*` 命名与 0.5.4 的 `id` 一致，`check_qemu_trans.py` 与 `check_interface_alignment.py` 的该项通过。

## 待确认（执行前与用户确认）

1. **命名方案**：QEMU 的 `trans_*` 是否改为 `trans_<id>`（如 `trans_ld_ub_rrii_rd`）？还是**检查器侧**放宽匹配（如按 `mnemonic` 匹配，容忍多格式）？
2. **改动范围**：QEMU 补丁中有多少 `trans_*` 函数需改名？（`decode` 表由 `generate_decodetree.py` 生成？）
3. **是否影响 QEMU 解码逻辑**（函数名 vs 语义）

## 修改内容（待确认后细化）

- QEMU `target/dadao/*.c.inc` / `translate.c` 的 `trans_*` 函数命名
- `tools/qemu/check_qemu_trans.py` 的期望函数名构造
- `tools/qemu/generate_decodetree.py`（若其生成 `trans_*` 引用）
- 重生成/重建补丁（按 `docs/spec/component-patching.md`：裸 `git diff`，一文件一补丁）

## 约束

- **命令缺失/构建失败 → 停下报告，禁止自行安装/下载**
- 逐条核对，禁止正则批量替换
- 完成后 `make check` EXIT=0

## 验收标准

1. `python3 tools/qemu/check_qemu_trans.py`：**254/254**（M1 178/178）
2. `python3 tools/integ/check_interface_alignment.py` 的 `QEMU trans ↔ opcodes.yaml` **PASS**
3. 补丁格式合规（每份恰 1 个 `diff --git`）
4. `make check` EXIT=0
5. 反例验证（注入缺失/错名 trans → 检查失败）

## 完成区
**测试结果**：通过 5/5；全部 PASS

**修改文件**：
- `.work/source/qemu/target/dadao/insn.decode` — 重新生成自 opcodes.yaml（254 条，移除 ftmadd/fomadd，swym 改为 @misc 格式）
- `.work/source/qemu/target/dadao/insn_trans/trans_arith.c.inc` — 重命名 62 个 trans_* 函数，移除 ftmadd/fomadd
- `.work/source/qemu/target/dadao/insn_trans/trans_block.c.inc` — 重命名 8 个 trans_* 函数
- `.work/source/qemu/target/dadao/insn_trans/trans_compare.c.inc` — 重命名 16 个 trans_* 函数
- `.work/source/qemu/target/dadao/insn_trans/trans_cond_assign.c.inc` — 重命名 10 个 trans_* 函数
- `.work/source/qemu/target/dadao/insn_trans/trans_ctrl.c.inc` — 重命名 18 个 trans_* 函数，swym 参数类型 arg_main→arg_misc
- `.work/source/qemu/target/dadao/insn_trans/trans_extend.c.inc` — 重命名 20 个 trans_* 函数
- `.work/source/qemu/target/dadao/insn_trans/trans_imm.c.inc` — 重命名 10 个 trans_* 函数
- `.work/source/qemu/target/dadao/insn_trans/trans_logic.c.inc` — 重命名 16 个 trans_* 函数
- `.work/source/qemu/target/dadao/insn_trans/trans_mem.c.inc` — 重命名 32 个 trans_* 函数
- `.work/source/qemu/target/dadao/insn_trans/trans_shift.c.inc` — 重命名 20 个 trans_* 函数
- `tools/integ/check_interface_alignment.py` — EXPECTED_TRANS 256→254
- `components/qemu/patches/` — 重新生成 31 份补丁

**验收结果**：
```
$ python3 tools/qemu/check_qemu_trans.py
check_qemu_trans: 254/254 insns have trans impl (M1 178/178)

$ python3 tools/integ/check_interface_alignment.py
4.Opcodes    QEMU trans ↔ opcodes.yaml                  PASS     check_qemu_trans: 254/254 insns have trans impl (M1 178/178)
4.Opcodes    QEMU trans_* 定义数                           PASS     254 trans_* 函数
总计: 80 项 | PASS: 80 | FAIL: 0 | MANUAL: 0

$ make build-qemu
build-qemu: PASS

$ make check
repository checks: PASS

反例验证：注入 trans_ld_ub_WRONG_rd → check_qemu_trans 报 253/254 MISSING，还原后 254/254
```

**新发现/坑**：
1. **swym 格式变更**：旧 decode 文件中 swym 是 @main 格式（mask=0xFF000000），但 opcodes.yaml 定义为 @misc 格式（mask=0xFFFC0000）。重新生成 decode 文件后，swym 从 arg_main 变为 arg_misc，需同步修改函数签名。
2. **ftmadd/fomadd 不存在于 opcodes.yaml**：旧 decode 文件有 256 条（含 ftmadd/fomadd），但 opcodes.yaml 只有 254 条。这两个 ILLI 存根已从 decode 文件和源码中移除。
3. **EXPECTED_TRANS 硬编码**：`check_interface_alignment.py` 中 `EXPECTED_TRANS = 256` 需随 opcodes.yaml 条目数同步更新。
4. **补丁生成流程**：修改源码后需 `make_patch.py` 重新生成补丁，不能直接 `git checkout` 补丁文件（会还原到旧版本）。

**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审阅范围**：全部修改文件（11 个源文件 + 1 个检查器 + 31 份补丁）

**finding 列表**：

| # | finding | 严重度 | 处置 | 改了什么 | 复验证据 |
|---|---------|--------|------|---------|---------|
| 1 | swym 从 @main 改为 @misc，函数签名需同步 | 高 | ✅已修 | `trans_swym_oiii_imm` 参数 `arg_main` → `arg_misc` | `make build-qemu` EXIT=0 |
| 2 | ftmadd/fomadd 不存在于 opcodes.yaml | 中 | ✅已修 | 从 trans_arith.c.inc 移除两个函数 | grep 确认不存在，254/254 |
| 3 | EXPECTED_TRANS 硬编码 256 | 中 | ✅已修 | `check_interface_alignment.py` 改为 254 | 80/80 PASS |
| 4 | 补丁需重新生成 | 高 | ✅已修 | `make_patch.py qemu` 重新生成 31 份 | 每份 1 个 diff --git |

**判决**：所有 finding 已修复，可标「待验收」。

#### 第 1 轮 reviewer 验收

**审查范围**：`components/qemu/patches/`（31 份）、`tools/integ/check_interface_alignment.py`、`.work/source/qemu/target/dadao/{insn.decode,insn_trans/*.c.inc}`、`contracts/opcodes.yaml`。全部为独立重跑，未采信工程师转述。

**重跑记录（我自己的输出/退出码）**：

```
$ python3 tools/qemu/check_qemu_trans.py
check_qemu_trans: 254/254 insns have trans impl (M1 178/178)
EXIT=0

$ python3 tools/integ/check_interface_alignment.py
        4.Opcodes    QEMU trans ↔ opcodes.yaml   PASS   check_qemu_trans: 254/254 insns have trans impl (M1 178/178)
        4.Opcodes    QEMU trans_* 定义数          PASS   254 trans_* 函数
        总计: 80 项 | PASS: 80 | FAIL: 0 | MANUAL: 0
EXIT=0

$ make build-qemu      # configure OK; ninja: no work to do（源码 mtime < 二进制，改名后源码已编入）
build-qemu: PASS
EXIT=0

$ make check
check-patch-tree: 2 component(s), 67 patches OK
repository checks: PASS
EXIT=0
```

**反例注入（我自己做，非复跑脚本）**：

1) `check_qemu_trans` —— 复制补丁集到 `/tmp/opencode/QEMU-025t/patches_bad`，`trans_ld_ub_rrii_rd` → `trans_ld_ub_WRONG_rd`：
```
$ python3 tools/qemu/check_qemu_trans.py --src /tmp/opencode/QEMU-025t/patches_bad
MISSING: ld.ub_rrii_rd -> trans_ld_ub_rrii_rd [M1]
check_qemu_trans: 253/254 insns have trans impl (M1 177/178)
$ ... --strict  → EXIT=1
```
2) `check_interface_alignment` —— 注入到**仓库内**补丁后运行，报 FAIL/EXIT=1；随后从源树 `git diff` 重建被注入文件，sha256 复原一致（`b31258…`）：
```
4.Opcodes    QEMU trans ↔ opcodes.yaml   FAIL   MISSING: ld.ub_rrii_rd -> trans_ld_ub_rrii_rd [M1]
总计: 80 项 | PASS: 79 | FAIL: 1 | MANUAL: 0     IFACE_EXIT=1
还原后 sha = b312581120aba68cf96630e0d93c2c1d1ec6def12ea2b571c1f9bd6969898465（注入前一致）
```
> 还原说明：本任务修改过的补丁相对 HEAD 已变更，误用 `git checkout` 会还原到旧版；已改用源树 `git diff` 重建并 sha 校验复原。复原后 `git status` 仍为 33 项、全 `M`、无未跟踪文件；三项检查重回 254/254、80/80、EXIT=0。

**约束核验（逐条）**：

| # | 约束 | 结果 | 证据 |
|---|------|------|------|
| 1 | `check_qemu_trans` 254/254（M1 178/178） | ✅ | 重跑输出，EXIT=0 |
| 2 | `check_interface_alignment` 80/80（含 `QEMU trans ↔ opcodes.yaml`） | ✅ | 重跑输出，EXIT=0 |
| 3 | `make build-qemu` / `make check` EXIT=0 | ✅ | 见上 |
| 4 | 补丁格式：每份恰 1 个 `diff --git` | ✅ | 31/31 份计数均为 1，无例外 |
| 5 | 补丁 == 源树 `git diff <base>` | ✅ | 31/31 逐份 `diff` 一致（fails=0） |
| 6 | 命名正确性（id↔trans） | ✅ | 254 个 id 无 sanitize 碰撞；直接构造 `trans_<sanitize(id)>` 全部命中；定义集合大小=254、无重复 |
| 7 | 未改指令语义（仅函数名/引用） | ✅ | 见下方「语义不变证据」 |
| 8 | swym @main→@misc、ftmadd/fomadd 移除与 opcodes.yaml 一致 | ✅ | 见下 |
| 9 | 反例注入可报 MISSING | ✅ | 见上 |
| 10 | 改动范围与任务一致 | ✅ | 33 项 = 31 补丁 + 1 检查器（`EXPECTED_TRANS 256→254`）+ 1 任务文件 |

**命名抽查（含 rd/rb、or.w、add.so、cmp.uo）**：`ld.ub_rrii_rd→trans_ld_ub_rrii_rd`、`cmp.uo_orrr_rd→trans_cmp_uo_orrr_rd`、`cmp.uo_orrr_rb→trans_cmp_uo_orrr_rb`、`or.w_rwii_rd→trans_or_w_rwii_rd`、`or.w_rwii_rb→trans_or_w_rwii_rb`、`or.w_orrr_rd→trans_or_w_orrr_rd`、`add.so_rrrr_rd→trans_add_so_rrrr_rd`、`add.so_orrr_rb→trans_add_so_orrr_rb` —— 全部命中且语义字段（rd/rb 变体）正确。

**语义不变证据（比 diff 更强）**：以「函数体指纹」（签名去函数名 + body 原文）建立旧→新映射：244 个唯一匹配 + 9 个同体 ILLI 存根（`gen_exception_illegal`，互换亦语义等价）+ 3 个无匹配。对全部映射逐函数比对**承担的 pattern 集合**，**不一致 0**。旧×新归一化 diff 仅三处差异，且均属任务声明范围：
- `trans_arith`：移除 `ftmadd`/`fomadd` 两个 ILLI 存根；
- `trans_ctrl`：`trans_swym_*` 参数 `arg_main`→`arg_misc`。
无 rd/rb 等错配。

**swym / ftmadd / fomadd 与 opcodes.yaml 一致性**：`opcodes.yaml` swym 条目 `mask=0xFFFC0000`（@misc）、ftmadd/fomadd **不存在**；decode 终态 `swym_oiii_imm … @misc`、无 ftmadd/fomadd；仓库与源树 grep 均无残留。`validate_decodetree.py <源树decode> <opcodes.yaml>` → **PASS**（254/254，错误 0）。用 `generate_decodetree.py` 重新生成 decode == 源树文件 == 补丁终态（逐字节 identical），证明 decode 系忠实再生而非手改。

**观察（非阻塞）**：
- 20 份与命名无关的补丁（非 `insn.decode`/`insn_trans/*`）仅 `index` 行哈希缩写长度变化（如 `0000000..34dfe04` → `0000000000..34dfe04da6`），**patch 正文逐字节不变**，系 `git` 缩写配置差异所致，`git apply` 不使用该哈希，功能无影响。
- `tools/qemu/generate_decodetree.py` 文档字符串仍写「256 条 pattern」（实际 254），属陈旧注释；该文件本次未改动，不影响验收，建议后续任务顺手更新。

**判决**：**Accepted**。验收命令块在本人独立重跑下全部通过（254/254、80/80、`make build-qemu`/`make check` EXIT=0），硬约束逐条守住，反例注入证实检查器对错名敏感且已复原。主会话可将任务状态改为 `已验证`（最终接受仍由架构师终审）。

**备注**：审查者仅在 `/tmp/opencode/QEMU-025t/` 与仓库内做了可复原的反例注入，未修改任何交付物；仓库最终状态与审查前一致（33 项修改，全 `M`）。