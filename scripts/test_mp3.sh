#!/bin/bash
set -e
APP_ID="wx567a639466e247cd"
APP_SECRET="fc7252e95b7d8dae7027b9a87874f00a"
CONTAINER=$(docker ps --filter name=gzh-expert-app -q | head -n1)
TOKEN=$(docker exec "$CONTAINER" wget -qO- "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=${APP_ID}&secret=${APP_SECRET}" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("access_token",""))')
echo "token=${TOKEN:0:20}..."
echo
echo "=== 1) freepublish/get (single) ==="
docker exec "$CONTAINER" wget -qO- "https://api.weixin.qq.com/cgi-bin/freepublish/get?access_token=${TOKEN}&publish_id=test"
echo
echo
echo "=== 2) freepublish/getarticle ==="
docker exec "$CONTAINER" wget -qO- --header='Content-Type: application/json' --post-data='{"article_id":"test"}' "https://api.weixin.qq.com/cgi-bin/freepublish/getarticle?access_token=${TOKEN}"
echo
echo
echo "=== 3) material/list_material type=news ==="
docker exec "$CONTAINER" wget -qO- --header='Content-Type: application/json' --post-data='{"type":"news","offset":0,"count":5}' "https://api.weixin.qq.com/cgi-bin/material/list_material?access_token=${TOKEN}"
echo
echo
echo "=== 4) draft/list ==="
docker exec "$CONTAINER" wget -qO- --header='Content-Type: application/json' --post-data='{"offset":0,"count":5,"no_content":1}' "https://api.weixin.qq.com/cgi-bin/draft/list?access_token=${TOKEN}"
echo
echo
echo "=== 5) dataperm/check (test account permissions) ==="
docker exec "$CONTAINER" wget -qO- "https://api.weixin.qq.com/dataperm/check?access_token=${TOKEN}&appid=${APP_ID}&secret=${APP_SECRET}"
echo
echo
echo "=== 6) /cgi-bin/account/accountlist ==="
docker exec "$CONTAINER" wget -qO- "https://api.weixin.qq.com/cgi-bin/account/accountlist?access_token=${TOKEN}"
echo
