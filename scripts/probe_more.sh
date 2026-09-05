#!/bin/bash
set -e
APP_ID="wx567a639466e247cd"
APP_SECRET="fc7252e95b7d8dae7027b9a87874f00a"
CONTAINER=$(docker ps --filter name=gzh-expert-app -q | head -n1)
echo "container=$CONTAINER"
TOKEN=$(docker exec "$CONTAINER" wget -qO- "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=${APP_ID}&secret=${APP_SECRET}" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("access_token",""))')
echo "token=${TOKEN:0:20}..."
echo
echo "=== A) datacube/getarticletotal (2025-01-01 ~ 2026-06-13) ==="
docker exec "$CONTAINER" wget -qO- --header='Content-Type: application/json' --post-data='{"begin_date":"2025-01-01","end_date":"2026-06-13"}' "https://api.weixin.qq.com/datacube/getarticletotal?access_token=${TOKEN}"
echo
echo
echo "=== B) /cgi-bin/message/mass/list ==="
docker exec "$CONTAINER" wget -qO- --header='Content-Type: application/json' --post-data='{}' "https://api.weixin.qq.com/cgi-bin/message/mass/list?access_token=${TOKEN}"
echo
echo
echo "=== C) dataperm/getapilistperms ==="
docker exec "$CONTAINER" wget -qO- --header='Content-Type: application/json' --post-data='{}' "https://api.weixin.qq.com/dataperm/getapilistperms?access_token=${TOKEN}"
echo
echo
echo "=== D) /cgi-bin/account/getaccountbasicinfo ==="
docker exec "$CONTAINER" wget -qO- "https://api.weixin.qq.com/cgi-bin/account/getaccountbasicinfo?access_token=${TOKEN}"
echo
echo
echo "=== E) /cgi-bin/account/getaccountbindlist (类型/认证状态) ==="
docker exec "$CONTAINER" wget -qO- "https://api.weixin.qq.com/cgi-bin/account/getaccountbindlist?access_token=${TOKEN}"
echo
echo
echo "=== F) /cgi-bin/message/mass/get (last mass msg) ==="
docker exec "$CONTAINER" wget -qO- --header='Content-Type: application/json' --post-data='{"msg_id":1}' "https://api.weixin.qq.com/cgi-bin/message/mass/get?access_token=${TOKEN}"
echo
echo
echo "=== G) /cgi-bin/material/get_materialcount ==="
docker exec "$CONTAINER" wget -qO- --header='Content-Type: application/json' --post-data='{}' "https://api.weixin.qq.com/cgi-bin/material/get_materialcount?access_token=${TOKEN}"
echo
