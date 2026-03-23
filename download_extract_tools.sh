#!/bin/bash

set -eu

SDK_VERSION=$1

python3 download_pico_toolchains.py $SDK_VERSION --output .
tar -xf arm-toolchain/arm-toolchain.tar.xz -C arm-toolchain --strip-components=1
rm arm-toolchain/arm-toolchain.tar.xz
tar -xzf riscv-toolchain/riscv-toolchain.tar.gz -C riscv-toolchain
rm riscv-toolchain/riscv-toolchain.tar.gz
tar -xzf picotool/picotool.tar.gz -C picotool
rm picotool/picotool.tar.gz
tar -xzf pico-sdk-tools/pico-sdk-tools.tar.gz -C pico-sdk-tools
rm pico-sdk-tools/pico-sdk-tools.tar.gz
