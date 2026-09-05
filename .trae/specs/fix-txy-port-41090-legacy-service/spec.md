# 修复腾讯云 41090 端口被旧服务占用 Spec

## Why

yuanbao 调用 `127.0.0.1:41090` 时，被腾讯云上的**旧 Python 服务** `/root/gzh-txh-api-v2/server.py`（pid=4064805）拦截，该服务是直调模式（直接调阿里云 mp_proxy + MiniMax anime 风格封面），**完全没有走 STCP visitor 转发到 NAS**。NAS 上已配置好的 ModelScope 魔搭封面（财经媒体风格）根本没被调用，导致用户反复看到 anime 风格封面。

## 证据链

1. 腾讯云 41090 端口被 `python pid=4064805` 监听（不是 frpc STCP visitor）
2. STCP visitor 容器 `gzh-txh-frpc-visitor` **不存在**（`docker ps --filter name=gzh-txh-frpc-visitor` 返回空）
3. 腾讯云上的旧 server.py 在 `/root/gzh-txh-api-v2/`，用 `python-requests/2.34.2` 直调阿里云 mp_proxy
4. 阿里云日志显示源 IP `159.75.44.211`（腾讯云）+ `python-requests/2.34.2`，而非 NAS 的 `27.47.10.14` + `Python-urllib/3.11`
5. NAS 最新 server.py（含 ModelScope 集成）最后活动是 23 小时前，今天 yuanbao 的调用没到达 NAS

## What Changes

- **停止腾讯云上的旧 Python 服务** `/root/gzh-txh-api-v2/server.py`（pid=4064805）
- **禁用其开机自启**（如果有 systemd service 或 cron 条目）
- **部署真正的 STCP visitor 容器** `gzh-txh-frpc-visitor`，把腾讯云 127.0.0.1:41090 → NAS 41090
- **验证 yuanbao 调用链路**：yuanbao → 腾讯云 41090 → STCP visitor → NAS 41090 → NAS server.py（ModelScope 魔搭封面）

## Impact

- Affected code: 腾讯云 `/root/gzh-txh-api-v2/server.py`（停止运行）
- Affected flow: yuanbao → 127.0.0.1:41090 → NAS 41090（恢复 STCP 转发）
- 不影响：NAS server.py（已配置好 ModelScope）、阿里云 mp_proxy、yuanbao 的 SKILL 文档

## 访问腾讯云的方式

沙箱无法直连腾讯云（159.75.44.211），需要通过阿里云跳板：
- 沙箱 → `ssh aliyun-gzh` → 阿里云
- 阿里云 → `ssh -i ~/.ssh/id_ed25519_nas ubuntu@159.75.44.211` → 腾讯云

注意：阿里云上的 `~/.ssh/id_ed25519` 不能连腾讯云，需要用沙箱本地的 `C:\Users\Administrator\.ssh\id_ed25519_nas`（通过 `ssh -J aliyun-gzh` ProxyJump 方式）。

## ADDED Requirements

### Requirement: 腾讯云 41090 端口走 STCP visitor

腾讯云 41090 端口 SHALL 由 STCP visitor 容器（frpc）监听，通过 STCP 隧道转发到 NAS 41090，而不是被本地 Python 服务占用。

#### Scenario: yuanbao 调用走 NAS

- **WHEN** yuanbao 调用 `http://127.0.0.1:41090/api/gzh/draft`
- **THEN** 请求通过 STCP visitor 转发到 NAS 41090
- **AND** NAS 的 server.py 处理请求（含 ModelScope 魔搭封面）
- **AND** 阿里云 mp_proxy 日志显示源 IP 为 NAS 出口 IP（27.47.10.14）+ `Python-urllib/3.11`

### Requirement: 旧 Python 服务停止

腾讯云上的 `/root/gzh-txh-api-v2/server.py` SHALL 被停止，且不再自动启动。

#### Scenario: 旧服务已停止

- **WHEN** 检查腾讯云上 41090 端口监听
- **THEN** 监听进程是 frpc（STCP visitor），不是 python
- **AND** `/root/gzh-txh-api-v2/server.py` 进程不存在

## MODIFIED Requirements

### Requirement: STCP visitor 容器部署

在腾讯云上部署 `gzh-txh-frpc-visitor` 容器，配置 STCP visitor 把 127.0.0.1:41090 → NAS gzh-txh-bvid-form（41090）。

配置文件（frp v0.68.1，用 `bindAddr`/`bindPort`）：
```toml
serverAddr = "127.0.0.1"
serverPort = 37000
auth.token = "StockAgent_2025_Token"

[[visitors]]
name = "gzh-txh-bvid-form-visitor"
type = "stcp"
serverName = "gzh-txh-bvid-form"
secretKey = "gzh-txh-bvid-form-sk-2026"
bindAddr = "127.0.0.1"
bindPort = 41090
```

容器运行参数：
```
docker run -d --name gzh-txh-frpc-visitor --restart=unless-stopped --network host -v /opt/docker_related/gzh-txy-visitor/frpc.toml:/etc/frp/frpc.toml snowdreamtech/frpc:latest
```
