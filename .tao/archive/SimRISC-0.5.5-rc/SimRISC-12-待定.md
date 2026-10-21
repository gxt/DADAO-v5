# SimRISC待定指令

> **版本：0.5.5-rc**（与 SimRISC-00 一致）
> **分类：待定 [deferred]**（2 条）— cfxld/cfxst

<!-- ASSEMBLY_LIST_START -->
## 1. 汇编指令速查

### 1.1 待定（2 条）｜ **deferred** — 暂不归类，待必须启用时

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `cfxld` | `crii` | `cfx` | `cfxld cfxHA, [rbHB, immu12]` | `cfxld_crii_cfx` |
| `cfxst` | `crii` | `cfx` | `cfxst cfxHA, [rbHB, immu12]` | `cfxst_crii_cfx` |

<!-- ASSEMBLY_LIST_END -->

<!-- LEGALITY_START -->
## 2. 合法性检查


**scope: excluded（decode ILLI）：**
* `cfxld_crii_cfx`：decode ILLI
* `cfxst_crii_cfx`：decode ILLI
<!-- LEGALITY_END -->


## 3. SRAM块传输指令

这类指令用于核芯功能扩展的内部存储与内存之间的块传输，要求 64 字节对齐，并且是 64 字节的倍数。

操作数类型为：`crii`

```simrisc
cfxld    cfxHA, [rbHB, immu12]
cfxst    cfxHA, [rbHB, immu12]
```

其中：
- cfx_<cfxname> 指定核芯功能扩展名称。
- rbHB 指定内存地址，要求 64 字节对齐。
- 传输长度 = immu12 × 64 字节。
- 内部存储侧的目标块由 `cfx_⟨cfxname⟩_sram_block_sel`（cg7 rc0）选择，块内起始偏移由 `cfx_⟨cfxname⟩_sram_addr`（cg7 rc1）指定。`cfx_⟨cfxname⟩_sram_addr` 及内存侧 `rbHB` 均需 64 字节对齐。
- cfxld：将内存数据传输到核芯功能扩展的内部存储中。
- cfxst：将核芯功能扩展的内部存储数据传输到内存中。
- 若 cfx_<cfxname> 为 reserved 核芯功能扩展（7-14、19-61），触发 ILLI 异常。

---

## 附录：版本与变更记录

> **发布动作**：把顶部 `-rc` 段去 `-rc` 并补发布日期，再于其上方新开空 `-rc` 段。

### 0.5.5-rc（未发布）

- 标题章节号统一为 `N` / `N.M` / `N.M.K`。
- `fence` 编码改 `100-000`（`ha=0x20`），`immu18` 按 `fm[17:12]`/`pred[11:6]`/`succ[5:0]` 解释，新增 `PRED_*`/`SUCC_*` 常量与 `|` 组合写法。
- LR-SC 改名并重排编码：`<lr|sc>.<b|w|t|o>.<nn|an|nr|ar>` 共 24 条；删除 `lr.*.nr` 与 `sc.*.an`；语义不变、仍 `scope: excluded`。
- 引入 `scope: excluded`（`cfxld`/`cfxst`/`fence`/`lr_*`/`sc_*`）。
- 新增「合法性检查」章（生成区）。
- 全量删除 `rela.si`；0 号寄存器作源操作数语义澄清。
- LR-SC 对齐口径订正：地址**按数据宽度自然对齐**（`.b`=1 / `.w`=2 / `.t`=4 / `.o`=8 字节），不满足 ⇒ MALIGN（原「即 8 字节对齐」措辞废止）。
- cfx 系列记法约定；cfx 字段重命名。
- 新增「汇编指令速查」章（生成区）。
- 「原子指令」章（`fence` / `lr`·`sc`）迁至 `SimRISC-11`；本册仅余 SRAM 块传输（`cfxld`/`cfxst`），deferred 记 27 → 2；原 §4 重编为 §3。

### 0.5.4（2026-09-28）

- 本册由原《SimRISC 系统类指令》的原子指令部分拆出，独立成「待定」分册（`fence` / LR-SC / `cfxld`/`cfxst` / SRAM 块传输）。

### 0.5.2（2026-07-18）

- 修复 `lr`/`sc` 描述不一致；`fence` 编码整理。

### 0.4.1（2026-07-14）

- 初版：同步上游原子指令（`fence` / LR-SC）。
