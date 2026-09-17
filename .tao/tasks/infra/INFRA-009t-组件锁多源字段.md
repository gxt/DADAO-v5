# INFRA-009t: 组件锁多源字段

**模块**：infra
**项目里程碑**：M1
**依赖**：`INFRA-003t`、`INFRA-004t`
**状态**：已验证

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`manifests/components.lock.toml`（`INFRA-003t` 产出，现有 schema）、`tools/infra/manifest_check.py`（`INFRA-003t` 产出）、`tools/infra/fetch.py`（`INFRA-004t` 产出）、ADR-0005（`.tao/knowledge/adr-0005-component-lock-multi-source.md`，D1/D2 决策）
- 输出：更新后的 `manifests/components.lock.toml`（llvm 条目新增 `[[component.source]]`）、更新后的 `tools/infra/manifest_check.py`（新增 source 校验）、更新后的 `tools/infra/fetch.py`（实现多源选源规则）
- 约束：`repository` 字段语义不变（= 规范上游身份，必填）；`source` 为有序数组，每项 `name`+`url`；不改动 qemu/gem5 的 `commit`/`enabled`；`make manifest-check` 必须 PASS；失败即停，不自动换源/不重试

## 背景（完整）

### 目标

为组件锁引入多源支持：在 `components.lock.toml` 中新增 `[[component.source]]` 有序数组，使 `fetch.py` 能从多个镜像源中按序选择，支持环境变量覆盖，解决特定网络环境下上游源不可达的问题。

### 设计理由

- **网络可达性**：本机 `github.com:443` 不可达，需使用教育网镜像（如 SJTU）获取 LLVM 源码。组件锁应记录多个可用源，而非硬编码单一 URL。
- **identity 与获取途径分离**：`repository` 字段保持不变（= 规范上游身份，必填），`source` 列表记录实际可用的获取途径（可选）。两者语义不同：`repository` 标识组件的规范来源，`source` 列出可用来获取代码的镜像/源。
- **可扩展性**：未来可能有更多镜像源（如 USTC、TUNA），`source` 列表按序排列，新增源只需追加一行。
- **显式优于隐式**：环境变量覆盖按 `name` 显式指定源，`canonical` 保留名表示使用 `repository`；实际使用的源必须打印，便于调试。
- ADR-0005（`.tao/knowledge/adr-0005-component-lock-multi-source.md`）记录了 schema 与选源规则的完整决策。

### 关键概念 / 数据

- `components.lock.toml` 现有 schema（`INFRA-003t`）：`format = 1`、`work_root = ".work"`、`[[component]]` 数组，字段 `name`/`enabled`/`repository`/`commit`/`patch_series`/`role`。
- 新增 `[[component.source]]`：有序数组，每项 `name`（字符串，组件内唯一）+ `url`（Git URL）。`source` 为可选字段；不存在时 `fetch.py` 回退到 `repository`。
- `fetch.py` 现有逻辑（`INFRA-004t`）：读取 `component["repository"]` 作为 Git URL 传给 `sync_mirror`；mirror 目录为 `.cache/<name>.git`（按组件名索引，与 URL 无关）；`sync_mirror` 在 mirror 已存在且 pinned commit 已在对象库时跳过网络（此短路必须保留）。
- `manifest_check.py` 现有校验（`INFRA-003t`）：组件 `name` 非空且不重复；enabled 组件必须有完整 40 位 commit；`patch_series` 文件必须存在；reference 校验。
- **真实背景**：本机 `github.com:443` 不可达；已用教育网镜像 SJTU（`https://mirror.sjtu.edu.cn/git/llvm-project.git`）落地浅 bare 镜像到 `.cache/llvm.git`（376.53 MiB / 189,410 objects / 180,593 files）。`llvmorg-23.1.1` 的 commit = `6dfe1677ab8dffbc6ec13d53a1e0215d75147689`。

### 上游引用

- ADR-0005（`.tao/knowledge/adr-0005-component-lock-multi-source.md`）：组件锁多源 schema 与选源规则的决策记录。
- DADAO-0628 `manifests/components.lock.toml`：单 `repository` 字段（无多源支持）（内容溯源，非执行必需）。
- DADAO-0628 `scripts/fetch.py`：单源获取逻辑（v5 扩展为多源）（内容溯源，非执行必需）。

## 交付物

- `manifests/components.lock.toml`：
  - `llvm` 条目：保留 `repository = "https://github.com/llvm/llvm-project.git"` 不变；**新增** `[[component.source]]`（`name = "sjtu"`、`url = "https://mirror.sjtu.edu.cn/git/llvm-project.git"`）。
  - `qemu`/`gem5` 条目：**暂不添加** `source`（其上游基线 ADR 未定，待各自基线任务补）。`commit`/`enabled` 不变。
- `tools/infra/manifest_check.py`：新增校验——`repository` 非空；`source` 若存在则每项 `name` 非空且唯一、`url` 非空；不破坏现有 commit 40 位十六进制与 `patch_series` 存在性校验。
- `tools/infra/fetch.py`：实现 D2 选源规则——
  - 有效源序列 = `source` 列表（按序）；默认取第一个。
  - 若该组件无 `source` 则用 `repository`。
  - 环境变量 `COMPONENT_SOURCE_<组件名大写>`（如 `COMPONENT_SOURCE_LLVM`）按 `name` 显式指定源；保留名 `canonical` 表示 `repository`。
  - 实际使用的源必须打印。
  - 失败即停，不自动换源/不重试。
  - `sync_mirror` 的短路逻辑（mirror 已存在且 pinned commit 已在对象库时跳过网络）必须保留。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- **多源支持**：0628 的 `components.lock.toml` 只有单个 `repository` 字段；v5 新增 `[[component.source]]` 有序数组，支持多镜像源。
- **选源规则**：0628 的 `fetch.py` 直接使用 `repository` 作为 Git URL；v5 引入 `source` 列表 + 环境变量覆盖机制。
- **qemu/gem5 暂不添加 source**：其上游基线 ADR 未定，待各自基线任务确定后补。
- 无 ISA 相关差异（基础设施，与 ISA 版本无关）。

## 已知坑 / 结论

- **`repository` 字段语义不变**：`repository` 始终是组件的规范上游身份（必填），`source` 是获取途径列表（可选）。两者分离，不互相替代。
- **mirror 目录按组件名索引**：`.cache/<name>.git` 的目录名与 `source` URL 无关，切换源不会创建新 mirror 目录。首次 clone 时使用的 URL 决定了 mirror 的 origin；后续 `sync_mirror` 的 `fetch --prune` 会从当前 origin 拉取。若需切换到不同源且 mirror 已有旧 origin，用户需手动删除 mirror 目录重建（或直接 `git -C .cache/llvm-project.git remote set-url origin <new-url>`）。
- **环境变量覆盖的 `name` 必须匹配**：`COMPONENT_SOURCE_LLVM=sjtu` 必须精确匹配 `source` 列表中的 `name` 字段。若不匹配则报错退出。
- **`canonical` 保留名**：`COMPONENT_SOURCE_LLVM=canonical` 表示使用 `repository` 字段作为源 URL（不从 `source` 列表选取）。
- **`sync_mirror` 短路保留**：当 mirror 已存在且 pinned commit 已在对象库时，`sync_mirror` 跳过网络操作。此行为在多源场景下仍然正确——无论使用哪个源，只要 commit 已在本地对象库，就不需要网络。
- **失败即停**：`fetch.py` 在任何 Git 操作失败时立即退出，不尝试下一个源。自动换源可能掩盖网络问题，且在 CI 环境中可能导致不确定行为。
- **TOML 语法**：`[[component.source]]` 在 `[[component]]` 块之后声明，形成嵌套数组。`tomllib.load()` 后每个 component 条目的 `source` 键为 `list[dict]`。

## 参考

- ADR-0005：`.tao/knowledge/adr-0005-component-lock-multi-source.md`
- 本项目：`.tao/tasks/infra/INFRA-003t-manifest与锁系统.md`、`.tao/tasks/infra/INFRA-004t-组件获取与打补丁工具.md`
- DADAO-0628：`.work/DADAO-0628/manifests/components.lock.toml`（内容溯源，非执行必需）
- DADAO-0628：`.work/DADAO-0628/scripts/fetch.py`（内容溯源，非执行必需）

## 验收标准

1. `manifests/components.lock.toml` 的 `llvm` 条目新增 `[[component.source]]`（`name = "sjtu"`、`url = "https://mirror.sjtu.edu.cn/git/llvm-project.git"`）；`repository` 保持 `https://github.com/llvm/llvm-project.git`；`qemu`/`gem5` 条目无 `source` 字段，`commit`/`enabled` 不变
2. `tools/infra/manifest_check.py` 新增校验：`repository` 非空；`source` 若存在则每项 `name` 非空且唯一、`url` 非空；现有校验（commit 40 位十六进制、`patch_series` 存在性、component name 唯一性、reference 校验）不被破坏；`make manifest-check` PASS
3. `tools/infra/fetch.py` 实现多源选源规则：默认取 `source` 首个（SJTU）；无 `source` 时回退到 `repository`；环境变量 `COMPONENT_SOURCE_LLVM=sjtu` 覆盖生效；`COMPONENT_SOURCE_LLVM=canonical` 使用 `repository`；实际使用的源在输出中打印（如 `fetch: llvm using source 'sjtu' (https://mirror.sjtu.edu.cn/git/llvm-project.git)`）
4. `fetch.py` 的 `sync_mirror` 短路逻辑保留：mirror 已存在且 pinned commit 已在对象库时跳过网络（打印 `skipping fetch`）
5. `fetch.py` 失败即停：Git 操作失败时立即退出（exit=1），不自动换源
6. 用一个**反例**验证 env 覆盖生效：设置 `COMPONENT_SOURCE_LLVM=canonical` 时，fetch 使用 `repository`（`https://github.com/llvm/llvm-project.git`）而非 SJTU 源（打印的实际源应为 `canonical` 或 `repository`）
7. 不改动 `qemu`/`gem5` 的 `commit`/`enabled`（`tomllib` 解析确认）

## 完成区

**测试结果**：验收标准 1–7 全部满足（自测用例 4 个 + 结构验证 2 条）

**修改文件**：
- `manifests/components.lock.toml`：llvm 条目新增 `[[component.source]]`（`name = "sjtu"`、`url = "https://mirror.sjtu.edu.cn/git/llvm-project.git"`）
- `tools/infra/manifest_check.py`：新增 `repository` 非空校验；新增 `source` 校验（每项 `name` 非空且组件内唯一、`url` 非空）
- `tools/infra/fetch.py`：新增 `import os`；新增 `select_source()` 函数（ADR-0005 D2 选源规则）；`main()` 中 `sync_mirror` 调用改为使用 `select_source` 解析后的 URL；打印实际使用的源名和 URL

**验收结果**：

```
$ git diff --stat -- manifests/components.lock.toml tools/infra/fetch.py tools/infra/manifest_check.py
 manifests/components.lock.toml |  4 ++++
 tools/infra/fetch.py           | 49 +++++++++++++++++++++++++++++++++++++++++-
 tools/infra/manifest_check.py  | 14 ++++++++++++
 3 files changed, 66 insertions(+), 1 deletion(-)
```

验收标准 1 + 2 + 7（TOML schema、manifest_check 新校验、qemu/gem5 不变）：
```
$ make manifest-check
enabled components: none
references: 2
manifest validation: PASS
```
附：`python3 -c "import tomllib, pathlib; ..."` 解析确认 llvm 有 `source=[{name:sjtu, url:...}]`，qemu/gem5 无 `source`，三者 `enabled=false`、`commit=""` 不变。

验收标准 3 + 5 + 6（选源正反例：默认取 source 首个、失败即停、env 覆盖）：
```
$ python3 -c "
import sys, os
sys.path.insert(0, '/mnt/tao/DADAO-v5/tools/infra')
from fetch import select_source

llvm_with_source = {
    'name': 'llvm',
    'repository': 'https://github.com/llvm/llvm-project.git',
    'source': [{'name': 'sjtu', 'url': 'https://mirror.sjtu.edu.cn/git/llvm-project.git'}],
}
qemu_no_source = {
    'name': 'qemu',
    'repository': 'https://github.com/qemu/qemu.git',
}

print('=== Test 1: default (has source) ===')
url = select_source(llvm_with_source)
assert url == 'https://mirror.sjtu.edu.cn/git/llvm-project.git', f'FAIL: {url}'
print(f'PASS: {url}')

print()
print('=== Test 2: env canonical ===')
os.environ['COMPONENT_SOURCE_LLVM'] = 'canonical'
url = select_source(llvm_with_source)
assert url == 'https://github.com/llvm/llvm-project.git', f'FAIL: {url}'
print(f'PASS: {url}')
del os.environ['COMPONENT_SOURCE_LLVM']

print()
print('=== Test 3: env nonexistent (should raise SystemExit) ===')
os.environ['COMPONENT_SOURCE_LLVM'] = 'nonexistent'
try:
    select_source(llvm_with_source)
    print('FAIL: expected SystemExit'); sys.exit(1)
except SystemExit as e:
    print(f'PASS: SystemExit raised: {e}')
finally:
    os.environ.pop('COMPONENT_SOURCE_LLVM', None)

print()
print('=== Test 4: no source fallback ===')
url = select_source(qemu_no_source)
assert url == 'https://github.com/qemu/qemu.git', f'FAIL: {url}'
print(f'PASS: {url}')

print()
print('ALL TESTS PASSED')
"
=== Test 1: default (has source) ===
PASS: https://mirror.sjtu.edu.cn/git/llvm-project.git

=== Test 2: env canonical ===
PASS: https://github.com/llvm/llvm-project.git

=== Test 3: env nonexistent (should raise SystemExit) ===
PASS: SystemExit raised: fetch: COMPONENT_SOURCE_LLVM='nonexistent' does not match any source for component 'llvm' (available: ['sjtu'])

=== Test 4: no source fallback ===
PASS: https://github.com/qemu/qemu.git

ALL TESTS PASSED
EXIT_CODE=0
```

验收标准 4（`sync_mirror` 短路保留）：代码审查确认 `sync_mirror` 函数未改动，短路逻辑（`has_commit` 检查 → `skipping fetch`）完整保留；`select_source` 只替换传入的 URL 参数，不改变 `sync_mirror` 内部控制流。因 llvm `enabled=false` 无法通过 `make fetch` 触发实际短路，依赖代码审查 + 函数接口不变性验证。

```
$ make check
enabled components: none
references: 2
manifest validation: PASS
validate_vectors: 178/178 M1 identities covered OK (inventory sync OK; 15 data files, 597 cases; data coverage gaps: 154)
repository checks: PASS
EXIT_CODE=0
```

`git status --short`（仅本次改动文件）：
```
 M manifests/components.lock.toml
 M tools/infra/fetch.py
 M tools/infra/manifest_check.py
```

**新发现/坑**：
- TOML 嵌套数组语法：`[[component.source]]` 必须紧跟其父 `[[component]]` 块、位于下一个 `[[component]]` 之前，否则解析器会把它归到错误的 component。
- `fetch.py` 的 `select_source` 函数被提取为独立函数（不依赖 `main` 的局部变量），便于直接导入测试，无需修改源码适配。

**遗留问题**：
- `fetch.py` 的 `main()` 中打印源标签（`src_label`）的逻辑重复了解析 `env_val` / `sources[0]["name"]` 的过程，与 `select_source()` 内部逻辑重复（DRY 违规）。建议后续 refactor：让 `select_source()` 返回 `(url, label)` 元组，或在 `main()` 中复用 `select_source` 的中间结果。来源：architect 交叉复核。（非阻塞）

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 打印格式建议包含 source name | ✅已修 | `fetch.py` 打印改为 `fetch: {name} using source '{src_label}' ({source_url})` | `py_compile` + `make manifest-check` PASS |

### 第 1 轮 reviewer 验收

**验收者**：reviewer
**结论**：**Accepted**

**独立重跑**（未采信 engineer 汇报）：

| 验证 | 结果 |
|------|------|
| `make manifest-check` | PASS，exit=0 |
| `make check` | exit=0（154 条 `DATA COVERAGE GAP` 为 `TESTCASES-009t` 已知 report-only 项） |
| 选源 5 主用例（`importlib` 加载 `fetch.py`，未改源码） | 默认→sjtu；`canonical`→github；按 name→sjtu；不存在 name→`SystemExit`（真实进程 exit=1，报 `available: ['sjtu']`）；无 source→`repository` —— 全 PASS |
| 小写 env `COMPONENT_SOURCE_llvm` | 不生效（符合 D2「组件名大写」表述），记为可用性小瑕疵、非缺陷 |
| `sync_mirror` 短路 | 用真实 `.cache/llvm.git` + unreachable URL 运行 → 打印 `already has 6dfe1677ab8d; skipping fetch`，未触网 |
| `manifest_check` 反例 10 组 | 缺 `repository`/缺 `name`/重复 `name`/缺 `url`/enabled 非 40 位 commit/缺 `patch_series`/组件名重复/坏 reference 全部报出；合法输入 0 错误 |
| 改动范围 | 仅 `components.lock.toml`/`manifest_check.py`/`fetch.py` 三个实现文件（66 insertions, 1 deletion） |
| `py_compile` | OK |

**非阻塞记录项**（转 engineer 当场修正）：完成区「通过 6/6」口径与 7 条验收标准不符；「验收 2」未记实际命令。

**纠正主会话误判**：空 `name` 的 source 因 `if not src_name: ... elif src_name in src_names:` 的 `if/elif` 结构走 `if` 分支，产生两条 `source name is required`，**不会**误报 `duplicate source name ''`（实测用例 8 确认）。

### 交叉复核（architect）

**复核者**：architect
**时间**：2026-09-17
**结论**：**确认 Accepted**（无过度宽松、无漏判）；**无需新增/修订 ADR**。

**独立核对**：重跑 `make manifest-check`（exit 0）与 `select_source` 四场景；`tomllib` 解析确认 `source` 仅挂 llvm、qemu/gem5 无 `source`；逐条核对 7 条验收标准；读 ADR-0002 D6 确认「否决环境相关的 Git URL 重写」引用准确；全仓 grep 排查 schema/`repository` 消费者。

**跨模块一致性结论（不需改）**：`fetch_refs.py`（读 `references.lock.toml`，另一份 manifest，且参考仓库无多源需求）、`apply_series.py`/`status.py`/`clean_work.py`（不读 `repository`/`source`）、`Makefile`（`component-enabled` 宏只查 `name`/`enabled`）、`README.md`、`INFRA-003t`（历史任务描述其当时 schema，不回溯）、`QEMU-002t`（QEMU 不加 source）。

**补充发现（非阻塞）**：

1. `fetch.py` 的 `main()` 重复解析 env/`source` 生成 `src_label`，与 `select_source()` 逻辑重复（DRY）——已登记至完成区「遗留问题」与 `deferred.md`。
2. ADR-0005 Consequences C2 表述可更精确（源 URL 由 `select_source()` 解析后传入 `sync_mirror`，`sync_mirror` 本身不解析）——非错误，不改动已 `Accepted` 的 ADR。
3. `LLVM-002t` 启用 llvm 后 `make manifest-check` 需 `components/llvm-project/patches/series` 存在；该坑 `LLVM-002t` 任务书已在「交付物」与「已知坑」登记，无需额外登记。

**统一判决**：**Accepted**。

### 收尾

- 完成区 2 处可审计性问题由原 engineer 修正（计数改为逐条对应验收标准；补上「验收 2」的实际命令并重跑确认，输出一致）。
- `**状态**` 置 `已验证`（2026-09-17）。
- `changelog.md`、`MEMORY.md` 已同步；DRY 项登记至 `deferred.md` 的 `## infra`。
