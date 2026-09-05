#!/bin/bash
set -e
APP_ID="wx567a639466e247cd"
APP_SECRET="${WECHAT_APP_SECRET:?need WECHAT_APP_SECRET in env}"

TOKEN=$(curl -sS "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=${APP_ID}&secret=${APP_SECRET}" | python3 -c "import json,sys; print(json.loads(sys.stdin.read()).get('access_token',''))")
echo "TOKEN=${TOKEN:0:20}..."

# Try various endpoints
echo ""
echo "=== 1. freepublish/list ==="
curl -sS --max-time 15 "https://api.weixin.qq.com/cgi-bin/freepublish/list?access_token=${TOKEN}&offset=0&count=20" -w " HTTP:%{http_code}\n" -o /tmp/fp1.json
cat /tmp/fp1.json | head -c 400

echo ""
echo "=== 2. freepublish/getarticle (newer API) ==="
curl -sS --max-time 15 "https://api.weixin.qq.com/cgi-bin/freepublish/getarticle?access_token=${TOKEN}&offset=0&count=20" -w " HTTP:%{http_code}\n" -o /tmp/fp2.json
cat /tmp/fp2.json | head -c 400

echo ""
echo "=== 3. draft/list (for drafts) ==="
curl -sS --max-time 15 "https://api.weixin.qq.com/cgi-bin/draft/list?access_token=${TOKEN}&offset=0&count=20" -w " HTTP:%{http_code}\n" -o /tmp/draft1.json
cat /tmp/draft1.json | head -c 400

echo ""
echo "=== 4. material/get_material_list (news) ==="
curl -sS --max-time 15 "https://api.weixin.qq.com/cgi-bin/material/get_material_list?access_token=${TOKEN}&type=news&offset=0&count=20" -w " HTTP:%{http_code}\n" -o /tmp/mat1.json
cat /tmp/mat1.json | head -c 400

echo ""
echo "=== 5. datacube/getarticletotal (interface api) ==="
curl -sS --max-time 15 "https://api.weixin.qq.com/datacube/getarticletotal?access_token=${TOKEN}" -X POST -H "Content-Type: application/json" -d '{"begin_date":"2025-01-01","end_date":"2026-06-10"}' -w " HTTP:%{http_code}\n" -o /tmp/dc1.json
cat /tmp/dc1.json | head -c 400
