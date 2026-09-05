# Tasks

- [x] Task 1: 停止腾讯云上的旧 Python 服务
  - [x] 1.1 通过阿里云跳板 SSH 到腾讯云，找到 `/root/gzh-txh-api-v2/server.py` 进程（pid=4064805）
  - [x] 1.2 停止该进程（`sudo kill 4064805`，pkill -f 匹配失败因命令行是相对路径）
  - [x] 1.3 检查是否有 systemd service 或 cron 条目（无任何自启动机制，手动 nohup 启动）
  - [x] 1.4 验证 41090 端口已释放（`ss -tlnp | grep 41090` 返回空）

- [x] Task 2: 部署 STCP visitor 容器
  - [x] 2.1 在腾讯云创建配置文件 `/opt/docker_related/gzh-txy-visitor/frpc.toml`（STCP visitor，41090 → NAS gzh-txh-bvid-form）
  - [x] 2.2 启动 `gzh-txh-frpc-visitor` 容器（`--restart=unless-stopped --network host`）
  - [x] 2.3 验证容器运行状态（Up 44 seconds）
  - [x] 2.4 验证 41090 端口被 frpc 监听（`ss -tlnp | grep 41090` 显示 `frpc pid=514243`）

- [x] Task 3: 端到端验证 yuanbao 调用走 NAS
  - [x] 3.1 在腾讯云本机 curl `/health`，返回含 `modelscope_configured: true`（NAS 响应）
  - [x] 3.2 在腾讯云本机 curl `/api/gzh/draft` 传 BV1y73W6MEEk，封面 URL 为 `modelscope-studios.oss-cn-zhangjiakou.aliyuncs.com`（魔搭 OSS）
  - [x] 3.3 检查 NAS 容器日志，确认 `[cover] modelscope ok`（时间戳 16:57-16:58，刚发生）
  - [x] 3.4 检查阿里云 mp_proxy 日志，源 IP 是 NAS（27.47.10.14, Python-urllib/3.11），不是腾讯云

- [x] Task 4: 清理临时 STCP visitor（阿里云上的）
  - [x] 4.1 停止并删除阿里云上的临时 `frpc-nas-visitor` 容器
  - [x] 4.2 删除临时配置文件 `/tmp/frpc-nas-visitor.toml`

# Task Dependencies

- Task 2 依赖 Task 1（41090 端口必须先释放）
- Task 3 依赖 Task 2
- Task 4 依赖 Task 3
