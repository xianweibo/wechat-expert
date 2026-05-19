#!/bin/bash
set -e

APP_ID="wx567a639466e247cd"
APP_SECRET_FILE="/tmp/.mp_app_secret"
DRAFT_JSON="/tmp/draft-test.json"

if [ ! -f "${APP_SECRET_FILE}" ]; then
    echo "错误: 请先创建密钥文件: echo '你的AppSecret' > ${APP_SECRET_FILE}"
    exit 1
fi

APP_SECRET=$(cat "${APP_SECRET_FILE}")

echo "=== 1. 获取 Access Token ==="
TOKEN_RESP=$(curl -s "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=${APP_ID}&secret=${APP_SECRET}")
echo "响应: ${TOKEN_RESP}"
TOKEN=$(echo "${TOKEN_RESP}" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
echo "Token: ${TOKEN}"

if [ -z "${TOKEN}" ]; then
    echo "获取Token失败，退出"
    exit 1
fi

echo ""
echo "=== 2. 创建草稿 ==="
DRAFT_RESP=$(curl -s -X POST "https://api.weixin.qq.com/cgi-bin/draft/add?access_token=${TOKEN}" \
    -H "Content-Type: application/json" \
    -d @${DRAFT_JSON})
echo "响应: ${DRAFT_RESP}"

echo ""
echo "=== 测试完成 ==="