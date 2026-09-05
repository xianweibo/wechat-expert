#!/bin/bash
APP_ID="wx567a639466e247cd"
APP_SECRET="fc7252e95b7d8dae7027b9a87874f00a"
CONTAINER=$(docker ps --filter name=gzh-expert-app -q | head -n1)
echo "container=$CONTAINER"
TOKEN=$(docker exec "$CONTAINER" wget -qO- "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=${APP_ID}&secret=${APP_SECRET}" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("access_token",""))')
echo "token=${TOKEN:0:20}..."
echo

run() {
    local label="$1"
    local method="$2"
    local url="$3"
    local data="$4"
    echo "=== $label ==="
    if [ "$method" = "GET" ]; then
        docker exec "$CONTAINER" wget -qO- "${url}${data:+?$data}" 2>/dev/null || true
    else
        docker exec "$CONTAINER" wget -qO- --header='Content-Type: application/json' --post-data="$data" "$url" 2>/dev/null || true
    fi
    echo
    echo
}

run "D) /cgi-bin/account/getaccountbasicinfo (GET)" GET "https://api.weixin.qq.com/cgi-bin/account/getaccountbasicinfo?access_token=${TOKEN}"
run "E) /cgi-bin/account/getaccountbindlist (GET)" GET "https://api.weixin.qq.com/cgi-bin/account/getaccountbindlist?access_token=${TOKEN}"
run "F) /cgi-bin/message/mass/get" POST "https://api.weixin.qq.com/cgi-bin/message/mass/get?access_token=${TOKEN}" '{"msg_id":1}'
run "G) /cgi-bin/material/get_materialcount" POST "https://api.weixin.qq.com/cgi-bin/material/get_materialcount?access_token=${TOKEN}" '{}'
run "H) /cgi-bin/material/batchget_material" POST "https://api.weixin.qq.com/cgi-bin/material/batchget_material?access_token=${TOKEN}" '{"type":"news","offset":0,"count":5}'
run "I) /cgi-bin/freepublish/batchget" POST "https://api.weixin.qq.com/cgi-bin/freepublish/batchget?access_token=${TOKEN}" '{"offset":0,"count":5,"no_content":0}'
run "J) /cgi-bin/draft/batchget" POST "https://api.weixin.qq.com/cgi-bin/draft/batchget?access_token=${TOKEN}" '{"offset":0,"count":5,"no_content":0}'
run "K) /cgi-bin/openapi/rid/get" POST "https://api.weixin.qq.com/cgi-bin/openapi/rid/get?access_token=${TOKEN}" '{"rid":"6a2c31b4-7e7db463-77e568bc","openid":"","limit":5}'
