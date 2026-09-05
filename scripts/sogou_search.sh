#!/bin/bash
cd /vol2/1000/docker_related/gzh-chroma
for Q in "中国式牛市" "村级三好" "vx_163" "MzU0MzU1ODI3MA"; do
    echo "=== $Q ==="
    python3 sogou_playwright.py "$Q" 2 "tmp_$$.json" 2>&1 | tail -n 8
    rm -f "tmp_$$.json"
done
