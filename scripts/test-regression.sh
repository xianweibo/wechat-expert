#!/bin/bash
set -a
source /vol2/1000/docker_related/gzh-worker/.env
set +a
export YUTTO_AUTH="SESSDATA=${BILIBILI_SESSDATA};bili_jct=${BILIBILI_BILI_JCT}"
cd /tmp
sudo docker run --rm -v /tmp:/data siguremo/yutto --auth "$YUTTO_AUTH" --subtitle-only https://space.bilibili.com/290663424 -d /data -b 2>&1 | tail -30
