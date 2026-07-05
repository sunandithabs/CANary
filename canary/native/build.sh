#!/usr/bin/env bash
# Builds the native CRC-15 shared library.
# Run this once after cloning the repo (or whenever crc15.c changes).
set -euo pipefail
cd "$(dirname "$0")"
gcc -shared -fPIC -O2 -o libcrc15.so crc15.c
echo "Built libcrc15.so"
