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

# Build dependencies:
#   - LLVM: cmake / ninja / bison / flex / zlib / libzstd
#   - QEMU: glib / pixman / fdt
#   - clang: doctor.py's native build path requires both ninja and clang
#   - gem5: scons / m4 / python3-dev / libprotobuf / libhdf5 / libpng
#     (v5 addition; the exact list is pending confirmation by the gem5 module,
#     candidates taken from INFRA-007t. zlib1g-dev is shared with LLVM above.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential ca-certificates cmake git ninja-build clang python3 \
    bison flex pkg-config libglib2.0-dev libpixman-1-dev libfdt-dev \
    zlib1g-dev libzstd-dev \
    scons m4 python3-dev python3-pip \
    libprotobuf-dev protobuf-compiler libhdf5-dev libpng-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
