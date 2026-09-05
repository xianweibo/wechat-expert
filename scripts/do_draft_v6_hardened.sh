#!/usr/bin/env bash
# do_draft_v6_hardened.sh
#
# Demo：未来 do_draft_vN.sh 的推荐模板
# 引入 scripts/draft_helpers.write_draft，自动 normalize_quotes，
# 并在 json.dumps 之前本地 json.loads 自检，避免打到 mp_proxy 才 400。
#
# 用法：
#   1. 复制本文件为 do_draft_vN.sh
#   2. 替换 TITLE / TOP / BODY / FOOT / DIGEST / THUMB_MEDIA_ID
#   3. ./do_draft_vN.sh

set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"

DRAFT_HELPERS_DIR="$HERE" python3 << 'PYEOF'
import os
import sys
sys.path.insert(0, os.environ["DRAFT_HELPERS_DIR"])

from draft_helpers import write_draft

TITLE = "SpaceX 上市：一场靠神话支撑的万亿美元 IPO"
AUTHOR = "小喇叭大只讲"

TOP = (
  "<p>内容不作为投资建议，注意风险。<br/>"
  "都是历史数据，仅作为学习。<br/>"
  "独立学者：<br/>"
  "没想到啊，我才没休息几天又可以玩了。</p>"
  "<hr/>"
)
BODY = (
  "<h2>SpaceX 上市：一场靠神话支撑的万亿美元 IPO</h2>"
  "<h3>一、135 美元一股，马斯克主动定</h3>"
  "<p>这次 SpaceX IPO 最反常的地方是定价方式。...</p>"
)
FOOT = (
  "<hr/>"
  "<p>=======</p>"
  "<p>以下不是建议<br/>"
  "只是根据历史数据,量化模式回测<br/>"
  "都是历史数据和我本人的记录，不作为建议荐股！！！<br/>"
  "每天都更新，仅供学习</p>"
  "<p>=======</p>"
)

THUMB_MEDIA_ID = "bRcX-a6nPWS8NtJrTuhJbHLnxDAx-a6P97m4JCY8C5932I0jtrAVWaSGTJbRb5Qk"
DIGEST = "SpaceX 上市 135 美元主动定价、1.77 万亿估值是收入 100 倍..."

draft = {
  "title": TITLE,
  "author": AUTHOR,
  "content": TOP + BODY + FOOT,
  "thumb_media_id": THUMB_MEDIA_ID,
  "digest": DIGEST,
  "need_open_comment": 1,
  "only_fans_can_comment": 0,
}

out_path = "/tmp/draft_v6.json"
n = write_draft(draft, out_path)
print(f"saved {n} bytes -> {out_path}")
PYEOF

echo "=== send ==="
curl -sS --max-time 60 -X POST http://127.0.0.1:39800/api/admin/mp-draft-add \
  -H 'Content-Type: application/json' \
  -H 'X-Worker-Secret: cBsFHdghYA1W07VpultIKEynOSQwNM8z' \
  --data-binary @/tmp/draft_v6.json \
  -o /tmp/draft_v6_resp.json \
  -w 'HTTP %{http_code} size %{size_download}B\n'
cat /tmp/draft_v6_resp.json