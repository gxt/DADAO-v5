# DADAO-v5 development container.
#
# Reproducible build-dependency image for the "clean host / dev container"
# build path. It ships only toolchain dependencies -- no DADAO implementation
# or patches; sources are fetched and patched inside the mounted /workspace via
# `make fetch` + `make apply-series`.
#
# The base image is pinned to a fixed release so the image is reproducible.
FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive

# Build dependencies (M1 scope: LLVM MC + QEMU):
#   - LLVM: cmake / ninja / bison / flex / zlib / libzstd
#   - QEMU: glib / pixman / fdt
#   - clang: doctor.py's native build path requires both ninja and clang
# gem5 dependencies are intentionally NOT installed here: gem5 is out of M1
# scope. Add them when the gem5 module starts; they must not gate the M1
# milestone.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential ca-certificates cmake git ninja-build clang python3 \
    bison flex pkg-config libglib2.0-dev libpixman-1-dev libfdt-dev \
    zlib1g-dev libzstd-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
