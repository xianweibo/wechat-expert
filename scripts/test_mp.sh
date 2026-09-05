#!/bin/bash
set -e
SECRET="${BILIBILI_WORKER_SECRET:?need BILIBILI_WORKER_SECRET in env}"
APP="http://127.0.0.1:39800"

echo "=== 1) /api/v2/heartbeat ==="
curl -s "$APP/api/v2/heartbeat"
echo
echo
echo "=== 2) /api/admin/mp-published (empty body) ==="
curl -s -X POST "$APP/api/admin/mp-published" \
  -H "X-Worker-Secret: $SECRET" \
  -H "Content-Type: application/json" \
  --data '{}'
echo
echo
echo "=== 3) /api/admin/mp-appmsg-list (type=news, count=1) ==="
curl -s -X POST "$APP/api/admin/mp-appmsg-list" \
  -H "X-Worker-Secret: $SECRET" \
  -H "Content-Type: application/json" \
  --data '{"begin":0,"count":1,"type":"news"}'
echo
echo
echo "=== 4) /api/admin/mp-appmsg-list (no type) ==="
curl -s -X POST "$APP/api/admin/mp-appmsg-list" \
  -H "X-Worker-Secret: $SECRET" \
  -H "Content-Type: application/json" \
  --data '{"begin":0,"count":1}'
echo
echo
echo "=== 5) Direct WeChat token from container ==="
CONTAINER=$(docker ps --filter name=gzh-expert-app -q | head -n1)
echo "container=$CONTAINER"
docker exec "$CONTAINER" sh -c 'curl -s "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid='"'"'$(printenv WECHAT_APP_ID)'"'"'&secret='"'"'$(printenv WECHAT_APP_SECRET)'"'"'"'
echo
echo
echo "=== 6) Direct appmsg/list (older endpoint) from container ==="
docker exec "$CONTAINER" sh -c 'TOKEN=$(curl -s "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid='"'"'$(printenv WECHAT_APP_ID)'"'"'&secret='"'"'$(printenv WECHAT_APP_SECRET)'"'"'" | python3 -c "import sys,json;print(json.load(sys.stdin).get(\"access_token\",\"\"))"); echo "token=$TOKEN"; curl -s "https://api.weixin.qq.com/cgi-bin/appmsg/list?access_token=$TOKEN&begin=0&count=1&type=news"'
echo
