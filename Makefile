# DADAO-v5 top-level orchestration.
#
# Make is the stable user interface (ADR-0002: .tao/knowledge/adr-0002-build-orchestration.md); the actual manifest/fetch/patch
# logic is delegated to Python standard-library scripts under scripts/. All
# disposable data lives under .work/ (gitignored); persistent upstream mirrors
# live under .cache/ and are never touched by clean-work.

PYTHON ?= python3

# Component source/build trees (all under the disposable .work/ root). The
# llvm source is the monorepo checkout with its `llvm/` project subdirectory.
QEMU_SRC   ?= .work/source/qemu
QEMU_BUILD ?= .work/build/qemu
LLVM_SRC   ?= .work/source/llvm/llvm
LLVM_BUILD ?= .work/build/llvm
GEM5_SRC   ?= .work/source/gem5
GEM5_BUILD ?= .work/build/gem5

DOCKER_TAG ?= dadao-v5-dev:local

.DEFAULT_GOAL := help

.PHONY: help manifest-check doctor status fetch fetch-refs apply-series prepare \
        clean-work build-mc build-qemu build-gem5 docker-image docker-shell check

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
	@echo "  make build-mc        Build LLVM MC tools (stub until llvm commit is locked)"
	@echo "  make build-qemu      Configure and compile QEMU (stub until qemu commit is locked)"
	@echo "  make build-gem5      Build gem5 (stub; command owned by the gem5 module)"
	@echo "  make docker-image    Build the development image ($(DOCKER_TAG))"
	@echo "  make docker-shell    Open a shell in the development image"
	@echo "  make clean-work      Remove generated .work content only"
	@echo "  make check           Run repository-level structural checks"

manifest-check:
	@$(PYTHON) scripts/manifest_check.py

doctor:
	@$(PYTHON) scripts/doctor.py

status:
	@$(PYTHON) scripts/status.py

fetch: manifest-check
	@$(PYTHON) scripts/fetch.py

fetch-refs: manifest-check
	@$(PYTHON) scripts/fetch_refs.py

apply-series: manifest-check
	@$(PYTHON) scripts/apply_series.py

prepare: fetch apply-series

# -DLLVM_TARGETS_TO_BUILD=DADAO is a placeholder: the exact target name is
# registered by the llvm module (0.5.3) and must be confirmed there.
build-mc: manifest-check
	@$(call component-enabled,llvm) || { \
	  echo "build-mc: component 'llvm' is not enabled / commit pending (manifests/components.lock.toml); refusing to fake success"; \
	  exit 1; \
	}
	cmake -G Ninja -B $(LLVM_BUILD) -S $(LLVM_SRC) \
	  -DLLVM_TARGETS_TO_BUILD=DADAO \
	  -DLLVM_ENABLE_PROJECTS="" \
	  -DCMAKE_BUILD_TYPE=RelWithDebInfo \
	  -DLLVM_ENABLE_ASSERTIONS=ON
	ninja -C $(LLVM_BUILD) llvm-mc llvm-objdump
	@echo "build-mc: PASS"

build-qemu: manifest-check
	@$(call component-enabled,qemu) || { \
	  echo "build-qemu: component 'qemu' is not enabled / commit pending (manifests/components.lock.toml); refusing to fake success"; \
	  exit 1; \
	}
	cd $(QEMU_SRC) && ./configure \
	  --target-list=dadao-softmmu \
	  --enable-tcg \
	  --disable-werror
	$(MAKE) -C $(QEMU_SRC) -j$$(nproc)
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
	@$(PYTHON) scripts/clean_work.py

check: manifest-check
	@$(PYTHON) -m compileall -q scripts
	@echo "repository checks: PASS"
