# m15-spec-005: IDL 块在 spec 内的布局改造（节末集中 + 三级标题）

**模块**：spec
**项目里程碑**：M15
**依赖**：`m15-idl-001`…`m15-idl-012` 全部合入（否则每册重渲染两遍）；`m15-spec-001`（`idl/render.py` 已就绪）
**可并行分片**：否（一次改 `render.py` + 12 册，串行）
**预估**：4–6 h
**档位**：中改
**状态**：待验收

## 目标

当前 IDL 块（`idl/render.py` 生成的 ```idl``` 段）**内联插在散文段落之间、无标题、无导语、块首 `# id:` 与上下文重复**，读起来生硬。按用户 2026-11-19 裁定（`discussing.md` N26）改为：

1. **每册每个 `##` 节末尾集中**该节全部 operation，配**一个三级标题** `### N.M 形式化语义（IDL）`（标题数 = 该册含 IDL 块的 `##` 节数，现场为 2–5 个；**不是逐指令一个**）；
2. 块前一句生成导语：「本节各指令的形式化语义由 `idl/SimRISC-0X.idl` 生成，逐条如下：」；
3. 块内去掉与上下文重复的 `# id:` 行，改用一行粗体标注 `**`<id>`**`；
4. 保留 `<!-- IDL:<id> BEGIN/END -->` 标记（`render.py --check` 与 `check-idl-sync` 依赖）；
5. **不新增附录**（`check-spec-numbering` 断言 6/7 限定 `SimRISC-01`–`12` 尾段只能是附录 A、B）。

## 硬约束

1. **散文一字不动**：只允许 `render.py` 写标记块与上述导语/标题；散文段落原样保留（"散文零改动" 判据改为「剥掉标记块 + 生成标题/导语后与基线逐字节相同」）。
2. **不升级版本号**；变更记录在 `SimRISC-00` 的 `0.5.7-rc` 段追加条目。
3. **不逐条加标题**：`SimRISC-07` 有 50 条指令，逐条标题会让目录失控。
4. 术语一律「寄存器组」。

## 交付

1. `idl/render.py`：支持新布局（节末聚合 + 三级标题 + 导语 + 去 `# id:`）；`--check` 仍逐字节校验；
2. 12 册 `spec/SimRISC-0X-*.md` 全部重渲染；
3. `spec/.manifests.toml` 的 12 册 sha256 同笔重算；
4. `SimRISC-00` 变更记录追加条目。

## 验收（逐条贴真实 rc）

1. `python3 idl/render.py --check` rc=0（12 册全部逐字节一致）；
2. `make check-idl-sync`、`check-manifests-guard`、`check-spec-numbering`、`check-spec-changelog`、`check-spec-purity`、`check-spec-codeblocks`、`check-spec-drift`、`check-spec-refs`、`check-asm-list`、`check-asm-prose`、`check-legality-drift` 全 rc=0；
3. **散文零改动**：每册剥掉「标记块 + 生成标题 + 导语」后与改造前逐字节相同（逐册给哈希）；
4. 标题数与节数现场统计相等（逐册打印 `节数 / 新标题数`），且无 `#####`；
5. **可达 FAIL ≥2 路**：① 某册手改生成标题 ⇒ `--check` 必须红；② 删某册的导语 ⇒ 判据必须红（各 `cp`+md5 还原）。

## 批次

- 批 1：`render.py` 改造 + 先在 `SimRISC-03`（8 条，最小）上验证 + 全套门控；
- 批 2：其余 11 册重渲染 + 门控 + 散文哈希逐册核对。

## 待裁定

（无。布局方案已由用户 2026-11-19 裁定为 A：节末集中 + 三级标题；时机为用户选「等 12 册全部合入后」。）

## 完成区

**测试结果**：一键证据脚本 23 项全 PASS（rc=0）：`render.py --check` rc=0（263 条 operation / 12 册逐字节一致）、`--self-test` rc=0（11 类注入各自 FAIL、基线/还原 PASS）、11 个门控 rc=0、散文哈希 12 册逐册与基线相同、逐册标题数=有块节数且无 `#####`；注入 ①（手改生成标题）②（删导语）③（改散文）均须红且 `cp`+md5 还原后回绿，三条全部实测红、还原回绿。
**修改文件**：`idl/render.py`；`spec/SimRISC-00-指令系统设计.md`（变更记录一条）、`spec/SimRISC-01`…`SimRISC-12`（12 册重渲染）；`spec/.manifests.toml`（13 册 sha256）；本任务书。
**验收结果**：
- `python3 idl/render.py --check` rc=0：「PASS（源 operation=263 条 / 落点 12 册 / 标记块 263 个，逐字节一致）」。
- 门控全 rc=0：`check-idl-sync`、`check-manifests-guard`、`check-spec-numbering`（h5+=0、wrapper=0）、`check-spec-changelog`、`check-spec-purity`、`check-spec-codeblocks`、`check-spec-drift`、`check-spec-refs`、`check-asm-list`、`check-asm-prose`、`check-legality-drift`。
- 逐册「节数 / 新标题数」：01 4/4、02 3/3、03 3/3、04 2/2、05 4/4、06 4/4、07 5/5、08 2/2、09 2/2、10 2/2、11 4/4、12 3/3；`#####` 全 0。
- 散文哈希：12 册剥「块 + 生成标题 + 导语」后与基线逐册相同（`--prose-hash` 逐条 diff 为空；逐册哈希见运行期证据）。
- 块内 `# id:` 已全部消失（`grep '^# id:' spec/` 命中 0），粗体 id 行数 = 块数（07 另有 1 条原有散文粗体）。
- 二次渲染幂等（`write` 更新 0 册）。
**新发现/坑**：
1. 任务书写「标题数 = 每册 3–4 个」，实际有块节数为 2–5（04/08/09/10 为 2、**07 为 5**、11 为 4）；按验收判据「标题数 = 有块节数（现场统计）」执行，未按 3–4 硬凑。
2. `python3 -m py_compile` 会生成 `idl/__pycache__`，`check-manifests-guard` 因 `idl` 的 `subdirs` 只有 `lib` 判红（rc=2）；验证后须删该目录。
3. 「散文零改动」剥除函数（`render.py --prose-hash`）先删块/标题/导语、再把连续空行归一：块从散文中间移出必然留下空行堆积，直接逐字节比会假红；文字行本身逐行相同。
4. 节末插入点必须让位 `<!-- ASSEMBLY_LIST_START -->` / `<!-- LEGALITY_START -->`（在其之前插入），否则块会落进 `check-asm-list` 重生成的区域。
**遗留问题**：无。批 1 的 `SimRISC-03` 先在临时树验证（`--check`、散文哈希、节号连续性），再与其余 11 册在批 2 一次性落盘——中间态其余 11 册仍是旧布局，仓库级 `--check` 不可能全绿，故批 1 不落盘。
补充（失败命令留痕）：`make check` 在 `check-isa-coverage` 处 rc=2——缺 `llvm-mc`（需 `make install-host`），与本次改动无关（该门控读 `.td` 补丁与 `opcodes.yaml`）；此前 63 项检查全 PASS。任务验收清单的 11 个门控均单独跑过、全 rc=0。

- **散文比对基线（固定）**：`09ed2bbf`（本任务 WIP 之前）。证据脚本的 `BASE_REF` 已改为**必填**（缺省取 `HEAD` 会退化为同源自比、恒真绿，属 `Process-07 §5b` 第七例）。

## 审阅记录

### 第 1 轮 engineer 自审

**判决**：通过（无未修 finding）。自主逐行审查范围：`idl/render.py` 新增/改写的 8 个函数与自检、12 册渲染结果抽样（04/07/01/03 的节末区与附录边界）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 生成标题的节号与所在节不一致时，块会被静默搬回错误节 | ✅已修 | `generated_regions` 增加「标题节号 == 所在 `## N.`」断言；self-test 增 `region-section-mismatch` 注入 | self-test 第 5/11 项 rc=1 期望非零 ⇒ PASS |
| `drop_line` 定义后未使用（死代码） | ✅已修 | 删除该函数 | `grep 'def drop_line' idl/render.py` 无命中 |
| self-test 取首条正文行用 `+4` 魔数，绑定旧布局 | ✅已修 | 改为逐行跳过 BEGIN/注释/粗体/围栏 | `--self-test` 11/11 PASS |
| `--prose-hash` 局部 `import hashlib` | ✅已修 | 移到模块头 | `--check` / `--self-test` rc=0 |
| 未做「标题数=节数」的自动断言（只靠外部统计） | ⏸延后 | — | 由 `check-spec-numbering` + 证据脚本现场统计覆盖（非本脚本职责） |

### 第 1 轮 reviewer 验收

**判决：Accepted**（3 条 finding 交 architect 收尾改，不返工）。基线＝固定 commit `09ed2bbf`（非 `HEAD`/merge-base）；下列命令均由 reviewer 在任务工作树内亲自执行，rc 为实测值。

**重跑记录**
- `python3 idl/render.py --check` 三次（开审/中段/收尾）：均 rc=0「PASS（源 operation=263 条 / 落点 12 册 / 标记块 263 个，逐字节一致）」。
- `python3 idl/render.py --self-test`：rc=0，`[self-test 1/11]…[11/11] restored rc=0 ⇒ PASS` 共 11 条 PASS。
- 11 门控逐条 `make -s <t>; echo $?`：`check-idl-sync`=0、`check-manifests-guard`=0（sha256 22 全符）、`check-spec-numbering`=0（h5+=0、wrapper=0）、`check-spec-changelog`=0（header_versions=['0.5.7-rc']）、`check-spec-purity`=0（hits=0）、`check-spec-codeblocks`=0（519 行）、`check-spec-drift`=0（11 合约 0 错）、`check-spec-refs`=0（1332 引用 0 失败）、`check-asm-list`=0（12 册）、`check-asm-prose`=0（0 violations）、`check-legality-drift`=0（12 章）。
- 运行期证据目录内的 `run.sh`（显式传基线）：`RUNSH_RC=0`，23 项全 PASS（含其 3 路注入红→`cp`+md5 还原→回绿）。
- **散文零改动（reviewer 自写剥除器，不采信 `--prose-hash`）**：剥「IDL 块＋生成标题＋导语」后与基线比——12 册非空行序列逐字节相同、空行折叠后全文相同、块数两侧相等 ⇒ 12/12 PASS，rc=0（如 07 非空行 349 行、块 50==50；01 156 行、38==38）。
- **布局（reviewer 自写结构扫描 12 册全量 ＋ 目视 03/07/12/04 节末与附录边界）**：每册每节恰 1 个 `### N.M 形式化语义（IDL）` 且节号＝所在 `## N.`；导语紧贴首块；末块到下一边界无散文；263 块各含 1 行 ``**`<id>`**``；块内 `# id:`=0；`<!-- IDL:… BEGIN/END -->` 263 对；`#####`=0；导语均指向本册 idl ⇒ 全 PASS rc=0。
- **可达 FAIL（reviewer 独立 2 路，`cp`+md5 还原）**：① 改 05 册生成标题 → `--check` rc=1，还原 md5 复原 → rc=0；② 给 12 册加一行散文 → `--prose-hash` 由 `e34994c7…` 变 `1a096b46…`、自写判据 FAIL，还原后哈希回同 → rc=0。
- **manifest 同笔**：`spec/.manifests.toml` 22 条 sha256 现算全对（含 13 册 SimRISC），mismatch=0，rc=0。
- **范围**：`git show --name-only HEAD` 恰 16 文件（`idl/render.py`＋12 册＋`spec/.manifests.toml`＋`SimRISC-00`＋本任务书），未动 `spec/`、`idl/` 之外；`SimRISC-00` 仅 +1 条 `0.5.7-rc` 变更记录、无版本号变更（01–12 册头与基线逐字节同）；注入前后工作区快照 md5 16/16 相同（写本记录前复核；写入本记录后除本任务书外 15/16 仍相同）、`git status -uall` 干净、无 `idl/__pycache__`。
- 补充：`command -v llvm-mc` rc=1（不在 PATH），与完成区所述 `make check` 在 `check-isa-coverage` rc=2 的环境成因一致（非本任务改动）。
- 采信范围：无——判决全部基于本次亲自重跑；engineer 完成区自述仅作对照（对照中已发现下述 finding 2 的数字笔误）。

**约束核验**：①散文一字不动 ✅；②不升版本号 ✅；③不逐条加标题（每节 1 个）✅；④术语「寄存器组」✅（本次变更内「银行」0 处）。

**Finding（不阻断，交 architect 收尾）**
1. 任务书「标题数＝每册 3–4」系数字写错：现场 2–5（04/08/09/10＝2、07＝5）；判据以「标题数＝有块节数（现场统计）」为准，实现正确，**不得为凑 3–4 合并/拆分节**。
2. 完成区「新发现 #1」写「07/11 为 5」有误：11 的有块节数＝4（11 有 5 个 `##` 节、§1 指令域与执行条件无 IDL 块），与同表「11 4/4」自相矛盾；仅 07 为 5——数字笔误，改完成区即可。
3. 证据 `run.sh` 的 `BASE_REF` 缺省取 `HEAD`、注释理由（「本任务不改 git 历史」）不成立（`HEAD` 即本次 WIP），按缺省跑会把「与基线比对」退化为同源自比；本次已显式传基线重跑得 23 PASS。建议改为必填并把基线 commit 写入完成区。

