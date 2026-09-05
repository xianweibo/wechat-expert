#!/bin/bash
# Deploy gzh-chroma vector DB container on Aliyun
set -e

ALIYUN_DATA="/home/gongzhonghao/apps/gzh-chroma"
mkdir -p "$ALIYUN_DATA"

# Use a minimal chromadb container with persistent volume
docker stop gzh-chroma 2>/dev/null || true
docker rm gzh-chroma 2>/dev/null || true

docker run -d \
  --name gzh-chroma \
  --restart unless-stopped \
  -p 8100:8000 \
  -v "$ALIYUN_DATA:/chroma/chroma" \
  -e IS_PERSISTED=TRUE \
  -e PERSIST_DIRECTORY=/chroma/chroma \
  -e ANONYMIZED_TELEMETRY=False \
  chromadb/chroma:latest

echo "gzh-chroma container started"
docker ps | grep gzh-chroma
echo ""
echo "Test connection..."
sleep 3
curl -sS http://127.0.0.1:8100/api/v1/heartbeat
echo ""
echo "API: http://127.0.0.1:8100"
