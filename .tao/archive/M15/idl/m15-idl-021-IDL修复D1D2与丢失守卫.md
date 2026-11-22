# m15-idl-021: IDL 修复批（D1 `rb0` 写宽 + D2 8 条 rf 对齐守卫 + 补丢失守卫 + 注释订正）

**模块**：idl
**项目里程碑**：M15
**依赖**：无（`m15-idl-020` 盘点已给依据；`spec-006` 的册名不影响本任务）
**可并行分片**：否（改 `.idl` 源 → 重渲染 spec）
**预估**：3–4 h
**档位**：中改
**状态**：已验证

## 背景（`m15-idl-020 IDL 差异盘点` 的 D1/D2 + N31 的丢失守卫）

1. **D1（P1）`jump`/`br.*` 的 `rb0` 写回宽度**：IDL 的 `jump()` 只写 `target[47:0]`；而 `spec/SimRISC-06 §1/§2`、`ADR-0012 D8.3/D8.4`（「`rb0[63:48]` 恒为 0」已**作废**）、三执行机（QEMU `tcg_gen_st_i64`、gem5 `branchTo(uint64_t)`+b5.hh「over all 64 bits」、RTL `jumpTarget=(…)(63,0)`）都**写完整 64 位、取低 48 位去取指**。
2. **D2（P1）8 条 rf 访存缺对齐守卫**：`ld.t_rrii_rf`/`st.t_rrii_rf`/`ld.o_rrii_rf`/`st.o_rrii_rf`/`ldm.t_rrri_rf`/`stm.t_rrri_rf`/`ldm.o_rrri_rf`/`stm.o_rrri_rf` —— `SimRISC-01 §4` 正文（`.t`=4 / `.o`=8 字节）+ 附录 B `excp_malign` **32 条含这 8 条** + `contracts/opcodes.yaml` 的 `aligned(4/8)`/`rule_refs:[excp_malign]` **三方一致**。
3. **丢失守卫（N31）**：`m15-idl-001` 的 8 条 rf 守卫曾实现（证据 md5 `828191b0…`）但**未提交即丢失**，合入版（`0c5df887…`）无守卫；本次一并补做。
4. **过期注释**：8 条 rf 的「本册附录 B 的 `excp_malign` 未列本族 ⇒ 不判 MALIGN」前提已被 `af7ffb09` 推翻，且注释里的「§4 正文与附录 B 不一致，两处待统一」也不再成立。

## 要做

1. **D1**：改 `idl/SimRISC-06.idl` 的 `jump()`/分支写回——`rb[0]` 写**完整 64 位**（`target` 为 `Bits<64>`），取指侧取低 48 位（由 `ip()` 的语义或调用点体现，按 spec 措辞）；
2. **D2**：8 条 rf 各加对齐守卫（`.t` 族 `is_naturally_aligned(32, ea)`、`.o` 族 `is_naturally_aligned(64, ea)` ⇒ `raise(Malign)`），**顺序按 `m15-idl-001` R1 裁定「静态先」**；
3. **订正过期注释**（8 条 rf 块头）：删「附录 B 未列本族 ⇒ 不判 MALIGN」与「两处待统一」，改为指向 §4 + 附录 B + 合同一致；
4. **重渲染**：`python3 idl/render.py` 更新 12 册 spec 块；`spec/.manifests.toml` 相应 sha256 同笔重算；
5. **顺带清 `spec-006` 遗留**（若 `spec-006` 已合入）：
   - `.idl` 注释里 **9 处 `idl/README §N`** 改成新册 `spec/IDL-ISA语义描述语言与语义库.md` 的 §N；
   - 新册 §4.7 的 **3 处 `m15-idl-016/017`** 任务号去掉（改为「实现见 `discussion.md` N30」或直接删）。

## 验收（逐条贴真实 rc）

1. `python3 idl/render.py --check` rc=0（263 条 / 12 册逐字节一致）；
2. `check-idl-sync`、`check-manifests-guard`、`check-fp-contract`、`check-legality-drift`、`check-spec-*`、`check-knowledge-refs` 全 rc=0；
3. **D1 行为**：`jump` 的 `rb[0]` 为 64 位（`Bits<64>`），与三执行机一致；用 `compile_expression` 核 `rb[0]` 的 `type.width == 64`；
4. **D2 行为**：8 条 rf 的 `Malign` 守卫在位且顺序在静态判定之后（用 `check_semantics.py` 或等价核）；
5. **可达 FAIL ≥2 路**：① 去掉 `ld.t_rrii_rf` 的对齐守卫 ⇒ 对应用例/断言红；② 把 `jump()` 改回只写 `[47:0]` ⇒ 宽度断言红（`cp`+md5 还原）；
6. 散文零改动（基线固定 commit，剥块后逐字节比对）。

## 完成区

**测试结果**：通过 19/19（14 个门控 + 5 个自建检查）；4/4 注入「注入⇒FAIL⇒还原⇒回绿」；失败原因：无。
**修改文件**：
- `idl/SimRISC-01.idl`（8 条 rf 补对齐守卫 + 块头注释订正）
- `idl/SimRISC-03.idl`、`idl/SimRISC-05.idl`、`idl/SimRISC-06.idl`（`idl/README §N`→「语言规范 §N」；D1 写回口径）
- `idl/README.md`（加 `diff-vs-udb.md` 索引行）
- `spec/IDL-ISA语义描述语言与语义库.md`（§4.3 `jump`/`ip` 模型；§4.7 去 3 处任务号；附录记 D1）
- `spec/SimRISC-01/03/05/06-*.md`（重渲染 4 册）
- `spec/.manifests.toml`（5 份 sha256 重算）

**验收结果**（运行期证据目录内 `run.sh`，真实 rc）：
1. `python3 idl/render.py --check` rc=0（263 条 / 12 册）；`check-idl-sync`、`check-manifests-guard`、`check-fp-contract`、`check-legality-drift`、`check-spec-*`（含 archive/verify 共 8 个）、`check-knowledge-refs` 全 rc=0。
2. D1：`compile_expression` 求 `rb[6'd0]` 宽 **64**、RHS `target` 宽 **64**（idlc 0.1.8）。
3. D2：8 条 rf 的 `Malign` 守卫在位；宽度由 `contracts/opcodes.yaml` 的 `aligned(4/8)` 现场派生（32/64 位）；顺序 `Illegal`（静态）< guard < 访存。
4. 可达 FAIL 4 路全绿：① 去掉 `ld.t_rrii_rf` 守卫 ⇒ D2 rc=1；② `jump` 改回 `target[47:0]` ⇒ RHS 宽 48 rc=1；③ 改 `.idl` 不重渲染 ⇒ render rc=1；④ 改散文 ⇒ prose rc=1（均 `cp`+md5 还原）。
5. 散文零改动：12 册剥块后与基线 `7282b64d` 逐字节相等（另 SimRISC-00 同）。

**新发现/坑**：
- `jump`/`ip` 在迁册后位于 `spec/IDL-ISA语义描述语言与语义库.md §4.3`（不在 `.idl`）；D1 须改该册并同笔重算 `spec/.manifests.toml` 的 sha256。
- `check-spec-archive-verify` 在任务工作树内需要 `.cache/refs/DADAO.wiki`，本次以只读软链复用主工作树 `.cache`（gitignore，不计改动）。
- 附带试跑 `check-isa-coverage`/`check-width-sizes` 因任务工作树无 `install-host` 工具链 rc=2，非本任务改动面。

**遗留问题**：新册附录 0.1.0 历史条目仍保留旧口径「高 16 位恒 0 / 只写 `target[47:0]`」（历史记录不改写）；版本号未升级（待用户认可）。

## 审阅记录

### 第 1 轮 engineer 自审

- 依据核对：`m15-idl-020` 的 D1/D2、`contracts/opcodes.yaml` 的 `aligned(4/8)`、附录 B `excp_malign`（32 条含全部 8 条 rf）。
- 实现核对：`jump` body 改 `rb[6'd0] = target;`、`ip()` 描述去「恒 0」；15 条控制流与 `aip.si` 注释同步；8 条 rf 守卫在静态判定后、访存前；注释统一为「§4 正文 + 附录 B + 编码表」三方一致。
- 防造假：所有断言均可在注入后 FAIL（4 路已实测），散文比对锚定基线 commit。
- 判决：无未修 finding。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| idlc 不校验赋值位宽（静默通过） | ✅已修 | D1 用 `compile_expression` 分别求 LHS/RHS 宽度 | 注入 `target[47:0]` ⇒ RHS 48，rc=1 |
| `check-spec-purity` 禁 ADR/任务号 | ✅已修 | 附录 D1 条目去 ADR 指针；§4.7 去 3 处任务号 | purity rc=0 |
| 残留旧注释口径 | ✅已修 | `SimRISC-05/06` 注释同步 | comments 检查 rc=0 |

### 第 1 轮 reviewer 验收（2026-11-20，中改）

**重跑记录**（命令均在仓库根、相对路径；证据脚本 = 运行期证据目录内 `run.sh`）：
- 证据脚本 **rc=0，ALL PASS（fail=0）**，19/19（render/d1/d2/comments/prose + 14 门控），4 路注入 `inj=1/back=0/md5=ok`。**首跑 rc=1**：`check-manifests-guard` 报「`idl` 多出子目录 `__pycache__`」——根因是审查者散文核验时 `import render` 生成的 `.pyc`（gitignore、非交付物）；删后复跑 PASS、再 import 即复现 FAIL，因果确证，**非交付物缺陷**（记重试 1 次）。
- **独立注入①**：删 `ld.t_rrii_rf` 守卫（md5 `135192e2→1e7cb348`，非空）⇒ 同一脚本 **rc=1**：`d2-rf-alignment FAIL rc=1`、`render-check FAIL rc=1`、`check-idl-sync rc=2`；`cp` 还原 md5 相等。
- **独立注入②**：`rb[6'd0] = target;` → `target[47:0]`（md5 `507ace96→d3a15f92`）⇒ **rc=1**：`d1-jump-width FAIL rc=1`、`RHS target[47:0] width=48（期望 64）`；`cp` 还原 md5 相等。
- **回绿复跑 rc=0 ALL PASS**；验收前后 `git status --porcelain -uall` 均空，12 文件 md5 与注入前逐个相等。

**判据核验**：
1. **D1 ✓**：§4.3 `jump` body = `rb[6'd0] = target;`；描述「完整 64 位写回、取指取低 48 位」；`ip()` 已无「高 16 位恒 0」。审查者**自写**脚本经 `compile_expression` 求解：`LHS rb[6'd0] width=64`、`RHS target width=64`（idlc 0.1.8，rc=0）。ADR-0012 **状态 = Accepted**，D8.4 明载「`rb0[63:48]` 恒为 0」**作废**、D8.3 为 64 位写回 + 取指取低 48 位。
2. **D2 ✓**：8 条 rf 守卫在位；宽度由 `contracts/opcodes.yaml` 现场派生（`.t`=32 / `.o`=64）对 `aligned(4/8)` 全符；顺序 4 条 rrri 均 `STATIC > STATIC > GUARD > MAL > ACCESS`、4 条 rrii 无静态判定 `GUARD > MAL > ACCESS`，合 `m15-idl-001` R1「静态先」。
3. **散文零改动 ✓**：基线 `7282b64d`（= `merge-base master HEAD`）；23 册剥块比对，`SimRISC-00..12` 全 SAME，仅语言规范册 DIFF（D1/§4.7/附录，属任务范围）。
4. **可达 FAIL ≥2 路 ✓**：上列独立注入①②（均不采信工程师自检）。
5. **重渲染/manifest ✓**：`render.py --check` rc=0；`spec/.manifests.toml` **23 条 sha256 现算全符**（含 5 册改动）。
6. **遗留 ✓**：语言规范册 §4.7 3 处 `m15-idl-016/017` 已去（grep rc=1）；`.idl` 内 `idl/README §` = **0**（9 处改「语言规范 §」，另 `SimRISC-05` 1 处 `README §4.3/T1` 同步）；`idl/README.md` 已加 `diff-vs-udb.md` 索引行。
7. **门控 ✓**（审查者独立重跑，非采信）：`render.py --check`、`check-idl-sync`、`check-manifests-guard`、`check-fp-contract`、`check-legality-drift`、`check-spec-{numbering,purity,codeblocks,drift,refs,changelog}`、`check-knowledge-refs` **全 rc=0**。
8. **范围 ✓**：`git show --name-only HEAD` 恰 12 文件，与完成区「修改文件」声明一致。

**备注（不阻断）**：证据脚本的 d2/prose 检查打印派生计数但不设期望值（上游删条目会跟着少判，由 `check-legality-drift` 等兜底）；`BASE` 取 `merge-base master HEAD`（当前即 `7282b64d`）。

**判决：Accepted**。审查未改任何代码（注入全 `cp`+md5 还原、快照对账一致）。
