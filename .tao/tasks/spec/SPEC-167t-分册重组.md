# SPEC-167t: 分册重组（11=核芯功能扩展 / 12=其它指令 / 非法指令并入 00）

**模块**：spec
**项目里程碑**：M9（收尾前）
**依赖**：FMA 链已完成（`SPEC-158t`/`TESTCASES-058t` 均验证）；`LLVM-126t`/`129t` 不触 spec
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源（用户裁定，2026-10-22/23）

- 「带 cfx 的指令，是否应该叫特权指令」→ 规范原文：`trap/escape/cfx2rd/cfx2rc/cfxld/cfxst` **可在任意运行模式执行**，是否允许由 cfx mask 控制 ⇒ "特权"名不符实
- 「`SimRISC-11` 改为核芯功能扩展指令分册，就放带 cfx 的 6 条指令；`SimRISC-12` 改为其它指令，把 `ct*` 指令移动到该分册，新开一节；`cfxld/cfxst` 移动到新的 `SimRISC-11` 中，注明待定」
- 「可以」（确认归属：`swym`/`fence`/`lr`/`sc` → 12；ILLI/UNDI 规则 → 00）
- 「`swym` 叫占位指令并不合适」→ 「**空转指令**」（体现 `swym N` 的时延语义；`N=0` 为空操作）

## 目标结构（最终形态）

```
SimRISC-00  指令系统设计
   § 编码布局 / 寄存器 / 异常规则（原 11 §2 ILLI/UNDI 并入）
SimRISC-11  核芯功能扩展指令
   trap / escape / cfx2rd / cfx2rc / cfxld(待定) / cfxst(待定)
SimRISC-12  其它指令
   §1 原子指令（fence / lr.* / sc.*）
   §2 空转指令（swym；N=0 为空操作，N>0 为时延）
   §3 位扫描与位计数（ctlz / cttz / ctpop；有效位宽由 hd 决定）
```

## 具体改动

1. **文件重命名**（git mv，保留历史）：
   - `spec/SimRISC-11-其它.md` → `spec/SimRISC-11-核芯功能扩展指令.md`
   - `spec/SimRISC-12-待定.md` → `spec/SimRISC-12-其它指令.md`
2. **SimRISC-11**：只留 cfx 6 条（`trap`/`escape`/`cfx2rd`/`cfx2rc`/`cfxld`/`cfxst`），`cfxld`/`cfxst` 标 **待定**（`deferred`）；删除"特权指令"提法，标题与首段按"任意模式可执行、cfx mask 控制"重写。
3. **SimRISC-12**：迁入 `fence`/`lr`/`sc`（原 11 §4）、`swym`（原 11 §1，节名改**空转指令**）、`ct*`（原 04 §2.2.2，新节**位扫描与位计数**）；`SimRISC-04` 删除 `ct*` 小节并留一句跨册指引（手册名 + 小节标题，不带 §）。
4. **SimRISC-00**：并入原 11 §2 的 ILLI/UNDI 规则（编码→异常的总规则），与既有"异常"章合并去重。
5. **引用同步**：`contracts/opcodes.yaml` 的 `spec_cite`（`fence`/`lr`/`sc`/`swym`/`ctlz`/`cttz`/`ctpop` 由 `SimRISC-11`/`04` 改指新册）；`tests/**` 同类引用；`spec/README.md` 索引；`manifests/spec-readonly.lock.toml` 重算。
6. **生成物**：各册附录 A/B 重生成（`gen_asm_list --embed-spec`、`gen_legality_list --apply`）；`check_tables` 的册名映射同步。
7. **门控**：`check_spec_numbering`（册名/编号不变，仅内容重排）、`check_spec_changelog`（互锁组按册名读取，确认不受影响）、`check_spec_cite_targets`（助记符→新册附录 A）。

## 验收

1. **结构**：11 册只含 cfx 6 条（`grep -c` 指令行 = 6，`cfxld`/`cfxst` 标 `待定`）；12 册含原子/空转/位扫描三节；04 册无 `ctlz/cttz/ctpop` 小节但有一句跨册指引。
2. **引用**：`grep -n "SimRISC-0[0-9]: \(fence\|lr\.\|sc\.\|swym\|ctlz\|cttz\|ctpop\)" contracts/opcodes.yaml` 全部指向新册；`check_spec_cite_targets` rc=0；`grep -rn 'SimRISC-1[12] §' spec/ tests/ contracts/` ⇒ 0。
3. **纯净度**：`check_spec_purity` rc=0（不得因搬迁带入 `scope`/任务号）。
4. **语义零漂移**：逐条比对搬迁前后指令语义段（应逐字相同，仅位置变化）。
5. **门控**：`check_tables`（6 表）、`check_asm_list_consistency`、`check-asm-prose`、`check-spec-numbering`、`check-spec-changelog`、`check-spec-readonly`、`check-instrinfo`、`check_qemu_trans --strict`（266/266）、L1、L2 全绿。
6. **可达 FAIL ≥3**：① 把 `fence` 留在 11 ⇒ 结构断言红；② `ctlz` 的 `spec_cite` 仍指 04 ⇒ cite_targets 红；③ 12 册重新出现 `占位指令` 节名 ⇒ 结构断言红。

## 接口规范

- **输入**：`spec/SimRISC-{00,04,11,12}`、`spec/README.md`、`manifests/spec-readonly.lock.toml`、`contracts/**`、`tests/**`、`tools/spec/**`、`tools/llvm/gen_asm_list.py`。
- **输出**：重排后的 4 册 + 索引 + 锁 + 引用 + 生成物 + 门控适配。
- **约束**：**不改任何指令语义/编码**；不新增/删除指令；不 commit/push；临时目录 `/tmp/opencode/SPEC-167t/`。

## 风险与纪律

- 册重命名牵动 `manifests`、`README`、门控册名映射，**先全局 `grep` 出所有引用点**再动手。
- 搬迁语义段前后必须**逐字比对**（`diff`），禁借机改写。
- 若发现 `SimRISC-00` 已有等价异常规则 ⇒ 合并去重，不重复写。

## 完成区
（执行后填写，≤30 行）

## 审阅记录
