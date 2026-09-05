#!/bin/bash
# Deploy updated mp_proxy.ts from paste.rs
set -e

PASTE_URL="https://paste.rs/5fc0b"
APP_DIR="/home/gongzhonghao/apps/gzh-expert-git"
TS=$(date +%Y%m%d_%H%M%S)

cd "${APP_DIR}"

echo "==> backup existing mp_proxy.ts"
sudo -n cp -v src/mp_proxy.ts "src/mp_proxy.ts.bak.${TS}" 2>/dev/null || true

echo "==> fetch new mp_proxy.ts from paste.rs"
curl -fsSL "${PASTE_URL}" -o /tmp/mp_proxy.ts.new
echo "    downloaded $(wc -c < /tmp/mp_proxy.ts.new) bytes"

echo "==> skip standalone tsc check (project deps are installed by docker build)"
# echo "==> syntax check" skipped: node:20-alpine lacks project deps; rely on docker build to catch type errors

echo "==> install to ${APP_DIR}/src/mp_proxy.ts"
sudo -n cp /tmp/mp_proxy.ts.new src/mp_proxy.ts
sudo -n chown gongzhonghao:gongzhonghao src/mp_proxy.ts 2>/dev/null || true

echo "==> rebuild & restart app container"
sudo -n docker compose -f docker-compose.yml up -d --build app 2>&1 | tail -n 20

echo "==> wait & test"
sleep 6
APP_ID="wx567a639466e247cd"
APP_SECRET="${WECHAT_APP_SECRET:?need WECHAT_APP_SECRET in env}"
CONTAINER=$(sudo -n docker ps --filter name=gzh-expert-app -q | head -n1)
TOKEN=$(sudo -n docker exec "$CONTAINER" wget -qO- "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=${APP_ID}&secret=${APP_SECRET}" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("access_token",""))')
echo "token=${TOKEN:0:20}..."

echo "=== test /api/admin/mp-published ==="
curl -s -X POST http://127.0.0.1:39800/api/admin/mp-published \
    -H "X-Worker-Secret: ${BILIBILI_WORKER_SECRET:?need BILIBILI_WORKER_SECRET in env}" \
    -H "Content-Type: application/json" \
    --data '{}' | python3 -c 'import sys,json; d=json.load(sys.stdin); print(json.dumps({k: (len(v) if isinstance(v,list) else v) for k,v in d.items()}, ensure_ascii=False))'

echo
echo "=== test /api/admin/mp-articles-all ==="
curl -s -X POST http://127.0.0.1:39800/api/admin/mp-articles-all \
    -H "X-Worker-Secret: ${BILIBILI_WORKER_SECRET:?need BILIBILI_WORKER_SECRET in env}" \
    -H "Content-Type: application/json" \
    --data '{}' | python3 -c 'import sys,json; d=json.load(sys.stdin); a=d.get("articles",[]); print(f"total={d.get(\"total\")} got={len(a)}"); [print(f"  - {x[\"publish_time\"]} | {x[\"title\"][:50]} | {len(x[\"content\"])} chars | {x[\"author\"]}") for x in a]'
