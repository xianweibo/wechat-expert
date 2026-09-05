# Tasks

- [x] Task 1: 在阿里云上启动 STCP visitor 访问 NAS SSH
  - [x] 1.1 在阿里云上创建 frpc visitor 配置文件（连接腾讯云 frps 159.75.44.211:37000，访问 NAS gzh-txh-ssh，本地映射 41022）
  - [x] 1.2 用 `snowdreamtech/frpc:latest` 镜像启动临时 frpc 容器
  - [x] 1.3 验证 `ssh -p 41022 paulproject@127.0.0.1` 能连上 NAS（从阿里云执行）

- [x] Task 2: 检查并更新 NAS server.py
  - [x] 2.1 通过 STCP visitor SSH 到 NAS，检查 `/vol2/1000/docker_related/gzh-txh-api/server.py` 是否含 `modelscope_cover_image`（grep 返回 2 次匹配，已是最新版）
  - [x] 2.2 如不是最新版，通过 SCP（经 STCP visitor）把本地最新 `gzh-txh-api/server.py` 传到 NAS（跳过，已是最新版）

- [x] Task 3: 更新 NAS .env 并重启容器
  - [x] 3.1 在 NAS `/vol2/1000/docker_related/gzh-txh-api/.env` 确认 `MoTa_API_KEY=ms-afb56c75-90a2-4585-b04f-0e77ee379fff`（已存在）
  - [x] 3.2 追加 `MOTASCOPE_MODEL=Tongyi-MAI/Z-Image-Turbo`（原本缺失，已追加）
  - [x] 3.3 `sudo docker compose -f docker-compose.yml up -d --force-recreate`（容器已 Recreated → Started）
  - [x] 3.4 验证 `docker exec gzh-txh-api env` 输出含 `MoTa_API_KEY=ms-...` 和 `MOTASCOPE_MODEL=Tongyi-MAI/Z-Image-Turbo`
  - [x] 3.5 验证 `curl -s http://127.0.0.1:41090/health` 返回 `{"ok": true, "modelscope_configured": true}`

- [x] Task 4: 端到端验证封面走魔搭
  - [x] 4.1 从 NAS 本机 curl 41090，传入 BVID `BV1y73W6MEEk` 测试
  - [x] 4.2 查看容器日志，确认含 `[cover] modelscope ok`（未回退 MiniMax）
  - [x] 4.3 封面 URL 为 `modelscope-studios.oss-cn-zhangjiakou.aliyuncs.com`（魔搭 OSS，非 MiniMax）
  - [x] 4.4 端到端耗时 39.9 秒，魔搭出图约 11 秒（poll#2 SUCCEED）

- [x] Task 5: 清理 STCP visitor 临时容器
  - [x] 5.1 停止并删除阿里云上的 `frpc-nas-visitor` 容器
  - [x] 5.2 删除临时文件 `/tmp/frpc-nas-visitor.toml`、`/tmp/env_append.txt`、`/tmp/test_draft.sh`

# Task Dependencies

- Task 2、Task 3 依赖 Task 1（需要 STCP visitor 才能访问 NAS）
- Task 4 依赖 Task 2、Task 3
- Task 5 依赖 Task 4
