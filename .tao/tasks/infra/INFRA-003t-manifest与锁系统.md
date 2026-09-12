# INFRA-003t: manifest 系统 + 组件锁 + 参考锁

**模块**：infra
**项目里程碑**：M1
**依赖**：`INFRA-002t`
**状态**：已验证

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：DADAO-v5 现有 `README.md`（规范版本表）；DADAO 参考仓库 `https://github.com/gxt/DADAO.git`（head `f9bde048…`，见交付物）
- 输出：`manifests/components.lock.toml`、`manifests/references.lock.toml`、`scripts/manifest_check.py`
- 约束：组件锁只需占位/待定 commit（LLVM/QEMU/gem5 的精确 commit 在后续 llvm/qemu/gem5 模块确定）；reference 锁 DADAO-0628 `2d270604b778d609e1a09b4047271b5309005ffc`；不得复制 0.4.1 的补丁/代码正文

## 背景（完整）

### 目标

提供机器可读、可校验的锁系统：component 锁（上游可构建组件按精确 commit + 补丁序列）与 reference 锁（只读参考仓库按精确 commit），并由 `manifest_check.py` 做结构校验，作为 `make check` 的一部分。

### 设计理由

- ADR-0002：每个组件按完整 commit 获取；tag/branch 不作为可复现基线；环境相关 Git URL 重写、仅按可变分支选版本、未审查的 `fixups` 层均被拒绝。
- 0628 `components.lock.toml` 头注释明确：component 在 ADR 记录上游选择与精确 commit 之前保持 disabled；tag/branch 不被接受为可复现基线。
- reference 采用 `policy = "reference-only"`：只复用规范文本 / 架构与教训，不复制实现。

### 关键概念 / 数据

- `components.lock.toml` schema（0628）：`format = 1`、`work_root = ".work"`，`[[component]]` 数组，字段 `name` / `enabled` / `repository` / `commit` / `patch_series` / `role`。
- `references.toml` schema（0628）：`format`、`captured_on`、`policy`，`[[reference]]` 数组，字段 `id` / `path` / `repository` / `head` / `dirty` / `purpose` / `reuse` / `selected_paths`。
- `manifest_check.py` 校验规则（0628）：
  - spec lock（0628 有、v5 无）：`commit` 为 40 位 SHA-1；`status` ∈ {candidate, frozen}；`foundation_included` 非空。
  - component：`name` 非空且不重复；**enabled 组件必须有完整 40 位 commit**；`patch_series` 文件必须存在。
  - reference：`id` 非空；`head` 为完整 commit；`path` 为绝对路径。
  - 全部通过后打印 spec / enabled components / reference 数量，退出码 0。

### 上游引用

- DADAO-0628 `manifests/components.lock.toml`：component 列表与 schema（含 llvm / qemu / gem5 / llvm-test-suite / embench / musl / linux 的 repository 与 commit；本任务只转述机制，不复制其 commit 作为 v5 基线）。
- DADAO-0628 `manifests/references.toml`：reference 列表与 schema（wiki-candidate、legacy-meta、legacy-llvm、legacy-linux、legacy-musl、llvm-test-suite；`policy = "reference-only"`；`reuse` 字段声明"只取架构/教训/接口，不复制实现"）。
- DADAO-0628 `manifests/spec.lock.toml`：spec 锁的字段布局（`status = "frozen"`、`foundation_included` / `foundation_excluded`）。
- DADAO-0628 `scripts/manifest_check.py`：上述校验逻辑。
- DADAO-0628 `docs/adr/0002-build-orchestration.md`：commit 锁定与 `.work/` 约定。

## 交付物

- `manifests/components.lock.toml`：
  - `format = 1`、`work_root = ".work"`。
  - `[[component]]`：`llvm`（repository `https://github.com/llvm/llvm-project.git`，role "LLVM MC + CodeGen"）、`qemu`（`https://github.com/qemu/qemu.git`，role "CPU core / decode / scalar execution / bare-metal machine"）、`gem5`（`https://github.com/gem5/gem5.git`，role "functional second reference"）。
  - **commit 待定**：三组件 `enabled = false`、`commit = ""`，注释说明待 llvm/qemu/gem5 模块的 ADR 记录上游选择与精确 commit 后再改为 `enabled = true` 并填入完整 40 位 commit。
  - `patch_series` 指向 `components/<name>/patches/series`。
- `manifests/references.lock.toml`：
  - `format = 1`、`policy = "reference-only"`。
  - `[[reference]]` id `dadao-0628`：repository `https://github.com/holight1/DADAO-0628.git`、`head = "2d270604b778d609e1a09b4047271b5309005ffc"`、`path` 指向 `.work/DADAO-0628`、`reuse = "架构与工程教训，不复制实现"`。
  - `[[reference]]` id `dadao`：repository `https://github.com/gxt/DADAO.git`、`head = "f9bde0481668ffab325db8d8c5d8c4cc791c6232"`、`path` 指向 `.work/DADAO`；其 checkout 由 `INFRA-004t` 的 `fetch_refs.py` 获取。
  - DADAO 与 DADAO-0628 是两套互不相关的仓库（均已不再更新）；DADAO-0628 直接使用已有 `.work/DADAO-0628` clone，`fetch_refs.py` 只做 commit 检查、不重新拉取。
  - `path` 字段按 v5 实际位置填写（`.work/DADAO-0628` 等）。v5 简化 schema，省略 0628 的 `dirty`（执行时计算）、`purpose`（并入 `reuse`）、`selected_paths`（本阶段不需要）字段。
- `scripts/manifest_check.py`：实现 component/reference 锁校验；**v5 无 spec lock 文件**（规范版本表在 `README.md`，脚本不校验 spec 锁），并对 disabled 组件的待定 commit 放行。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- 无 ISA 相关差异（基础设施，与 ISA 版本无关）。
- spec lock：v5 **不使用 spec lock 文件**（规范版本表在 `README.md`）；`manifest_check.py` 只校验 component/reference 锁，不校验 spec 锁。
- 文件名：reference 锁用 `references.lock.toml`（0628 为 `references.toml`）。
- 组件范围：v5 本阶段只锁 llvm / qemu / gem5 三个核心组件（musl / linux / embench / llvm-test-suite 属后续阶段）；commit 全部待定。
- 参考锁：v5 显式锁定 DADAO-0628（`2d270604`）与 DADAO（`f9bde048`），而非 0628 的 wiki-candidate / legacy-* 列表。

## 已知坑 / 结论

- enabled 组件必须有完整 40 位 commit；占位期应保持 `enabled = false`，否则校验失败。
- tag/branch 不作为可复现基线。
- 0628 的 `manifest_check.py` 要求 reference `path` 为绝对路径；v5 若改用项目内相对路径（`.work/DADAO-0628`），需相应调整校验规则并在任务中说明。
- 0628 references 的 `path` 指向其原作者的本地绝对路径，v5 必须改指向本项目内的真实位置（`.work/DADAO-0628` 等），否则 `make status` 会显示 `missing`。

## 参考

- DADAO-0628：`.work/DADAO-0628/manifests/components.lock.toml`
- DADAO-0628：`.work/DADAO-0628/manifests/references.toml`
- DADAO-0628：`.work/DADAO-0628/manifests/spec.lock.toml`
- DADAO-0628：`.work/DADAO-0628/scripts/manifest_check.py`
- DADAO-0628：`.work/DADAO-0628/docs/adr/0002-build-orchestration.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `manifests/components.lock.toml` 含 llvm/qemu/gem5 三组件，commit 明确标注待定且 `enabled = false`
2. `manifests/references.lock.toml` 锁定 DADAO-0628 `2d270604b778d609e1a09b4047271b5309005ffc`
3. `scripts/manifest_check.py` 对 v5 schema 校验通过（退出码 0），且能检出 enabled 组件缺 commit、patch_series 缺失等错误
4. `python3 scripts/manifest_check.py` 直接调用退出码 0

## 完成区

**测试结果**：通过 4/4（对应「验收标准」1–4）；失败原因：无

**修改文件**：
- `manifests/components.lock.toml`（新建）
- `manifests/references.lock.toml`（新建）
- `scripts/manifest_check.py`（新建，已 `chmod +x`）

**验收结果**：

验收标准 4（真实终端输出，日志 `.tao/logs/INFRA-003t-manifest-check.log`）：

```
$ python3 scripts/manifest_check.py
enabled components: none
references: 2
manifest validation: PASS
exit=0
```

验收标准 1–2（`manifests` 解析结果，日志 `.tao/logs/INFRA-003t-verify.log`）：

```
### components.lock.toml parsed fields
format: 1 work_root: .work
  name=llvm enabled=False commit='' patch_series=components/llvm/patches/series role='LLVM MC + CodeGen'
  name=qemu enabled=False commit='' patch_series=components/qemu/patches/series role='CPU core / decode / scalar execution / bare-metal machine'
  name=gem5 enabled=False commit='' patch_series=components/gem5/patches/series role='functional second reference'
### references.lock.toml parsed fields
format: 1 captured_on: 2026-09-12 policy: reference-only
  id=dadao-0628 head=2d270604b778d609e1a09b4047271b5309005ffc path=.work/DADAO-0628 repository=https://github.com/holight1/DADAO-0628.git reuse='架构与工程教训，不复制实现'
  id=dadao head=f9bde0481668ffab325db8d8c5d8c4cc791c6232 path=.work/DADAO repository=https://github.com/gxt/DADAO.git reuse='各阶段早期实现的架构与工程教训，不复制实现'
```

验收标准 3（错误检出能力，独立临时树 `/tmp/opencode/INFRA-003t-test`，日志 `.tao/logs/INFRA-003t-error-detection.log`）：

```
### baseline (placeholder manifests) -> expect exit 0
enabled components: none
references: 2
manifest validation: PASS
exit=0

### enabled component with empty commit -> expect exit 1
ERROR: component llvm: enabled components require a full commit
ERROR: component llvm: missing patch series /tmp/opencode/INFRA-003t-test/components/llvm/patches/series
exit=1

### enabled component with valid commit but missing series -> expect exit 1
ERROR: component llvm: missing patch series /tmp/opencode/INFRA-003t-test/components/llvm/patches/series
exit=1

### duplicate component name -> expect exit 1
ERROR: components.lock.toml: invalid or duplicate component 'llvm'
exit=1

### reference with short head -> expect exit 1
ERROR: reference dadao-0628: head must be a full commit
exit=1

### reference with absolute path -> expect exit 1
ERROR: reference dadao-0628: path must be a non-empty project-relative path
exit=1
```

（注：错误检出为**顺序**测试，后段会累积前段的注入错误，故日志中同一轮可能出现多条 `ERROR`；各 `exit=1` 与新增错误行对应关系明确。上表为按用例归并后的摘要，完整原始输出见日志。）

`git status --porcelain`（交付物为未跟踪新文件）：

```
?? manifests/components.lock.toml
?? manifests/references.lock.toml
?? scripts/manifest_check.py
```

**验收标准逐条自审**：
1. `components.lock.toml` 含 llvm/qemu/gem5 三组件，`enabled = false`、`commit = ""`，头注释说明待 ADR 记录后改为 `enabled = true` 并填 40 位 commit —— ✅ 通过
2. `references.lock.toml` 锁定 DADAO-0628 `2d270604b778d609e1a09b4047271b5309005ffc`（`tomllib` 解析确认）—— ✅ 通过
3. `manifest_check.py` 对 v5 schema 校验通过（exit 0）；并以临时树注入用例检出 enabled 缺 commit、patch_series 缺失、重名组件、reference 短 head、reference 绝对路径 —— ✅ 通过
4. `python3 scripts/manifest_check.py` 直接调用 exit 0 —— ✅ 通过

**新发现/坑**：
- **任务书内部矛盾**：「与 DADAO-0628 的差异」一节（第 66 行）仍写 v5 有 spec lock schema（`[versions]` / `status == "frozen"`），与同任务书「接口规范」「交付物」「验收标准」及 `README.md`/`MEMORY.md` 矛盾——后者一致声明 v5 不使用 `manifests/spec.lock.toml`（commit `ca0c55f` 已删除该文件）。本任务按后者执行：`manifest_check.py` **不校验 spec 锁**。建议后续修订任务书删除该过时段落。
- **`patch_series` 校验须按 `enabled` 门控**：占位期三组件 `enabled = false`，且 `components/<name>/patches/series` 尚未创建（由 llvm/qemu 后续任务创建）。若照搬 0628 无条件校验 `patch_series` 存在，会令 `python3 scripts/manifest_check.py` 非零退出，违反验收标准 4。故实现为：仅对 enabled 组件要求完整 commit 与 `patch_series` 文件存在；仍满足「能检出 enabled 组件 patch_series 缺失」。
- **reference `path` 规则**：从 0628 的「必须绝对路径」改为「必须非空且项目相对路径」，对齐任务书已知坑（v5 用 `.work/DADAO-0628` 等相对位置）。
- **`manifests/dadao.lock.toml` 已被取代**：其 DADAO head 已迁入 `references.lock.toml`；按用户决策删除该文件，`references.lock.toml` 成为唯一参考锁来源。
- **`captured_on` 字段**：0628 schema 含该字段，v5 省略清单只列 `dirty`/`purpose`/`selected_paths`，故保留并填执行日 `2026-09-12`；`manifest_check.py` 不校验该字段。

**遗留问题**：
- 【已处置】`manifests/dadao.lock.toml` 已删除（DADAO head 由 `references.lock.toml` 单一承载）；`manifest_check.py` 不读取该文件，不受影响。

## 审阅记录

### 第 1 轮 reviewer 验收

**审查者**：reviewer
**审查时间**：2026-09-12
**判决**：**Accepted**

---

#### 1. 重跑记录

**验收标准 4：`python3 scripts/manifest_check.py` 直接调用**
```
$ python3 scripts/manifest_check.py
enabled components: none
references: 2
manifest validation: PASS
exit=0
```
✅ 退出码 0，与完成区一致。

**验收标准 1–2：`tomllib` 精确解析 `components.lock.toml`**
```
format: 1, work_root: .work
  name=llvm  enabled=False  commit=''  patch_series=components/llvm/patches/series  role='LLVM MC + CodeGen'
  name=qemu  enabled=False  commit=''  patch_series=components/qemu/patches/series  role='CPU core / decode / scalar execution / bare-metal machine'
  name=gem5  enabled=False  commit=''  patch_series=components/gem5/patches/series  role='functional second reference'
```
✅ 三组件齐全，全部 `enabled=false`、`commit=""`，值与任务书一致。

**验收标准 1–2：`tomllib` 精确解析 `references.lock.toml`**
```
format: 1, captured_on: 2026-09-12, policy: reference-only
  id=dadao-0628  head=2d270604b778d609e1a09b4047271b5309005ffc  path=.work/DADAO-0628  repository=https://github.com/holight1/DADAO-0628.git
  id=dadao       head=f9bde0481668ffab325db8d8c5d8c4cc791c6232  path=.work/DADAO       repository=https://github.com/gxt/DADAO.git
```
✅ 两个 reference head 精确匹配任务书要求。

**验收标准 3：错误检出能力（独立临时树，8 个用例）**
```
Test 1: baseline (placeholder)              -> exit=0   ✅
Test 2: enabled + empty commit              -> exit=1   ✅  "enabled components require a full commit"
Test 3: enabled + valid commit + no series  -> exit=1   ✅  "missing patch series"
Test 4: enabled + valid commit + series OK  -> exit=0   ✅
Test 5: duplicate component name            -> exit=1   ✅  "invalid or duplicate component"
Test 6: reference short head                -> exit=1   ✅  "head must be a full commit"
Test 7: reference absolute path             -> exit=1   ✅  "path must be a non-empty project-relative path"
Test 8: reference empty id                  -> exit=1   ✅  "reference id is required"
```
✅ 脚本能检出所有设计的错误场景。

**辅助验证**
- `manifests/dadao.lock.toml`：不存在 ✅（已删除）
- `manifests/spec.lock.toml`：不存在 ✅（v5 不使用）
- `scripts/manifest_check.py`：可执行（`-rwxrwxr-x`）✅
- `manifest_check.py` 中无 `spec`/`versions`/`frozen`/`foundation` 相关逻辑 ✅

---

#### 2. 约束核验

| 约束 | 结果 |
|------|------|
| 组件 commit 为占位（`enabled=false`、`commit=""`） | ✅ 守住 |
| 不复制 0.4.1 补丁/代码正文 | ✅ 守住（lock 文件只含路径/URL/commit hash） |
| v5 不使用 spec lock 文件 | ✅ 守住（`spec.lock.toml` 不存在，脚本不校验 spec） |
| reference path 为项目相对路径（非绝对路径） | ✅ 守住（`.work/DADAO-0628`、`.work/DADAO`） |
| `patch_series` 仅对 enabled 组件校验存在性 | ✅ 守住（disabled 组件不触发缺失报错） |

---

#### 3. 修改文件清单核验

| 文件 | 完成区声称 | 仓库实际 |
|------|-----------|---------|
| `manifests/components.lock.toml` | 新建 | ✅ 存在，内容正确 |
| `manifests/references.lock.toml` | 新建 | ✅ 存在，内容正确 |
| `scripts/manifest_check.py` | 新建 | ✅ 存在，已 chmod +x |
| `manifests/dadao.lock.toml` | 用户决策删除 | ✅ 不存在 |

`git status` 中额外的 `M .tao/tasks/infra/INFRA-003t-manifest与锁系统.md` 是主会话对任务书的用户决策调整（删除 dadao.lock.toml 引用 + 修正 spec lock 描述），非工程师交付物，改动合理。

---

#### 4. 与完成区自审结论的差异

无实质差异。完成区自审结论准确，所有 4 条验收标准逐条自审与 reviewer 独立验证一致。

---

#### 5. 最终判决

**Accepted** — 全部 4 条验收标准在 reviewer 独立重跑下通过，全部约束守住，无阻塞缺陷。

### 交叉复核（architect）

**复核者**：architect
**时间**：2026-09-12
**结论**：确认 reviewer 的 **Accepted** 判决；4 条验收标准与全部约束经独立核对满足。

**补充发现（非 INFRA-003t 交付缺陷）**：

- **F1（中，跨模块规划不一致）**：`manifest_check.py` 要求 enabled 组件的 `components/<name>/patches/series` 存在，但 `LLVM-002t`/`QEMU-002t` 翻转 `enabled=true` 时并不创建该文件（首次由 `LLVM-003t`/`QEMU-003t` 创建）。按其任务书字面执行，002t 一完成即会让 `make manifest-check` 报 `missing patch series`。建议后续处置：修订 `LLVM-002t`/`QEMU-002t` 交付物要求创建占位 `series`，或新增 infra 任务预创建。**（已处置：按方案 A 修订 `LLVM-002t`/`QEMU-002t` 的交付物、已知坑与验收标准，要求翻转 `enabled` 时创建占位空 `series`。）**
- **F2（低，流程）**：任务头部状态未推进；主会话收尾置 `已验证`。
- **F3（低，文档）**：完成区「新发现/坑」关于 spec lock 矛盾的一条已随任务书修订而过时。
- **F4（低，残余风险）**：DADAO head `f9bde048…` 未做远端可达性核验（`.work/DADAO` 由 INFRA-004t 获取）；建议 INFRA-004t 验收时校验该 commit 可达。

**统一判决**：**Accepted**（reviewer 与 architect 一致）。
