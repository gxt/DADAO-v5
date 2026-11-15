# m13-testcases-048: 伪指令专用汇编载体（7 个展开形态，`tests/inst/00-isa-design/`）

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-spec-010`（`rf2rf` 已合）、`m13-spec-011`（伪指令正文迁入 `SimRISC-00 §5`、写宽对照表）
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（≥2 路注入 + 相关门控）
**状态**：待开始

## 用户裁定（2026-11-15）

> 「同意A，两个补充也可以。SimRISC-03 中的伪指令应该移动到 SimRISC-00的第5章…；此外，在tests/inst/00 目录下，新增这7种伪指令的专门的汇编测试」
> 随后确认口径 **a（按展开形态 7 个）**：「a；或者，就以伪指令名称来区分也可以，那就4个；你的建议」

**采纳 (a) 7 个展开形态**（主会话建议，理由：失败归因可定位到具体形态；`set.ft` 的 imm 窄写 vs reg 整 64 位正是本次裁定点，合并会互相掩盖）。

## 7 个载体（`tests/inst/00-isa-design/`）

| # | 载体 | 覆盖的展开形态 | 关键点 |
|---|---|---|---|
| 1 | `pseudo_set.rd_imm.S` | `set.rd rd, imm64` → 1–4 条 `set.zw/set.ow` + `or.w/andn.w` | 零/全 1/±小值/稀疏位型；**只能一条 `set.zw`/`set.ow`**；指令数最少化 |
| 2 | `pseudo_set.rd_reg.S` | `set.rd rd, rs` → `rb2rd`/`rf2rd`/`ra2rd`/`rd2rd` | 四种源银行各 1 点；整 64 位 |
| 3 | `pseudo_set.rb_imm.S` | `set.rb rb, imm64` → `set.zw-rb` + `or.w-rb` | **rb 无 `set.ow`** ⇒ 负值形态与 rd 不同；只能一条 `set.zw` |
| 4 | `pseudo_set.rb_reg.S` | `set.rb rb, rs` → `rd2rb`/`rb2rb` | 两种源；整 64 位 |
| 5 | `pseudo_set.ft_imm32.S` | `set.ft rf, imm32` → 2× `set.w` | **只写低 32、高 32 不动**（写宽对照表第一行）；边界 imm=0 / 0xFFFFFFFF |
| 6 | `pseudo_set.fo_imm64.S` | `set.fo rf, imm64` → 4× `set.w`（imm=0 ⇒ `rd2rf` from `rd0`） | 整 64 位；`imm=0` 走 `rd2rf` 特例 |
| 7 | `pseudo_set.fx_reg.S` | `set.ft/set.fo rf, rf` → **`rf2rf`** | **整 64 位**（写宽对照表第二行，`m13-spec-010` 后可观察变化）；高半必须被覆盖 |

## 任务

1. 新建 7 个 `.S`：**检查点内联期望**（`inst_test.inc` 现有宏优先，缺宏时在 `.S` 内 `.macro`），每册 **≤127 点**、点号连续；期望全部由 `SimRISC-00 §5` + `SimRISC-03`（新三章）+ `SimRISC-02` 推导，**不得从 qemu/llvm 反推**；
2. **双注册表**：`tools/testcases/validate_vectors.py::NON_ID_CARRIERS` 与 `tools/testcases/check_tests_index.py::NON_ID_CARRIERS` **逐文件**登记（现只有 `undi_reserved.S` 一条）；`tests/inst.yaml` 增 7 条索引（`platforms: [system]`、`level: full`）；
3. `tests/case-ledger.tsv` 重生成；`tests/inst/README.md` 与 `MIGRATION.md` 同步（新增一节说明伪指令载体）。
4. **写宽对照**：载体 5 与 7 必须各自断言"高 32 保持" vs "高 32 被覆盖"，成为这次语义变化的第一道回归。

## 验收（逐条贴真实 rc）

1. 7 个载体均能汇编（安装根 `llvm-mc` 已支持 `rf2rf`）并在 qemu 上执行：贴 `run_asm_suite --platforms qemu` 的 id/镜像/检查点计数与 rc；
2. 每册 ≤127 点、点号连续；`validate-vectors`（非 id 载体 8 条：`undi_reserved` + 7）、`check-tests-index`（现场条数）、`check-case-ledger` rc=0；
3. **注入 ≥2 路**（`cp`+md5 还原）：① 把载体 5 的期望改成"高 32 被覆盖" ⇒ 应红（证明它守的是窄写）；② 把载体 7 的期望改成"高 32 保持" ⇒ 应红；
4. `check-inst-asm` 现场计数（id 数不变 264；镜像数 +新增）；`check-no-residue`、`check-knowledge-refs` rc=0；
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 命名裁定（用户 2026-11-15）

- 采用**方案 A**（保留助记符点号）：`pseudo_set.rd_imm.S`、`pseudo_set.rd_reg.S`、`pseudo_set.rb_imm.S`、`pseudo_set.rb_reg.S`、`pseudo_set.ft_imm32.S`、`pseudo_set.fo_imm64.S`、**`pseudo_set.fx_reg.S`**（`fx` = `ft`/`fo` 两族寄存器源，二者都展开 `rf2rf`）；
- 索引 id 顺延：`inst-00-isa-design-002` … `-008`（`-001` 归 `undi_reserved.S`）。

## 硬约束

- 只改 `tests/inst/00-isa-design/**`、`tests/inst.yaml`、`tests/case-ledger.tsv`、`tools/testcases/{validate_vectors.py,check_tests_index.py}`（仅 `NON_ID_CARRIERS` 登记）、`tests/inst/{README.md,MIGRATION.md}`、本任务书；
- **不改** `spec/`、`contracts/`、`components/**`；禁 `install-host`/`check-modules`/`build-*`；不 sync/reset 节点；不提交 git；注入还原 `cp`+md5。

## 待裁定

（实现中写）

## 审阅记录

（待填）
