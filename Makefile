# DADAO-v5 top-level orchestration.
#
# Make is the stable user interface (ADR-0002: .tao/knowledge/adr-0002-build-orchestration.md); the actual manifest/fetch/patch
# logic is delegated to Python standard-library scripts under tools/infra/. All
# disposable data lives under .work/ (gitignored); persistent upstream mirrors
# live under .cache/ and are never touched by clean-work.

PYTHON ?= python3

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
        clean-work build-mc build-qemu build-gem5 docker-image docker-shell check \
        validate-vectors check-spec-refs check-spec-drift check-asm-list \
        check-interface validate-encoding

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
	@echo "  make apply-series    Apply ordered patch series to fetched sources"
	@echo "  make prepare         Fetch enabled components and apply their patch series"
	@echo "  make build-mc        Build LLVM MC tools (requires llvm-project enabled)"
	@echo "  make build-qemu      Configure and compile QEMU (requires qemu enabled)"
	@echo "  make build-gem5      Build gem5 (stub; command owned by the gem5 module)"
	@echo "  make docker-image    Build the development image ($(DOCKER_TAG))"
	@echo "  make docker-shell    Open a shell in the development image"
	@echo "  make clean-work      Remove generated .work content only"
	@echo "  make validate-vectors  Validate tests/vectors schema/inventory/coverage"
	@echo "  make check           Run repository-level structural checks"
	@echo "  make check-interface  Check cross-module interface alignment"
	@echo "  make validate-encoding  Validate opcodes.yaml encoding consistency"
	@echo "  make check-spec-drift  Audit contract provenance against README versions"
	@echo "  make check-spec-refs Audit spec references in contract-*.md (standalone)"
	@echo "  make check-asm-list  Check spec embedded assembly table consistency"

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

apply-series: manifest-check
	@$(PYTHON) tools/infra/apply_series.py

prepare: fetch apply-series

# DADAO is registered by adding it to LLVM_ALL_TARGETS in llvm/CMakeLists.txt
# (see ADR-0007).
build-mc: manifest-check
	@$(call component-enabled,llvm-project) || { \
	  echo "build-mc: component 'llvm-project' is not enabled / commit pending (manifests/components.lock.toml); refusing to fake success"; \
	  exit 1; \
	}
	cmake -G Ninja -B $(LLVM_BUILD) -S $(LLVM_SRC) \
	  -DLLVM_TARGETS_TO_BUILD=DADAO \
	  -DLLVM_ENABLE_PROJECTS="" \
	  -DCMAKE_BUILD_TYPE=RelWithDebInfo \
	  -DLLVM_ENABLE_ASSERTIONS=ON
	ninja -j$(JOBS) -C $(LLVM_BUILD) llvm-mc llvm-objdump llvm-objcopy llvm-readobj FileCheck not LLVMDADAOCodeGen
	@echo "build-mc: PASS"

build-qemu: manifest-check
	@$(call component-enabled,qemu) || { \
	  echo "build-qemu: component 'qemu' is not enabled / commit pending (manifests/components.lock.toml); refusing to fake success"; \
	  exit 1; \
	}
	mkdir -p $(QEMU_BUILD)
	cd $(QEMU_BUILD) && $(CURDIR)/$(QEMU_SRC)/configure \
	  --target-list=dadao-softmmu \
	  --enable-tcg \
	  --disable-werror
	$(MAKE) -C $(QEMU_BUILD) -j$(JOBS)
	@echo "build-qemu: PASS"

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

check: manifest-check validate-vectors check-spec-drift check-patch-tree check-asm-list check-interface validate-encoding check-qemu-semantics
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

# 组件补丁集校验 (2026-09-23): 树形补丁集四断言，见 docs/spec/component-patching.md。
check-patch-tree:
	@$(PYTHON) tools/infra/check_patch_tree.py

# spec 引用审计 (INFRA-011t): Check 1 引用有效性 + Check 2 无引用规范断言.
# Standalone target, not part of `make check`.
check-spec-refs:
	@$(PYTHON) tools/infra/check_spec_refs.py

# Spec embedded assembly list consistency (SPEC-037t).
check-asm-list:
	@$(PYTHON) tools/spec/check_asm_list_consistency.py

# Interface alignment gate (INTEG-003t / INTEG-007t): cross-module
# contract↔implementation consistency (LLVM/QEMU/opcodes/inventory).
check-interface:
	@$(PYTHON) tools/integ/check_interface_alignment.py

# Encoding validation gate (INTEG-008t): opcodes.yaml encoding consistency
# (value/mask, field overlap, bank, legality refs, decode conflicts).
validate-encoding: contracts/opcodes.yaml
	@$(PYTHON) tools/spec/validate_encoding.py contracts/opcodes.yaml

# QEMU semantic execution gate (SPEC-069t): runs ISA semantic test vectors
# through QEMU. Requires 'make build-qemu' to have been run.
# Runs all semantic/boundary cases in reg-shift-extend + reg-compare (~14s).
# Uses symlinked temp dir + --batch for full coverage.
# Exit code propagates correctly (no pipe; shell rc capture per AGENTS.md).
QEMU_SEM_DIR = /tmp/opencode/qemu-sem-gate
check-qemu-semantics:
	@mkdir -p $(QEMU_SEM_DIR) && \
	  ln -sf $(CURDIR)/tests/vectors/isa/reg-shift-extend.yaml $(QEMU_SEM_DIR)/ 2>/dev/null; \
	  ln -sf $(CURDIR)/tests/vectors/isa/reg-compare.yaml $(QEMU_SEM_DIR)/ 2>/dev/null; \
	  echo "check-qemu-semantics: running shift+compare (all cases)..."; \
	  $(PYTHON) tests/scripts/run_qemu_test.py --batch $(QEMU_SEM_DIR) > /tmp/opencode/check-qemu-sem.log 2>&1; \
	  rc=$$?; \
	  tail -5 /tmp/opencode/check-qemu-sem.log; \
	  if [ $$rc -ne 0 ]; then \
	    echo "check-qemu-semantics: FAIL (rc=$$rc)"; \
	    exit $$rc; \
	  fi; \
	  echo "check-qemu-semantics: PASS"

# 构建并行度（用户裁定 2026-10-01：限制 cc1plus 类进程）
JOBS ?= 8
