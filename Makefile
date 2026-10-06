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
TARGET_SYSROOT_DIR := $(shell $(PYTHON) tools/infra/paths.py target_sysroot_dir)
TEST_ARTIFACTS_DIR := $(shell $(PYTHON) tools/infra/paths.py test_artifacts_dir)

# Non-empty guard: abort if any path variable is empty (manifest missing/corrupt).
_install_dir_vars = REPO_ROOT SDK_DIR HOST_TOOLCHAIN_DIR HOST_TOOLCHAIN_BIN TARGET_SYSROOT_DIR TEST_ARTIFACTS_DIR
$(foreach v,$(_install_dir_vars),$(if $($v),,$(error $v is empty — check manifests/install-dirs.lock.toml and tools/infra/paths.py)))

# Component source/build trees (all under the disposable .work/ root). The
# llvm source is the monorepo checkout with its `llvm/` project subdirectory.
QEMU_SRC   ?= .work/source/qemu
QEMU_BUILD ?= .work/build/qemu
LLVM_SRC   ?= .work/source/llvm-project/llvm
LLVM_BUILD ?= .work/build/llvm
GEM5_SRC   ?= .work/source/gem5
GEM5_BUILD ?= .work/build/gem5

DOCKER_TAG ?= dadao-v5-dev:local

.DEFAULT_GOAL := help

.PHONY: help manifest-check doctor status fetch fetch-refs apply-series prepare \
        clean-work build-mc build-mc-lite build-mc-reconfig build-lld \
        build-qemu build-qemu-reconfig build-gem5 docker-image docker-shell check \
        validate-vectors check-spec-refs check-spec-drift check-asm-list \
        check-legality-drift check-interface validate-encoding check-scope \
        check-rule-refs check-fp-contract check-instrinfo \
        check-dirs check-no-residue check-cfx-aliases check-asm-prose check-lit \
        test-codegen \
        check-patch-tree check-index-blobs check-source-state check-asm-list-drift size-report \
        check-tasks check-spec-codeblocks check-legality-invariants

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
	@echo "  make build-mc        Build LLVM MC + CodeGen tools incl. llc (skips cmake if build.ninja exists)"
	@echo "  make build-mc-lite   Build LLVM MC/objdump/FileCheck/not only (no objcopy/readobj/CodeGen)"
	@echo "  make build-mc-reconfig  Force cmake re-run then build LLVM MC + CodeGen tools incl. llc"
	@echo "  make build-lld       Build LLD linker (bin/ld.lld); re-runs cmake with LLVM_ENABLE_PROJECTS=lld"
	@echo "  make build-qemu      Compile QEMU (skips configure if build.ninja exists)"
	@echo "  make build-qemu-reconfig  Force configure re-run then compile QEMU"
	@echo "  make build-gem5      Build gem5 (stub; command owned by the gem5 module)"
	@echo "  make docker-image    Build the development image ($(DOCKER_TAG))"
	@echo "  make docker-shell    Open a shell in the development image"
	@echo "  make clean-work      Remove generated .work content only"
	@echo "  make validate-vectors  Validate tests/vectors schema/inventory/coverage"
	@echo "  make check           Run repository-level structural checks"
	@echo "  make check-interface  Check cross-module interface alignment"
	@echo "  make validate-encoding  Validate opcodes.yaml encoding consistency"
	@echo "  make check-scope     Check opcodes.yaml scope partition (m1/fp/excluded; SPEC-086t)"
	@echo "  make check-spec-drift  Audit contract provenance against README versions"
	@echo "  make check-spec-refs Audit spec references in contract-*.md (standalone)"
	@echo "  make check-asm-list  Check spec embedded assembly table consistency"
	@echo "  make check-asm-prose  Check prose assembly format gate (strict mode)"
	@echo "  make check-spec-codeblocks  Check spec prose \`\`\`simrisc blocks vs opcodes.yaml (ISS-077)"
	@echo "  make check-lit        Run lit MC + E2E tests (requires build-mc + build-qemu)"
	@echo "  make test-codegen     Run M3 CodeGen E2E gate (llc->llvm-mc->objcopy->qemu; INTEG-012t)"
	@echo "  make check-patch-tree  Check component patch tree (spec/Process-01, 9 assertions)"
	@echo "  make check-index-blobs  Check new-file patch index blob hashes (INFRA-038t/ISS-119)"
	@echo "  make check-legality-drift  Check LEGALITY section drift gate (SPEC-074t)"
	@echo "  make check-legality-invariants  Check ftroot/foroot n=2 + rule-rename gate (ISS-079)"
	@echo "  make check-rule-refs  Check rule_refs bidirectional gate (SPEC-071t)"
	@echo "  make check-fp-contract  Check FP semantics contract completeness (SPEC-087t)"
	@echo "  make check-instrinfo  Cross-check DADAOInstrInfo.td against opcodes.yaml (LLVM-046t)"
	@echo "  make check-cfx-aliases  Check cfx alias table drift gate (SPEC-075t)"
	@echo "  make check-asm-list-drift  Check assembly-list drift gate (INFRA-027t)"
	@echo "  make check-dirs      Validate install-dirs paths and symlink prefix guard"
	@echo "  make check-no-residue  Detect unexpected untracked temp files"
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
# build-mc skips cmake when build.ninja already exists (incremental fast path).
# Use build-mc-reconfig to force a cmake re-run (e.g. after changing CMakeLists.txt).
LLVM_MC_FULL_TARGETS = llvm-mc llvm-objdump llvm-objcopy llvm-readobj FileCheck not LLVMDADAOCodeGen llc
LLVM_MC_LITE_TARGETS = llvm-mc llvm-objdump FileCheck not

build-mc: manifest-check
	@$(call component-enabled,llvm-project) || { \
	  echo "build-mc: component 'llvm-project' is not enabled / commit pending (manifests/components.lock.toml); refusing to fake success"; \
	  exit 1; \
	}
	@test -f $(LLVM_BUILD)/build.ninja || \
	  cmake -G Ninja -B $(LLVM_BUILD) -S $(LLVM_SRC) \
	    -DLLVM_TARGETS_TO_BUILD=DADAO \
	    -DLLVM_ENABLE_PROJECTS="" \
	    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
	    -DLLVM_ENABLE_ASSERTIONS=ON
	ninja -j$(JOBS) -C $(LLVM_BUILD) $(LLVM_MC_FULL_TARGETS)
	@echo "build-mc: PASS"

# build-mc-lite: same as build-mc but omits llvm-objcopy, llvm-readobj, and
# LLVMDADAOCodeGen.  Sufficient for lit MC tests + encoding oracle + FileCheck.
build-mc-lite: manifest-check
	@$(call component-enabled,llvm-project) || { \
	  echo "build-mc-lite: component 'llvm-project' is not enabled / commit pending; refusing to fake success"; \
	  exit 1; \
	}
	@test -f $(LLVM_BUILD)/build.ninja || \
	  cmake -G Ninja -B $(LLVM_BUILD) -S $(LLVM_SRC) \
	    -DLLVM_TARGETS_TO_BUILD=DADAO \
	    -DLLVM_ENABLE_PROJECTS="" \
	    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
	    -DLLVM_ENABLE_ASSERTIONS=ON
	ninja -j$(JOBS) -C $(LLVM_BUILD) $(LLVM_MC_LITE_TARGETS)
	@echo "build-mc-lite: PASS"

# build-mc-reconfig: always re-run cmake (for when CMakeLists.txt / patches change).
build-mc-reconfig: manifest-check
	@$(call component-enabled,llvm-project) || { \
	  echo "build-mc-reconfig: component 'llvm-project' is not enabled / commit pending; refusing to fake success"; \
	  exit 1; \
	}
	cmake -G Ninja -B $(LLVM_BUILD) -S $(LLVM_SRC) \
	  -DLLVM_TARGETS_TO_BUILD=DADAO \
	  -DLLVM_ENABLE_PROJECTS="" \
	  -DCMAKE_BUILD_TYPE=RelWithDebInfo \
	  -DLLVM_ENABLE_ASSERTIONS=ON
	ninja -j$(JOBS) -C $(LLVM_BUILD) $(LLVM_MC_FULL_TARGETS)
	@echo "build-mc-reconfig: PASS"

# build-lld: build the LLD linker (produces .work/build/llvm/bin/ld.lld).
# See INFRA-043t.
#
# LLD is an LLVM sub-project, so it only exists when CMake is configured with
# -DLLVM_ENABLE_PROJECTS=lld — a different configuration from build-mc
# (LLVM_ENABLE_PROJECTS="").  build-mc/build-mc-lite/build-mc-reconfig share
# this same .work/build/llvm tree, so build-lld re-runs cmake there to switch
# the project set.  build-mc's incremental fast path (ninja over the existing
# build.ninja) keeps working afterwards, and build-mc-reconfig restores the
# lld-less configuration.  Unlike build-mc we cannot skip cmake when build.ninja
# already exists: that guard would keep the lld-less configuration and leave the
# `lld` target unavailable.
#
# The ninja target is `lld` (not `ld.lld`): lld/CMakeLists.txt creates the
# `ld.lld`/`lld-link`/`ld64.lld`/`wasm-ld` names as POST_BUILD copies of the
# `lld` executable (add_lld_symlink -> ALWAYS_GENERATE), so no separate ninja
# target named ld.lld exists.  Building `lld` writes bin/ld.lld.
LLD_TARGETS = lld

build-lld: manifest-check
	@$(call component-enabled,llvm-project) || { \
	  echo "build-lld: component 'llvm-project' is not enabled / commit pending (manifests/components.lock.toml); refusing to fake success"; \
	  exit 1; \
	}
	cmake -G Ninja -B $(LLVM_BUILD) -S $(LLVM_SRC) \
	  -DLLVM_TARGETS_TO_BUILD=DADAO \
	  -DLLVM_ENABLE_PROJECTS=lld \
	  -DCMAKE_BUILD_TYPE=RelWithDebInfo \
	  -DLLVM_ENABLE_ASSERTIONS=ON
	ninja -j$(JOBS) -C $(LLVM_BUILD) $(LLD_TARGETS)
	@echo "build-lld: PASS"

# build-qemu skips configure when build.ninja already exists (incremental fast
# path).  After applying patches that only touch .c/.h files (not meson.build),
# the incremental path compiles only changed objects (~3s for one file).
# Use build-qemu-reconfig to force a full configure (e.g. after changing
# meson.build or configure options).
build-qemu: manifest-check
	@$(call component-enabled,qemu) || { \
	  echo "build-qemu: component 'qemu' is not enabled / commit pending (manifests/components.lock.toml); refusing to fake success"; \
	  exit 1; \
	}
	@if [ -f $(QEMU_BUILD)/build.ninja ]; then \
	  echo "build-qemu: build.ninja exists, skipping configure (use build-qemu-reconfig to force)"; \
	else \
	  mkdir -p $(QEMU_BUILD) && \
	  cd $(QEMU_BUILD) && $(CURDIR)/$(QEMU_SRC)/configure \
	    --target-list=dadao-softmmu \
	    --enable-tcg \
	    --disable-werror; \
	fi
	$(MAKE) -C $(QEMU_BUILD) -j$(JOBS)
	@echo "build-qemu: PASS"

# build-qemu-reconfig: always re-run configure (for when meson.build changes).
build-qemu-reconfig: manifest-check
	@$(call component-enabled,qemu) || { \
	  echo "build-qemu-reconfig: component 'qemu' is not enabled / commit pending; refusing to fake success"; \
	  exit 1; \
	}
	mkdir -p $(QEMU_BUILD)
	cd $(QEMU_BUILD) && $(CURDIR)/$(QEMU_SRC)/configure \
	  --target-list=dadao-softmmu \
	  --enable-tcg \
	  --disable-werror
	$(MAKE) -C $(QEMU_BUILD) -j$(JOBS)
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

docker-image:
	docker build -t $(DOCKER_TAG) containers/dev

docker-shell:
	docker run --rm -it -v "$(PWD):/workspace" $(DOCKER_TAG) /bin/bash

clean-work:
	@$(PYTHON) tools/infra/clean_work.py

check: manifest-check validate-vectors check-spec-drift check-patch-tree check-index-blobs check-asm-list check-asm-list-drift check-asm-prose check-spec-codeblocks check-legality-drift check-legality-invariants check-interface validate-encoding check-scope check-rule-refs check-fp-contract check-instrinfo check-qemu-semantics check-cfx-aliases check-dirs check-no-residue check-lit
	@$(PYTHON) tools/infra/check_issues.py
	@$(PYTHON) -m compileall -q tools
	@echo "repository checks: PASS"

# Vector schema/inventory/coverage gate (TESTCASES-002t). Requires the M1
# encoding table (contracts/opcodes.yaml) to exist.
validate-vectors: contracts/opcodes.yaml
	@$(PYTHON) tools/testcases/validate_vectors.py

# spec drift check (INFRA-012t): fail-closed provenance audit for contract-*.md.
check-spec-drift:
	@$(PYTHON) tools/infra/check_spec_drift.py

# 组件补丁集校验 (2026-09-23): 树形补丁集断言（现 9 条），见 spec/Process-01-组件补丁组织与构建编排.md。
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
# 规则见 spec/Process-01 §11「组件源文件规模约定」。
size-report:
	@$(PYTHON) tools/infra/size_report.py

# 待收尾任务自查 (INFRA-029t): 报告型，列出「完成区已填 + 待验收」的漏 /complete 任务。
# 默认退出码 0，不并入 `make check` 阻断路径；--strict 时命中 >0 则失败。
check-tasks:
	@$(PYTHON) tools/infra/check_tasks.py

# spec 引用审计 (INFRA-011t): Check 1 引用有效性 + Check 2 无引用规范断言.
# Standalone target, not part of `make check`.
check-spec-refs:
	@$(PYTHON) tools/infra/check_spec_refs.py

# cfx alias drift gate (SPEC-075t): verify .tao/knowledge/contract-cfx-aliases.md is up-to-date.
check-cfx-aliases:
	@$(PYTHON) tools/spec/check_cfx_aliases.py

# Install/product directory path guard (INFRA-019t): validates
# manifests/install-dirs.lock.toml and scans for symlink prefix violations.
check-dirs:
	@$(PYTHON) tools/infra/check_dirs.py

# Residue gate (INFRA-025t): detect unexpected untracked temp files.
check-no-residue:
	@$(PYTHON) tools/infra/check_dirs.py --residue

# Spec embedded assembly list consistency (SPEC-037t).
check-asm-list:
	@$(PYTHON) tools/spec/check_asm_list_consistency.py

# Assembly-list drift gate (INFRA-027t): verify .tao/knowledge/contract-asm-list.md
# is up-to-date (regenerates to a temp file, byte-diff; never overwrites).
check-asm-list-drift:
	@$(PYTHON) tools/spec/check_asm_list_drift.py

# Assembly prose format gate (SPEC-076t): detect old-format assembly
# in prose fenced-code blocks.  --strict: exit 1 if any violation (baseline=0).
check-asm-prose:
	@$(PYTHON) tools/spec/check_asm_prose.py --strict

# Spec prose ```simrisc code-block gate (SPEC-103t/ISS-077): every instruction
# line in spec/**/*.md (excl. historical SimRISC-0.5.3) must use a mnemonic
# from contracts/opcodes.yaml (pseudo-instructions excepted) with a valid
# operand count.
check-spec-codeblocks:
	@$(PYTHON) tools/spec/check_spec_codeblocks.py

# lit gate (INFRA-021t): run llvm-lit on MC (22/22) + E2E (3/3).
# MC needs llvm-mc/llvm-objdump/FileCheck (build-mc-lite suffices).
# E2E needs llvm-objcopy (full build-mc) + qemu-system-dadao (build-qemu) + trampoline.
# llvm-lit missing => explicit error (never silent skip).
LIT_BIN = $(LLVM_BUILD)/bin/llvm-lit
check-lit:
	@test -x $(LIT_BIN) || { echo "check-lit: ERROR: $(LIT_BIN) not found — run 'make build-mc' first"; exit 1; }
	$(LIT_BIN) tests/llvm/lit/MC/DADAO tests/e2e/lit -v

# M3 CodeGen end-to-end gate (INTEG-012t).  Reuses the build-mc/build-qemu
# build trees.  Pipeline (single TU, per ADR-0003 D5):
#   llc -march=dadao <prog.ll> -> .s; cat codegen_crt0.s prog.s -> .s;
#   llvm-mc --triple=dadao -filetype=obj -> .o;
#   llvm-objcopy -O binary --only-section=.text -> .bin;
#   qemu-system-dadao -M dadao-m1 -bios trampoline.bin -kernel .bin ...
# The guest process exit code is compared against tests/llvm/codegen/expected.yaml.
# Fail-closed: any mismatch / timeout / machine fault => non-zero exit.
LLC_BIN = $(LLVM_BUILD)/bin/llc
LLVM_MC_BIN = $(LLVM_BUILD)/bin/llvm-mc
LLVM_OBJCOPY_BIN = $(LLVM_BUILD)/bin/llvm-objcopy
QEMU_BIN = $(QEMU_BUILD)/qemu-system-dadao
CODEGEN_E2E_WORK = tests/llvm/codegen-e2e
CODEGEN_E2E_LOG = .work/log/integ/test-codegen.log
test-codegen: build-mc build-qemu
	@test -x $(LLC_BIN) || { echo "test-codegen: ERROR: $(LLC_BIN) not found"; exit 1; }
	@test -x $(LLVM_MC_BIN) || { echo "test-codegen: ERROR: $(LLVM_MC_BIN) not found"; exit 1; }
	@test -x $(LLVM_OBJCOPY_BIN) || { echo "test-codegen: ERROR: $(LLVM_OBJCOPY_BIN) not found"; exit 1; }
	@test -x $(QEMU_BIN) || { echo "test-codegen: ERROR: $(QEMU_BIN) not found"; exit 1; }
	@rm -rf $(CODEGEN_E2E_WORK); \
	  mkdir -p .work/log/integ; \
	  $(PYTHON) tools/integ/run_codegen_e2e.py \
	    --llc $(LLC_BIN) --llvm-mc $(LLVM_MC_BIN) --llvm-objcopy $(LLVM_OBJCOPY_BIN) \
	    --qemu $(QEMU_BIN) --trampoline tests/scripts/trampoline.bin \
	    --crt0 tests/scripts/codegen_crt0.s --work-dir $(CODEGEN_E2E_WORK) \
	    > $(CODEGEN_E2E_LOG) 2>&1; \
	  rc=$$?; \
	  tail -20 $(CODEGEN_E2E_LOG); \
	  if [ $$rc -ne 0 ]; then echo "test-codegen: FAIL (rc=$$rc)"; exit $$rc; fi; \
	  echo "test-codegen: PASS"

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
	@$(PYTHON) tools/integ/check_interface_alignment.py

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

# Scope partition gate (SPEC-086t/089t): opcodes.yaml scope ∈ {m1,fp,excluded},
# counts 152/60/15/227, excluded <=> decode ILLI (m1/fp carry none),
# fp <=> id endswith _rf, and the old M1-exclusion boolean field has disappeared.
check-scope:
	@$(PYTHON) tools/spec/check_scope.py

# Rule references bidirectional gate (SPEC-071t): checks rule_refs in opcodes.yaml
# against legality_rules.yaml (ID existence + orphan detection with exemptions).
check-rule-refs: contracts/opcodes.yaml
	@$(PYTHON) tools/spec/check_rule_refs.py

# FP semantics contract gate (SPEC-087t): scope: fp 60 条语义投影完备性
# (id 双向覆盖/12 族计数/spec_cite/required_keys/legality 双向/锚点/版本头)。
check-fp-contract:
	@$(PYTHON) tools/spec/check_fp_contract.py

# QEMU semantic execution gate (SPEC-069t): runs ISA semantic test vectors
# through QEMU. Requires 'make build-qemu' to have been run.
# Runs all semantic/boundary cases in reg-shift-extend + reg-compare.
# Uses symlinked temp dir + --batch for full coverage; cases run in parallel
# via --jobs $(JOBS) (JOBS defaults to 8; never nproc/full-core).
# Exit code propagates correctly (no pipe; shell rc capture per AGENTS.md).
# D6 compliance: gate dir under TEST_ARTIFACTS_DIR, log under .work/log/qemu/.
# ISS-089: the gate dir is transient, so the setup must be explicit — create it,
# then verify each vector is a symlink resolving to the expected file. ln errors
# are NOT swallowed (a silent failure would feed the gate the wrong/empty input).
QEMU_SEM_DIR = $(TEST_ARTIFACTS_DIR)/harness/gate
QEMU_SEM_LOG = .work/log/qemu/check-qemu-semantics.log
QEMU_SEM_VEC_DIR = $(CURDIR)/tests/vectors/isa
check-qemu-semantics:
	@mkdir -p .work/log/qemu || { echo "check-qemu-semantics: ERROR: cannot create .work/log/qemu"; exit 1; }; \
	  mkdir -p $(QEMU_SEM_DIR) || { echo "check-qemu-semantics: ERROR: cannot create gate dir $(QEMU_SEM_DIR) (path occupied?)"; exit 1; }; \
	  for v in reg-shift-extend.yaml reg-compare.yaml; do \
	    [ -e $(QEMU_SEM_VEC_DIR)/$$v ] || { echo "check-qemu-semantics: ERROR: vector $(QEMU_SEM_VEC_DIR)/$$v not found"; exit 1; }; \
	    ln -sf $(QEMU_SEM_VEC_DIR)/$$v $(QEMU_SEM_DIR)/$$v || { echo "check-qemu-semantics: ERROR: failed to symlink $$v into $(QEMU_SEM_DIR)"; exit 1; }; \
	    [ -L $(QEMU_SEM_DIR)/$$v ] || { echo "check-qemu-semantics: ERROR: $(QEMU_SEM_DIR)/$$v is not a symlink (stale/occupied path?)"; exit 1; }; \
	    [ "$$(readlink -f $(QEMU_SEM_DIR)/$$v)" = "$$(readlink -f $(QEMU_SEM_VEC_DIR)/$$v)" ] || { echo "check-qemu-semantics: ERROR: $(QEMU_SEM_DIR)/$$v does not point to $(QEMU_SEM_VEC_DIR)/$$v"; exit 1; }; \
	  done; \
	  echo "check-qemu-semantics: running shift+compare (all cases)..."; \
	  $(PYTHON) tests/scripts/run_qemu_test.py --batch $(QEMU_SEM_DIR) --jobs $(JOBS) > $(QEMU_SEM_LOG) 2>&1; \
	  rc=$$?; \
	  tail -5 $(QEMU_SEM_LOG); \
	  if [ $$rc -ne 0 ]; then \
	    echo "check-qemu-semantics: FAIL (rc=$$rc)"; \
	    rm -rf $(QEMU_SEM_DIR); \
	    exit $$rc; \
	  fi; \
	  rm -rf $(QEMU_SEM_DIR); \
	  echo "check-qemu-semantics: PASS"

# 构建并行度（用户裁定 2026-10-01：限制 cc1plus 类进程）
JOBS ?= 8
