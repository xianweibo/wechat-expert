#!/bin/sh
# Verify player/v2 API (subtitles + login_mid)
sleep 2.5
wget -qO- \
  --header="User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  --header="Referer: https://www.bilibili.com/" \
  --header="Cookie: SESSDATA=${BILIBILI_SESSDATA}; bili_jct=${BILIBILI_BILI_JCT}" \
  "https://api.bilibili.com/x/player/v2?bvid=BV1rmtT6hENL&cid=41479769266"
