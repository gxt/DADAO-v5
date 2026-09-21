# TESTCASES-011m: testcases 里程碑

**模块**：testcases
**项目里程碑**：M1
**状态**：待开始
**目标**：DADAO-v5 的独立测试向量层完成——M1 scope（`contracts/opcodes.yaml` 中 `excluded_m1 != true`，178 条）内每条指令身份 `(insn, format)` 均有 ≥1 条 active 向量，5 类向量（encoding/legality/semantic/boundary/overlap）齐备，期望值全部独立派生自 `spec/`、`.tao/knowledge/contract-isa.md` 与 `.tao/knowledge/adr-0004-test-machine.md`；`tools/testcases/validate_vectors.py` 的 schema + 覆盖率 + inventory 同步 + `expected_pc` + `encoding.word` mask/value 校验全部接入 `make check` 并通过；`tests/vectors/isa/` 为方案 A 的目标文件集（14 个 `reg-*`/`mem-*`/`ctrl-*`/`misc` + 保留编码文件）；control-flow/load 的 deferred 已按 `expected_pc` 方案重设计或显式登记
**关联任务**：`TESTCASES-002t`、`TESTCASES-003t`、`TESTCASES-004t`、`TESTCASES-005t`、`TESTCASES-006t`、`TESTCASES-007t`、`TESTCASES-008t`、`TESTCASES-009t`、`TESTCASES-010t`

> **旧 `004t`/`005t`/`006t`（向量覆盖率修复 / validator 身份唯一性 / 语义向量地址迁移）已关闭**——其范围被 `002t` 覆盖或已达成；证据见 `.tao/knowledge/deferred.md` `## testcases`。本次最终重排后，`004t`/`005t`/`006t` 三个编号**复用为新任务**（load/store、`br.*`、`jump`/`call`/`ret`），故上「关联任务」指新任务。

## 核验
- 关联任务是否均已 `已验证`
- 各任务产出的文件是否都存在：
  - `tests/vectors/schema.md`、`tests/vectors/inventory.md`、`tests/vectors/README.md`
  - `tests/vectors/isa/` 目标文件集：`reg-arith`/`reg-logic`/`reg-shift-extend`/`reg-compare`/`reg-cond-assign`/`reg-imm-block`/`mem-rd`/`mem-rb`/`mem-ra`/`ctrl-br`/`ctrl-jump`/`ctrl-call`/`ctrl-ret`/`misc`（+ `008t` 保留编码文件）
  - 数据从零生成，`tests/vectors/isa/` 只含目标文件集（无任何旧/历史文件混入）
  - `tools/testcases/validate_vectors.py`、`Makefile`（`check` 含 `validate-vectors`）
- **数据级覆盖（机械可验，缺一不得置 `里程碑`）**：M1 scope 内**每个 `(insn, format)` 在 `tests/vectors/isa/*.yaml` 中至少有 1 条 `status: active` 的对应 class case**（由 `009t` 验收标准 7 核验）；`python3 tools/testcases/validate_vectors.py` 零错误、`make check` PASS。**不得仅以 validator 输出的 `178/178` 作为数据覆盖判据**（该数字为 inventory 声明级：inventory 行集 == `opcodes.yaml` M1 身份集，实测零数据/仅 1 条 case 亦输出 `178/178`）。
- **【前置阻断·009t 登记 → 010t 消解】**：`009t` 发现 **154 个数据级覆盖率缺口**（141 legality + 2 boundary + 11 overlap），由 `TESTCASES-010t` 消解（补 active case 或降级 ✓ → `deferred <reason>`）。**`010t` 完成且 `validate_vectors.py` gap = 0 后，本里程碑方可置 `里程碑`**。详见 `.tao/knowledge/deferred.md`「`010m` 阻断（用户裁定 B1）」与 `TESTCASES-010t` 任务书。
- **覆盖率主键与 scope 自洽**：validator 以 `(insn, format)` 为身份、以 `excluded_m1` 为 scope 判据；M1 内的 RA 存取/块赋值（`ld.o-ra`/`st.o-ra`/`ldm.o-ra`/`stm.o-ra`/`ra2rd`/`rd2ra`）与 `swym`/`illi`/`fence` 均被计入
- **测试机语义自洽**：`expected_fault` 可表达 ADR-0004 D5.8 的 `UNMAPPED`（`0x87`）；`ret` 冷 RA 的期望为 `RASUF`（非 ILLI）；相对控制流立即数用 `imm=1`（`rb0`=当前指令地址，ADR-0004 D6.5）
- **inventory 自洽**：inventory 含 `format` 列、M1 行集与 `opcodes.yaml` 一致（F2/F3），`file` 列与最终布局一致

## 【2026-09-15 最终裁决·阻断】F1/F5/F6/F7/F10 处置核验（缺一不得置 `里程碑`）

- **F1**：`orrr` 的 `shl`/`shr`/`ext`（20 身份）semantic/boundary 期望值已按**寄存器形式**重算，`input_state` 预置 shamt 寄存器（`003t`）；validator 的「src 字段寄存器必被预置」守卫（`003t`）生效且零误报。
- **F10**：全部 encoding 向量经语义推演确认「可解码执行无 fault」（不 ILLI/不自跳/unmapped/RASUF）；访存 encoding 的 base/地址/count 合法（`004t`），其余各文件由 `003t`~`007t` 分别生成时即须满足。
- **F5**：`UNDI`（保留编码）可在向量层表达并有 ≥1 active 向量 + validator 支持（`008t`，方案 A：复用 `class: legality` + `encoding.reserved: true`；已记录取舍，不立 ADR）。
- **F6**：`schema.md` 已澄清 encoding 类对**恒 fault 指令**（`illi`）豁免；`ret-riii` 的 encoding 缺省另因「返回目标依赖 harness 布局」（**非**恒 fault），二者在 inventory 均显式标注且理由正确（`002t`/`006t`/`007t`）。
- **F7**：`rela.si-rb` semantic 已 active（`003t`）；`jump-iiii`/`jump-rrii`/`call-iiii`/`call-rrii` 4 条经 **`expected_pc`** 方案全部改 active（`006t`）；`br.*` taken/not-taken 全覆盖（`005t`）；**无 PC-only deferred 残留**。
- 复核证据须来自各任务返工后的真实 `validate_vectors.py` + `make check` 重跑，不接受叙述。

## 跨模块影响已处置（见 `AGENTS.md`「模块里程碑与跨模块交互」）

- 向量是 `llvm`（lit 字节 oracle，`LLVM-012t`）与 `qemu`（harness `QEMU-014t`~`019t`）的公共输入；本里程碑达成前须确认无待处置的上游接口变更（`opcodes.yaml`/`legality_rules.yaml`/ADR-0004 冻结）。
- **schema 变更的下游同步**：本次新增 `expected_pc` 字段与 `008t` 的保留编码表达（方案 A：`encoding.reserved`），是 v5 内部模块间格式约定（非外部契约），但 `llvm`/`qemu`/`integ` 消费向量 schema，仍须同步其消费方式（登记跨模块影响；不立 ADR，以 `002t`/`008t` 任务书记录为准）。
- `integ`（`INTEG-002t`/`INTEG-003t`）消费向量做 E2E；若向量 schema 或故障语义在本模块内变更，须同步 `integ` 任务书。
- 若 `spec`/`qemu` 模块在本模块执行期间产生合约/接口变更（如 fault 码、地址图），本里程碑须后移或增加交互任务。

（核验通过后，主会话将 `**状态**` 置为 `里程碑`）
