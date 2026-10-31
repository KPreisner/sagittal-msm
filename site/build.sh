#!/usr/bin/env sh
# Assemble the GitHub Pages site: the page, its script, and the committed charts and figures.
# Usage: sh site/build.sh [output-dir]   (default: _site)
set -eu
out="${1:-_site}"
rm -rf "$out"
mkdir -p "$out/img"
cp site/index.html site/app.js "$out/"
cp docs/figures/slicing.png "$out/img/"
cp benchmarks/results/gpu_2023.png benchmarks/results/compare.png \
   benchmarks/results/structure.png benchmarks/results/memory.png "$out/img/"
echo "Built site in $out/"
