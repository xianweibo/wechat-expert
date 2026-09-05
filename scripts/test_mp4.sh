#!/bin/bash
set -e
APP_ID="wx567a639466e247cd"
APP_SECRET="${WECHAT_APP_SECRET:?need WECHAT_APP_SECRET in env}"
CONTAINER=$(docker ps --filter name=gzh-expert-app -q | head -n1)
TOKEN=$(docker exec "$CONTAINER" wget -qO- "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=${APP_ID}&secret=${APP_SECRET}" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("access_token",""))')
echo "token=${TOKEN:0:20}..."
echo
echo "=== 1) getapi_access_token (basic info) ==="
docker exec "$CONTAINER" wget -qO- "https://api.weixin.qq.com/cgi-bin/get_current_selfmenu_info?access_token=${TOKEN}"
echo
echo
echo "=== 2) customservice/getkflist (basic service account test) ==="
docker exec "$CONTAINER" wget -qO- "https://api.weixin.qq.com/cgi-bin/customservice/getkflist?access_token=${TOKEN}"
echo
echo
echo "=== 3) user/info (basic user API) ==="
docker exec "$CONTAINER" wget -qO- "https://api.weixin.qq.com/cgi-bin/user/info?access_token=${TOKEN}&openid=test&lang=zh_CN"
echo
echo
echo "=== 4) /cgi-bin/menu/get (custom menu - service account feature) ==="
docker exec "$CONTAINER" wget -qO- "https://api.weixin.qq.com/cgi-bin/menu/get?access_token=${TOKEN}"
echo
echo
echo "=== 5) /cgi-bin/groups/getid (user groups - service account) ==="
docker exec "$CONTAINER" wget -qO- --header='Content-Type: application/json' --post-data='{"openid":"test"}' "https://api.weixin.qq.com/cgi-bin/groups/getid?access_token=${TOKEN}"
echo
echo
echo "=== 6) /wxa/... is mini-program, skip ==="
echo
echo "=== 7) Test full account type: /cgi-bin/message/mass/sendall (subscription service only) ==="
docker exec "$CONTAINER" wget -qO- "https://api.weixin.qq.com/cgi-bin/message/mass/sendall?access_token=${TOKEN}"
echo
