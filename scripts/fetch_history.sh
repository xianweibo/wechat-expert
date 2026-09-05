#!/bin/bash
# Fetch WeChat MP history articles
set -e

APP_ID="wx567a639466e247cd"
APP_SECRET="${WECHAT_APP_SECRET:?need WECHAT_APP_SECRET in env}"

# Get access token
echo "[1/3] Get access token..."
TOKEN=$(curl -sS "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=${APP_ID}&secret=${APP_SECRET}" | python3 -c "import json,sys; print(json.loads(sys.stdin.read()).get('access_token',''))")
if [ -z "$TOKEN" ]; then
  echo "Failed to get access token"
  exit 1
fi
echo "    TOKEN=${TOKEN:0:20}..."

# Fetch free publish list
echo "[2/3] Fetch free publish list..."
curl -sS --max-time 30 "https://api.weixin.qq.com/cgi-bin/freepublish/list?access_token=${TOKEN}&offset=0&count=20" -o /tmp/freepublish.json
echo "    File: $(ls -la /tmp/freepublish.json | awk '{print $5}') bytes"

# Fetch draft list (if any)
echo "[3/3] Fetch draft list..."
curl -sS --max-time 30 "https://api.weixin.qq.com/cgi-bin/draft/count?access_token=${TOKEN}" -o /tmp/draft_count.json
echo "    Draft count: $(cat /tmp/draft_count.json)"

echo ""
echo "=== freepublish.json head ==="
head -c 800 /tmp/freepublish.json
echo ""
echo "=== END ==="
