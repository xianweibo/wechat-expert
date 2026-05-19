#!/bin/bash
set -e

TOKEN="104_IvfqoCQYjtdYnMiGAWRZamRuelEM74N4AMjMzAQfBuV0D4gSazWAuno6hwFT9V2P3TCPIz-TqU7jZDEM7u0ync9GupUxDPGwrcEaTwlHnohLOKko4ydzCdQdFkMMTDfADADKU"

echo "=== 1. 上传封面图 ==="
# 用 convert (ImageMagick) 生成测试图
if command -v convert &>/dev/null; then
    convert -size 200x200 xc:blue /tmp/cover.jpg
elif command -v python3 &>/dev/null; then
    python3 -c "
import struct, zlib
# Minimal valid JPEG
SOI = b'\xff\xd8'
APP0 = b'\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
DQT = b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x0c\x0b\x0c\x0c\x0f\x0f\x0f\x0c\x0f\x0f\x0f\x0c\x0e\x0f\x0f\x0e\x0c\x0e\x0e\x0e\x0c\x11\x10\x0f\x10\x11\x10\x0e\x0f\x0f\x0e\x0f\x11\x12\x11\x10\x0f\x10\x10\x10'
SOF0 = b'\xff\xc0\x00\x0b\x08\x00\xc8\x00\xc8\x01\x01\x11\x00'
DHT = b'\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b'
SOS = b'\xff\xda\x00\x08\x01\x01\x00\x00?\x00\x02\x00\x00\x00\x3f\x00'
EOI = b'\xff\xd9'
with open('/tmp/cover.jpg', 'wb') as f:
    f.write(SOI + APP0 + DQT + SOF0 + DHT + SOS + b'\x00' * 50 + EOI)
"
else
    printf '\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x0c\x0b\x0c\x0c\x0f\x0f\x0f\x0c\x0f\x0f\x0f\x0c\x0e\x0f\x0f\x0e\x0c\x0e\x0e\x0e\x0c\x11\x10\x0f\x10\x11\x10\x0e\x0f\x0f\x0e\x0f\x11\x12\x11\x10\x0f\x10\x10\x10\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc0\x00\x0b\x08\x00\xc8\x00\xc8\x01\x01\x11\x00\xff\xda\x00\x08\x01\x01\x00\x00?\x00\x02\x00\x00\x00\x3f\x00' > /tmp/cover.jpg
fi
ls -la /tmp/cover.jpg

echo ""
echo "=== 2. 上传素材 ==="
UPLOAD_RESP=$(curl -s -X POST "https://api.weixin.qq.com/cgi-bin/material/add_material?access_token=${TOKEN}&type=image" -F "media=@/tmp/cover.jpg;filename=cover.jpg;type=image/jpeg")
echo "上传响应: ${UPLOAD_RESP}"
MEDIA_ID=$(echo "${UPLOAD_RESP}" | grep -o '"media_id":"[^"]*"' | cut -d'"' -f4)
echo "media_id: ${MEDIA_ID}"

if [ -z "${MEDIA_ID}" ]; then
    echo "上传失败，退出"
    echo "完整响应: ${UPLOAD_RESP}"
    exit 1
fi

echo ""
echo "=== 3. 创建草稿 ==="
curl -s -X POST "https://api.weixin.qq.com/cgi-bin/draft/add?access_token=${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"articles\":[{\"title\":\"测试文章-公众号专家\",\"author\":\"公众号专家\",\"digest\":\"测试摘要\",\"content\":\"<p>这是一篇测试文章，用于验证公众号草稿API是否正常工作。</p><p>公众号专家 - 每日财经观察与量化样本学习工具</p>\",\"thumb_media_id\":\"${MEDIA_ID}\",\"need_open_comment\":1,\"only_fans_can_comment\":0}]}"

echo ""
echo "=== 完成 ==="