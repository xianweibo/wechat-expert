#!/bin/bash
set -e
cd /vol2/1000/docker_related/gzh-chroma
cat > one_url.json <<'JSON'
[
  {"title":"中国式牛市最最最好","url":"http://mp.weixin.qq.com/s?__biz=MzU0MzU1ODI3MA==&mid=2247483975&idx=1&sn=7d157bf9076cbcaca5bbd28004f79d40&chksm=fb08dd56cc7f5440fe8919bd163644eea6f15b9751d6ff023cd7b7fc2fc5ee3639b7f3b2ea19#rd"}
]
JSON
mkdir -p articles_smoke
python3 fetch_articles.py one_url.json articles_smoke 2>&1 | tail -n 30
echo '---'
ls -la articles_smoke/
