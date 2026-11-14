### `m13-testcases-037`：`sc` 保留粒度（精确地址 + 访问宽度）正式向量

> **本任务无 `tests/inst.yaml` 片段**：5 个新检查点挂在**既有** id `sc.b.nn_orrr_rd` 的链例尾部
> （`contracts/opcodes.yaml` 无独立「保留粒度」身份；另建 `.S` 会撞 `validate_vectors` 的
> 「同一 stem 只能一个 `.S`」与 `check_tests_index` 的载体↔索引双向断言）⇒ id 数 / 镜像数不变。
> 另：L1 `check_tests_index` 现拒绝 `tests/inst/` 下**任何** `*.yaml`（§5.5 的 YAML 退役），
> 与 §5.3 的 `.fragments/<任务>.inst.yaml` 协议冲突——需新增清单条目的分片任务会撞红，待架构侧处置。

- **载体**：`tests/inst/12-misc/sc.b.nn_orrr_rd.S` **只追加**点 17–21（链例 16 → 21），原故障例
  点号 17 → 22（点号仍连续 1..22 = 链例 21 + 故障例 1）；文件头分类计数改 semantic 7 → 12，
  「保留粒度」写入头部（键 = 精确地址 + 访问宽度）、GAP 段收窄。**无新 id / 无新文件 / 无宏层改动**。
- **id 归属判据**：`contracts/opcodes.yaml` **没有**独立的「保留粒度」身份 ⇒ 不能新建 `.S`
  ——`validate_vectors` 断言「同一 stem 只能有一个 `.S`」（新文件与既有 `sc.b.nn_orrr_rd.S` 撞 stem）
  且 `check_tests_index` 断言「载体集 == 索引集」（新文件须改根清单，属串行合并面）。故按任务书
  允许的形态挂在既有 `sc.<w>.<序>` 的链例尾部：点号 +5、影像数不变（265 id / 901 镜像）。
- **语义**（`spec/SimRISC-12 §1`「保留机制」+ `contract-isa §14.2` + 用户裁定 2026-11-14
  「ISS-435 严格按 spec」）：点 17 同字异址写（`st.b@A+1`）、点 18 同址异宽写（`st.t@A`）、
  点 19 同址同宽同 hart 写 ⇒ `sc` **必须成功（0）**（清除侧只列「另一 hart 同址同宽 store」）；
  点 20 本 hart 另一条 `lr`、点 21 `sc` 自消费后二次 `sc` ⇒ **失败（1）**。每点手算拍值内联断言
  （`__VERIFY_MEM`），每点一行、点号连续。
- **三方逐字节**：`run_asm_suite.py`（同一 ELF：chipyard / qemu / gem5）2/2 镜像（链例 21 点 =
  168 B、故障例 `0xF8`）三平台 rc=0 且字节流逐字节相同；点 17–21 实测 `0 0 0 1 1`。
- **改前正证**：同一 ELF 在改前二进制（qemu 安装根 `b34ed7f9…` / chipyard `pre-sim`
  `ac35dffb…`）上首红点 = 17；record-only 复刻探针逐点 `1 1 1`（spec `0 0 0`）⇒ 向量真的守护裁定。
- **门控**：`check-inst-asm`（目标体，`--qemu` = 改后二进制）265 id / 901 镜像全绿；检查点数
  +5（链例 21）；`check-tests-index`/`validate-vectors`/`check-case-ledger`/`check-no-residue`/
  `check-knowledge-refs` rc=0（`case-ledger.tsv` 由 `--write` 重生成：+6 行、1 行点号改）。
- **GAP（不伪造）**：① 多 hart 对同址同宽 store 清标记（Tiny 单 hart，无载体）；② **异常或中断
  进入清标记**：链例可构造（固件 hmon 返回槽指向固定 `.text` 桩），但三平台实测分歧 ——
  MALIGN/CFXMEM/ILLI 三路径 `chipyard 1 / qemu 1 / gem5 0`、CFXTRAP 路径 `1 / 0 / 0`
  （spec 均为 1）⇒ **不进正式向量**（不把任一平台行为写成期望），登记为待修实现缺口；
  ③ 存储序强度；④ `sc` 偶发失败。
