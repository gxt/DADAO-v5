# DADAO-v5 top-level orchestration.
#
# Make is the stable user interface (ADR-0002: .tao/adr/adr-0002-build-orchestration.md); the actual manifest/fetch/patch
# logic is delegated to Python standard-library scripts under tools/infra/. All
# disposable data lives under .work/ (gitignored); persistent upstream mirrors
# live under .cache/ and are never touched by clean-work.

PYTHON ?= python3

# Install/product directory paths — single source of truth from
# manifests/install-dirs.lock.toml via tools/infra/paths.py.
# These are absolute, realpath-resolved paths.  To change them, edit the
# manifest; do NOT hardcode paths here.
REPO_ROOT          := $(shell $(PYTHON) tools/infra/paths.py repo_root)
SDK_DIR            := $(shell $(PYTHON) tools/infra/paths.py sdk_dir)
HOST_TOOLCHAIN_DIR := $(shell $(PYTHON) tools/infra/paths.py host_toolchain_dir)
HOST_TOOLCHAIN_BIN := $(shell $(PYTHON) tools/infra/paths.py host_toolchain_bin)
HOST_TOOLS_BIN     := $(shell $(PYTHON) tools/infra/paths.py host_tools_bin)
TARGET_SYSROOT_DIR := $(shell $(PYTHON) tools/infra/paths.py target_sysroot_dir)
TEST_ARTIFACTS_DIR := $(shell $(PYTHON) tools/infra/paths.py test_artifacts_dir)

# Non-empty guard: abort if any path variable is empty (manifest missing/corrupt).
_install_dir_vars = REPO_ROOT SDK_DIR HOST_TOOLCHAIN_DIR HOST_TOOLCHAIN_BIN HOST_TOOLS_BIN TARGET_SYSROOT_DIR TEST_ARTIFACTS_DIR
$(foreach v,$(_install_dir_vars),$(if $($v),,$(error $v is empty — check manifests/install-dirs.lock.toml and tools/infra/paths.py)))

# Component source/build trees (all under the disposable .work/ root). The
# llvm source is the monorepo checkout with its `llvm/` project subdirectory.
QEMU_SRC   ?= .work/source/qemu
QEMU_BUILD ?= .work/build/qemu
LLVM_SRC   ?= .work/source/llvm-project/llvm
LLVM_BUILD ?= .work/build/llvm
# cfx alias runtime table (LLVM-135t): *data*, not code.  llvm-mc/llvm-objdump
# (and clang's inline assembler) read <exe-dir>/../share/dadao/cfx-aliases.txt,
# so aliases are names/numbers resolved at run time -- renaming a cfx or
# renumbering its registers needs only a copy, never an LLVM rebuild.
# Source of truth: contracts/cfx-aliases.txt (generated from spec; drift gate
# `check-cfx-alias-table`).
CFX_ALIAS_TABLE_SRC     ?= contracts/cfx-aliases.txt
CFX_ALIAS_TABLE_BUILD   ?= $(LLVM_BUILD)/share/dadao/cfx-aliases.txt
CFX_ALIAS_TABLE_INSTALL ?= $(HOST_TOOLCHAIN_DIR)/share/dadao/cfx-aliases.txt
GEM5_SRC   ?= .work/source/gem5
GEM5_BUILD ?= .work/build/gem5

DOCKER_TAG ?= dadao-v5-dev:local

.DEFAULT_GOAL := help

.PHONY: help manifest-check doctor status fetch fetch-refs apply-series prepare \
        clean-work build-mc build-mc-lite build-mc-reconfig build-lld \
        build-builtins build-qemu build-qemu-reconfig build-gem5 build-bootrom build-picolibc \
        build-musl build-musl-shared test-picolibc-smoke install-host install-cfx-aliases docker-image docker-shell check \
        check-picolibc-tests check-picolibc-tests-full check-rnd-probe \
        check-minmax-probe check-fma-probe check-clmul-probe \
        check-testcases-suites check-testcases-suites-full \
        check-modules check-full check-components check-knowledge-refs \
        check-inst check-inst-smoke check-tests-index check-arch check-arch-smoke \
        check-unit check-unit-full check-tset-libc-smoke check-tset-llvm-smoke check-tset-embench-smoke \
        check-tset-libc-full check-tset-llvm-full check-tset-embench-full \
        clean-tests test-repro check-night check-night-report \
        validate-vectors check-spec-refs check-spec-drift check-asm-list \
        check-legality-drift check-interface validate-encoding check-scope \
        check-rule-refs check-fp-contract check-instrinfo \
        check-dirs check-no-residue check-spec-readonly check-cfx-aliases check-asm-prose check-lit \
        check-cfx-alias-table check-cfx-alias-install check-cfx-vectors \
        check-lit-full \
        check-run-artifacts \
        test-codegen test-elf test-m6 \
        check-patch-tree check-index-blobs check-source-state check-asm-list-drift size-report \
        check-musl-freshness check-builtins-freshness check-install-tools check-milestones-fresh \
        check-tasks check-spec-codeblocks check-legality-invariants \
        check-isa-coverage check-spec-numbering check-spec-changelog check-spec-archive check-contracts-dir \
        check-rev-vectors \
        check-spec-archive-verify check-milestone check-sync-nonmaskable \
        check-component-changelog check-syscall-abi check-spec-purity check-spec-cite-targets \
        check-width-sizes check-code-range

# ── 工作树互斥锁 (INFRA-099t / ISS-229) ─────────────────────────────────────────
# 同一工作树内会写共享状态的目标 —— 构建树 `.work/build/**`、安装根 $(SDK_DIR)、
# SDK 产物目录 $(TEST_ARTIFACTS_DIR) —— 以及跑这些写者的门控，全部**串行化**：
# `GATE_LOCKED_TARGETS` 里每个名字都是**门控目标**（目标体 + 其前置在
# `_locked-<name>`），由 tools/infra/gate_lock.py 在一个 flock(2) 上运行，锁文件
# = $(GATE_LOCK)。这是 `ISS-229` 的机械化：L2 与 L3 并发曾读到瞬态不完整的安装根
# ⇒ Embench 假 FAIL（`stddef.h not found`）；手动 `build-mc` 与 L2 内
# `install-host` 并发 ⇒ 构建树写坏。规范见 docs/Process-07 §2。
#
# 语义（细节 + 自测见 tools/infra/gate_lock.py）：
#   * **嵌套放行**：同一 make 树内 `check-modules → check-arch-smoke → install-host →
#     build-mc` 通过 DADAO_GATE_LOCK_HELD 直接通过（并由「持有者 pid 是本进程祖先」
#     校验，环境标记本身不能关掉互斥），不会自锁。
#   * **独立进程等待有上界**：GATE_LOCK_WAIT 秒（默认 3600，够一次 L3 持有）；
#     超时打印「锁文件 + 持有者 pid/开始时间/目标/命令」，rc=75。
#   * **fail-fast**：`GATE_LOCK_FAILFAST=1` ⇒ 一次非阻塞尝试失败即 rc=75 + 提示。
#   * **锁不可用**（父目录不可写 / 无 flock(2)）⇒ rc=69 且**不运行**目标（不静默跳过）。
#   * 锁文件 `.dadao/gate.lock` 在 .gitignore 的 `.dadao/` 下，不入库。
GATE_LOCK          ?= $(REPO_ROOT)/.dadao/gate.lock
GATE_LOCK_WAIT     ?= 3600
GATE_LOCK_FAILFAST ?= 0
GATE_LOCK_TOOL      = $(PYTHON) tools/infra/gate_lock.py

# 互斥面的**单一真源**（文档只指这里，不另列清单，避免漂移）。
GATE_LOCKED_TARGETS = install-host install-cfx-aliases clean-work \
                      build-mc build-mc-lite build-mc-reconfig build-lld build-qemu build-qemu-reconfig \
                      build-builtins build-bootrom build-picolibc build-musl build-musl-shared \
                      test-codegen test-elf test-m6 test-picolibc-smoke \
                      check-lit check-lit-full \
                      check-inst check-inst-smoke check-arch check-arch-smoke \
                      check-unit check-unit-full check-tset-libc-smoke check-tset-llvm-smoke check-tset-embench-smoke \
                      check-tset-libc-full check-tset-llvm-full check-tset-embench-full \
                      clean-tests test-repro check-night \
                      check-picolibc-tests check-picolibc-tests-full check-rnd-probe \
                      check-minmax-probe check-fma-probe check-clmul-probe \
                      check-testcases-suites check-testcases-suites-full \
                      check check-modules check-full

# $(call gate-locked,<target>): 在锁下重入 make 跑 `_locked-<target>`。
# 必须重入而不能只锁 recipe：`install-host: build-mc build-lld ...` 的**前置**
# 才是写者，而前置在 recipe 之前执行。`-f $(firstword $(MAKEFILE_LIST))` 让重入
# 读同一个 makefile（`make -f`/探针 makefile 亦然）。一行（不用 `\` 续行，避免
# recipe 被拆行）。
gate-locked = $(GATE_LOCK_TOOL) run --lock "$(GATE_LOCK)" --wait $(GATE_LOCK_WAIT) --failfast $(GATE_LOCK_FAILFAST) --target $(1) -- $(MAKE) -f $(firstword $(MAKEFILE_LIST)) --no-print-directory _locked-$(1)

# 每个被锁目标 = 一条只做「进锁 + 重入」的门控规则；`_locked-<name>` 是原规则。
# `+` = make 的「recursive invocation」标记：把 jobserver 交给重入的 make，否则
# `make -jN` 会在子 make 里退化成 `-j1` 并打印 "jobserver unavailable"（本仓库
# `make -n` 本就不可用，见 Process-07 §1，`+` 使其在 -n 下也执行此行，同任何含
# $(MAKE) 的行）。
define gate-locked-rule
$(1):
	+@$$(call gate-locked,$(1))
endef
$(foreach t,$(GATE_LOCKED_TARGETS),$(eval $(call gate-locked-rule,$(t))))
.PHONY: $(GATE_LOCKED_TARGETS) $(addprefix _locked-,$(GATE_LOCKED_TARGETS))

# $(call component-enabled,<name>) exits 0 only when <name> is enabled in
# manifests/components.lock.toml. Build targets use it to refuse to pretend
# they built a component whose upstream commit is still pending.
component-enabled = $(PYTHON) -c "import tomllib,sys;m=tomllib.load(open('manifests/components.lock.toml','rb'));sys.exit(0 if any(c['name']=='$(1)' and c.get('enabled') for c in m.get('component',[])) else 1)"

help:
	@echo "DADAO-v5 orchestration"
	@echo ""
	@echo "  make help            Show this help"
	@echo "  make manifest-check  Validate specification/component/reference locks"
	@echo "  make doctor          Check host or container build prerequisites"
	@echo "  make status          Show locked components and references"
	@echo "  make fetch           Fetch enabled components at exact commits"
	@echo "  make fetch-refs      Fetch locked reference repositories"
	@echo "  make apply-series    Apply ordered patch series then auto-commit (E5)"
	@echo "  make prepare         Fetch enabled components and apply their patch series"
	@echo "  make check-source-state  Report each source tree's E1 state (clean + base+1)"
	@echo "  make build-mc        Build LLVM MC+CodeGen+clang+lli from one config (targets DADAO;X86, projects clang;lld)"
	@echo "  make build-mc-lite   Build LLVM MC/objdump/FileCheck/not only (no objcopy/readobj/CodeGen/clang/lli)"
	@echo "  make build-mc-reconfig  Force cmake re-run then build the full LLVM tool set"
	@echo "  make build-lld       Build LLD linker (bin/ld.lld); shares the one-shot LLVM config"
	@echo "  make build-qemu      Compile QEMU (skips configure if build.ninja exists)"
	@echo "  make build-qemu-reconfig  Force configure re-run then compile QEMU"
	@echo "  make build-gem5      Build gem5 (stub; command owned by the gem5 module)"
	@echo "  make build-bootrom   Assemble+link the SEE bootrom firmware and sample app (QEMU-047t; needs install-host)"
	@echo "  make build-picolibc  Build picolibc for dadao-unknown-elf and install it into the target sysroot (INFRA-057t; needs install-host + fetch/apply-series)"
	@echo "  make build-musl      Build the static musl libc (libc.a + crt) for dadao-unknown-elf in .work/source/musl (INFRA-082t; needs install-host + fetch/apply-series)"
	@echo "  make build-musl-shared  Build musl shared/PIC libc.so + the PIC static archive libc_pic.a (for -static-pie) + link a dynamic smoke executable (PT_INTERP/DT_NEEDED), and install libc.so + libc_pic.a + the ld-musl-dadao.so.1 symlink into the target sysroot (INFRA-085t stage A1/B1, INFRA-108t; needs install-host + fetch/apply-series)"
	@echo "  make build-builtins  Rebuild the compiler-rt builtins with the current build-tree clang and stage the archive into that clang's resource dir (ISS-293; needs build-mc + a configured compiler-rt build tree)"
	@echo "  make test-picolibc-smoke  Compile/link/run a minimal picolibc printf program (QEMU semihosting; INFRA-057t)"
	@echo "  make check-picolibc-tests  Run the picolibc self-test representative set (L2; TESTCASES-042t)"
	@echo "  make check-picolibc-tests-full  Run the full picolibc self-test set (opt-in/L3-like; TESTCASES-042t)"
	@echo "  make check-rnd-probe  Run the ftrnd/fornd roundToIntegral probes at -O0 and -O2 (L3; TESTCASES-060t)"
	@echo "  make check-minmax-probe  Run the ftmin/ftmax/fomin/fomax min/max probes at -O0 and -O2 (L3; TESTCASES-059t)"
	@echo "  make check-fma-probe  Run the ftfma/fofma single-rounding / dot / GEMM / Horner probes at -O0 and -O2 (L3; TESTCASES-058t)"
	@echo "  make check-clmul-probe  Run the clmul.o instruction / GHASH / CRC-32C probes at -O0 and -O2 (L3; TESTCASES-057t)"
	@echo "  make check-testcases-suites  Run the two upstream reference suites (libc-test + llvm-test-suite) fast subset (opt-in, not L2; TESTCASES-045t)"
	@echo "  make check-testcases-suites-full  Run every enumerable C case with main() from both suites (opt-in/L3-like; TESTCASES-045t)"
	@echo "  make check-tset-libc-smoke  libc-test user-mode smoke representative set (L2; TESTCASES-075t)"
	@echo "  make check-tset-llvm-smoke  llvm-test-suite user-mode smoke representative set (L2; TESTCASES-075t)"
	@echo "  make check-tset-embench-smoke  Embench-IoT user-mode full set -O0/-O2 (L2; TESTCASES-075t)"
	@echo "  make check-tset-{libc,llvm,embench}-full  tset full set, both link modes (night only; TESTCASES-076t)"
	@echo "  make check-builtins-freshness  compiler-rt builtins archive must be the one the current clang built (build-id sidecar), in every consumer copy (L1; ISS-293/INFRA-101t)"
	@echo "  make install-host    Install needed tools: cross toolchain (clang/llc/ld.lld …) into \$$(HOST_TOOLCHAIN_BIN) + host lli into \$$(HOST_TOOLS_BIN); adr-0016 D3/D4/D5/D11"
	@echo "  make install-cfx-aliases  Copy contracts/cfx-aliases.txt to the build tree + install root only (no rebuild; LLVM-135t)"
	@echo "  make docker-image    Build the development image ($(DOCKER_TAG))"
	@echo "  make docker-shell    Open a shell in the development image"
	@echo "  make clean-work      Remove generated .work content only"
	@echo "  make validate-vectors  Validate tests/inst vectors schema/inventory/coverage (L1)"
	@echo "  make check           Run repository-level structural checks (L1: static + component smoke)"
	@echo "  make check-modules   Run L2 = the four scopes' smoke sets (inst/arch/unit + tset x3; no FP probes)"
	@echo "  make check-full      Run L3 = check-inst + check-arch + check-unit-full + 4 FP probes + test-m6 (tset smoke is L2-only; tset full is night-only; TESTCASES-082t)"
	@echo "  make check-night     Run the night set (tset full x3 + long arch) and write .dadao/tests/night/<date>/ (setsid nohup; TESTCASES-076t)"
	@echo "  make check-night-report  Gate: the night report exists and is structurally complete + green (milestone closure; TESTCASES-076t)"
	@echo "  make clean-tests     Remove one scope's generated artifacts (SCOPE=inst|arch|unit|tset|night|all; DRY_RUN=1 to list; TESTCASES-076t)"
	@echo "  make test-repro      Prove build products regenerate byte-identically (SCOPE=...; TESTCASES-076t)"
	@echo "  make check-components  Component availability smoke (llc/clang --print-targets/qemu; L1)"
	@echo "  make check-inst-smoke  inst semantic smoke (representative subset; L2; TESTCASES-072t)"
	@echo "  make check-inst      inst semantic full set (tests/inst; L3; TESTCASES-072t)"
	@echo "  make check-knowledge-refs  Dangling .work/** reference gate (L1; INFRA-058t)"
	@echo "  make check-run-artifacts  Run-directory three-piece set + .work/log new-name gate (L1; INFRA-093t)"
	@echo "  make check-width-sizes  64-bit width + ELF64/rela/got + DWARF64 addr_size probe (L1; LLVM-130t)"
	@echo "  make check-code-range  DADAO code-span gate: REL26 edge ≤ 32 MiB + exec_span < 30 MiB (L1; ADR-0036/INFRA-106t)"
	@echo "  make check-contracts-dir  Whitelist gate for .tao/contracts/ + contracts/ top level (L1; INFRA-071t)"
	@echo "  make check-component-changelog  Component changelog list-form/milestone-section gate (L1; INFRA-084t)"
	@echo "  make check-syscall-abi  syscall argument-bank tables agree across musl C stub / cancellable asm / QEMU host, and cover every syscall musl can issue (L1; ISS-249)"
	@echo "  make check-contracts-pending  Contract pending markers (待定/待裁定/TODO/TBD) must carry an ADR-/ISS- pointer (L1; 2026-10-17)"
	@echo "  make check-contract-relocs  contract-elf §2.2 vs contract-dynlink §4.3 relocation type-table agreement (L1; 2026-10-17)"
	@echo "  make check-milestones-fresh  milestones.md task-flow table gate: status/coverage/length/order/format (L1; INFRA-091t)"
	@echo "  make check-milestone  Milestone closure: SIMRISC archive + sha + sync-nonmaskable + knowledge whitelist + m-book + night report + check-tasks --strict (not L1)"
	@echo "  make check-sync-nonmaskable  Sync exception causes must not be maskable (only IPI/TIMER/UART*/… may; SPEC-175t; not L1)"
	@echo "  make check-interface  Check cross-module interface alignment (L1)"
	@echo "  make validate-encoding  Validate opcodes.yaml encoding consistency"
	@echo "  make check-scope     Check opcodes.yaml scope partition (m1/fp/excluded; SPEC-086t)"
	@echo "  make check-spec-drift  Audit contract provenance against README versions"
	@echo "  make check-spec-refs Audit spec references in contract-*.md (L1; INFRA-011t/058t)"
	@echo "  make check-isa-coverage  ISA<->backend coverage matrix drift gate (L1; LLVM-081t/INFRA-069t)"
	@echo "  make check-rev-vectors  rev vector re-derivation + spec_cite/oracle drift gate (L1; ISS-335)"
	@echo "  make check-spec-numbering  Check 21-volume heading numbering structure (L1; SPEC-133t/INFRA-069t)"
	@echo "  make check-spec-changelog  Check 21-volume appendix changelog structure (L1; SPEC-134t/INFRA-069t)"
	@echo "  make check-spec-archive  Check SimRISC per-version archives exist (milestone closure; SPEC-154t/INFRA-109t)"
	@echo "  make check-spec-archive-verify  Verify archive content sha256 against snapshot provenance (milestone closure; SPEC-154t/INFRA-109t)"
	@echo "  make check-spec-purity  spec/SimRISC-* must not carry scope/task-id/ADR/ISS/contract refs (L1; SPEC-165t)"
	@echo "  make check-spec-cite-targets  Every spec_cite book+section must exist in spec/ (L1; SPEC-165t)"
	@echo "  make check-asm-list  Check spec embedded assembly table consistency"
	@echo "  make check-asm-prose  Check prose assembly format gate (strict mode)"
	@echo "  make check-spec-codeblocks  Check spec prose \`\`\`simrisc blocks vs opcodes.yaml (ISS-077)"
	@echo "  make check-unit       unit scope representative set: lit + codegen/elf + ir-lli + picolibc fast (L2; TESTCASES-074t)"
	@echo "  make check-unit-full  unit scope full set: check-unit + lit full (L3 only; TESTCASES-076t)"
	@echo "  make check-lit        Run lit MC + CodeGen + E2E tests (requires install-host; check-unit member)"
	@echo "  make check-lit-full   Run full generated lit MC suite from contracts/opcodes.yaml (opt-in; TESTCASES-037t)"
	@echo "  make test-codegen     Run M3 CodeGen E2E gate (llc->llvm-mc->objcopy->qemu; INTEG-012t; check-unit member)"
	@echo "  make test-elf         Run M4 multi-TU/multi-section ELF E2E gate (llc->ld.lld->qemu; INTEG-016t; check-unit member)"
	@echo "  make check-arch-smoke  arch smoke: SEE/semihosting + cfx permission + 25 svc (L2; TESTCASES-073t)"
	@echo "  make check-arch      arch full cfx set: arch-smoke + cfx min-ROM probes (L3; TESTCASES-073t)"
	@echo "  make test-m6          Run M6 E2E gate (lli value-level diff + Embench all benches -O0/-O2 + full lit MC suite; opt-in, INTEG-025t)"
	@echo "  make check-patch-tree  Check component patch tree (docs/Process-01, 9 assertions)"
	@echo "  make check-index-blobs  Check new-file patch index blob hashes (INFRA-038t/ISS-119)"
	@echo "  make check-legality-drift  Check LEGALITY section drift gate (SPEC-074t)"
	@echo "  make check-legality-invariants  Check ftroot/foroot n=2 + rule-rename gate (ISS-079)"
	@echo "  make check-rule-refs  Check rule_refs bidirectional gate (SPEC-071t)"
	@echo "  make check-fp-contract  Check FP semantics contract completeness (SPEC-087t)"
	@echo "  make check-instrinfo  Cross-check DADAOInstrInfo.td against opcodes.yaml (LLVM-046t)"
	@echo "  make check-cfx-aliases  Check cfx alias table drift gate (SPEC-075t)"
	@echo "  make check-cfx-alias-table  contracts/cfx-aliases.txt (runtime table) == spec projection (L1; LLVM-135t)"
	@echo "  make check-cfx-alias-install  Runtime table copies (build tree + install root) == source (needs install-host; LLVM-135t)"
	@echo "  make check-cfx-vectors  Re-derive the cfx MC vector encodings from opcodes.yaml + alias contract (L1; LLVM-060t)"
	@echo "  make check-asm-list-drift  Check assembly-list drift gate (INFRA-027t)"
	@echo "  make check-dirs      Validate install-dirs paths and symlink prefix guard"
	@echo "  make check-no-residue  Detect unexpected untracked temp files"
	@echo "  make check-spec-readonly  Verify read-only spec volumes against sha256 lock (SPEC-119t)"
	@echo "  make size-report  Report added-component-file sizes (advisory, not a gate)"
	@echo "  make check-tasks  Report tasks with filled 完成区 but status still 待验收 (advisory; --strict to fail)"

manifest-check:
	@$(PYTHON) tools/infra/manifest_check.py

doctor:
	@$(PYTHON) tools/infra/doctor.py

status:
	@$(PYTHON) tools/infra/status.py

fetch: manifest-check
	@$(PYTHON) tools/infra/fetch.py

fetch-refs: manifest-check
	@$(PYTHON) tools/infra/fetch_refs.py

# E5: after applying, apply_series.py commits locally (message
# "dadao: <component> patch series") so the worktree ends clean at base+1.
apply-series: manifest-check
	@$(PYTHON) tools/infra/apply_series.py

prepare: fetch apply-series

# DADAO is registered by adding it to LLVM_ALL_TARGETS in llvm/CMakeLists.txt
# (see ADR-0007).
#
# INFRA-050t: ONE cmake configuration for the whole LLVM tool set.  The tree
# .work/build/llvm is shared by build-mc / build-mc-lite / build-lld, so all of
# them must agree on the configuration; otherwise each would keep switching the
# tree back and forth.  The single configuration is:
#   - targets  DADAO + X86   (X86 is needed by lli's JIT value-level oracle)
#   - projects clang + lld   (clang compiler binary + ld.lld linker)
# and produces all four tools (clang/llc/ld.lld + lli) from one source commit.
# The config is stamped into the disposable build tree; the incremental fast
# path reconfigures only when the stamp differs, so a stale tree can never be
# silently reused (use build-mc-reconfig to force).  ADR-0016 D3/D11.
LLVM_TARGETS ?= DADAO;X86
LLVM_PROJECTS ?= clang;lld
LLVM_BUILD_CONFIG = targets=$(LLVM_TARGETS) projects=$(LLVM_PROJECTS) build_type=RelWithDebInfo assertions=ON

# Single-line shell snippet: (re)configure $(LLVM_BUILD) only when its stamped
# configuration differs.  A failing cmake aborts before the stamp is written.
LLVM_CONFIGURE = echo '$(LLVM_BUILD_CONFIG)' | cmp -s - $(LLVM_BUILD)/.dadao-llvm-config 2>/dev/null || { echo "llvm: configuring $(LLVM_BUILD) [$(LLVM_BUILD_CONFIG)]"; cmake -G Ninja -B $(LLVM_BUILD) -S $(LLVM_SRC) -DLLVM_TARGETS_TO_BUILD="$(LLVM_TARGETS)" -DLLVM_ENABLE_PROJECTS="$(LLVM_PROJECTS)" -DCMAKE_BUILD_TYPE=RelWithDebInfo -DLLVM_ENABLE_ASSERTIONS=ON || exit 1; echo '$(LLVM_BUILD_CONFIG)' > $(LLVM_BUILD)/.dadao-llvm-config; }

LLVM_MC_FULL_TARGETS = llvm-mc llvm-objdump llvm-objcopy llvm-readobj llvm-nm llvm-readelf llvm-dwarfdump FileCheck not LLVMDADAOCodeGen llc lli clang
LLVM_MC_LITE_TARGETS = llvm-mc llvm-objdump FileCheck not

_locked-build-mc: manifest-check
	@$(call component-enabled,llvm-project) || { \
	  echo "build-mc: component 'llvm-project' is not enabled / commit pending (manifests/components.lock.toml); refusing to fake success"; \
	  exit 1; \
	}
	@$(LLVM_CONFIGURE)
	ninja -j$(JOBS) -C $(LLVM_BUILD) $(LLVM_MC_FULL_TARGETS)
	@echo "build-mc: PASS"

# build-mc-lite: same as build-mc but omits llvm-objcopy, llvm-readobj,
# LLVMDADAOCodeGen, lli and clang.  Sufficient for lit MC tests + encoding
# oracle + FileCheck.  Shares the one-shot configuration above.
_locked-build-mc-lite: manifest-check
	@$(call component-enabled,llvm-project) || { \
	  echo "build-mc-lite: component 'llvm-project' is not enabled / commit pending; refusing to fake success"; \
	  exit 1; \
	}
	@$(LLVM_CONFIGURE)
	ninja -j$(JOBS) -C $(LLVM_BUILD) $(LLVM_MC_LITE_TARGETS)
	@echo "build-mc-lite: PASS"

# build-mc-reconfig: force a cmake re-run (drops the config stamp first).
_locked-build-mc-reconfig: manifest-check
	@$(call component-enabled,llvm-project) || { \
	  echo "build-mc-reconfig: component 'llvm-project' is not enabled / commit pending; refusing to fake success"; \
	  exit 1; \
	}
	@rm -f $(LLVM_BUILD)/.dadao-llvm-config
	@$(LLVM_CONFIGURE)
	ninja -j$(JOBS) -C $(LLVM_BUILD) $(LLVM_MC_FULL_TARGETS)
	@echo "build-mc-reconfig: PASS"

# build-lld: build the LLD linker (produces .work/build/llvm/bin/ld.lld).
# See INFRA-043t / INFRA-050t.
#
# Since INFRA-050t, lld is part of the single shared configuration
# (LLVM_ENABLE_PROJECTS=clang;lld), so build-lld no longer needs its own cmake
# re-run: it reuses the stamped configuration via $(LLVM_CONFIGURE).
#
# The ninja target is `lld` (not `ld.lld`): lld/CMakeLists.txt creates the
# `ld.lld`/`lld-link`/`ld64.lld`/`wasm-ld` names as POST_BUILD copies of the
# `lld` executable (add_lld_symlink -> ALWAYS_GENERATE), so no separate ninja
# target named ld.lld exists.  Building `lld` writes bin/ld.lld.
LLD_TARGETS = lld

_locked-build-lld: manifest-check
	@$(call component-enabled,llvm-project) || { \
	  echo "build-lld: component 'llvm-project' is not enabled / commit pending (manifests/components.lock.toml); refusing to fake success"; \
	  exit 1; \
	}
	@$(LLVM_CONFIGURE)
	ninja -j$(JOBS) -C $(LLVM_BUILD) $(LLD_TARGETS)
	@echo "build-lld: PASS"

# build-qemu skips configure when build.ninja already exists (incremental fast
# path).  After applying patches that only touch .c/.h files (not meson.build),
# the incremental path compiles only changed objects (~3s for one file).
# Use build-qemu-reconfig to force a full configure (e.g. after changing
# meson.build or configure options).
_locked-build-qemu: manifest-check
	@$(call component-enabled,qemu) || { \
	  echo "build-qemu: component 'qemu' is not enabled / commit pending (manifests/components.lock.toml); refusing to fake success"; \
	  exit 1; \
	}
	@if [ -f $(QEMU_BUILD)/build.ninja ]; then \
	  echo "build-qemu: build.ninja exists, skipping configure (use build-qemu-reconfig to force)"; \
	else \
	  mkdir -p $(QEMU_BUILD) && \
	  cd $(QEMU_BUILD) && $(CURDIR)/$(QEMU_SRC)/configure \
	    --target-list=dadao-softmmu,dadao-linux-user \
	    --enable-tcg \
	    --disable-werror; \
	fi
	PYTHONHASHSEED=0 $(MAKE) -C $(QEMU_BUILD) -j$(JOBS)
	@echo "build-qemu: PASS"

# build-qemu-reconfig: always re-run configure (for when meson.build changes).
_locked-build-qemu-reconfig: manifest-check
	@$(call component-enabled,qemu) || { \
	  echo "build-qemu-reconfig: component 'qemu' is not enabled / commit pending; refusing to fake success"; \
	  exit 1; \
	}
	mkdir -p $(QEMU_BUILD)
	cd $(QEMU_BUILD) && $(CURDIR)/$(QEMU_SRC)/configure \
	  --target-list=dadao-softmmu,dadao-linux-user \
	  --enable-tcg \
	  --disable-werror
	PYTHONHASHSEED=0 $(MAKE) -C $(QEMU_BUILD) -j$(JOBS)
	@echo "build-qemu-reconfig: PASS"

# gem5 is a v5 addition and has no build command yet (the gem5 module owns it).
# This target is a deliberate skeleton: even once the component is enabled it
# must not claim success until a real recipe exists.
build-gem5: manifest-check
	@$(call component-enabled,gem5) || { \
	  echo "build-gem5: component 'gem5' is not enabled / commit pending (manifests/components.lock.toml); refusing to fake success"; \
	  exit 1; \
	}
	@echo "build-gem5: gem5 build command is not defined yet (owned by the gem5 module); refusing to fake success"
	@exit 1

# install-host (INFRA-047t, ADR-0016 D3/D4/D5/D11): stage only the needed host
# tool set from the .work/ build trees into the install root's bin/, install the
# lit runner (package + launcher) so the install root is self-contained, and lay
# down the target sysroot skeleton.  .work/ stays the single build truth (D9);
# the install root is a cache — re-run after rebuilding the components.
#
# D11 scope: just the tools the gates/executors need — llvm-mc/llvm-objdump/
# llvm-readobj/llvm-nm/llvm-readelf/llvm-dwarfdump/FileCheck/not (lit MC +
# symbol/ELF/DWARF inspection),
# llc (CodeGen), llvm-objcopy (test-codegen), lld + ld.lld (test-elf), clang
# (M6 cross compiler, INFRA-050t), qemu-system-dadao (D4), llvm-lit (lit runner).
# No full `cmake --install`.  (llvm-nm/llvm-readelf: INFRA-098t / ISS-261.)
#
# INFRA-050t dual destination: the cross toolchain (clang/llc/ld.lld) and the
# other target/cross tools go into $(HOST_TOOLCHAIN_BIN); the host-only lli
# value-level oracle goes into $(HOST_TOOLS_BIN) (resolved via paths.py, D7).
# The build tree's bin/clang is a symlink to a versioned clang-NN, so install
# with `cp -L` to dereference it (otherwise the installed symlink dangles).
#
# INFRA-053t: every install writes to a per-process temp name and then rename(2)s
# it over the destination ($(call atomic-install,...)).  rename(2) atomically
# replaces an existing regular file *or* a stale (e.g. previously dangling)
# symlink, so re-runs stay idempotent — and two concurrent `make install-host`
# runs can no longer hit `cp: cannot create regular file ...: File exists`.
# That error came from `cp -L --remove-destination`, which unlinks then opens
# O_CREAT|O_EXCL (a non-atomic pair): the loser's O_EXCL open fails EEXIST when
# the winner recreates the destination in between (ISS-172).
#
# NOTE (concurrency): install-host's *writes* are race-safe (INFRA-053t above),
# and concurrent runs of the writers/gates in one worktree are now *serialized*
# mechanically rather than by convention (INFRA-099t / ISS-229): every target in
# $(GATE_LOCKED_TARGETS) — install-host and the build-*/test-*/check* targets
# that share the build trees, this install root and $(TEST_ARTIFACTS_DIR) — runs
# under one flock(2) on $(GATE_LOCK) via tools/infra/gate_lock.py.  Independent
# processes wait (bounded by GATE_LOCK_WAIT, rc=75 with the holder's pid/target
# on timeout) or are refused at once with GATE_LOCK_FAILFAST=1; nested calls
# from the same make tree pass through.  See docs/Process-07 §2.
HOST_LLVM_TOOLS = llvm-mc llvm-objdump llvm-objcopy llvm-readobj llvm-nm llvm-dwarfdump FileCheck not llc clang
# Zero-copy aliases, `<link>:<target>` (both live in $(HOST_TOOLCHAIN_BIN)).
# Single source of truth for the install aliases: the install recipe creates
# them and tools/infra/check_install_tools.py asserts their shape.  Relative
# symlinks resolve inside the install root and cost no bytes, unlike
# atomic-install (cp -aL) which would copy the (multi-GB) target again.
#
#   llvm-readelf -> llvm-readobj : upstream builds llvm-readelf as that same
#     binary (llvm/tools/llvm-readobj/CMakeLists.txt: `add_llvm_tool_symlink`),
#     so the GNU-style dumper is llvm-readobj in GNU output mode.  The build
#     tree's bin/llvm-readelf is a relative symlink too (ISS-261 / INFRA-098t).
#   clang++ -> clang : same binary as the C driver (INFRA-056t).
#   ld.lld -> lld    : lld's post-build copies (INFRA-043t).
HOST_LLVM_TOOL_SYMLINKS = ld.lld:lld clang++:clang llvm-readelf:llvm-readobj
HOST_LIT_DIR = $(HOST_TOOLCHAIN_DIR)/share/lit

# $(call atomic-install,<src>,<dst>): install <src> over <dst> via a per-process
# temp file + rename(2).  Idempotent and race-free (INFRA-053t / ISS-172).
# `cp -L` dereferences a source symlink (e.g. bin/clang -> clang-NN); rename(2)
# atomically replaces a regular/symlink destination, including a dangling one.
define atomic-install
cp -aL $(1) $(2).tmp.$$$$ && mv -f $(2).tmp.$$$$ $(2)
endef

# $(call atomic-install-dir,<srcdir>,<dstdir>): same temp+rename(2) convention as
# atomic-install, for a directory tree.  A rename(2) cannot overwrite a
# *non-empty* directory (ENOTEMPTY), so the previous <dstdir> is removed just
# before the final rename; the staged copy is always complete before it is
# exposed and re-runs are idempotent (INFRA-054t).
define atomic-install-dir
rm -rf $(2).tmp.$$$$ && cp -aL $(1) $(2).tmp.$$$$ && rm -rf $(2) && mv -f $(2).tmp.$$$$ $(2)
endef

# clang builtin (resource-dir) headers — INFRA-054t / ISS-174.
#
# Source: the `lib/clang/<ver>/include` tree emitted by the clang build (upstream
# `clang/lib/Headers/**` — freestanding headers such as stddef.h/stdint.h/
# stdbool.h/stdarg.h/limits.h/float.h).  A clang binary resolves its resource dir
# from its own prefix as `$(HOST_TOOLCHAIN_DIR)/lib/clang/<ver>`, so that dir must
# contain a real `include/` tree or every `#include <stddef.h>` fails with
# "file not found".
#
# <ver> is probed *live* from the build tree (never hardcoded): it is the same
# version the just-built clang reports via `-print-resource-dir`, so the staged
# dir lines up with what the installed clang looks for.
#
# The whole clang builtin `include/` tree is staged (these are the compiler's own
# freestanding headers — no target libc/OS/syscall header is introduced).  The
# resource-dir `lib/` gets exactly one entry: the DADAO compiler-rt builtins
# archive (INFRA-079t below), which the driver links itself.  These headers and
# that archive belong to the *host* compiler (D3), not to the target sysroot
# (D5) — ADR-0016 D3/D5/D11 scope is unchanged.
CLANG_RESOURCE_VER := $(shell ls -1 $(LLVM_BUILD)/lib/clang 2>/dev/null | head -n1)
CLANG_HEADERS_SRC  = $(LLVM_BUILD)/lib/clang/$(CLANG_RESOURCE_VER)/include
CLANG_RESOURCE_DIR = $(HOST_TOOLCHAIN_DIR)/lib/clang/$(CLANG_RESOURCE_VER)

# DADAO compiler-rt builtins (INFRA-079t / ADR-0027 D5): the independent
# builtins archive is produced by the compiler-rt standalone project into its
# per-target runtime dir (LLVM_ENABLE_PER_TARGET_RUNTIME_DIR=ON).  It is
# installed into the clang resource dir at exactly the path the driver reports
# for `-rtlib=compiler-rt -print-libgcc-file-name`; that relative path is
# probed live from the build-tree clang (never hardcoded), so the installed
# archive and the driver lookup cannot drift apart.
# Deliberately recursively expanded (`=`): the probe must run when the recipe
# runs, i.e. *after* build-mc has produced bin/clang, not at parse time (a clean
# checkout has neither the clang binary nor the archive yet).
COMPILER_RT_BUILD     ?= .work/build/compiler-rt-builtins
# ISS-293: the *source* of the install copy is `<build dir>/<the path the driver
# reports>`, not "the first archive matching a wildcard" -- the build tree also
# holds a retired narrow-scope archive under lib/linux/ (INFRA-079t), and a
# wildcard that picked it would install the wrong library.  Both sides of the
# copy then provably share one relative path.
#
# ISS-301: ONE probe, ONE path.  `-print-libgcc-file-name` is the only
# authoritative answer to "which archive does the build-tree clang link", and it
# names `<llvm-build>/lib/clang/<ver>/<resource-rel>`.  The previous derivation
# dropped the `clang/<ver>/` half, so `build-builtins` re-staged into
# `<llvm-build>/<resource-rel>` -- a directory no consumer reads -- while the
# copy the clang actually links stayed stale (and the freshness gate went red).
# Every consumer below (build-builtins stage target, install-host destination,
# and tools/infra/check_builtins_freshness.py, which splits the same probe) now
# derives from this one variable, so the three copies cannot drift apart again.
# The probe answers with an absolute path; it is reduced to the part below
# `lib/clang/` (`<ver>/lib/<triple>/libclang_rt.builtins.a`), which is byte-for-
# byte the same in the build tree and in the install root.
BUILTINS_RESOURCE_PATH = $(shell $(LLVM_BUILD)/bin/clang --target=dadao-unknown-elf -rtlib=compiler-rt -print-libgcc-file-name 2>/dev/null | sed -e 's|^.*/lib/clang/||')
BUILTINS_RESOURCE_VER  = $(firstword $(subst /, ,$(BUILTINS_RESOURCE_PATH)))
# Same file in the build tree (what bin/clang links) and in the install root
# (what install-host must refresh) -- one shape, two prefixes.
BUILTINS_BUILD_DST     = $(if $(BUILTINS_RESOURCE_PATH),$(LLVM_BUILD)/lib/clang/$(BUILTINS_RESOURCE_PATH))
BUILTINS_ARCHIVE_DST   = $(if $(BUILTINS_RESOURCE_PATH),$(HOST_TOOLCHAIN_DIR)/lib/clang/$(BUILTINS_RESOURCE_PATH))
# compiler-rt's own tree mirrors the resource dir *below* `lib/` (no `<ver>`):
# `<build dir>/lib/<triple>/libclang_rt.builtins.a`.
BUILTINS_BUILD_REL     = $(patsubst $(BUILTINS_RESOURCE_VER)/%,%,$(BUILTINS_RESOURCE_PATH))
BUILTINS_ARCHIVE_SRC   = $(if $(BUILTINS_BUILD_REL),$(COMPILER_RT_BUILD)/$(BUILTINS_BUILD_REL))

# build-builtins (ISS-293): rebuild the compiler-rt builtins with the *current*
# build-tree clang and re-stage the archive into that clang's resource dir.
#
# Why a clean rebuild: nothing in ninja tracks the compiler *binary* as an
# input of these objects, so after a codegen change (LLVM-116t moved `shl`) an
# incremental `ninja` reports "no work to do" and the archive keeps the retired
# encoding -- the new qemu then decodes it as undefined and the guest dies with
# SIGILL.  `-t clean` forces the whole target set through the current compiler
# (a few seconds; 148 tiny sources).
#
# Why the staging copy: `.work/build/llvm/bin/clang` links the archive from its
# own resource dir (`-print-libgcc-file-name`), and nothing else ever refreshed
# that copy -- it is a third consumer beside the build product and the install
# root.  `make install-host` stages the same archive into the install root.
#
# Why a producer sidecar (INFRA-101t): the gate used to order mtimes (archive
# >= clang).  A deterministic relink after `touch one .td` moves clang's mtime
# without changing its bytes, so the proxy demanded a full builtins rebuild
# (LLVM-122t).  `tools/infra/toolchain_id.py --write` records the clang/ld.lld
# **content identity** (GNU build-id) + the archive sha256 next to the build
# product; `check-builtins-freshness` compares identity, not time.
#
# It depends on build-mc so `make -j install-host` cannot run the rebuild
# before the compiler exists (the recipe probe would fail); with the tree
# already built that prerequisite is a no-op.
_locked-build-builtins: manifest-check build-mc
	@$(call component-enabled,llvm-project) || { \
	  echo "build-builtins: component 'llvm-project' is not enabled / commit pending (manifests/components.lock.toml); refusing to fake success"; \
	  exit 1; \
	}
	@test -f $(LLVM_BUILD)/bin/clang || { echo "build-builtins: ERROR: $(LLVM_BUILD)/bin/clang not found -- run 'make build-mc' first"; exit 1; }
	@test -f $(LLVM_BUILD)/bin/ld.lld || { echo "build-builtins: ERROR: $(LLVM_BUILD)/bin/ld.lld not found -- run 'make build-lld' first (the producer sidecar records clang and ld.lld content identity)"; exit 1; }
	@test -f $(COMPILER_RT_BUILD)/build.ninja || { echo "build-builtins: ERROR: no configured compiler-rt build tree at $(COMPILER_RT_BUILD) -- configure it once (INFRA-079t) first"; exit 1; }
	@test -n "$(BUILTINS_BUILD_DST)" || { echo "build-builtins: ERROR: cannot resolve the builtins path from '$(LLVM_BUILD)/bin/clang --target=dadao-unknown-elf -rtlib=compiler-rt -print-libgcc-file-name'"; exit 1; }
	ninja -C $(COMPILER_RT_BUILD) -t clean
	ninja -j$(JOBS) -C $(COMPILER_RT_BUILD) builtins
	@test -f $(BUILTINS_ARCHIVE_SRC) || { echo "build-builtins: ERROR: archive not produced at $(BUILTINS_ARCHIVE_SRC)"; exit 1; }
	@mkdir -p $(dir $(BUILTINS_BUILD_DST))
	@$(call atomic-install,$(BUILTINS_ARCHIVE_SRC),$(BUILTINS_BUILD_DST))
	@$(PYTHON) tools/infra/toolchain_id.py --write $(COMPILER_RT_BUILD)/.dadao-builtins-toolchain --tool-dir $(LLVM_BUILD)/bin --archive $(BUILTINS_ARCHIVE_SRC)
	@echo "build-builtins: PASS"

# clang++ (INFRA-056t): the C++ driver is the *same binary* as the C driver
# (upstream bin/clang++ is itself a symlink to clang-NN), so install it as a
# relative symlink to the already-installed `clang` — mirroring the ld.lld -> lld
# precedent.  Deliberately NOT added to $(HOST_LLVM_TOOLS): the clang binary
# is ~4 GB, so atomic-install would copy it a second time.  Being relative and
# resolving to the installed `clang`, it is zero-copy and same-source/same-commit.
# Same reasoning for llvm-readelf (INFRA-098t): upstream builds it as a symlink
# to llvm-readobj, so it must not be copied as a 319 MB standalone file.
# All three aliases are enumerated in $(HOST_LLVM_TOOL_SYMLINKS) (one variable,
# consumed by the recipe below and by tools/infra/check_install_tools.py).
_locked-install-host: install-cfx-aliases build-mc build-lld build-qemu build-builtins
	@mkdir -p $(HOST_TOOLCHAIN_BIN) $(HOST_TOOLS_BIN)
	@for t in $(HOST_LLVM_TOOLS); do \
	  $(call atomic-install,$(LLVM_BUILD)/bin/$$t,$(HOST_TOOLCHAIN_BIN)/$$t) || exit 1; \
	done
	@$(call atomic-install,$(LLVM_BUILD)/bin/lld,$(HOST_TOOLCHAIN_BIN)/lld)
	@for s in $(HOST_LLVM_TOOL_SYMLINKS); do \
	  ln -sfn $${s#*:} $(HOST_TOOLCHAIN_BIN)/$${s%%:*} || exit 1; \
	done
	@$(call atomic-install,$(LLVM_BUILD)/bin/lli,$(HOST_TOOLS_BIN)/lli)
	@$(call atomic-install,$(QEMU_BUILD)/qemu-system-dadao,$(HOST_TOOLCHAIN_BIN)/qemu-system-dadao)
	@$(call atomic-install,$(QEMU_BUILD)/qemu-dadao,$(HOST_TOOLCHAIN_BIN)/qemu-dadao)
	@rm -rf $(HOST_LIT_DIR)
	@mkdir -p $(HOST_LIT_DIR)
	@cp -a $(LLVM_SRC)/utils/lit/lit $(HOST_LIT_DIR)/lit
	@rm -rf $(HOST_LIT_DIR)/lit/__pycache__
	@printf '%s\n' '#!/usr/bin/env python3' '# DADAO install-root lit launcher (INFRA-047t): the lit package is installed in ../share/lit' 'import os' 'import sys' '' '_prefix = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))' 'sys.path.insert(0, os.path.join(_prefix, "share", "lit"))' '' 'from lit.main import main' '' 'if __name__ == "__main__":' '    main()' > $(HOST_TOOLCHAIN_BIN)/llvm-lit
	@chmod +x $(HOST_TOOLCHAIN_BIN)/llvm-lit
	@test -d $(CLANG_HEADERS_SRC) || { echo "install-host: ERROR: clang builtin headers not found at $(CLANG_HEADERS_SRC) — build tree incomplete (run 'make build-mc')"; exit 1; }
	@mkdir -p $(CLANG_RESOURCE_DIR)
	@$(call atomic-install-dir,$(CLANG_HEADERS_SRC),$(CLANG_RESOURCE_DIR)/include)
	@test -f $(BUILTINS_ARCHIVE_SRC) || { echo "install-host: ERROR: compiler-rt builtins archive not found under $(COMPILER_RT_BUILD)/lib/ — build the compiler-rt standalone 'builtins' target first (INFRA-079t)"; exit 1; }
	@case "$(BUILTINS_BUILD_REL)" in lib/*) ;; *) echo "install-host: ERROR: cannot resolve the builtins install path from '$(LLVM_BUILD)/bin/clang --target=dadao-unknown-elf -rtlib=compiler-rt -print-libgcc-file-name' (got '$(BUILTINS_RESOURCE_PATH)')"; exit 1 ;; esac
	@mkdir -p $(dir $(BUILTINS_ARCHIVE_DST))
	@$(call atomic-install,$(BUILTINS_ARCHIVE_SRC),$(BUILTINS_ARCHIVE_DST))
	@$(PYTHON) tools/infra/check_install_tools.py
	@$(PYTHON) tools/llvm/check_cfx_alias_install.py
	@mkdir -p $(TARGET_SYSROOT_DIR)/include $(TARGET_SYSROOT_DIR)/lib
	@printf '%s\n' '# DADAO target sysroot (dadao-unknown-elf)' '' 'Layout per ADR-0016 D5 (.tao/adr/adr-0016-dadao-install-layout.md):' '' '- include/ — target C headers (populated when a target libc/toolchain lands)' '- lib/     — target libraries' '' 'Placeholder only: there is no header/library consumer yet, so no content is' 'fabricated here. Consumers must resolve this path from' 'manifests/install-dirs.lock.toml via tools/infra/paths.py' '(target_sysroot_dir()), never hardcode it.' > $(TARGET_SYSROOT_DIR)/README.md
	@echo "install-host: PASS"

# install-cfx-aliases (LLVM-135t): stage the data-only cfx alias table into the
# build tree and the install root.  Deliberately **only copies** -- after an
# alias rename/renumber this is the whole update (no build-mc, no relink); the
# next llvm-mc/llvm-objdump run picks the new names up.  (`install-cfx-aliases`
# itself is the gate-locked wrapper; this is its body.)
_locked-install-cfx-aliases:
	@test -f $(CFX_ALIAS_TABLE_SRC) || { echo "install-cfx-aliases: ERROR: missing $(CFX_ALIAS_TABLE_SRC) -- regenerate with 'python3 tools/llvm/gen_cfx_alias_table.py'"; exit 1; }
	@mkdir -p $(dir $(CFX_ALIAS_TABLE_BUILD)) $(dir $(CFX_ALIAS_TABLE_INSTALL))
	@$(call atomic-install,$(CFX_ALIAS_TABLE_SRC),$(CFX_ALIAS_TABLE_BUILD))
	@$(call atomic-install,$(CFX_ALIAS_TABLE_SRC),$(CFX_ALIAS_TABLE_INSTALL))
	@echo "install-cfx-aliases: PASS"

# build-bootrom (QEMU-047t / ADR-0020 D12): assemble and link the SEE bootrom
# firmware with the project toolchain (llvm-mc + ld.lld + tests/shared/bootrom/
# bootrom.lds; ADR-0003 / ADR-0019 / contract-elf §6.1.2) and emit the flat
# `-bios` image, plus the sample user application loaded by `-kernel`
# (ADR-0004 D2.3 path B: raw-bin dual image).  Tools come from the install root
# (ADR-0016 D9); run `make install-host` first.  Outputs live under the SDK
# test-artifacts root (ADR-0016 D6, resolved via paths.py):
#   $(BOOTROM_DIR)/{bootrom.o,bootrom.elf,bootrom.bin,bootrom_app.o,bootrom_app.bin}
BOOTROM_DIR = $(TEST_ARTIFACTS_DIR)/bootrom
_locked-build-bootrom:
	@test -x $(LLVM_MC_BIN) || { echo "build-bootrom: ERROR: $(LLVM_MC_BIN) not found — run 'make install-host' first"; exit 1; }
	@test -x $(LLD_BIN) || { echo "build-bootrom: ERROR: $(LLD_BIN) not found — run 'make install-host' first"; exit 1; }
	@test -x $(LLVM_OBJCOPY_BIN) || { echo "build-bootrom: ERROR: $(LLVM_OBJCOPY_BIN) not found — run 'make install-host' first"; exit 1; }
	@mkdir -p $(BOOTROM_DIR)
	$(LLVM_MC_BIN) --triple=dadao-unknown-elf -filetype=obj tests/shared/bootrom/bootrom.S -o $(BOOTROM_DIR)/bootrom.o
	$(LLD_BIN) -T tests/shared/bootrom/bootrom.lds $(BOOTROM_DIR)/bootrom.o -o $(BOOTROM_DIR)/bootrom.elf
	$(LLVM_OBJCOPY_BIN) -O binary $(BOOTROM_DIR)/bootrom.elf $(BOOTROM_DIR)/bootrom.bin
	$(LLVM_MC_BIN) --triple=dadao-unknown-elf -filetype=obj tests/shared/bootrom/bootrom_app.S -o $(BOOTROM_DIR)/bootrom_app.o
	$(LLVM_OBJCOPY_BIN) -O binary --only-section=.text $(BOOTROM_DIR)/bootrom_app.o $(BOOTROM_DIR)/bootrom_app.bin
	@echo "build-bootrom: PASS (outputs under $(BOOTROM_DIR))"

# build-picolibc (INFRA-057t): build the DADAO port of picolibc with Meson and
# install it into the target sysroot (headers under $(TARGET_SYSROOT_DIR)/
# include, libraries under .../lib).  The cross file, the machine directory and
# the semihosting syscall stubs live in the component patch set
# (components/picolibc/patches/**); run 'make fetch apply-series' first.
# The target is idempotent (Meson reconfigure + incremental Ninja + install).
# Requires the install-root clang (run 'make install-host' first).
_locked-build-picolibc:
	@test -x $(HOST_TOOLCHAIN_BIN)/clang || { echo "build-picolibc: ERROR: $(HOST_TOOLCHAIN_BIN)/clang not found — run 'make install-host' first"; exit 1; }
	@$(PYTHON) tools/infra/build_picolibc.py --jobs $(JOBS)

# test-picolibc-smoke (INFRA-057t): minimal end-to-end check — a printf("hi")
# program is compiled against the installed picolibc, linked with the project
# crt0/linker script and run under QEMU via semihosting; the guest must print
# "hi" and exit 0.  Needs 'make build-picolibc' + 'make install-host' first.
_locked-test-picolibc-smoke: build-picolibc
	@$(PYTHON) tools/infra/test_picolibc_smoke.py

# check-picolibc-tests (TESTCASES-042t, L2): the picolibc upstream self-test
# representative set — one test per Meson suite, mechanically derived by the
# harness (no hand-picked list).  The harness configures the picolibc Meson test
# build (for the authoritative test inventory), then compiles/links/runs each
# test under qemu-system-dadao -machine dadao-m1 + semihosting.  Fails if any
# representative reports a genuine test failure (fail=0); backend/library gaps
# are reported separately as `blocked`, never as silent skips.
_locked-check-picolibc-tests: build-picolibc
	@$(PYTHON) tools/testcases/picolibc_tests.py --stage fast --jobs $(JOBS)

# check-picolibc-tests-full (TESTCASES-042t): the full picolibc self-test set
# (opt-in; L3-like — hundreds of compile/link/QEMU runs, several minutes).
_locked-check-picolibc-tests-full: build-picolibc
	@$(PYTHON) tools/testcases/picolibc_tests.py --stage full --jobs $(JOBS)

# check-rnd-probe (TESTCASES-060t): ftrnd/fornd roundToIntegral integration --
# 6-mode x value matrix (bit patterns), rf0[33:32] mode sensitivity, flag rules
# (static never sets NX / 0x20 sets NX iff inexact / sNaN sets NV) and the
# C-level floor/ceil/trunc/round/nearbyint mapping.  Expectations come from
# tools/testcases/oracle_rnd.py (exact Fraction arithmetic from spec/, never
# from QEMU).  Two optimisation levels, ~1 s each => L2 (Process-07 §3 rule 2).
_locked-check-rnd-probe: install-host build-musl
	@mkdir -p .work/log/testcases
	@$(PYTHON) tools/testcases/run_rnd_probe.py --opt O0 \
	    --json-out .work/log/testcases/TESTCASES-060t-O0.json \
	    > .work/log/testcases/TESTCASES-060t-O0.log 2>&1; \
	  rc=$$?; \
	  tail -2 .work/log/testcases/TESTCASES-060t-O0.log; \
	  if [ $$rc -ne 0 ]; then echo "check-rnd-probe: FAIL (-O0 rc=$$rc)"; exit $$rc; fi
	@$(PYTHON) tools/testcases/run_rnd_probe.py --opt O2 \
	    --json-out .work/log/testcases/TESTCASES-060t-O2.json \
	    > .work/log/testcases/TESTCASES-060t-O2.log 2>&1; \
	  rc=$$?; \
	  tail -2 .work/log/testcases/TESTCASES-060t-O2.log; \
	  if [ $$rc -ne 0 ]; then echo "check-rnd-probe: FAIL (-O2 rc=$$rc)"; exit $$rc; fi
	@echo "check-rnd-probe: PASS (O0 + O2)"

# check-minmax-probe (TESTCASES-059t): ftmin/ftmax/fomin/fomax integration --
# NaN/±0 matrix (value + rf0[4:0] as two assertions), C23 fminimum/fmaximum
# expansion (canonical NaN, no libcall), clamp / 4x4 / integer-control forms.
# Expectations come from tools/testcases/oracle_minmax.py (exact Fraction
# arithmetic from spec/SimRISC-07 §2.4, never from QEMU/LLVM).  Two
# optimisation levels, ~1 s each => L2 (Process-07 §3 rule 2).
_locked-check-minmax-probe: install-host build-musl
	@mkdir -p .work/log/testcases
	@$(PYTHON) tools/testcases/run_minmax_probe.py --opt O0 \
	    --json-out .work/log/testcases/TESTCASES-059t-O0.json \
	    > .work/log/testcases/TESTCASES-059t-O0.log 2>&1; \
	  rc=$$?; \
	  tail -2 .work/log/testcases/TESTCASES-059t-O0.log; \
	  if [ $$rc -ne 0 ]; then echo "check-minmax-probe: FAIL (-O0 rc=$$rc)"; exit $$rc; fi
	@$(PYTHON) tools/testcases/run_minmax_probe.py --opt O2 \
	    --json-out .work/log/testcases/TESTCASES-059t-O2.json \
	    > .work/log/testcases/TESTCASES-059t-O2.log 2>&1; \
	  rc=$$?; \
	  tail -2 .work/log/testcases/TESTCASES-059t-O2.log; \
	  if [ $$rc -ne 0 ]; then echo "check-minmax-probe: FAIL (-O2 rc=$$rc)"; exit $$rc; fi
	@echo "check-minmax-probe: PASS (O0 + O2)"

# check-fma-probe (TESTCASES-058t): ftfma/fofma integration -- single-rounding
# discriminators (C path + asm path + the two-step value, all three judged on
# value and rf0[4:0]), NaN/Inf/±0, four rounding directions, overflow /
# underflow, dot products (16/64/256, exact-fma and contracted `acc += a*b`),
# 4x4 GEMM and Horner (every intermediate accumulator hashed).  Expectations
# come from tools/testcases/oracle_fma.py (exact Fraction arithmetic + ONE
# rounding from spec/SimRISC-07 §2.5, never from QEMU/softfloat/host fma).
# Also asserts the per-symbol instruction mix (fused kernels: one fofma/ftfma,
# no fomul/foadd/rf2rf) and that no fma libcall reaches the object/image.
# Two optimisation levels, measured ~1 s => L2 (Process-07 §3 rule 2).
_locked-check-fma-probe: install-host build-musl
	@mkdir -p .work/log/testcases
	@$(PYTHON) tools/testcases/run_fma_probe.py --opt O0 \
	    --json-out .work/log/testcases/TESTCASES-058t-O0.json \
	    > .work/log/testcases/TESTCASES-058t-O0.log 2>&1; \
	  rc=$$?; \
	  tail -2 .work/log/testcases/TESTCASES-058t-O0.log; \
	  if [ $$rc -ne 0 ]; then echo "check-fma-probe: FAIL (-O0 rc=$$rc)"; exit $$rc; fi
	@$(PYTHON) tools/testcases/run_fma_probe.py --opt O2 \
	    --json-out .work/log/testcases/TESTCASES-058t-O2.json \
	    > .work/log/testcases/TESTCASES-058t-O2.log 2>&1; \
	  rc=$$?; \
	  tail -2 .work/log/testcases/TESTCASES-058t-O2.log; \
	  if [ $$rc -ne 0 ]; then echo "check-fma-probe: FAIL (-O2 rc=$$rc)"; exit $$rc; fi
	@echo "check-fma-probe: PASS (O0 + O2)"

# check-clmul-probe (TESTCASES-057t): clmul.o integration -- instruction level
# (boundary cells + 64 seeded random cells, all three compiler-visible exits:
# generic `llvm.clmul` low half, `llvm.dadao.clmul.hi` high half, the
# `__builtin_dadao_clmul` i128 composite, plus the `{lo,hi}` pair intrinsic),
# GHASH (GCM specification Appendix B test cases 1-4 with their published
# intermediates, zero H, all-ones H, single/two-block chains, AAD + partial
# blocks) and CRC-32C through a clmul folding kernel + GF(2) Barrett reduction
# (lengths 0/1/7/8/9/15/16/17/63/64/65/1000, `"123456789" -> 0xE3069283`).
# Expectations come from tools/testcases/oracle_clmul.py: GF(2) polynomial
# arithmetic in plain Python integers + the published standards' vectors, never
# from QEMU/LLVM.  Two optimisation levels, measured ~1 s => L2 (Process-07 §3
# rule 2).
_locked-check-clmul-probe: install-host build-musl
	@mkdir -p .work/log/testcases
	@$(PYTHON) tools/testcases/run_clmul_probe.py --opt O0 \
	    --json-out .work/log/testcases/TESTCASES-057t-O0.json \
	    > .work/log/testcases/TESTCASES-057t-O0.log 2>&1; \
	  rc=$$?; \
	  tail -2 .work/log/testcases/TESTCASES-057t-O0.log; \
	  if [ $$rc -ne 0 ]; then echo "check-clmul-probe: FAIL (-O0 rc=$$rc)"; exit $$rc; fi
	@$(PYTHON) tools/testcases/run_clmul_probe.py --opt O2 \
	    --json-out .work/log/testcases/TESTCASES-057t-O2.json \
	    > .work/log/testcases/TESTCASES-057t-O2.log 2>&1; \
	  rc=$$?; \
	  tail -2 .work/log/testcases/TESTCASES-057t-O2.log; \
	  if [ $$rc -ne 0 ]; then echo "check-clmul-probe: FAIL (-O2 rc=$$rc)"; exit $$rc; fi
	@echo "check-clmul-probe: PASS (O0 + O2)"

# check-testcases-suites (TESTCASES-045t stage 1): drive the two upstream
# *reference* suites -- libc-test and llvm-test-suite -- through the static musl
# flow (compile -> ld.lld -T dadao.lds -> flat image -> qemu-system-dadao
# -machine dadao-m1, "path B").  Upstream's own harnesses are unusable here
# (libc-test's runtest.exe needs fork/waitpid/signals; llvm-test-suite's
# CMake/lit driver assumes a hosted OS), so tools/testcases/run_suite.py drives
# the corpora directly and classifies every case live.
#
# OPT-IN LEVEL: this target is deliberately NOT listed in L1/L2/L3.  The stage-1
# case list is a *curated* stratified subset (each entry records its tier and
# why), and docs/Process-07 §3 requires an L2 "representative set" to be
# *mechanically* derived; assigning a curated list to L2 would violate that.  It
# stays an on-demand target ("按需" level) until stage 3 replaces the curation
# with a mechanical derivation and the cost/FAIL story has been measured.
#
# Exit status follows tools/testcases/run_suite.py: non-zero on any `fail` or
# `timeout` (a genuine wrong result / hang).  `enosys`, `compile-error` and
# `unsupported` are counted and listed, never silently skipped, and do not turn
# the target red -- they are the documented state of an unfinished port.
_locked-check-testcases-suites:
	@$(PYTHON) tools/testcases/run_suite.py --stage fast \
		--json-out .work/log/testcases/runs/fast.json

# check-testcases-suites-full (TESTCASES-045t): every enumerable C case with
# main() in both suites (upstream `External/`, C++/Fortran/ObjC sources and
# helper TUs without main() are counted as `unsupported` with their reason).
# Opt-in, L3-like: hundreds of compile/link/QEMU runs; `--timeout` is raised for
# the benchmarks whose default problem size exceeds the fast-stage budget.
_locked-check-testcases-suites-full:
	@$(PYTHON) tools/testcases/run_suite.py --stage full --timeout 300 \
		--json-out .work/log/testcases/runs/full.json

# ── tset smoke（TESTCASES-075t，L2）──────────────────────────────────────────
# 三个 user-mode 上游套件驱动已迁 `tools/testcases/tset/<suite>/`（旧路径 = 薄
# wrapper，命令行等价）；代表集由各 suite 的 `run_smoke.py` **机械派生**
# （libc-test: 每顶层语料类别取源码最小用例；llvm-ts: 每棵树取源码最小用例；
# embench: 全量 benchmark，任务口径 ~1 min），计数现场统计、不写死。
# 运行目录/三件套仍按 `docs/Process-08`（`<test-artifacts>/<suite>-user/...`）。
# JSON 落 `$(TSET_GATE_JSON_DIR)`（易失汇总，非运行目录；权威记录仍是各驱动在
# `<test-artifacts>/<suite>-user/<UTC>-.../` 下的三件套，A2 只查时间戳目录）。
TSET_GATE_JSON_DIR = .work/tests/gates

# check-tset-libc-smoke: libc-test 代表集（每顶层类别 1 例，static）。
_locked-check-tset-libc-smoke:
	@mkdir -p .work/log/testcases $(TSET_GATE_JSON_DIR)
	@test -x $(HOST_TOOLCHAIN_BIN)/clang || { echo "check-tset-libc-smoke: ERROR: $(HOST_TOOLCHAIN_BIN)/clang not found — run 'make install-host'"; exit 1; }
	@test -f .work/source/musl/lib/libc.a || { echo "check-tset-libc-smoke: ERROR: .work/source/musl/lib/libc.a not found — run 'make build-musl'"; exit 1; }
	@$(PYTHON) tools/testcases/tset/libc-test/run_smoke.py --link-mode static \
	    --json-out $(TSET_GATE_JSON_DIR)/check-tset-libc-smoke.json \
	    > .work/log/testcases/check-tset-libc-smoke.log 2>&1; \
	  rc=$$?; \
	  grep -E "^(check-tset-libc-smoke|  (类别数|结构断言)|结果:)" .work/log/testcases/check-tset-libc-smoke.log | tail -6; \
	  if [ $$rc -ne 0 ]; then echo "check-tset-libc-smoke: FAIL (rc=$$rc; log .work/log/testcases/check-tset-libc-smoke.log)"; exit $$rc; fi; \
	  echo "check-tset-libc-smoke: PASS"

# check-tset-llvm-smoke: llvm-test-suite 代表集（每棵树 1 例，static）。
_locked-check-tset-llvm-smoke:
	@mkdir -p .work/log/testcases $(TSET_GATE_JSON_DIR)
	@test -x $(HOST_TOOLCHAIN_BIN)/clang || { echo "check-tset-llvm-smoke: ERROR: $(HOST_TOOLCHAIN_BIN)/clang not found — run 'make install-host'"; exit 1; }
	@test -f .work/source/musl/lib/libc.a || { echo "check-tset-llvm-smoke: ERROR: .work/source/musl/lib/libc.a not found — run 'make build-musl'"; exit 1; }
	@test -d .work/source/llvm-test-suite || { echo "check-tset-llvm-smoke: ERROR: .work/source/llvm-test-suite not found — run 'make fetch'"; exit 1; }
	@$(PYTHON) tools/testcases/tset/llvm-ts/run_smoke.py --link-mode static --jobs $(JOBS) \
	    --json-out $(TSET_GATE_JSON_DIR)/check-tset-llvm-smoke.json \
	    > .work/log/testcases/check-tset-llvm-smoke.log 2>&1; \
	  rc=$$?; \
	  grep -E "^(check-tset-llvm-smoke|  (树数|结构断言)|结果:)" .work/log/testcases/check-tset-llvm-smoke.log | tail -6; \
	  if [ $$rc -ne 0 ]; then echo "check-tset-llvm-smoke: FAIL (rc=$$rc; log .work/log/testcases/check-tset-llvm-smoke.log)"; exit $$rc; fi; \
	  echo "check-tset-llvm-smoke: PASS"

# check-tset-embench-smoke: Embench-IoT 全量 benchmark（默认 -O0/-O2，static）。
_locked-check-tset-embench-smoke:
	@mkdir -p .work/log/testcases $(TSET_GATE_JSON_DIR)
	@test -x $(HOST_TOOLCHAIN_BIN)/clang || { echo "check-tset-embench-smoke: ERROR: $(HOST_TOOLCHAIN_BIN)/clang not found — run 'make install-host'"; exit 1; }
	@test -f .work/source/musl/lib/libc.a || { echo "check-tset-embench-smoke: ERROR: .work/source/musl/lib/libc.a not found — run 'make build-musl'"; exit 1; }
	@test -d .work/source/embench-iot || { echo "check-tset-embench-smoke: ERROR: .work/source/embench-iot not found — run 'make fetch'"; exit 1; }
	@$(PYTHON) tools/testcases/tset/embench/run_embench_user_suite.py --link-mode static \
	    --json-out $(TSET_GATE_JSON_DIR)/check-tset-embench-smoke.json \
	    > .work/log/testcases/check-tset-embench-smoke.log 2>&1; \
	  rc=$$?; \
	  tail -3 .work/log/testcases/check-tset-embench-smoke.log; \
	  if [ $$rc -ne 0 ]; then echo "check-tset-embench-smoke: FAIL (rc=$$rc; log .work/log/testcases/check-tset-embench-smoke.log)"; exit $$rc; fi; \
	  echo "check-tset-embench-smoke: PASS"

# ── tset full（夜跑成员；TESTCASES-076t，P6）────────────────────────────────────
# 「full」= 该套件的**全部可枚举用例 × 两种链接档**（static / dynamic），**只在**
# `make check-night` 里跑；不进 L2/L3（否则每次 check-full 变成夜跑）。
# 三个驱动的 `--link-mode` 口径：libc-test / embench 只接受 static|dynamic，llvm-ts
# 另有 both —— 这里**逐档各跑一次**，三套件同一口径（日志、rc 逐档记录）。
TSET_FULL_MODES ?= static dynamic

_locked-check-tset-libc-full:
	@test -n "$(TSET_FULL_MODES)" || { echo "check-tset-libc-full: ERROR: TSET_FULL_MODES 为空（禁 vacuous 绿）"; exit 1; }
	@mkdir -p .work/log/testcases $(TSET_GATE_JSON_DIR)
	@test -x $(HOST_TOOLCHAIN_BIN)/clang || { echo "check-tset-libc-full: ERROR: $(HOST_TOOLCHAIN_BIN)/clang not found — run 'make install-host'"; exit 1; }
	@test -f .work/source/musl/lib/libc.a || { echo "check-tset-libc-full: ERROR: .work/source/musl/lib/libc.a not found — run 'make build-musl'"; exit 1; }
	@fail=0; for m in $(TSET_FULL_MODES); do \
	  echo "check-tset-libc-full: [$$m] full suite"; \
	  $(PYTHON) tools/testcases/tset/libc-test/run_libc_test_user_suite.py --link-mode $$m \
	    --json-out $(TSET_GATE_JSON_DIR)/check-tset-libc-full-$$m.json \
	    > .work/log/testcases/check-tset-libc-full-$$m.log 2>&1; \
	  rc=$$?; tail -3 .work/log/testcases/check-tset-libc-full-$$m.log; \
	  if [ $$rc -ne 0 ]; then echo "check-tset-libc-full: FAIL ($$m rc=$$rc)"; fail=1; fi; \
	done; if [ $$fail -ne 0 ]; then exit 1; fi; echo "check-tset-libc-full: PASS"

_locked-check-tset-llvm-full:
	@test -n "$(TSET_FULL_MODES)" || { echo "check-tset-llvm-full: ERROR: TSET_FULL_MODES 为空（禁 vacuous 绿）"; exit 1; }
	@mkdir -p .work/log/testcases $(TSET_GATE_JSON_DIR)
	@test -x $(HOST_TOOLCHAIN_BIN)/clang || { echo "check-tset-llvm-full: ERROR: $(HOST_TOOLCHAIN_BIN)/clang not found — run 'make install-host'"; exit 1; }
	@test -f .work/source/musl/lib/libc.a || { echo "check-tset-llvm-full: ERROR: .work/source/musl/lib/libc.a not found — run 'make build-musl'"; exit 1; }
	@test -d .work/source/llvm-test-suite || { echo "check-tset-llvm-full: ERROR: .work/source/llvm-test-suite not found — run 'make fetch'"; exit 1; }
	@fail=0; for m in $(TSET_FULL_MODES); do \
	  echo "check-tset-llvm-full: [$$m] full suite"; \
	  $(PYTHON) tools/testcases/tset/llvm-ts/run_llvm_ts_user.py --link-mode $$m --jobs $(JOBS) \
	    --json-out $(TSET_GATE_JSON_DIR)/check-tset-llvm-full-$$m.json \
	    > .work/log/testcases/check-tset-llvm-full-$$m.log 2>&1; \
	  rc=$$?; tail -3 .work/log/testcases/check-tset-llvm-full-$$m.log; \
	  if [ $$rc -ne 0 ]; then echo "check-tset-llvm-full: FAIL ($$m rc=$$rc)"; fail=1; fi; \
	done; if [ $$fail -ne 0 ]; then exit 1; fi; echo "check-tset-llvm-full: PASS"

_locked-check-tset-embench-full:
	@test -n "$(TSET_FULL_MODES)" || { echo "check-tset-embench-full: ERROR: TSET_FULL_MODES 为空（禁 vacuous 绿）"; exit 1; }
	@mkdir -p .work/log/testcases $(TSET_GATE_JSON_DIR)
	@test -x $(HOST_TOOLCHAIN_BIN)/clang || { echo "check-tset-embench-full: ERROR: $(HOST_TOOLCHAIN_BIN)/clang not found — run 'make install-host'"; exit 1; }
	@test -f .work/source/musl/lib/libc.a || { echo "check-tset-embench-full: ERROR: .work/source/musl/lib/libc.a not found — run 'make build-musl'"; exit 1; }
	@test -d .work/source/embench-iot || { echo "check-tset-embench-full: ERROR: .work/source/embench-iot not found — run 'make fetch'"; exit 1; }
	@fail=0; for m in $(TSET_FULL_MODES); do \
	  echo "check-tset-embench-full: [$$m] full suite"; \
	  $(PYTHON) tools/testcases/tset/embench/run_embench_user_suite.py --link-mode $$m \
	    --json-out $(TSET_GATE_JSON_DIR)/check-tset-embench-full-$$m.json \
	    > .work/log/testcases/check-tset-embench-full-$$m.log 2>&1; \
	  rc=$$?; tail -3 .work/log/testcases/check-tset-embench-full-$$m.log; \
	  if [ $$rc -ne 0 ]; then echo "check-tset-embench-full: FAIL ($$m rc=$$rc)"; fail=1; fi; \
	done; if [ $$fail -ne 0 ]; then exit 1; fi; echo "check-tset-embench-full: PASS"

# build-musl (INFRA-082t): configure and build the static musl libc for
# dadao-unknown-elf inside .work/source/musl (the DADAO port lives as a
# tree-shaped patch set, components/musl/patches/**; run 'make fetch
# apply-series' first).  P1 is the STATIC subset: --disable-shared is
# deliberate (the dynamic linker is P2, ADR-0025 D6).  Products:
# lib/libc.a + lib/crt{1,i,n}.o.  The target is idempotent (configure is
# skipped once config.mak exists and records the same mode) and, by default,
# also links and verifies a minimal static program (see
# tools/infra/build_musl.py).  Requires the install-root clang (run
# 'make install-host' first).  Stale objects are guarded: a change in the
# toolchain binaries (clang / ld.lld stamp, obj/.dadao-toolchain-stamp) or a
# tree without a stamp runs 'make clean' before building; the decision
# ("... => 'make clean'" / "... => incremental build") is printed.  Applies to
# build-musl-shared too (same script, same in-tree build directory).
_locked-build-musl:
	@test -x $(HOST_TOOLCHAIN_BIN)/clang || { echo "build-musl: ERROR: $(HOST_TOOLCHAIN_BIN)/clang not found — run 'make install-host' first"; exit 1; }
	@$(PYTHON) tools/infra/build_musl.py --jobs $(JOBS)

# build-musl-shared (INFRA-085t stage A1): the SHARED/PIC counterpart -- same
# source tree, configured *without* --disable-shared so musl links lib/libc.so
# from -fPIC objects, with -Wl,--hash-style=gnu and -Wl,-soname,libc.so pinning
# the dynamic-section shape (contract-dynlink.md §5 rulings 6/7, §6.1).  Checks
# libc.so is ET_DYN/big-endian with DT_SONAME + DT_GNU_HASH and without
# DT_HASH/DT_RELR/version sections, then installs libc.so plus the
# ld-musl-dadao.so.1 -> libc.so symlink into the target sysroot lib dir
# (ADR-0016 D5).  The static line is checked in the same run (lib/libc.a is
# built from the same non-PIC objects), so the two modes cannot drift apart.
# Stage B1 (INFRA-085t): the same run links a dynamic EXECUTABLE with the
# interpreter passed explicitly (-dynamic-linker /lib/ld-musl-dadao.so.1,
# contract-dynlink.md §6.1 / ADR-0026 D2) and checks PT_INTERP + DT_NEEDED.
# Running/loading it is P3 (qemu-user) and is not done here.
_locked-build-musl-shared:
	@test -x $(HOST_TOOLCHAIN_BIN)/clang || { echo "build-musl-shared: ERROR: $(HOST_TOOLCHAIN_BIN)/clang not found — run 'make install-host' first"; exit 1; }
	@$(PYTHON) tools/infra/build_musl.py --jobs $(JOBS) --shared

docker-image:
	docker build -t $(DOCKER_TAG) containers/dev

docker-shell:
	docker run --rm -it -v "$(PWD):/workspace" $(DOCKER_TAG) /bin/bash

_locked-clean-work:
	@$(PYTHON) tools/infra/clean_work.py

# ── 门控分层 (INFRA-058t；用户 2026-10-09 裁定，落 milestones「规划中」) ─────────
# L1 `make check`（默认，秒~几十秒）   = 仓库完整性（静态检查）+ 组件可用性冒烟
# L2 `make check-modules`（几十~几百秒）= **四 scope 代表集**（inst/arch/unit + tset×3）
# L3 `make check-full`（几百~几千秒）   = **全量**（check-inst/check-arch/check-unit-full
#                                        + 4 个 FP 探针）+ test-m6（全量 lit + ir-lli + Embench E2E）
# 夜跑 `make check-night`（小时级）     = tset full×3 + 长 arch；报告 `.dadao/tests/night/<date>/`
# tset（TESTCASES-082t）：smoke 只在 L2（`check-modules`），full 只在夜跑（`check-night`）；
# L3 不直接列 tset smoke ⇒ 「一个检查只在一层」（docs/Process-07 §4）。
# 说明（TESTCASES-076t）：`check-interface`/`check-code-range` 只做静态/合成 fixture 断言
# ⇒ 按 docs/Process-07 §3 判据 1 归 L1（原在 L2）。四个 FP 探针（rnd/minmax/fma/clmul）
# 覆盖无向量的 `fp` 身份，属 **inst scope 的 FP 语义代表集**，只在 L3。
# 「层间不重复」= 同一检查只在一层「直接」列出；触发点见 AGENTS.md「门控分层与触发点」。
# 旧名 `check-qemu-semantics`/`check-qemu-smoke`/`test-semihost`/`check-{libc-test,llvm-ts,embench}-smoke`
# 已于 TESTCASES-076t 删除（P6 收口）；现行名 = check-inst / check-inst-smoke / check-arch-smoke /
# check-tset-{libc,llvm,embench}-smoke。
_locked-check: manifest-check validate-vectors check-spec-drift check-patch-tree check-index-blobs check-asm-list check-asm-list-drift check-asm-prose check-spec-codeblocks check-legality-drift check-legality-invariants validate-encoding check-scope check-rule-refs check-fp-contract check-instrinfo check-isa-coverage check-cfx-aliases check-cfx-alias-table check-cfx-vectors check-case-ledger check-tests-index check-rev-vectors check-decodetree-repro check-qemu-forms check-dirs check-no-residue check-spec-readonly check-spec-refs check-knowledge-refs check-contracts-dir check-spec-numbering check-spec-changelog check-spec-purity check-spec-cite-targets check-component-changelog check-syscall-abi check-musl-freshness check-builtins-freshness check-milestones-fresh check-contracts-pending check-contract-relocs check-run-artifacts check-width-sizes check-components check-interface check-code-range
	@$(PYTHON) tools/infra/check_issues.py
	@$(PYTHON) -m compileall -q tools
	@echo "repository checks (L1): PASS"

# L2 = 四 scope 的 **smoke** 集（TESTCASES-076t 收口；2026-10-27 用户裁定「L2 只保留四 scope
# smoke」⇒ 4 个 FP 探针**移出** L2，只在 L3）
#   inst : check-inst-smoke
#   arch : check-arch-smoke
#   unit : check-unit（= check-lit + test-codegen + test-elf + ir-lli + picolibc fast）
#   tset : check-tset-{libc,llvm,embench}-smoke
_locked-check-modules: check-inst-smoke check-arch-smoke check-unit check-tset-libc-smoke check-tset-llvm-smoke check-tset-embench-smoke
	@echo "module checks (L2): PASS"

# L3 = 全量（TESTCASES-076t；2026-10-27 用户裁定「一个检查只在一层」严格化；TESTCASES-082t 去 tset smoke）。
#   inst 全量 : check-inst；arch 全量 : check-arch
#   unit 全量 : check-unit-full（= check-unit + check-lit-full）；`check-unit` 只在 L2 **直接**列出，
#               此处经**前置依赖**间接跑到 ⇒ 符合 Process-07 §4「被上层前置依赖不算重复」
#   tset      : **不直接列出**（L2 已有 smoke；tset full 只在夜跑 check-night）；
#               `test-m6` 的 Embench E2E 是集成步骤，不算 tset smoke 重复
#   fp 语义   : 4 个 FP 探针（`fp` 身份无向量 ⇒ 探针是其唯一语义覆盖；已移出 L2，只在 L3）
#   整链      : test-m6（Embench E2E + ir-lli + 全量 lit；其 [1/3] 亦跑 check-lit-full）
_locked-check-full: check-inst check-arch check-unit-full check-rnd-probe check-minmax-probe check-fma-probe check-clmul-probe test-m6
	@echo "full checks (L3): PASS"

# Vector schema/inventory/coverage gate (TESTCASES-002t). Requires the M1
# encoding table (contracts/opcodes.yaml) to exist.
validate-vectors: contracts/opcodes.yaml
	@$(PYTHON) tools/testcases/validate_vectors.py

# spec drift check (INFRA-012t): fail-closed provenance audit for contract-*.md.
check-spec-drift:
	@$(PYTHON) tools/infra/check_spec_drift.py

# 21-volume heading numbering gate (SPEC-133t; INFRA-069t 并入 L1): depth <= 4,
# `N`/`N.M`/`N.M.K` shape, per-volume uniqueness + contiguity, no orphan parent.
check-spec-numbering:
	@$(PYTHON) tools/spec/check_numbering.py

# 21-volume appendix changelog gate (SPEC-134t; INFRA-069t 并入 L1): appendix
# exists and is last, version segments strictly reversed, header consistency,
# no table rows / task-ids.  Counts are recomputed live, never hardcoded.
check-spec-changelog:
	@$(PYTHON) tools/spec/check_spec_changelog.py

# spec 纯净度门控 (SPEC-165t, L1): `spec/SimRISC-*` 只写规范内容——禁用词表
# （scope / 里程碑 / 任务号 / ADR- / ISS- / contract-*.md / .tao/ / 旧表名 / v5）
# 任一命中即红；`--self-test` 含 ≥3 类注入。
check-spec-purity:
	@$(PYTHON) tools/spec/check_spec_purity.py

# spec_cite 目标存在性 (SPEC-165t, L1): `contracts/*.yaml` + `tests/**/*.yaml` 的
# `spec_cite` 必须指向 `spec/` 中真实存在的「书 + 节」（数字节号或节标题）。
check-spec-cite-targets:
	@$(PYTHON) tools/spec/check_spec_cite_targets.py

# SimRISC 版本归档门控 (SPEC-154t; 规则见 docs/Process-06 §8): 册头 ∪ 附录声明的
# 每个版本须有 `.tao/archive/SimRISC-<ver>/`（非空、含 SimRISC-00*、文件数与派生清单一致）。
# 只校验存在性与文件集，不校验内容（`-rc` 为时点快照）。派生失败 ⇒ 只查 A1/A2。
# **里程碑收尾**专项（INFRA-109t；用户 2026-10-25 裁定）：归档是只读历史快照，只在
# 发布/里程碑边界变化 ⇒ 结构与内容 sha 都**不入 L1**，挂 `check-milestone`。
check-spec-archive:
	@$(PYTHON) tools/spec/check_spec_archive.py

# 归档**内容**校验 (SPEC-154t/INFRA-109t; 里程碑收尾): 以各目录 `PROVENANCE.md` 的
# 快照提交为锚，逐文件 sha256 + 版本组合 sha256 全等；`-rc` 跳过（预发布）。
# 判据真源 = tools/spec/gen_spec_archive.py，此处只接线、不改判据。
check-spec-archive-verify:
	@$(PYTHON) tools/spec/gen_spec_archive.py --verify

# 组件补丁集校验 (2026-09-23): 树形补丁集断言（现 9 条），见 docs/Process-01-组件补丁组织与构建编排.md。
check-patch-tree:
	@$(PYTHON) tools/infra/check_patch_tree.py

# new-file 补丁 index blob hash 卫生 (INFRA-038t/ISS-119): 按补丁自身内容用
# `git hash-object --stdin` 重算 new-file 补丁的 index 新 hash；失配 ⇒ FAIL。
# 修改类补丁（有 old hash）不在此检查范围内，明确跳过。
check-index-blobs:
	@$(PYTHON) tools/infra/check_index_blobs.py

# E7 模块自检 (2026-10-03): 报告每个源树的 E1 状态（worktree 干净 + base+1）。
check-source-state:
	@$(PYTHON) tools/infra/check_patch_tree.py --source-state

# 组件源文件规模报告 (INFRA-028t): 仅报告（非强制），不进门控。
# 规则见 docs/Process-01 §11「组件源文件规模约定」。
size-report:
	@$(PYTHON) tools/infra/size_report.py

# 待收尾任务自查 (INFRA-029t): 报告型，列出「完成区已填 + 待验收」的漏 /complete 任务。
# 默认退出码 0，不并入 `make check` 阻断路径；--strict 时命中 >0 则失败。
check-tasks:
	@$(PYTHON) tools/infra/check_tasks.py

# 测试运行产物与日志命名门控 (INFRA-093t, L1): A1 三个 user-mode 驱动无固定
# 默认输出（`--json-out` 必填、无 DEFAULT_LOG_DIR 回落）；A2 `.work/tests/**`
# 与 test-artifacts 根下每个 `YYYYMMDDTHHMMSSZ-*` 运行目录须有
# run.json/run.log/meta.json（meta 含 command/started_utc/toolchain 摘要）；
# A3 `.work/log/**` 新增文件名须为 `check-<name>.log` 或
# `<任务号>-<用途>.(log|json|txt)`（存量按 `.run-artifacts-epoch` +
# `.run-artifacts-baseline` 豁免；标记缺失 ⇒ SKIP 并打印）。
# 规则真源 = docs/Process-08；可达 FAIL 见 `--self-test`。
check-run-artifacts:
	@$(PYTHON) tools/infra/check_run_artifacts.py

# 里程碑收尾门控 (2026-10-17, A2; 归 **L2 层 / 里程碑收尾专项**，**不入** `check-modules`):
# ⓪ SimRISC 归档：结构（`check-spec-archive`）+ 内容 sha256（`check-spec-archive-verify`）
#    ——归档只在发布/里程碑边界变化，故不入 L1（INFRA-109t；用户 2026-10-25 裁定）；
# ① 当前里程碑（`milestones.md` 中 `项目里程碑 = M<n>` 断言的最大 n）在 `.tao/tasks/**`
#    下有对应 `m` 册（命名惯例 `<PREFIX>-<nnn>m-*.md`；自报里程碑须与当前一致）；
# ② 该 `m` 册列出的全部任务号须在 `.tao/tasks/**`（或 `.tao/archive/**`，已完成并归档）
#    有对应任务书；册内零任务号 ⇒ vacuous FAIL（防「漏立任务」）；
# ③ 接 `check_tasks.py --strict`（漏收尾 = 0）。
# ④ 同步异常不可屏蔽（`check-sync-nonmaskable`，用户 2026-10-26 裁定「同步异常全部不可屏蔽；
#    仅异步可屏蔽」）——扫 DADAO-12/22/23 异常原因表，异步源（IPI/TIMER/UART*/…）之外出现「可」即红。
# ⑤ `.tao/knowledge/` 顶层白名单（`check-knowledge-dir`，用户 2026-10-26 裁定「从L1摘除，
#    放到里程碑check里」）——顶层白名单外文件即红。
# ⑥ 夜跑报告存在性/结构/结果（`check-night-report`，TESTCASES-076t）——没跑夜跑即红
#    （`.dadao/tests/night/<YYYY-MM-DD>/` 三件套 + tset×3/arch 行 + 全 rc=0）。
# 不并入 L1 的理由：`m` 册未建前本目标**必然红**（预期的收口信号），日常 L1 不应常态红。
check-milestone: check-spec-archive check-spec-archive-verify check-sync-nonmaskable check-knowledge-dir check-night-report
	@$(PYTHON) tools/infra/check_milestone_tasks.py
	@$(PYTHON) tools/infra/check_tasks.py --strict
	@echo "check-milestone: PASS (归档结构 + 内容 sha + 同步不可屏蔽 + knowledge 顶层白名单 + 夜跑报告 + m 册在场 + 所列任务号存在 + 漏收尾 = 0)"

# 同步异常不可屏蔽 (SPEC-175t; 里程碑层): 扫 DADAO-12/22/23 异常原因表的「是否可屏蔽」列，
# 只有异步源（IPI / TIMER / UART* / 占位行 …）允许「可」；`--self-test` 内置注入→FAIL→还原→PASS。
check-sync-nonmaskable:
	@$(PYTHON) tools/spec/check_sync_nonmaskable.py

# spec 引用审计 (INFRA-011t): Check 1 引用有效性 + Check 2 无引用规范断言.
# L1 成员 (INFRA-058t): 静态引用完整性检查（改后 0 误报）。覆盖 SimRISC-/DADAO-/
# Toolchain-01/Machine-01；数值节号 (§7.2) 命中标题 `7.2 …`；模板占位 (§x/§N) 跳过。
check-spec-refs:
	@$(PYTHON) tools/infra/check_spec_refs.py

# 被引用 `.work/**` 材料悬空门控 (INFRA-058t / INTEG-037t): 扫 AGENTS.md/spec/
# .tao/knowledge/.tao/contracts/.tao/tasks 中对 `.work/**` 的引用；悬空即红。L1 成员。
# 口径 (见 AGENTS.md「文档分层与单一真源」): 占位/通配/前缀截断跳过；
# `.work/build`/`.work/source` 豁免；删除语境引用不校验；其余具体路径要求存在。
check-knowledge-refs:
	@$(PYTHON) tools/infra/check_knowledge_refs.py

# `.tao/knowledge/` 顶层白名单门控 (INFRA-070t; **里程碑层**，随 `check-milestone`；2026-10-26
# 用户裁定「从L1摘除，放到里程碑check里」)：顶层只允许既定模式（台账集合 / 子目录）；
# `contract-*.md` 已随 INFRA-071t 迁出 ⇒ 顶层再出现即白名单外 FAIL。
# 计数现场统计、不写死。规则见 AGENTS.md「文档分层与单一真源」+ docs/Process-07。
check-knowledge-dir:
	@$(PYTHON) tools/infra/check_knowledge_dir.py

# 契约目录顶层白名单门控 (INFRA-071t, L1 成员; 守两处): `.tao/contracts/` 顶层只允许
# `contract-*.md` / `README.md` / 子目录; `contracts/` 顶层只允许 `*.yaml` / `README.md` /
# 子目录（`contract-*.md` 随 Phase B 迁出作废）。白名单外文件 / 目录缺失 / vacuous 即 FAIL。
check-contracts-dir:
	@$(PYTHON) tools/infra/check_contracts_dir.py

# 组件 changelog 形态门控 (INFRA-084t, L1 成员): `components/*/` 下的组件变更记录必须为
# 「列表式（无表格）+ 按里程碑分节」形态（体例真源 docs/Process-01 §10）——① 无表格分隔行
# ② 条目 `- **<日期> …**` ③ 条目紧接 `  - 摘要：` 缩进行 ④ `## M<k>` 节序严格递增
# ⑤ 覆盖全部（glob 现场派生；空集 vacuous FAIL）。**只做形态断言**，不做内容校验；
# 计数现场统计、不写死。可达 FAIL 见 `--self-test`。
# syscall 参数银行三载体一致性 (ISS-249, L1): musl __dadao_argmask / 可取消 asm 派发 /
# QEMU dadao_argmask 逐项一致 + 完整性（musl 能发出的 syscall 名全覆盖）。
# 有 .work/source 时读工作树，否则退回 components/ 下的补丁（新克隆也能跑）。
check-syscall-abi:
	@$(PYTHON) tools/qemu/check_syscall_abi.py

# musl 产物新鲜度 (ISS-258): 安装根 libc.so 必须由当前 musl 源 + 工具链构建
# （build_musl.py 成功构建后在 obj/ 落 toolchain/source 戳记；源 digest 变即
# 强制 make clean；安装副本与构建产物逐字节一致）。工具链判据 = clang/ld.lld
# 的**内容标识**（GNU build-id，退路 sha256；INFRA-101t，mtime/size 不参与）；
# 旧 `mtime=` 格式戳记判一次 stale 并打印 `migrated`。无构建树 / 无共享产物 ⇒
# SKIP；有产物则缺戳记即 FAIL。成本 ~1.2 s（内容摘要），按 docs/Process-07
# §1.1 归 L1（静态溯源，不跑被测语义）。
check-musl-freshness:
	@$(PYTHON) tools/infra/check_musl_freshness.py

# compiler-rt builtins 归档新鲜度 (ISS-293, L1): 工具链消费的三份归档（构建树产物 /
# 构建树 clang 资源目录副本 / 安装根副本）必须同一内容，且其**生产者标识**
# （build-builtins 写的 sidecar：clang/ld.lld build-id + 归档 sha256）等于当前
# 工具链；逐成员按**内容**对 .c.o，不看 mtime（INFRA-101t）。旧编码残留 → 新
# qemu 按 ILLI 打 SIGILL。`--self-test`：内容变必红 / 仅 mtime 变不假红。
check-builtins-freshness:
	@$(PYTHON) tools/infra/check_builtins_freshness.py --build-dir $(COMPILER_RT_BUILD)

# 安装集断言 (ISS-261 / INFRA-098t): 安装根须带上门控/执行器要用的工具，且每个都仍是
# 构建树同一个二进制（真值源 = 本 Makefile 的 HOST_LLVM_TOOLS + HOST_LLVM_TOOL_SYMLINKS，
# 脚本解析本文件，不另写第二份清单）。挂载点 = install-host 收尾（装完即断言），
# 亦可 `make check-install-tools` 单独调。**不入 L1**：未跑过 install-host 的新克隆
# 必然红（与 check-milestone 同类理由，层归属见 docs/Process-07 §1.1）。
check-install-tools:
	@$(PYTHON) tools/infra/check_install_tools.py

# 任务流水体例门控 (INFRA-091t, L1): 状态 == 任务书 / 覆盖 / 一句改动 ≤120 字符 /
# 时间倒序 / 格式。规则 = milestones.md「体例约定（硬约束）」+ docs/Process-07 §1.1。
check-milestones-fresh:
	@$(PYTHON) tools/infra/check_milestones_fresh.py

check-component-changelog:
	@$(PYTHON) tools/infra/check_component_changelog.py

# 契约「待定」指针门控 (2026-10-17, B4; L1 成员): `.tao/contracts/**` 出现
# 「待…定 / 待裁定 / TODO / TBD」类标记时，该行须同时含 `ADR-<n>` / `ISS-<n>` 指针
# （只认带编号的落点；光写「待后继 ADR 定」不算）；行内代码跨度与「」引用不计。
# 计数现场统计、不写死；可达 FAIL 见 `--self-test`。
check-contracts-pending:
	@$(PYTHON) tools/infra/check_contracts_pending.py

# 契约重定位类型表一致门控 (2026-10-17, B5; L1 成员): `contract-elf.md §2.2` 与
# `contract-dynlink.md §4.3` 的**现行表**逐行比对（类型号 ↔ 名）；只解析两小节内的
# 表格行 ⇒ 历史注记 / 其它小节的历史表不参与（旧值可留在注记里，以现行表为准）。
# 附加自洽：表非空、号/名唯一、号 0 起密集；可达 FAIL 见 `--self-test`。
check-contract-relocs:
	@$(PYTHON) tools/infra/check_contract_relocs.py

# cfx alias drift gate (SPEC-075t): verify .tao/contracts/contract-cfx-aliases.md is up-to-date.
check-cfx-aliases:
	@$(PYTHON) tools/spec/check_cfx_aliases.py

# cfx alias runtime-table drift gate (LLVM-135t, L1): contracts/cfx-aliases.txt
# (the file llvm-mc/llvm-objdump read at run time) must equal the spec
# projection; the generator's --check names the first differing line.
check-cfx-alias-table:
	@$(PYTHON) tools/llvm/gen_cfx_alias_table.py --check

# cfx alias table install gate (LLVM-135t; needs install-host): source table ==
# build-tree copy == install-root copy, byte for byte.  A stale/missing copy
# would silently change what the assembler accepts / the disassembler prints.
check-cfx-alias-install:
	@$(PYTHON) tools/llvm/check_cfx_alias_install.py

# cfx MC vector independent oracle (LLVM-060t; wired into L1 by LLVM-135t).
check-cfx-vectors:
	@$(PYTHON) tests/unit/llvm/lit/MC/DADAO/validate_cfx_vectors.py

# Install/product directory path guard (INFRA-019t): validates
# manifests/install-dirs.lock.toml and scans for symlink prefix violations.
check-dirs:
	@$(PYTHON) tools/infra/check_dirs.py

# Residue gate (INFRA-025t): detect unexpected untracked temp files.
check-no-residue:
	@$(PYTHON) tools/infra/check_dirs.py --residue

# 组件可用性冒烟 (INFRA-058t, L1): llc / clang --print-targets / qemu-system-dadao
# 可执行且确实认识 `dadao` 目标；不跑被测语义（那是 L2/L3）。
check-components:
	@$(PYTHON) tools/infra/check_components.py

# 位宽 / DWARF64 探针 (LLVM-130t, L1): DADAO 是 64 位原生目标（ADR-0036 D1）——
# ① 逐条静态断言编译 sizeof(void*/long/size_t)==8、_Alignof(max_align_t)==16、
#    sizeof(long double)==16、__BIGGEST_ALIGNMENT__==16；
# ② `-g -c` 必须 rc=0（修复前 `.debug_addr` 落 4 字节字段，汇编器拒绝 48 位重定位）；
# ③ `llvm-readelf -h` Class=ELF64；所有 RELA 段 entsize=24；`.got` 项宽 = 8
#    （`.got` size == 8 × `.rela.got` 条数，条数现场统计）；
# ④ `llvm-dwarfdump --debug-info`（在**链接后**的 `-g` 产物上；`.o` 的 ABS48 重定位
#    无法被 libObject 应用 ⇒ dwarfdump rc=1）每个 CU 的 `addr_size = 0x08` 且
#    `format = DWARF64`（驱动默认 `-gdwarf64`；显式 `-gdwarf32` 由驱动报错，DADAO
#    无 32 位 DWARF 重定位通道）。逐条可达 FAIL 见 `--self-test`（假工具注入，无需构建）。
# 需要安装根（未跑 `make install-host` 时 FAIL 并给出提示）；按 docs/Process-07 §1
# 归 L1（只做静态/尺寸断言，不跑被测语义）。
check-width-sizes:
	@$(PYTHON) tools/llvm/check-width-sizes.py

# 代码跨度门控 (INFRA-106t, L2; ADR-0036 D4/D7): 读链接后 DADAO ELF 的
# `--emit-relocs` 重定位，报告每个产物的最远 REL26 边 + 余量、REL20/REL14 边、
# 全部 SHF_EXECINSTR 段的 exec_span。判据：任一 REL26 边 > 32 MiB 或
# exec_span ≥ 30 MiB ⇒ 红（阈值单一真源在 tools/infra/check_code_range.py）。
# 目标体用合成 fixture 自检（正常绿 / 远距红 / 缺 --emit-relocs fail-closed），
# 不依赖 toolchain 重建；可达 FAIL 见脚本 `--self-test`。
check-code-range:
	@$(PYTHON) tools/infra/check_code_range.py --self-test

# spec 目录只读锁 (SPEC-119t): 只读册 sha256 校验；失配 ⇒ FAIL（须先取用户授权并同步改锁）。
# 规则见 docs/Process-06-spec目录保护规范.md §5。
check-spec-readonly:
	@$(PYTHON) tools/infra/check_spec_readonly.py

# Spec embedded assembly list consistency (SPEC-037t).
check-asm-list:
	@$(PYTHON) tools/spec/check_asm_list_consistency.py

# Assembly-list drift gate (INFRA-027t): verify .tao/contracts/contract-asm-list.md
# is up-to-date (regenerates to a temp file, byte-diff; never overwrites).
check-asm-list-drift:
	@$(PYTHON) tools/spec/check_asm_list_drift.py

# Assembly prose format gate (SPEC-076t): detect old-format assembly
# in prose fenced-code blocks.  --strict: exit 1 if any violation (baseline=0).
check-asm-prose:
	@$(PYTHON) tools/spec/check_asm_prose.py --strict

# Spec prose ```simrisc code-block gate (SPEC-103t/ISS-077): every instruction
# line in spec/**/*.md must use a mnemonic
# from contracts/opcodes.yaml (pseudo-instructions excepted) with a valid
# operand count.
check-spec-codeblocks:
	@$(PYTHON) tools/spec/check_spec_codeblocks.py

# lit gate (INFRA-021t): run llvm-lit on MC (M1/M4) + CodeGen (L2) + E2E.
# MC needs llvm-mc/llvm-objdump/FileCheck; CodeGen needs llc + FileCheck; E2E
# needs llvm-objcopy + qemu-system-dadao + trampoline (all installed by
# `make install-host`).
# llvm-lit missing => explicit error (never silent skip).
# INFRA-047t (ADR-0016 D9): tools are taken from the install root, not .work/build.
# INFRA-058t: L2 成员（功能代表集，受控子集）——已从 L1 `make check` 移出。
LIT_BIN = $(HOST_TOOLCHAIN_BIN)/llvm-lit
_locked-check-lit:
	@test -x $(LIT_BIN) || { echo "check-lit: ERROR: $(LIT_BIN) not found — run 'make install-host' first"; exit 1; }
	$(LIT_BIN) tests/unit/llvm/lit/MC/DADAO tests/unit/llvm/lit/CodeGen/DADAO tests/e2e/lit -v

# lit 全量档 (TESTCASES-037t): 由 contracts/opcodes.yaml 机械生成的全部 lit MC
# 编码用例（快档受控子集已随 check-lit 进 L2；本目标承载规模）。
# INFRA-058t: 归 **L3**（经 `check-full` → `test-m6` 步骤 [1/3] 承载；本目标亦可单独调）。
# 先跑结构+编码检查器，再跑 lit。
# 计数不写死：由 check_lit_gen.py / llvm-lit **现场统计**；本目标不设硬编码门限。
_locked-check-lit-full:
	@test -x $(LIT_BIN) || { echo "check-lit-full: ERROR: $(LIT_BIN) not found — run 'make install-host' first"; exit 1; }
	@$(PYTHON) tools/testcases/check_lit_gen.py \
	  --full-dir tests/unit/llvm/lit/MC/DADAO-gen \
	  --fast-file tests/unit/llvm/lit/MC/DADAO/gen-fast.s
	$(LIT_BIN) tests/unit/llvm/lit/MC/DADAO-gen -v

# M3 CodeGen end-to-end gate (INTEG-012t).  Tools are taken from the install
# root (ADR-0016 D9); install-host keeps it in sync with the .work/ build trees.
# Pipeline (single TU, per ADR-0003 D5):
#   llc -march=dadao <prog.ll> -> .s; cat codegen_crt0.s prog.s -> .s;
#   llvm-mc --triple=dadao -filetype=obj -> .o;
#   llvm-objcopy -O binary --only-section=.text -> .bin;
#   qemu-system-dadao -M dadao-m1 -bios trampoline.bin -kernel .bin ...
# The guest process exit code is compared against tests/unit/llvm/codegen/expected.yaml.
# Fail-closed: any mismatch / timeout / machine fault => non-zero exit.
LLC_BIN = $(HOST_TOOLCHAIN_BIN)/llc
LLVM_MC_BIN = $(HOST_TOOLCHAIN_BIN)/llvm-mc
LLVM_OBJCOPY_BIN = $(HOST_TOOLCHAIN_BIN)/llvm-objcopy
QEMU_BIN = $(HOST_TOOLCHAIN_BIN)/qemu-system-dadao
# Work dir under the SDK test-artifacts root (ADR-0016 D6), resolved via
# paths.py (D7) — never the source tree.
CODEGEN_E2E_WORK = $(TEST_ARTIFACTS_DIR)/codegen-e2e
CODEGEN_E2E_LOG = .work/log/integ/test-codegen.log
_locked-test-codegen: install-host
	@test -x $(LLC_BIN) || { echo "test-codegen: ERROR: $(LLC_BIN) not found"; exit 1; }
	@test -x $(LLVM_MC_BIN) || { echo "test-codegen: ERROR: $(LLVM_MC_BIN) not found"; exit 1; }
	@test -x $(LLVM_OBJCOPY_BIN) || { echo "test-codegen: ERROR: $(LLVM_OBJCOPY_BIN) not found"; exit 1; }
	@test -x $(QEMU_BIN) || { echo "test-codegen: ERROR: $(QEMU_BIN) not found"; exit 1; }
	@rm -rf $(CODEGEN_E2E_WORK); \
	  mkdir -p .work/log/integ; \
	  $(PYTHON) tools/testcases/unit/run_codegen_e2e.py \
	    --llc $(LLC_BIN) --llvm-mc $(LLVM_MC_BIN) --llvm-objcopy $(LLVM_OBJCOPY_BIN) \
	    --qemu $(QEMU_BIN) --trampoline tools/testcases/lib/trampoline.bin \
	    --crt0 tests/shared/crt0/codegen_crt0.s \
	    --vectors-dir tests/unit/llvm/codegen \
	    --expected tests/unit/llvm/codegen/expected.yaml \
	    --work-dir $(CODEGEN_E2E_WORK) \
	    > $(CODEGEN_E2E_LOG) 2>&1; \
	  rc=$$?; \
	  tail -20 $(CODEGEN_E2E_LOG); \
	  if [ $$rc -ne 0 ]; then echo "test-codegen: FAIL (rc=$$rc)"; exit $$rc; fi; \
	  echo "test-codegen: PASS"

# M4 multi-TU / multi-section ELF end-to-end gate (INTEG-016t).  Tools are taken
# from the install root (ADR-0016 D9); install-host keeps it in sync with the
# build trees.  Pipeline (multi-object, per contract-elf.md §6.1.2):
#   llvm-mc --triple=dadao -filetype=obj tests/shared/crt0/codegen_crt0.s -> crt0.o;
#   per TU llc -march=dadao -filetype=obj                            -> <tu>.o;
#   ld.lld -T tests/shared/linker/dadao.lds crt0.o <tu>.o ... -o <prog>.elf;
#   qemu-system-dadao -M dadao-m1 -kernel <prog>.elf ...
# The guest process exit code is compared against the independent M4 manifest
# tests/unit/llvm/codegen/m4/expected.yaml (TESTCASES-030t/032t).
# Fail-closed: any mismatch / timeout / build-step non-zero => non-zero exit.
# Coexists with test-codegen (raw-bin / trampoline: kept as-is).
LLD_BIN = $(HOST_TOOLCHAIN_BIN)/ld.lld
# Work dir under the SDK test-artifacts root (ADR-0016 D6), resolved via
# paths.py (D7); coexists with test-codegen's dir.
CODEGEN_ELF_WORK = $(TEST_ARTIFACTS_DIR)/elf-e2e
CODEGEN_ELF_LOG = .work/log/integ/test-elf.log
_locked-test-elf: install-host
	@test -x $(LLC_BIN) || { echo "test-elf: ERROR: $(LLC_BIN) not found"; exit 1; }
	@test -x $(LLVM_MC_BIN) || { echo "test-elf: ERROR: $(LLVM_MC_BIN) not found"; exit 1; }
	@test -x $(LLD_BIN) || { echo "test-elf: ERROR: $(LLD_BIN) not found"; exit 1; }
	@test -x $(QEMU_BIN) || { echo "test-elf: ERROR: $(QEMU_BIN) not found"; exit 1; }
	@rm -rf $(CODEGEN_ELF_WORK); \
	  mkdir -p .work/log/integ; \
	  $(PYTHON) tools/testcases/unit/run_elf_e2e.py \
	    --llc $(LLC_BIN) --llvm-mc $(LLVM_MC_BIN) --ldlld $(LLD_BIN) \
	    --qemu $(QEMU_BIN) --crt0 tests/shared/crt0/codegen_crt0.s \
	    --lds tests/shared/linker/dadao.lds \
	    --vectors-dir tests/unit/llvm/codegen/m4 \
	    --expected tests/unit/llvm/codegen/m4/expected.yaml \
	    --work-dir $(CODEGEN_ELF_WORK) \
	    > $(CODEGEN_ELF_LOG) 2>&1; \
	  rc=$$?; \
	  tail -20 $(CODEGEN_ELF_LOG); \
	  if [ $$rc -ne 0 ]; then echo "test-elf: FAIL (rc=$$rc)"; exit $$rc; fi; \
	  echo "test-elf: PASS"

# unit scope 门控（TESTCASES-074t；Process-09 §6/§8 分层）
# 用例资产：`tests/unit/llvm/`（lit MC/CodeGen、codegen m3/m4/m6、ir-lli manifest）
#          + `tests/unit/picolibc/`（picolibc 自测仍只在 picolibc 构建下跑）
# 判据与原 L2 成员**逐条未改**，只搬家 + 接线：
#   1. check-lit（MC + CodeGen + e2e lit）
#   2. test-codegen（M3 15 程序）
#   3. test-elf（M4 5 程序）
#   4. ir-lli 值级差分（host lli vs DADAO target；include 条数现场统计）
#   5. check-picolibc-tests fast（picolibc 上游自测代表集）
# 旧目标名全部保留、可单独调用（等价）；删除旧入口只在 TESTCASES-076t 做。
UNIT_IR_LLI_LOG = .work/log/unit/check-unit-ir-lli.log
_locked-check-unit: check-lit test-codegen test-elf check-picolibc-tests
	@mkdir -p .work/log/unit
	@echo "check-unit: [4/5] ir-lli value-level differential (host X86 vs DADAO target)"; \
	  $(PYTHON) $(DIFF_IR_LLI) --work-dir $(IR_LLI_WORK) > $(UNIT_IR_LLI_LOG) 2>&1; \
	  rc=$$?; \
	  tail -n 6 $(UNIT_IR_LLI_LOG); \
	  if [ $$rc -ne 0 ]; then echo "check-unit: FAIL (ir-lli rc=$$rc)"; exit $$rc; fi
	@echo "check-unit: PASS (lit + codegen + elf + ir-lli + picolibc fast)"

# unit scope **全量**（L3 专属；TESTCASES-076t，2026-10-27 用户裁定「一个检查只在一层」）。
# 构成 = L2 的 `check-unit`（**经前置依赖**跑到，不在 L3 直接列出）+ `check-lit-full`
#       （由 contracts/opcodes.yaml 机械生成的全量 MC 编码档）
# ⇒ lit 全量 + codegen + elf + ir-lli + picolibc 全覆盖；`check-unit` 本身只归 L2。
UNIT_FULL_LOG = .work/log/unit/check-unit-full.log
_locked-check-unit-full: check-unit check-lit-full
	@mkdir -p .work/log/unit
	@echo "check-unit-full: PASS (check-unit + check-lit-full)" > $(UNIT_FULL_LOG)
	@cat $(UNIT_FULL_LOG)

# arch scope 端到端门控（TESTCASES-073t；Process-09 §6/§8 分层）
# 用例资产：`tests/arch/umon/`（m5 SEE/semihosting + cfx 权限向量，条数由 manifest 现场统计）
# 驱动：`tools/testcases/arch/run_m5_e2e.py`（flat-bin 流水线）+
#       `tools/testcases/arch/min_rom_probe_*.py`（min-ROM 场景探针，原 `tools/qemu/`）
# 判据与原 `test-semihost`（INTEG-020t）**逐条未改**，只搬家 + 接线：
#   1. forward: SEE bootrom (`-bios`) + flat bin (`-kernel`) + `-semihosting`；
#      console / host 文件 / SYS_EXIT 退出码逐条比对，bootrom 生效性由 `-d cpu` 观测。
#   2. cfx-level permission counter-examples（4 例随同一驱动：reserved cfxha / masked
#      trap => ILLI；unimplemented cfx / RO-write => CFXREG；ADR-0020 D9）。
#   3. 25 服务表覆盖（`min_rom_probe_046t`，>=1/id）。
#   `check-arch-smoke` = **L2 代表集**（上述 1–3；= 原 test-semihost 的测试面）；
#   `check-arch` = **L3**（= smoke + cfx 场景探针 044/045/049）。
# 工具/LD 从安装根取（ADR-0016 D9），bootrom 由 `make build-bootrom` 产出。
ARCH_M5_DIR = tests/arch/umon
ARCH_M5_RUNNER = tools/testcases/arch/run_m5_e2e.py
ARCH_MIN_ROM_DIR = tools/testcases/arch
ARCH_E2E_WORK = $(TEST_ARTIFACTS_DIR)/arch/m5-e2e
ARCH_SMOKE_LOG = .work/log/arch/check-arch-smoke.log
ARCH_PROBE_LOG = .work/log/arch/check-arch-smoke-svc.log
# L3 追加的 cfx 场景探针（原 min_rom_probe_*）：SEE/trap/escape 语义面 + RAM 映射/CFXMEM。
# `045t` = trap/escape/cfx2* 全寄存器面；`049t` = RAM 映射 + 越界 cause；
# `047t` 沿用旧期望（`stack_in_ram0` 与 bootrom.S 常量不一致）⇒ 不入本门控，见任务书遗留。
ARCH_CFX_PROBES = 044t 045t 049t

_locked-check-arch-smoke: install-host build-bootrom
	@test -x $(LLVM_MC_BIN) || { echo "check-arch-smoke: ERROR: $(LLVM_MC_BIN) not found"; exit 1; }
	@test -x $(LLVM_OBJCOPY_BIN) || { echo "check-arch-smoke: ERROR: $(LLVM_OBJCOPY_BIN) not found"; exit 1; }
	@test -x $(QEMU_BIN) || { echo "check-arch-smoke: ERROR: $(QEMU_BIN) not found"; exit 1; }
	@test -f $(ARCH_MIN_ROM_DIR)/min_rom_probe_046t.py || { echo "check-arch-smoke: ERROR: min_rom_probe_046t.py not found"; exit 1; }
	@test -f $(BOOTROM_DIR)/bootrom.bin || { echo "check-arch-smoke: ERROR: $(BOOTROM_DIR)/bootrom.bin not found (run 'make build-bootrom')"; exit 1; }
	@mkdir -p .work/log/arch
	@rm -rf $(ARCH_E2E_WORK)
	@echo "check-arch-smoke: [1/2] forward semihosting + cfx-level permission counter-examples"; \
	  $(PYTHON) $(ARCH_M5_RUNNER) \
	    --llvm-mc $(LLVM_MC_BIN) --llvm-objcopy $(LLVM_OBJCOPY_BIN) \
	    --qemu $(QEMU_BIN) --bootrom $(BOOTROM_DIR)/bootrom.bin \
	    --vectors-dir $(ARCH_M5_DIR) --expected $(ARCH_M5_DIR)/expected.yaml \
	    --work-dir $(ARCH_E2E_WORK) > $(ARCH_SMOKE_LOG) 2>&1; \
	  rc=$$?; \
	  tail -n 30 $(ARCH_SMOKE_LOG); \
	  if [ $$rc -ne 0 ]; then echo "check-arch-smoke: FAIL (forward/permission rc=$$rc)"; exit $$rc; fi
	@echo "check-arch-smoke: [2/2] 25-service table coverage (min_rom_probe_046t)"; \
	  $(PYTHON) $(ARCH_MIN_ROM_DIR)/min_rom_probe_046t.py --qemu $(QEMU_BIN) > $(ARCH_PROBE_LOG) 2>&1; \
	  rc=$$?; \
	  tail -n 4 $(ARCH_PROBE_LOG); \
	  if [ $$rc -ne 0 ]; then echo "check-arch-smoke: FAIL (service coverage rc=$$rc)"; exit $$rc; fi
	@echo "check-arch-smoke: PASS (forward + permission + 25-service)"

# L3：arch 全 cfx 场景（smoke + cfx min-ROM 探针）。任一探针非零 ⇒ 整体红。
_locked-check-arch: check-arch-smoke
	@mkdir -p .work/log/arch
	@fail=0; for p in $(ARCH_CFX_PROBES); do \
	  echo "check-arch: [$$p] cfx min-ROM probe"; \
	  $(PYTHON) $(ARCH_MIN_ROM_DIR)/min_rom_probe_$$p.py > .work/log/arch/check-arch-probe-$$p.log 2>&1; \
	  rc=$$?; \
	  tail -n 3 .work/log/arch/check-arch-probe-$$p.log; \
	  if [ $$rc -ne 0 ]; then echo "check-arch: FAIL (min_rom_probe_$$p rc=$$rc)"; fail=1; fi; \
	done; \
	if [ $$fail -ne 0 ]; then exit 1; fi; \
	echo "check-arch: PASS (arch-smoke + cfx probes: $(ARCH_CFX_PROBES))"

# M6 end-to-end gate (INTEG-025t).  Three components, all fail-closed:
#   1. value-level differential: the same LLVM IR runs on the host `lli` (X86)
#      and on the DADAO target; both must expose the same value channel
#      (`@main` return low byte) -- tools/testcases/diff_ir_lli.py (038t).
#   2. Embench-IoT E2E: every benchmark under <embench-src>/src/ is compiled,
#      linked and run at -O0 and -O2; judgement = guest exit code 0
#      (support/main.c returns !correct) -- tools/testcases/tset/embench/run_embench_e2e.py.
#   3. the full generated lit MC suite (check-lit-full, 037t), driven through a
#      sub-make so its own exit code is captured.
# opt-in: NOT part of `make check` (the fast lit subset is already in check-lit).
# Tools come from the install root (ADR-0016 D9): run 'make install-host' first.
# Landing: work dirs under the SDK test-artifacts root (ADR-0016 D6 /
# Process-05 §6), resolved via paths.py (D7) -- never hardcoded.
DIFF_IR_LLI = tools/testcases/diff_ir_lli.py
EMBENCH_E2E = tools/testcases/tset/embench/run_embench_e2e.py
EMBENCH_SRC = .work/source/embench-iot
IR_LLI_WORK = $(TEST_ARTIFACTS_DIR)/ir-lli-diff
EMBENCH_E2E_WORK = $(TEST_ARTIFACTS_DIR)/m6-embench
IR_LLI_LOG = .work/log/integ/test-m6-ir-lli.log
EMBENCH_E2E_LOG = .work/log/integ/test-m6-embench.log
LIT_FULL_LOG = .work/log/integ/test-m6-lit-full.log
_locked-test-m6: install-host
	@test -x $(HOST_TOOLS_BIN)/lli || { echo "test-m6: ERROR: $(HOST_TOOLS_BIN)/lli not found — run 'make install-host'"; exit 1; }
	@test -x $(HOST_TOOLCHAIN_BIN)/clang || { echo "test-m6: ERROR: $(HOST_TOOLCHAIN_BIN)/clang not found — run 'make install-host'"; exit 1; }
	@test -d $(EMBENCH_SRC) || { echo "test-m6: ERROR: $(EMBENCH_SRC) not found — run 'make fetch'"; exit 1; }
	@mkdir -p .work/log/integ
	@echo "test-m6: [1/3] lit full MC suite (check-lit-full)"; \
	  $(MAKE) --no-print-directory check-lit-full > $(LIT_FULL_LOG) 2>&1; \
	  rc=$$?; \
	  tail -n 5 $(LIT_FULL_LOG); \
	  if [ $$rc -ne 0 ]; then echo "test-m6: FAIL (check-lit-full rc=$$rc)"; exit $$rc; fi
	@echo "test-m6: [2/3] lli value-level differential (host X86 vs DADAO target)"; \
	  $(PYTHON) $(DIFF_IR_LLI) --work-dir $(IR_LLI_WORK) > $(IR_LLI_LOG) 2>&1; \
	  rc=$$?; \
	  tail -n 6 $(IR_LLI_LOG); \
	  if [ $$rc -ne 0 ]; then echo "test-m6: FAIL (diff_ir_lli rc=$$rc)"; exit $$rc; fi
	@echo "test-m6: [3/3] Embench E2E (all benchmarks x -O0/-O2; judge guest exit 0)"; \
	  $(PYTHON) $(EMBENCH_E2E) --embench-src $(EMBENCH_SRC) --work-dir $(EMBENCH_E2E_WORK) \
	    > $(EMBENCH_E2E_LOG) 2>&1; \
	  rc=$$?; \
	  tail -n 8 $(EMBENCH_E2E_LOG); \
	  if [ $$rc -ne 0 ]; then echo "test-m6: FAIL (embench rc=$$rc)"; exit $$rc; fi
	@echo "test-m6: PASS (lit full + lli value-level diff + Embench E2E)"

# Legality drift gate (SPEC-074t): verifies LEGALITY sections in
# spec/SimRISC-01..12 exactly match content rendered from contracts/.
check-legality-drift:
	@$(PYTHON) tools/spec/check_legality_drift.py

# Legality invariants gate (SPEC-103t/ISS-079): ftroot/foroot n=2 constraint
# and rule-rename registry (new id effective, old id 0 hits) per contracts/.
check-legality-invariants:
	@$(PYTHON) tools/spec/check_legality_invariants.py

# Interface alignment gate (INTEG-003t / INTEG-007t): cross-module
# contract↔implementation consistency (LLVM/QEMU/opcodes/inventory).
check-interface:
	@$(PYTHON) tools/infra/check_interface_alignment.py

# Encoding validation gate (INTEG-008t): opcodes.yaml encoding consistency
# (value/mask, field overlap, bank, legality refs, decode conflicts).
validate-encoding: contracts/opcodes.yaml
	@$(PYTHON) tools/spec/validate_encoding.py contracts/opcodes.yaml

# InstrInfo cross-check gate (LLVM-046t / ISS-103): the committed
# DADAOInstrInfo.td (the .td truth, read from its patch) must match
# contracts/opcodes.yaml (the encoding truth).  Hermetic: reads only repo files,
# no .work/source checkout needed.
check-instrinfo:
	@$(PYTHON) tools/llvm/validate_instrinfo.py

# ISA<->backend coverage matrix drift gate (LLVM-081t; INFRA-069t 并入 L1):
# regenerates the two-layer projection from contracts/opcodes.yaml + the DADAO
# patch tree and byte-compares it against the committed matrix; drift => FAIL
# (lessons §2.11: generated projections need a drift gate).  Needs llvm-mc
# (run 'make install-host' first); counts are recomputed live, never hardcoded.
check-isa-coverage:
	@$(PYTHON) tools/llvm/gen_isa_coverage.py --check

# 逐条用例/pattern 删除哨兵 (INFRA-102t; ISS-102+ISS-118 合并, L1):
# 由现场语料重派生「身份清单」并与入库的 tests/case-ledger.tsv 逐字节比对；
# 删任一 vector 用例 / 任一 lit @@ OBJ: pattern ⇒ 少一行 ⇒ FAIL。
# 清单是生成物（--write 重生成），不含任何计数，无手写期望。
check-case-ledger:
	@$(PYTHON) tools/infra/check_case_ledger.py

# 测试根级索引门控 (TESTCASES-071t, L1): tests/{inst,arch,unit,tset}.yaml
# 只做静态校验（不跑 guest）：ID 全局唯一、file 存在于本 scope 目录、字段/
# platforms/level 合法、根级 *.yaml 的 scope 合法；计数现场派生、不写死。
# `--self-test` = 干净基线 + 13 类注入（各自可达 FAIL，含缺失 scope 目录）。
check-tests-index:
	@$(PYTHON) tools/testcases/check_tests_index.py

# rev 向量重派生门控 (ISS-335, L1): 由真源（contracts/opcodes.yaml + 独立 oracle）
# 重新派生 `tests/inst/rev/rev.yaml` 并逐字节比对；spec_cite/期望值/合法集任一漂移
# ⇒ FAIL。与 check-case-ledger 同层（L1），不重复进 L2/L3。
check-rev-vectors:
	@$(PYTHON) tools/testcases/generate_rev_vectors.py --check

# decodetree 可复现性 (ISS-058, L1): build-qemu recipe 必须固定 PYTHONHASHSEED=0；
# .work/source/qemu 在盘时实跑 decodetree 两种 seed，确认「敏感 ⇒ 已固定」。
check-decodetree-repro:
	@$(PYTHON) tools/qemu/check_decodetree_repro.py

# QEMU 形态哨兵 (ISS-225, L1): dadao-m1 的 umon syscall 接管实现符号 0 命中
# （helper.c.patch 必须存在且被扫描）。无需 qemu 二进制。
check-qemu-forms:
	@$(PYTHON) tools/qemu/semantics_gate.py --form-check

# Scope partition gate (SPEC-086t/089t; INFRA-102t 去计数): scope ∈
# {m1,fp,excluded,m3,m8,m9}；并集==全量、两两不交、每 scope 非空、
# excluded <=> decode ILLI (m1/fp/m3/m8/m9 carry none)、fp => id endswith _rf。
check-scope:
	@$(PYTHON) tools/spec/check_scope.py

# Rule references bidirectional gate (SPEC-071t): checks rule_refs in opcodes.yaml
# against legality_rules.yaml (ID existence + orphan detection with exemptions).
check-rule-refs: contracts/opcodes.yaml
	@$(PYTHON) tools/spec/check_rule_refs.py

# FP semantics contract gate (SPEC-087t; INFRA-102t 去计数): scope: fp 语义投影
# 完备性（id 集合双向/族集合现场双向/spec_cite/required_keys/规则引用由 legality
# 表达式现场派生/legality 双源/锚点/版本头）——不写死条数或族计数。
check-fp-contract:
	@$(PYTHON) tools/spec/check_fp_contract.py

# inst semantic execution gate (L3; SPEC-069t/INFRA-097t; TESTCASES-072t 更名+搬家)
# `make check-inst` = `tests/inst` 全量载体跑 QEMU；旧名 `check-qemu-semantics`
# 保留为**别名**（指向本目标）。QEMU 二进制取自安装根（ADR-0016 D9）。
# 载体集**现场派生**（册名/册数不写死）：`base/*.yaml` 全量 + 非 base 载体
# `rol/*.yaml`（QEMU-064t：rol.* scope m9）+ `atomics/*.yaml`（QEMU-067t）
# + `clmul/*.yaml`（QEMU-068t）。`rev/`、`bitcnt/` 不在本门控（M8 scope；见
# `tests/inst/inventory.md`「门控覆盖」）。ISS-235 = 载体集曾只覆盖 3/16 册。
# 结构断言（缺册/basename 重复/断链/0 册/运行 total ≠ 派生总数）+ 自证日志
# （ISS-236）在 `tools/qemu/semantics_gate.py`；`--check-only` 只跑派生+结构断言。
# 并发走 --jobs $(JOBS)（默认 8，禁 nproc）；退出码直传（无管道）。
# D6：gate 目录在 TEST_ARTIFACTS_DIR 下，日志在 .work/log/qemu/。
INST_DIR = $(CURDIR)/tests/inst
INST_SEM_DIR = $(TEST_ARTIFACTS_DIR)/harness/gate
INST_SEM_LOG = .work/log/qemu/check-inst.log
INST_TRAMPOLINE = tools/testcases/lib/trampoline.bin
_locked-check-inst:
	@mkdir -p .work/log/qemu || { echo "check-inst: ERROR: cannot create .work/log/qemu"; exit 1; }
	@$(PYTHON) tools/qemu/semantics_gate.py \
	    --vectors $(INST_DIR) --gate-dir $(INST_SEM_DIR) \
	    --qemu $(QEMU_BIN) --trampoline $(INST_TRAMPOLINE) \
	    --jobs $(JOBS) > $(INST_SEM_LOG) 2>&1; \
	  rc=$$?; \
	  tail -40 $(INST_SEM_LOG); \
	  if [ $$rc -ne 0 ]; then \
	    echo "check-inst: FAIL (rc=$$rc)"; \
	    exit $$rc; \
	  fi; \
	  echo "check-inst: PASS"

# inst 语义**冒烟**门控 (INFRA-058t, L2; TESTCASES-072t 更名+搬家):
# `check-inst` 的代表子集。代表集按 (class, mnemonic) **机械派生**（每组取第一条，
# 禁手工挑），计数现场统计；全量留在 L3（`check-full` → `check-inst`）。
# 旧名 `check-qemu-smoke` 保留为**别名**（指向本目标）。
INST_SMOKE_WORK = $(TEST_ARTIFACTS_DIR)/harness/smoke
INST_SMOKE_LOG = .work/log/qemu/check-inst-smoke.log
_locked-check-inst-smoke:
	@mkdir -p .work/log/qemu
	@test -x $(QEMU_BIN) || { echo "check-inst-smoke: ERROR: $(QEMU_BIN) not found — run 'make install-host' first"; exit 1; }
	@$(PYTHON) tools/testcases/inst/run_qemu_smoke.py --qemu $(QEMU_BIN) \
	    --trampoline $(INST_TRAMPOLINE) --vector-dir tests/inst/base \
	    --work-dir $(INST_SMOKE_WORK) --jobs $(JOBS) > $(INST_SMOKE_LOG) 2>&1; \
	  rc=$$?; \
	  tail -8 $(INST_SMOKE_LOG); \
	  if [ $$rc -ne 0 ]; then echo "check-inst-smoke: FAIL (rc=$$rc)"; exit $$rc; fi; \
	  echo "check-inst-smoke: PASS"

# ── 生成物管理 + 夜跑（TESTCASES-076t，P6）─────────────────────────────────────
# 生成物根 = `test_artifacts_dir`（`manifests/install-dirs.lock.toml`，禁硬编码）。
# scope → 目录的**映射表**单一真源 = `tools/testcases/manage_tests.py`（`SCOPE_MAP`）；
# 顶层出现未归属目录 ⇒ 红（防新产物目录悄悄长出）。
TESTS_ROOT ?= $(TEST_ARTIFACTS_DIR)
SCOPE ?=
DRY_RUN ?=
PRODUCER ?=
INJECT ?=
NIGHT_DATE ?=
NIGHT_DRY_RUN ?=
NIGHT_ALLOW_OVERWRITE ?=

# make clean-tests SCOPE=inst|arch|unit|tset|night|all [DRY_RUN=1]
_locked-clean-tests:
	@$(PYTHON) tools/testcases/manage_tests.py clean --scope "$(SCOPE)" --root "$(TESTS_ROOT)" $(if $(DRY_RUN),--dry-run,)

# make test-repro SCOPE=... [DRY_RUN=1] [PRODUCER='...'] [INJECT='...']
# 两次生产 + md5 逐文件比对；产物数 == 0 ⇒ 红（比较不为空）。
_locked-test-repro:
	@$(PYTHON) tools/testcases/manage_tests.py repro --scope "$(SCOPE)" --root "$(TESTS_ROOT)" $(if $(DRY_RUN),--dry-run,) $(if $(PRODUCER),--producer "$(PRODUCER)",) $(if $(INJECT),--inject "$(INJECT)",)

# make check-night  —— **由主会话** `setsid nohup make check-night > log 2>&1 &` 启动
# （本目标不自带 nohup，避免嵌套）；成员 = tset full×3 + 长 arch；报告只读落
# `<TESTS_ROOT>/night/<YYYY-MM-DD>/`（manifest.tsv / meta.json / run.log）。
_locked-check-night:
	@$(PYTHON) tools/testcases/night_run.py --root "$(TESTS_ROOT)" $(if $(NIGHT_DATE),--date $(NIGHT_DATE),) $(if $(NIGHT_DRY_RUN),--dry-run,) $(if $(NIGHT_ALLOW_OVERWRITE),--allow-overwrite,)

# make check-night-report —— 里程碑层：报告**存在性 + 结构 + 结果**（不跑长套件）；
# 未跑夜跑 ⇒ 明确 FAIL（不是 SKIP）。`NIGHT_DATE=` 指定日期，默认最新。
check-night-report:
	@$(PYTHON) tools/testcases/check_night_report.py --root "$(TESTS_ROOT)" $(if $(NIGHT_DATE),--date $(NIGHT_DATE),)

# 构建并行度（用户裁定 2026-10-01：限制 cc1plus 类进程）
JOBS ?= 8
