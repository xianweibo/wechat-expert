#!/bin/bash
set -e
APP_ID="wx567a639466e247cd"
APP_SECRET="fc7252e95b7d8dae7027b9a87874f00a"
CONTAINER=$(docker ps --filter name=gzh-expert-app -q | head -n1)
echo "container=$CONTAINER"
echo
echo "=== A) token via wget ==="
TOKEN_JSON=$(docker exec "$CONTAINER" wget -qO- "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=${APP_ID}&secret=${APP_SECRET}")
echo "$TOKEN_JSON"
TOKEN=$(echo "$TOKEN_JSON" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("access_token",""))')
echo
echo "token=$TOKEN"
echo
echo "=== B) freepublish/list via wget (POST) ==="
docker exec "$CONTAINER" wget -qO- --header='Content-Type: application/json' --post-data='{"offset":0,"count":5,"no_content":1}' "https://api.weixin.qq.com/cgi-bin/freepublish/list?access_token=${TOKEN}"
echo
echo
echo "=== C) appmsg/list via wget (GET) ==="
docker exec "$CONTAINER" wget -qO- "https://api.weixin.qq.com/cgi-bin/appmsg/list?access_token=${TOKEN}&begin=0&count=1&type=1"
echo
echo
echo "=== D) /cgi-bin/material/get_materialinfo (verify service account) ==="
docker exec "$CONTAINER" wget -qO- "https://api.weixin.qq.com/cgi-bin/getcallbackip?access_token=${TOKEN}"
echo
