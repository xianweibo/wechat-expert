#!/bin/bash
APP_ID="wx567a639466e247cd"
APP_SECRET="fc7252e95b7d8dae7027b9a87874f00a"
CONTAINER=$(docker ps --filter name=gzh-expert-app -q | head -n1)
TOKEN=$(docker exec "$CONTAINER" wget -qO- "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=${APP_ID}&secret=${APP_SECRET}" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("access_token",""))')
echo "token=${TOKEN:0:20}..."
echo

echo "=== 0,5 ==="
docker exec "$CONTAINER" wget -qO- --header='Content-Type: application/json' --post-data='{"offset":0,"count":5,"no_content":0}' "https://api.weixin.qq.com/cgi-bin/draft/batchget?access_token=${TOKEN}" > /tmp/r0.json
head -c 200 /tmp/r0.json
echo
echo
echo "size:"
ls -la /tmp/r0.json
python3 -c 'import json; d=json.load(open("/tmp/r0.json")); print("keys=", list(d.keys())); print("item_count=", d.get("item_count")); print("total_count=", d.get("total_count")); il=d.get("item_list"); print("item_list type=", type(il), "len=", len(il) if il else "None")'
